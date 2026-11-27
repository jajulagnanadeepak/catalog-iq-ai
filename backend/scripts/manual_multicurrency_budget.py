
import asyncio

from services.budget_service import BudgetService


async def main():
    service = BudgetService()

    queries = [
        "shirts under $200",
        "shirts under ₹10000",
        "shirts under €200",
        "shirts under £200",
        "trousers under ₹15000",
    ]

    for query in queries:
        print(f"\n--- {query} ---")
        result = await service.search(query)

        print("Success:", result["success"])
        print("Message:", result.get("message", ""))
        print("Currency:", result.get("currency"))
        print("Budget:", result.get("max_price"))
        print("Exchange-rate date:", result.get("exchange_rate_date"))

        for product in result.get("items", []):
            print(
                product["name"],
                "|",
                product["price"],
                product["currency"],
                "| Catalog price:",
                product["catalog_currency"],
            )


if __name__ == "__main__":
    asyncio.run(main())
