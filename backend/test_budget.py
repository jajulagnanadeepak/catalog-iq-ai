import asyncio

from services.budget_service import BudgetService


async def test():
    service = BudgetService()

    print("\n--- USD TEST ---")
    result = await service.search("shirts under $200")
    print(result)

    print("\n--- INR TEST ---")
    result = await service.search("shirts under ₹2000")
    print(result)


if __name__ == "__main__":
    asyncio.run(test())