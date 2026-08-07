from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from dependencies import get_db
from models.schemas import SearchPayload
from services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["Search"])


@router.post(
    "",
    summary="Semantic product search",
    description=(
        "Search the product catalog by natural language query. "
        "Returns ranked results with an interpretation string and per-item match scores. "
        "Phase 3 will replace keyword scoring with vector embeddings."
    ),
)
async def search_products(
    payload: SearchPayload,
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    service = SearchService(db)
    return await service.search(payload)
