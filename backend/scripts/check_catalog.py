import asyncio
from database.connection import get_database


async def check():
    db = get_database()
    collection = db["products"]

    print("\nPRODUCT IMAGE AUDIT")
    print("-" * 70)

    docs = await collection.find(
        {},
        {
            "_id": 1,
            "name": 1,
            "title": 1,
            "image": 1,
            "imageUrl": 1,
            "image_url": 1,
            "images": 1,
            "thumbnail": 1,
        },
    ).limit(15).to_list(length=15)

    if not docs:
        print("No products found in the products collection.")
        return

    for doc in docs:
        print(f"\nID: {doc.get('_id')}")
        print(f"Name: {doc.get('name') or doc.get('title') or 'Unknown'}")

        for field in ("image", "imageUrl", "image_url", "images", "thumbnail"):
            if field in doc:
                print(f"{field}: {doc[field]}")


if __name__ == "__main__":
    asyncio.run(check())
