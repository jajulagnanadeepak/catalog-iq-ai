"""
RecommendationService — deterministic product recommendations.

Current MVP:
- MongoDB catalog
- Query/category/tag relevance
- Rating/popularity
- Optional budget filtering
- Deterministic explanations

Future:
- Session intent
- User event history
- FAISS semantic similarity
- Seasonal signals
- Diversity guardrails
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
    ) -> list[dict]:

        # ---------------------------------------------------------
        # 1. Build MongoDB filter
        # ---------------------------------------------------------

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

        # ---------------------------------------------------------
        # 2. Score candidates
        # ---------------------------------------------------------

        scored_products = []

        query_tokens = self._tokenize(query or "")

        for doc in docs:
            product = self._to_product(doc)

            score = self._score_product(
                product=product,
                query_tokens=query_tokens,
                max_price=max_price,
            )

            scored_products.append(
                (score, product)
            )

        # ---------------------------------------------------------
        # 3. Highest score first
        # ---------------------------------------------------------

        scored_products.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        # ---------------------------------------------------------
        # 4. Build recommendation response
        # ---------------------------------------------------------

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
                ),
                "confidence": round(
                    min(0.95, max(0.50, score)),
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
    ) -> float:

        score = 0.0

        # ---------------------------------------------------------
        # Query relevance — 50%
        # ---------------------------------------------------------

        searchable_text = " ".join([
            product.name or "",
            product.brand or "",
            product.category or "",
            " ".join(product.tags or []),
            product.description or "",
            " ".join(product.colors or []),
        ]).lower()

        if query_tokens:

            matched_tokens = sum(
                1
                for token in query_tokens
                if token in searchable_text
            )

            query_score = matched_tokens / len(query_tokens)

            score += 0.50 * query_score

        # ---------------------------------------------------------
        # Rating — 20%
        # ---------------------------------------------------------

        rating_score = (product.rating or 0) / 5.0

        score += 0.20 * rating_score

        # ---------------------------------------------------------
        # Popularity — 15%
        # ---------------------------------------------------------

        reviews = product.reviews or 0

        popularity_score = min(
            reviews / 500.0,
            1.0,
        )

        score += 0.15 * popularity_score

        # ---------------------------------------------------------
        # Budget — 15%
        # ---------------------------------------------------------

        if max_price is not None:

            if product.price <= max_price:

                # Cheaper products receive a small advantage,
                # while still allowing quality/relevance to dominate.
                budget_score = 1.0 - (
                    product.price / max_price
                )

                budget_score = max(
                    0.0,
                    min(1.0, budget_score),
                )

                score += 0.15 * budget_score

        else:
            # No budget supplied.
            score += 0.15

        return score

    # =============================================================
    # EXPLANATION
    # =============================================================

    @staticmethod
    def _build_reason(
        product: Product,
        query: Optional[str],
        max_price: Optional[float],
    ) -> str:

        reasons = []

        if query:
            reasons.append(
                f"matches your search for '{query}'"
            )

        if product.category:
            reasons.append(
                f"fits the {product.category} category"
            )

        if max_price is not None:
            if product.price <= max_price:
                reasons.append(
                    f"stays within your ${max_price:g} budget"
                )

        if product.rating is not None:
            reasons.append(
                f"has a {product.rating:.1f}/5 rating"
            )

        if not reasons:
            return "Recommended based on catalog relevance."

        return "Recommended because it " + ", ".join(
            reasons[:3]
        ) + "."

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