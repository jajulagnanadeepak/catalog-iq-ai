from fastapi import APIRouter
from pydantic import BaseModel, Field

from search import semantic_search
from ai.intent_detector import IntentDetector
from ai.recommendation_engine import RecommendationEngine
from services.semantic_reranker import SemanticReranker
from services.session_intent_service import (
    session_intent_service,
)


router = APIRouter(tags=["Semantic Search"])

intent_detector = IntentDetector()
recommendation_engine = RecommendationEngine()
reranker = SemanticReranker()


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=50)
    session_id: str | None = None


@router.post("/semantic-search")
async def search_products(request: SearchRequest):

    # --------------------------------------------------
    # 1. Detect user query intent
    # --------------------------------------------------

    intent = intent_detector.detect_intent(
        request.query
    )

    # --------------------------------------------------
    # 2. Get persistent session intent
    # --------------------------------------------------

    session_intent = None

    if request.session_id:
        session_intent = (
            await session_intent_service.get_session_intent(
                request.session_id
            )
        )

    # --------------------------------------------------
    # 3. Recommendation intent
    # --------------------------------------------------

    if intent["intent"] == "recommendation":

        products = await recommendation_engine.recommend(
            request.query
        )

        return {
            "success": True,
            "intent": intent,
            "session_intent": session_intent,
            "count": len(products),
            "products": products,
        }

    # --------------------------------------------------
    # 4. Retrieve candidate pool from FAISS
    # --------------------------------------------------

    candidates = await semantic_search(
        request.query,
        top_k=100,
    )

    # --------------------------------------------------
    # 5. Personalized lightweight reranking
    # --------------------------------------------------

    products = reranker.rerank(
        query=request.query,
        results=candidates,
        limit=request.top_k,
        max_category_ratio=0.35,
        session_intent=session_intent,
    )

    # --------------------------------------------------
    # 6. Return final results
    # --------------------------------------------------

    return {
        "success": True,
        "intent": intent,
        "session_intent": session_intent,
        "retrieved_candidates": len(candidates),
        "count": len(products),
        "products": products,
    }