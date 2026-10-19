import asyncio
from database.connection import get_database

OLD_IMAGES = {
    "p-005": "https://images.unsplash.com/photo-1625910513462-efd3f1751e7c?w=600",
    "p-001": "https://images.unsplash.com/photo-1539533018447-63fcce2678e4?w=600",
}

NEW_IMAGES = {
    "p-005": "https://plus.unsplash.com/premium_photo-1674719144570-0728faf14f96?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=NHwxMjA3fDA%3D",
    "p-001": "https://plus.unsplash.com/premium_photo-1718913936342-eaafff98834b?q=80&w=1172&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=NHwxMjA3fDA%3D",
}

EXPECTED_NAMES = {
    "p-005": "Terry Polo Shirt",
    "p-001": "Mercer Wool Overcoat",
}


async def main():
    db = get_database()
    collection = db["products"]

    # Preflight: validate both records before writing anything.
    for product_id, expected_name in EXPECTED_NAMES.items():
        product = await collection.find_one({"_id": product_id})

        if not product:
            raise RuntimeError(
                f"ABORTED: Product {product_id} was not found."
            )

        if product.get("name") != expected_name:
            raise RuntimeError(
                f"ABORTED: Unexpected product name for {product_id}."
            )

        if product.get("image") != OLD_IMAGES[product_id]:
            raise RuntimeError(
                f"ABORTED: Current image for {product_id} differs "
                "from the expected broken URL. No updates performed."
            )

    # Update only the image field, using guarded filters.
    for product_id, expected_name in EXPECTED_NAMES.items():
        result = await collection.update_one(
            {
                "_id": product_id,
                "name": expected_name,
                "image": OLD_IMAGES[product_id],
            },
            {"$set": {"image": NEW_IMAGES[product_id]}},
        )

        if result.matched_count != 1:
            raise RuntimeError(
                f"Update guard failed for {product_id}. "
                "Stop and inspect the records."
            )

        print(f"Updated image: {expected_name} ({product_id})")

    # Read back and verify.
    for product_id, expected_name in EXPECTED_NAMES.items():
        product = await collection.find_one(
            {"_id": product_id},
            {"_id": 1, "name": 1, "image": 1},
        )

        if not product or product.get("image") != NEW_IMAGES[product_id]:
            raise RuntimeError(
                f"Verification failed for {product_id}."
            )

        print(f"VERIFIED: {product['name']}")
        print(f"Image: {product['image']}")


if __name__ == "__main__":
    asyncio.run(main())
