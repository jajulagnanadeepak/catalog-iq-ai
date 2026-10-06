"""
ProductService — handles filtering, sorting, and paginating products from MongoDB.
No AI logic — pure database operations.
"""

from typing import Optional

from database.connection import get_database
from models.product import Product


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

        # Category filter
        if category and category.lower() != "all":
            query["category"] = category

        # Price filters
        if min_price is not None:
            query.setdefault("price", {})["$gte"] = min_price

        if max_price is not None:
            query.setdefault("price", {})["$lte"] = max_price

        # Rating filter
        if min_rating is not None:
            query["rating"] = {"$gte": min_rating}

        # Determine MongoDB sort order
        sort_field, sort_dir = "name", 1

        if sort == "price-asc":
            sort_field, sort_dir = "price", 1

        elif sort == "price-desc":
            sort_field, sort_dir = "price", -1

        elif sort == "rating":
            sort_field, sort_dir = "rating", -1

        # Count matching products
        total = await self.collection.count_documents(query)

        # Pagination
        skip = (page - 1) * page_size

        cursor = (
            self.collection.find(query)
            .sort(sort_field, sort_dir)
            .skip(skip)
            .limit(page_size)
        )

        docs = await cursor.to_list(length=page_size)

        # Convert MongoDB documents to Product models
        items = [self._to_product(d) for d in docs]

        return {
            "items": [
                product.model_dump(by_alias=False)
                for product in items
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    async def get_product(self, product_id: str):
        """
        Fetch a product using the catalog's canonical product ID.

        Seeded products use values such as:
        p-001, p-002, ..., p-012

        These values are stored as MongoDB _id.
        """

        doc = await self.collection.find_one({
            "_id": product_id
        })

        if doc is None:
            return None

        return self._to_product(doc)

    @staticmethod
    def _to_product(doc: dict) -> Product:
        """
        Convert a raw MongoDB document to a Product model.
        """

        doc["id"] = str(doc.pop("_id"))

        return Product(**doc)