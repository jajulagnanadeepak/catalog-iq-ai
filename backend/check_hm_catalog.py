import asyncio

from database.connection import connect_db, close_db, get_database


async def main():
    await connect_db()

    try:
        db = get_database()
        collection = db["catalog_products"]

        count = await collection.count_documents({})

        print(f"catalog_products count: {count:,}")

        sample = await collection.find_one({})

        print("\nSample:")
        print(sample)

    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())