import asyncio
from database.connection import get_database


async def check():
    db = get_database()

    print("\nPRODUCTS COLLECTION SAMPLE:")
    
    docs = await db["products"].find({}).limit(3).to_list(length=3)

    for doc in docs:
        print("\n", doc)


asyncio.run(check())