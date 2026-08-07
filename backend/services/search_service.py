"""
SearchService — keyword-based product search.
Placeholder for future embedding/vector search (Phase 3).
The service architecture is ready — swap _score_doc() with a vector similarity call.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from models.product import Product
from models.schemas import SearchPayload
from typing import Optional


class SearchService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["products"]

    async def search(self, payload: SearchPayload) -> dict:
        """
        Keyword-based search over name, brand, category, tags, and description.
        Returns a SearchResult-shaped dict matching the frontend contract:
        { items, page, page_size, total, interpretation, matches }
        """
        query = payload.query.lower().strip()
        tokens = query.split() if query else []

        # Base MongoDB filter (price, rating, category)
        mongo_filter: dict = {}
        if payload.category and payload.category.lower() != "all":
            mongo_filter["category"] = payload.category
        if payload.min_price is not None:
            mongo_filter.setdefault("price", {})["$gte"] = payload.min_price
        if payload.max_price is not None:
            mongo_filter.setdefault("price", {})["$lte"] = payload.max_price
        if payload.min_rating is not None:
            mongo_filter["rating"] = {"$gte": payload.min_rating}

        docs = await self.collection.find(mongo_filter).to_list(length=500)

        # Score each document by token overlap
        scored = sorted(
            [{"doc": d, "score": self._score_doc(d, tokens)} for d in docs],
            key=lambda x: x["score"],
            reverse=True,
        )

        # Apply sort override if requested
        if payload.sort == "price-asc":
            scored.sort(key=lambda x: x["doc"]["price"])
        elif payload.sort == "price-desc":
            scored.sort(key=lambda x: x["doc"]["price"], reverse=True)
        elif payload.sort == "rating":
            scored.sort(key=lambda x: x["doc"]["rating"], reverse=True)

        total = len(scored)
        start = (payload.page - 1) * payload.page_size
        page_docs = scored[start : start + payload.page_size]

        items = [self._to_product(s["doc"]) for s in page_docs]
        matches = [
            {"product_id": str(s["doc"]["_id"]), "score": round(s["score"], 4)}
            for s in page_docs
        ]

        interpretation = (
            f'Interpreted as: intent to browse "{query}" ranked by keyword relevance.'
            if query
            else "Showing catalog items sorted by rating."
        )

        return {
            "items": [p.model_dump(by_alias=False) for p in items],
            "page": payload.page,
            "page_size": payload.page_size,
            "total": total,
            "interpretation": interpretation,
            "matches": matches,
        }

    @staticmethod
    def _score_doc(doc: dict, tokens: list[str]) -> float:
        """
        Keyword overlap score. Returns a float in [0, 1].
        TODO (Phase 3): Replace with cosine similarity against embedding vectors.
        """
        if not tokens:
            return 0.35 + doc.get("rating", 0) / 20
        haystack = " ".join(
            [
                doc.get("name", ""),
                doc.get("brand", ""),
                doc.get("category", ""),
                " ".join(doc.get("tags", [])),
                doc.get("description", ""),
            ]
        ).lower()
        hits = sum(1 for t in tokens if t in haystack)
        return 0.6 + hits * 0.1 if hits else 0.35 + doc.get("rating", 0) / 20

    @staticmethod
    def _to_product(doc: dict) -> Product:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return Product(**doc)
