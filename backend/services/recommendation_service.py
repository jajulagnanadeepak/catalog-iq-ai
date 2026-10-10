
"""
RecommendationService — deterministic personalized recommendations.

Features:
- MongoDB product catalog
- Query/category/tag relevance
- Session intent
- Rating and popularity scoring
- Optional budget filtering
- Deterministic explanations
"""

import re
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from models.product import Product


class RecommendationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["products"]

    async def get_recommendations(
        self,
        limit: int = 6,
        query: Optional[str] = None,
        max_price: Optional[float] = None,
        category: Optional[str] = None,
        session_intent: Optional[dict] = None,
        display_budget: Optional[float] = None,
        display_currency: str = "USD",
    ) -> list[dict]:

        mongo_query = {"in_stock": True}

        if max_price is not None:
            mongo_query["price"] = {"$lte": max_price}

        if category and category.lower() != "all":
            mongo_query["category"] = category

        docs = await self.collection.find(mongo_query).to_list(length=100)

        query_tokens = self._tokenize(query or "")
        query_category = self._query_category(query_tokens)

        primary_intent = None
        intent_confidence = 0.0

        if session_intent:
            primary_intent = session_intent.get("primary_category")
            try:
                intent_confidence = float(
                    session_intent.get("confidence", 0.0)
                )
            except (TypeError, ValueError):
                intent_confidence = 0.0

        scored_products = []

        for doc in docs:
            product = self._to_product(doc)

            # Respect the product category explicitly requested now.
            if query_category and not self._category_matches_intent(
                product.category, query_category
            ):
                continue

            # Exclude products that don't match descriptive query terms.
            if not self._matches_query_modifiers(
                product, query_tokens, query_category
            ):
                continue

            score = self._score_product(
                product=product,
                query_tokens=query_tokens,
                max_price=max_price,
                primary_intent=primary_intent,
                intent_confidence=intent_confidence,
            )

            scored_products.append((score, product))

        scored_products.sort(key=lambda item: item[0], reverse=True)

        recommendations = []

        for index, (score, product) in enumerate(
            scored_products[:max(1, limit)]
        ):
            recommendations.append(
                {
                    "id": f"r-{index}",
                    "title": "Recommended for you",
                    "reason": self._build_reason(
                        product=product,
                        query=query,
                        max_price=max_price,
                        primary_intent=primary_intent,
                        intent_confidence=intent_confidence,
                        display_budget=display_budget,
                        display_currency=display_currency,
                    ),
                    # Ranking score, not a calibrated probability.
                    "confidence": round(min(0.95, max(0.0, score)), 2),
                    "product": product.model_dump(by_alias=False),
                }
            )

        # Return [] if no products match, never None.
        return recommendations

    @classmethod
    def _matches_query_modifiers(
        cls,
        product: Product,
        query_tokens: set[str],
        query_category: Optional[str],
    ) -> bool:
        """Check descriptive terms against product details."""

        category_aliases = {
            "tops": {
                "top", "tops", "shirt", "shirts", "t-shirt",
                "tshirts", "tee", "tees", "polo", "blouse", "vest",
            },
            "outerwear": {
                "jacket", "jackets", "coat", "coats", "blazer", "outerwear",
            },
            "trousers": {
                "trouser", "trousers", "pant", "pants", "jean",
                "jeans", "chino", "shorts",
            },
            "footwear": {
                "shoe", "shoes", "sneaker", "sneakers", "boot",
                "boots", "sandal", "sandals", "footwear",
            },
            "bags": {"bag", "bags", "backpack", "handbag"},
            "swimwear": {"swimwear", "swimsuit", "bikini"},
            "knitwear": {"knitwear", "knit", "sweater", "sweaters"},
            "dresses": {"dress", "dresses"},
        }

        def normalize(token: str) -> str:
            token = token.lower()

            if len(token) > 4 and token.endswith("ies"):
                return token[:-3] + "y"

            if (
                len(token) > 3
                and token.endswith("s")
                and not token.endswith("ss")
            ):
                return token[:-1]

            return token

        category_terms = {
            normalize(term)
            for term in category_aliases.get(query_category, set())
        }

        modifiers = {
            normalize(token)
            for token in query_tokens
            if not token.isdigit()
        } - category_terms

        if not modifiers:
            return True

        product_text = " ".join(
            [
                product.name or "",
                product.brand or "",
                product.category or "",
                " ".join(product.tags or []),
                product.description or "",
                " ".join(product.colors or []),
            ]
        )

        product_tokens = {
            normalize(token)
            for token in re.findall(
                r"[a-zA-Z0-9]+", product_text.lower()
            )
        }

        return modifiers.issubset(product_tokens)

    def _score_product(
        self,
        product: Product,
        query_tokens: set[str],
        max_price: Optional[float],
        primary_intent: Optional[str],
        intent_confidence: float,
    ) -> float:
        """Score query relevance, session intent, quality, and budget."""

        def normalize_token(token: str) -> str:
            token = token.lower()

            if len(token) > 4 and token.endswith("ies"):
                return token[:-3] + "y"

            if (
                len(token) > 3
                and token.endswith("s")
                and not token.endswith("ss")
            ):
                return token[:-1]

            return token

        def tokens_from(text: str) -> set[str]:
            return {
                normalize_token(word)
                for word in re.findall(
                    r"[a-zA-Z0-9]+", text.lower()
                )
                if not word.isdigit()
            }

        name_tokens = tokens_from(product.name or "")
        tag_tokens = tokens_from(" ".join(product.tags or []))
        description_tokens = tokens_from(product.description or "")
        category_tokens = tokens_from(product.category or "")
        brand_tokens = tokens_from(product.brand or "")
        color_tokens = tokens_from(" ".join(product.colors or ""))

        searchable_tokens = (
            name_tokens
            | tag_tokens
            | description_tokens
            | category_tokens
            | brand_tokens
            | color_tokens
        )

        useful_query_tokens = {
            normalize_token(token)
            for token in query_tokens
            if not token.isdigit()
        }

        query_score = 0.0

        if useful_query_tokens:
            token_scores = []

            for token in useful_query_tokens:
                relevance = 0.0

                if token in name_tokens:
                    relevance = max(relevance, 1.0)

                if token in tag_tokens:
                    relevance = max(relevance, 0.95)

                if token in description_tokens:
                    relevance = max(relevance, 0.65)

                if token in category_tokens:
                    relevance = max(relevance, 0.50)

                if token in brand_tokens:
                    relevance = max(relevance, 0.30)

                if token in color_tokens:
                    relevance = max(relevance, 0.20)

                token_scores.append(relevance)

            query_score = sum(token_scores) / len(token_scores)

            if useful_query_tokens.issubset(searchable_tokens):
                query_score = min(1.0, query_score + 0.10)

        score = 0.60 * query_score

        # Session intent contributes without overpowering the current query.
        intent_score = 0.0

        if primary_intent and self._category_matches_intent(
            product.category, primary_intent
        ):
            intent_score = max(
                0.0, min(1.0, intent_confidence)
            )

        score += 0.15 * intent_score

        # Product rating: 10%.
        rating_score = (
            max(0.0, min(5.0, product.rating or 0)) / 5.0
        )
        score += 0.10 * rating_score

        # Popularity: 5%.
        reviews = max(0, product.reviews or 0)
        score += 0.05 * min(reviews / 500.0, 1.0)

        # Budget: 10%.
        if max_price is not None and max_price > 0:
            if product.price <= max_price:
                budget_score = 1.0 - (product.price / max_price)
                score += 0.10 * max(
                    0.0, min(1.0, budget_score)
                )
        else:
            score += 0.10

        return score

    @classmethod
    def _query_category(
        cls, query_tokens: set[str]
    ) -> Optional[str]:
        """Identify the category explicitly requested by the user."""

        aliases = {
            "tops": {
                "top", "tops", "shirt", "shirts", "tshirt",
                "tshirts", "tee", "tees", "polo", "blouse", "vest",
            },
            "outerwear": {
                "jacket", "jackets", "coat", "coats", "blazer",
            },
            "trousers": {
                "trouser", "trousers", "pant", "pants",
                "jean", "jeans", "chino", "shorts",
            },
            "footwear": {
                "shoe", "shoes", "sneaker", "sneakers",
                "boot", "boots", "sandal", "sandals",
            },
            "bags": {"bag", "bags", "backpack", "handbag"},
            "swimwear": {"swimwear", "swimsuit", "bikini"},
            "knitwear": {"knitwear", "knit", "sweater", "sweaters"},
            "dresses": {"dress", "dresses"},
        }

        for category_name, terms in aliases.items():
            if query_tokens.intersection(terms):
                return category_name

        return None

    @staticmethod
    def _category_matches_intent(
        product_category: Optional[str],
        intent_category: Optional[str],
    ) -> bool:
        if not product_category or not intent_category:
            return False

        product = product_category.lower().strip()
        intent = intent_category.lower().strip()

        aliases = {
            "tops": {
                "top", "tops", "shirt", "shirts", "t-shirt",
                "tshirts", "tee", "tees", "polo", "blouse", "vest",
            },
            "outerwear": {
                "outerwear", "jacket", "jackets", "coat", "coats", "blazer",
            },
            "trousers": {
                "trouser", "trousers", "pants", "pant", "jeans",
                "jean", "chino", "shorts",
            },
            "footwear": {
                "footwear", "shoes", "shoe", "sneakers", "sneaker",
                "boots", "boot", "sandals", "sandal",
            },
            "bags": {"bag", "bags", "backpack", "handbag"},
            "swimwear": {"swimwear", "swimsuit", "bikini"},
            "knitwear": {"knitwear", "knit", "sweater", "sweaters"},
            "dresses": {"dress", "dresses"},
        }

        if product == intent:
            return True

        for canonical, values in aliases.items():
            if intent in values and (
                product == canonical or product in values
            ):
                return True

            if product in values and intent == canonical:
                return True

        return False

    @staticmethod
    def _build_reason(
        product: Product,
        query: Optional[str],
        max_price: Optional[float],
        primary_intent: Optional[str],
        intent_confidence: float,
        display_budget: Optional[float] = None,
        display_currency: str = "USD",
    ) -> str:
        reasons = []

        if query:
            reasons.append(f"matches your search for '{query}'")

        if primary_intent and intent_confidence > 0:
            if RecommendationService._category_matches_intent(
                product.category, primary_intent
            ):
                reasons.append(
                    f"matches your current interest in {primary_intent}"
                )

        if product.category:
            reasons.append(
                f"fits the {product.category} category"
            )

        symbols = {
            "USD": "$",
            "INR": "\u20b9",
            "EUR": "\u20ac",
            "GBP": "\u00a3",
        }

        currency = display_currency.upper()
        symbol = symbols.get(currency, f"{currency} ")

        budget_to_display = (
            display_budget
            if display_budget is not None
            else max_price
        )

        if (
            max_price is not None
            and product.price <= max_price
            and budget_to_display is not None
        ):
            reasons.append(
                f"stays within your {symbol}{budget_to_display:,.2f} budget"
            )

        if product.rating is not None:
            reasons.append(
                f"has a {product.rating:.1f}/5 rating"
            )

        if not reasons:
            return "Recommended based on catalog relevance."

        return "Recommended because it " + ", ".join(reasons[:3]) + "."

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        if not text:
            return set()

        words = re.findall(r"[a-zA-Z0-9]+", text.lower())

        stop_words = {
            "the", "a", "an", "for", "and", "or", "with",
            "under", "below", "less", "than", "need", "want",
            "looking", "i", "me", "my", "in", "on", "at", "to",
            "please", "find", "show", "recommend", "recommendation",
            "products",
        }

        return {
            word for word in words
            if word not in stop_words
        }

    @staticmethod
    def _to_product(doc: dict) -> Product:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return Product(**doc)
