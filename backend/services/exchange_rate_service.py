
from datetime import datetime, timezone

import httpx


class ExchangeRateService:
    """Fetch and convert exchange rates using USD as the base."""

    API_URL = "https://api.frankfurter.dev/v1/latest"
    SUPPORTED_CURRENCIES = {"USD", "INR", "EUR", "GBP"}

    async def get_rates(self) -> dict:
        """Fetch the latest available exchange rates."""

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.API_URL,
                    params={
                        "base": "USD",
                        "symbols": "INR,EUR,GBP",
                    },
                )
                response.raise_for_status()
                data = response.json()

            rates = data.get("rates", {})

            required = ("INR", "EUR", "GBP")
            for currency in required:
                if currency not in rates or float(rates[currency]) <= 0:
                    raise ValueError(
                        f"Missing or invalid rate for {currency}"
                    )

            return {
                "base": "USD",
                "rates": {
                    "USD": 1.0,
                    **{
                        currency: float(rates[currency])
                        for currency in required
                    },
                },
                "date": data.get("date"),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }

        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            print(
                f"Exchange-rate error details: "
                f"{type(exc).__name__}: {exc}"
            )
            raise RuntimeError(
                "Unable to retrieve current exchange rates. "
                "Please try again later."
            ) from exc

    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> float:
        """Convert an amount between supported currencies."""

        if amount < 0:
            raise ValueError("Amount cannot be negative.")

        source = from_currency.upper()
        target = to_currency.upper()

        if (
            source not in self.SUPPORTED_CURRENCIES
            or target not in self.SUPPORTED_CURRENCIES
        ):
            raise ValueError("Unsupported currency.")

        if source == target:
            return round(amount, 2)

        data = await self.get_rates()
        rates = data["rates"]

        # Each rate is the amount of currency per 1 USD.
        amount_in_usd = amount / rates[source]
        converted_amount = amount_in_usd * rates[target]

        return round(converted_amount, 2)
