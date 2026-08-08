"""
ProductService — handles filtering, sorting, and paginating products from MongoDB.
No AI logic — pure database operations.
"""

from typing import Optional
from database.connection import get_database
from models.product import Product
from utils.pagination import paginate


class ProductService:

    @property
    def collection(self):
        """
        Always get the latest MongoDB collection.
        Prevents using a closed MongoClient after reload.
        """
        return get_database()["products"]

    async def list_products(
        self,
        page: int = 1,
        page_size: int = 8,
        category: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        sort: Optional[str] = None,
    ) -> dict:
        """
        Return a paginated, filtered, and sorted product list.
        Mirrors the frontend filterSort + paginate helpers in services.ts.
        """
        query: dict = {}

        if category and category.lower() != "all":
            query["category"] = category
        if min_price is not None:
            query.setdefault("price", {})["$gte"] = min_price
        if max_price is not None:
            query.setdefault("price", {})["$lte"] = max_price
        if min_rating is not None:
            query["rating"] = {"$gte": min_rating}

        # Determine sort order for MongoDB
        sort_field, sort_dir = "name", 1
        if sort == "price-asc":
            sort_field, sort_dir = "price", 1
        elif sort == "price-desc":
            sort_field, sort_dir = "price", -1
        elif sort == "rating":
            sort_field, sort_dir = "rating", -1

        total = await self.collection.count_documents(query)
        skip = (page - 1) * page_size

        cursor = (
            self.collection.find(query)
            .sort(sort_field, sort_dir)
            .skip(skip)
            .limit(page_size)
        )
        docs = await cursor.to_list(length=page_size)
        items = [self._to_product(d) for d in docs]

        return {
            "items": [p.model_dump(by_alias=False) for p in items],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    async def get_product(self, product_id: str):

        doc = await self.collection.find_one({
            "product_id": product_id
        })

        if doc is None:
            return None

        return self._to_product(doc)

    @staticmethod
    def _to_product(doc: dict) -> Product:
        """Convert a raw MongoDB document to a Product model."""
        doc["id"] = str(doc.pop("_id"))
        return Product(**doc)
