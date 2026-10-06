import asyncio

from database.connection import connect_db, close_db, get_database


async def main():
    await connect_db()

    db = get_database()

    products_count = await db["products"].count_documents({})
    Products_count = await db["Products"].count_documents({})

    print("products count:", products_count)
    print("Products count:", Products_count)

    print("\nproducts sample:")
    print(await db["products"].find_one())

    print("\nProducts sample:")
    print(await db["Products"].find_one())

    await close_db()


if __name__ == "__main__":
    asyncio.run(main())