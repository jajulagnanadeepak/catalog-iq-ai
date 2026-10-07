import asyncio

from database.connection import connect_db, close_db, get_database


async def migrate():
    await connect_db()

    db = get_database()
    collection = db["products"]

    result = await collection.update_many(
        {"currency": {"$exists": False}},
        {"$set": {"currency": "USD"}}
    )

    print(f"Updated products: {result.modified_count}")

    await close_db()


if __name__ == "__main__":
    asyncio.run(migrate())