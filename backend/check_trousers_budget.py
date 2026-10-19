import asyncio

from services.budget_service import BudgetService


async def test():
    service = BudgetService()

    result = await service.search(
        "trousers under $200"
    )

    print(result)


if __name__ == "__main__":
    asyncio.run(test())