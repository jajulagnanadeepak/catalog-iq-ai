from typing import Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from dependencies import get_db
from services.recommendation_service import RecommendationService
from services.session_intent_service import session_intent_service


router = APIRouter(
    prefix="/recommend",
    tags=["Recommendations"],
)


@router.get(
    "",
    summary="AI product recommendations",
    description="Returns deterministic personalized product recommendations using query, budget, category, and session intent.",
)
async def get_recommendations(
    limit: int = Query(
        6,
        ge=1,
        le=20,
        description="Number of recommendations",
    ),
    query: Optional[str] = Query(
        None,
        description="Optional search query",
    ),
    max_price: Optional[float] = Query(
        None,
        ge=0,
        description="Optional maximum price",
    ),
    category: Optional[str] = Query(
        None,
        description="Optional product category",
    ),
    session_id: Optional[str] = Query(
        None,
        description="Optional session ID for personalized intent",
    ),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    session_intent = None

    if session_id:
        session_intent = (
            await session_intent_service.get_session_intent(
                session_id
            )
        )

    service = RecommendationService(db)

    return await service.get_recommendations(
        limit=limit,
        query=query,
        max_price=max_price,
        category=category,
        session_intent=session_intent,
    )