"""
RecommendationService — deterministic personalized recommendations.

Features:
- MongoDB catalog
- Query/category/tag relevance
- Session intent
- Rating/popularity
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

        mongo_query = {
            "in_stock": True
        }

        if max_price is not None:
            mongo_query["price"] = {
                "$lte": max_price
            }

        if category and category.lower() != "all":
            mongo_query["category"] = category

        docs = await (
            self.collection
            .find(mongo_query)
            .to_list(length=100)
        )

        scored_products = []

        query_tokens = self._tokenize(query or "")

        primary_intent = None
        intent_confidence = 0.0

        if session_intent:
            primary_intent = session_intent.get(
                "primary_category"
            )

            intent_confidence = float(
                session_intent.get(
                    "confidence",
                    0.0
                )
            )

        for doc in docs:

            product = self._to_product(doc)

            score = self._score_product(
                product=product,
                query_tokens=query_tokens,
                max_price=max_price,
                primary_intent=primary_intent,
                intent_confidence=intent_confidence,
            )

            scored_products.append(
                (score, product)
            )

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
                    display_budget=display_budget,
                    display_currency=display_currency,
                    primary_intent=primary_intent,
                    intent_confidence=intent_confidence,
                ),

                "confidence": round(
                    min(
                        0.95,
                        max(
                            0.50,
                            score
                        )
                    ),
                    2,
                ),

                "product": product.model_dump(
                    by_alias=False
                ),
            })

        return recommendations

    # =============================================================
    # SCORING
    # =============================================================

    def _score_product(
        self,
        product: Product,
        query_tokens: set[str],
        max_price: Optional[float],
        primary_intent: Optional[str],
        intent_confidence: float,
    ) -> float:

        score = 0.0

        # Query relevance — 40%

        searchable_text = " ".join([
            product.name or "",
            product.brand or "",
            product.category or "",
            " ".join(product.tags or []),
            product.description or "",
            " ".join(product.colors or []),
        ]).lower()

        query_score = 0.0

        if query_tokens:

            matched_tokens = sum(
                1
                for token in query_tokens
                if token in searchable_text
            )

            query_score = (
                matched_tokens / len(query_tokens)
            )

        score += 0.40 * query_score

        # Session intent — 25%

        intent_score = 0.0

        if primary_intent:

            if self._category_matches_intent(
                product.category,
                primary_intent,
            ):
                intent_score = intent_confidence

        score += 0.25 * intent_score

        # Rating — 15%

        rating_score = (
            product.rating or 0
        ) / 5.0

        score += 0.15 * rating_score

        # Popularity — 10%

        reviews = product.reviews or 0

        popularity_score = min(
            reviews / 500.0,
            1.0,
        )

        score += 0.10 * popularity_score

        # Budget — 10%

        if max_price is not None:

            if product.price <= max_price:

                budget_score = 1.0 - (
                    product.price / max_price
                )

                budget_score = max(
                    0.0,
                    min(
                        1.0,
                        budget_score,
                    ),
                )

                score += 0.10 * budget_score

        else:
            score += 0.10

        return score

    # =============================================================
    # INTENT MATCHING
    # =============================================================

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
                "top",
                "tops",
                "shirt",
                "shirts",
                "t-shirt",
                "tshirts",
                "blouse",
                "vest",
            },

            "outerwear": {
                "outerwear",
                "jacket",
                "jackets",
                "coat",
                "coats",
                "blazer",
            },

            "trousers": {
                "trouser",
                "trousers",
                "pants",
                "pant",
                "jeans",
                "shorts",
            },

            "footwear": {
                "footwear",
                "shoes",
                "shoe",
                "sneakers",
                "boots",
                "sandals",
            },

            "bags": {
                "bag",
                "bags",
                "backpack",
                "handbag",
            },

            "swimwear": {
                "swimwear",
                "swimsuit",
                "bikini",
            },

            "knitwear": {
                "knitwear",
                "knit",
                "sweater",
                "sweaters",
            },
        }

        if product == intent:
            return True

        for canonical, values in aliases.items():

            if intent in values:

                if (
                    product == canonical
                    or product in values
                ):
                    return True

        return False

    # =============================================================
    # EXPLANATION
    # =============================================================

    
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
                product.category,
                primary_intent,
            ):
                reasons.append(
                    f"matches your current interest in {primary_intent}"
                )

        if product.category:
            reasons.append(f"fits the {product.category} category")

        symbols = {
            "USD": "$",
            "INR": "₹",
            "EUR": "€",
            "GBP": "£",
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
            reasons.append(f"has a {product.rating:.1f}/5 rating")

        if not reasons:
            return "Recommended based on catalog relevance."

        return "Recommended because it " + ", ".join(reasons[:3]) + "."


    # =============================================================
    # TEXT PROCESSING
    # =============================================================

    @staticmethod
    def _tokenize(text: str) -> set[str]:

        if not text:
            return set()

        words = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        stop_words = {
            "the",
            "a",
            "an",
            "for",
            "and",
            "or",
            "with",
            "under",
            "need",
            "want",
            "looking",
            "i",
            "me",
            "my",
        }

        return {
            word
            for word in words
            if word not in stop_words
        }

    # =============================================================
    # MONGO → PRODUCT
    # =============================================================

    @staticmethod
    def _to_product(doc: dict) -> Product:

        doc = dict(doc)

        doc["id"] = str(
            doc.pop("_id")
        )

        return Product(**doc)