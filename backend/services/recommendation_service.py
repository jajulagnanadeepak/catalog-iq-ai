"""
RecommendationService — popularity-based recommendations.
Pulls the highest-rated in-stock products from MongoDB.
Placeholder for collaborative/content-based filtering (Phase 5).
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from models.product import Product


_REASONS = [
    ("Because you viewed outerwear", "Similar silhouette and fabric weight to items in your history."),
    ("Trending in your size", "Popular with shoppers who share your style graph."),
    ("Frequently bought together", "Completes 3 of your saved looks."),
    ("Matches your saved palette", "Colour-matched to your last two purchases."),
    ("Restocked near you", "Back in stock in the size you follow."),
    ("High value pick", "Best price-to-rating ratio in this category."),
]


class RecommendationService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["products"]

    async def get_recommendations(self, limit: int = 6) -> list[dict]:
        """
        Return top-N recommendations sorted by rating.
        Shape mirrors the frontend Recommendation[] type:
        { id, title, reason, confidence, product }
        TODO (Phase 5): Use user event history for personalised filtering.
        """
        docs = (
            await self.collection
            .find({"in_stock": True})
            .sort("rating", -1)
            .limit(limit)
            .to_list(length=limit)
        )

        recommendations = []
        for i, doc in enumerate(docs):
            product = self._to_product(doc)
            title, reason = _REASONS[i % len(_REASONS)]
            recommendations.append({
                "id": f"r-{i}",
                "title": title,
                "reason": reason,
                "confidence": round(0.72 + ((i * 4) % 25) / 100, 2),
                "product": product.model_dump(by_alias=False),
            })

        return recommendations

    @staticmethod
    def _to_product(doc: dict) -> Product:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return Product(**doc)
