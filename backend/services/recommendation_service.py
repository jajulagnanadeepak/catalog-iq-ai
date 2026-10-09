
"""
RecommendationService — deterministic product recommendations.

Features:
- Query relevance with singular/plural normalization.
- Product-type filtering.
- Optional category, budget, and session-intent filtering.
- Ranking based on relevance, rating, popularity, and budget.
- No synthetic product data.
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
    ) -> list[dict]:

        mongo_query = {"in_stock": True}

        if max_price is not None:
            mongo_query["price"] = {"$lte": max_price}

        if category and category.lower() != "all":
            mongo_query["category"] = category

        docs = await self.collection.find(mongo_query).to_list(
            length=100
        )

        query_tokens = self._tokenize(query or "")

        primary_intent = None
        intent_confidence = 0.0

        if session_intent:
            primary_intent = session_intent.get("primary_category")
            intent_confidence = float(
                session_intent.get("confidence", 0.0)
            )

        requested_group = self._requested_product_group(query_tokens)

        scored_products = []

        for doc in docs:
            product = self._to_product(doc)

            # Enforce requested product type.
            if requested_group:
                product_words = self._tokenize(
                    " ".join([
                        product.name or "",
                        " ".join(product.tags or []),
                    ])
                )

                if not product_words.intersection(
                    self._product_groups()[requested_group]
                ):
                    continue

            score = self._score_product(
                product=product,
                query_tokens=query_tokens,
                max_price=max_price,
                primary_intent=primary_intent,
                intent_confidence=intent_confidence,
            )

            # Exclude products with no meaningful query match.
            if query_tokens:
                searchable_text = " ".join([
                    product.name or "",
                    product.brand or "",
                    product.category or "",
                    " ".join(product.tags or []),
                    product.description or "",
                    " ".join(product.colors or []),
                ])

                searchable_tokens = self._tokenize(searchable_text)

                if not query_tokens.intersection(searchable_tokens):
                    continue

            scored_products.append((score, product))

        scored_products.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        recommendations = []

        for index, (score, product) in enumerate(
            scored_products[:limit]
        ):
            recommendations.append({
                "id": f"r-{index}",
                "title": "Recommended for you",
                "reason": self._build_reason(
                    product=product,
                    query=query,
                    max_price=max_price,
                    primary_intent=primary_intent,
                    intent_confidence=intent_confidence,
                ),
                # This is a ranking score, not a calibrated probability.
                "confidence": round(min(0.95, max(0.0, score)), 2),
                "product": product.model_dump(by_alias=False),
            })

        return recommendations

    def _score_product(
        self,
        product: Product,
        query_tokens: set[str],
        max_price: Optional[float],
        primary_intent: Optional[str],
        intent_confidence: float,
    ) -> float:

        searchable_text = " ".join([
            product.name or "",
            product.brand or "",
            product.category or "",
            " ".join(product.tags or []),
            product.description or "",
            " ".join(product.colors or []),
        ])

        searchable_tokens = self._tokenize(searchable_text)

        # Query relevance: 70%
        query_score = 0.0

        if query_tokens:
            matched_tokens = query_tokens.intersection(searchable_tokens)
            query_score = len(matched_tokens) / len(query_tokens)

        score = 0.70 * query_score

        # Session intent: 10%
        if primary_intent and self._category_matches_intent(
            product.category,
            primary_intent,
        ):
            score += 0.10 * max(
                0.0, min(1.0, intent_confidence)
            )

        # Rating: 10%
        rating_score = (product.rating or 0) / 5.0
        score += 0.10 * max(0.0, min(1.0, rating_score))

        # Popularity: 5%
        reviews = product.reviews or 0
        score += 0.05 * min(max(reviews, 0) / 500.0, 1.0)

        # Budget: 5%
        if max_price is not None and max_price > 0:
            if product.price <= max_price:
                budget_score = 1.0 - product.price / max_price
                score += 0.05 * max(
                    0.0, min(1.0, budget_score)
                )
        elif max_price is None:
            score += 0.05

        return score

    @staticmethod
    def _normalize_token(token: str) -> str:
        """Normalize common English plurals for matching."""
        if len(token) > 4 and token.endswith("ies"):
            return token[:-3] + "y"

        if len(token) > 4 and token.endswith("ses"):
            return token[:-2]

        if len(token) > 3 and token.endswith("s"):
            return token[:-1]

        return token

    @classmethod
    def _tokenize(cls, text: str) -> set[str]:
        if not text:
            return set()

        words = re.findall(r"[a-zA-Z0-9]+", text.lower())

        stop_words = {
            "the", "a", "an", "for", "and", "or", "with",
            "under", "need", "want", "looking", "i", "me", "my",
        }

        return {
            cls._normalize_token(word)
            for word in words
            if word not in stop_words
        }

    @staticmethod
    def _product_groups() -> dict[str, set[str]]:
        return {
            "shirts": {
                "shirt", "polo", "tshirt", "tee", "blouse",
            },
            "trousers": {
                "trouser", "pant", "jean", "chino",
            },
            "shorts": {"short"},
            "jackets": {"jacket", "coat", "blazer"},
            "shoes": {"shoe", "sneaker", "boot", "sandal"},
            "dresses": {"dress"},
        }

    @classmethod
    def _requested_product_group(
        cls,
        query_tokens: set[str],
    ) -> Optional[str]:
        for group, aliases in cls._product_groups().items():
            if query_tokens.intersection(aliases):
                return group

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
                "tshirts", "blouse", "vest",
            },
            "outerwear": {
                "outerwear", "jacket", "jackets", "coat",
                "coats", "blazer",
            },
            "trousers": {
                "trouser", "trousers", "pants", "pant",
                "jeans", "shorts",
            },
            "footwear": {
                "footwear", "shoes", "shoe", "sneakers",
                "boots", "sandals",
            },
            "bags": {"bag", "bags", "backpack", "handbag"},
            "swimwear": {"swimwear", "swimsuit", "bikini"},
            "knitwear": {"knitwear", "knit", "sweater", "sweaters"},
        }

        if product == intent:
            return True

        for canonical, values in aliases.items():
            if intent in values:
                if product == canonical or product in values:
                    return True

        return False

    @staticmethod
    def _build_reason(
        product: Product,
        query: Optional[str],
        max_price: Optional[float],
        primary_intent: Optional[str],
        intent_confidence: float,
    ) -> str:

        reasons = []

        if query:
            reasons.append(f"matches your search for '{query}'")

        if primary_intent and intent_confidence > 0:
            if RecommendationService._category_matches_intent(
                product.category,
                primary_intent,
            ):
                reasons.append(
                    f"matches your current interest in {primary_intent}"
                )

        if product.category:
            reasons.append(f"fits the {product.category} category")

        if (
            max_price is not None
            and product.price <= max_price
        ):
            reasons.append(f"stays within your ${max_price:g} budget")

        if product.rating is not None:
            reasons.append(f"has a {product.rating:.1f}/5 rating")

        if not reasons:
            return "Recommended based on catalog relevance."

        return "Recommended because it " + ", ".join(reasons[:3]) + "."

    @staticmethod
    def _to_product(doc: dict) -> Product:
        doc = dict(doc)

        if "_id" in doc:
            doc["id"] = str(doc.pop("_id"))

        return Product(**doc)
