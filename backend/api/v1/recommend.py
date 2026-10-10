
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from dependencies import get_db
from services.exchange_rate_service import ExchangeRateService
from services.recommendation_service import RecommendationService
from services.session_intent_service import session_intent_service


router = APIRouter(prefix="/recommend", tags=["Recommendations"])

SUPPORTED_CURRENCIES = {"USD", "INR", "EUR", "GBP"}


@router.get(
    "",
    summary="AI product recommendations",
    description="Returns personalized recommendations with currency-aware budget filtering.",
)
async def get_recommendations(
    limit: int = Query(6, ge=1, le=20),
    query: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None, ge=0),
    currency: str = Query("USD"),
    category: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    currency = currency.upper().strip()

    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported currency. Use USD, INR, EUR, or GBP.",
        )

    exchange_service = ExchangeRateService()
    rates_data = None
    budget_usd = max_price

    # Fetch rates once if conversion is needed.
    if currency != "USD" and (
        max_price is not None or currency != "USD"
    ):
        try:
            rates_data = await exchange_service.get_rates()
        except RuntimeError as exc:
            raise HTTPException(
                status_code=503,
                detail=str(exc),
            ) from exc

        if max_price is not None:
            budget_usd = exchange_service.convert_with_rates(
                max_price, currency, "USD", rates_data["rates"]
            )

    session_intent = None
    if session_id:
        session_intent = await session_intent_service.get_session_intent(
            session_id
        )

    service = RecommendationService(db)

    recommendations = await service.get_recommendations(
        limit=limit,
        query=query,
        max_price=budget_usd,
        category=category,
        session_intent=session_intent,
        display_budget=max_price,
        display_currency=currency,
    )

    if currency != "USD":
        for item in recommendations:
            product = item.get("product", {})
            rates = rates_data["rates"]

            for field in ("price", "original_price"):
                amount = product.get(field)
                if amount is not None:
                    product[field] = exchange_service.convert_with_rates(
                        amount, "USD", currency, rates
                    )

            product["currency"] = currency

    return {
        "currency": currency,
        "budget": max_price,
        "exchange_rate_date": rates_data["date"] if rates_data else None,
        "recommendations": recommendations,
    }
