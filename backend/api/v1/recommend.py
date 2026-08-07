from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from dependencies import get_db
from services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@router.get(
    "",
    summary="AI product recommendations",
    description=(
        "Returns top-N product recommendations ordered by rating. "
        "Shape matches the frontend Recommendation[] type. "
        "Phase 5 will personalise results using user event history."
    ),
)
async def get_recommendations(
    limit: int = Query(6, ge=1, le=20, description="Number of recommendations to return"),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = RecommendationService(db)
    return await service.get_recommendations(limit=limit)
