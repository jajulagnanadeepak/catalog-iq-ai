
import asyncio

from services.exchange_rate_service import ExchangeRateService


async def main():
    service = ExchangeRateService()

    try:
        data = await service.get_rates()

        print("Base currency:", data["base"])
        print("Rate date:", data["date"])
        print("Rates:", data["rates"])

        print(
            "₹10,000 converted to USD:",
            await service.convert(10000, "INR", "USD"),
        )

        print(
            "€200 converted to USD:",
            await service.convert(200, "EUR", "USD"),
        )

    except RuntimeError as exc:
        print("Exchange-rate error:", exc)


if __name__ == "__main__":
    asyncio.run(main())
