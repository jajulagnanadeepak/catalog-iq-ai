import asyncio
from database.connection import get_database


async def check():
    db = get_database()

    for product_id in ["p-005", "p-001"]:
        product = await db["products"].find_one(
            {"_id": product_id},
            {"_id": 1, "name": 1, "image": 1, "tags": 1, "category": 1},
        )

        print(f"\nProduct {product_id}:")
        print(product if product else "Product not found")


if __name__ == "__main__":
    asyncio.run(check())
