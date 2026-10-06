from typing import Optional

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from dependencies import get_db
from services.recommendation_service import RecommendationService


router = APIRouter(
    prefix="/recommend",
    tags=["Recommendations"],
)


@router.get(
    "",
    summary="AI product recommendations",
    description=(
        "Returns deterministic product recommendations "
        "using catalog relevance, rating, popularity, "
        "and optional budget constraints."
    ),
)
async def get_recommendations(
    limit: int = Query(
        6,
        ge=1,
        le=20,
        description="Number of recommendations to return",
    ),

    query: Optional[str] = Query(
        None,
        description="Natural-language shopping query",
    ),

    max_price: Optional[float] = Query(
        None,
        ge=0,
        description="Maximum product price",
    ),

    category: Optional[str] = Query(
        None,
        description="Optional product category",
    ),

    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = RecommendationService(db)

    return await service.get_recommendations(
        limit=limit,
        query=query,
        max_price=max_price,
        category=category,
    )