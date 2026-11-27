from fastapi import APIRouter
from pydantic import BaseModel, Field

from config import settings
from search import semantic_search
from ai.intent_detector import IntentDetector
from ai.recommendation_engine import RecommendationEngine
from services.catalog_scope import classify as classify_scope
from services.semantic_reranker import SemanticReranker
from services.semantic_reranker_v2 import KIDS_PENALTY, SemanticRerankerV2
from services.session_intent_service import (
    session_intent_service,
)


router = APIRouter(tags=["Semantic Search"])

intent_detector = IntentDetector()
recommendation_engine = RecommendationEngine()
reranker = SemanticReranker()
reranker_v2 = SemanticRerankerV2()
reranker_v2_kids = SemanticRerankerV2(kids_penalty=KIDS_PENALTY)
reranker_v2_attr = SemanticRerankerV2(attribute_boost=True)
reranker_v2_kids_attr = SemanticRerankerV2(kids_penalty=KIDS_PENALTY, attribute_boost=True)

# (SEARCH_V2_KIDS_DOWNRANK, SEARCH_V2_ATTRIBUTE_BOOST) -> v2 instance
_V2_RERANKERS = {
    (False, False): reranker_v2,
    (True, False): reranker_v2_kids,
    (False, True): reranker_v2_attr,
    (True, True): reranker_v2_kids_attr,
}


def active_reranker():
    """v1 unless SEARCH_RERANK_VERSION=v2 (Phase 1, S1 + S2).

    With v2, SEARCH_V2_KIDS_DOWNRANK=true also enables S4 and
    SEARCH_V2_ATTRIBUTE_BOOST=true enables S3-lite, independently.
    """
    if settings.search_rerank_version == "v2":
        return _V2_RERANKERS[
            (bool(settings.search_v2_kids_downrank), bool(settings.search_v2_attribute_boost))
        ]
    return reranker


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
    # 2b. Out-of-catalogue queries (v2 + S5 flag only).
    #     Decided before retrieval; confirmed OOC skips FAISS.
    # --------------------------------------------------

    if (
        settings.search_rerank_version == "v2"
        and settings.search_v2_out_of_catalog
    ):
        scope = classify_scope(request.query)
        if scope.out_of_catalog:
            return {
                "success": True,
                "intent": intent,
                "session_intent": session_intent,
                "retrieved_candidates": 0,
                "count": 0,
                "products": [],
                "rerank_version": active_reranker().version,
                "out_of_catalog": True,
                "ooc_reason": scope.reason,
            }

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

    selected_reranker = active_reranker()

    products = selected_reranker.rerank(
        query=request.query,
        results=candidates,
        limit=request.top_k,
        max_category_ratio=0.35,
        session_intent=session_intent,
    )

    # --------------------------------------------------
    # 6. Return final results
    # --------------------------------------------------

    response = {
        "success": True,
        "intent": intent,
        "session_intent": session_intent,
        "retrieved_candidates": len(candidates),
        "count": len(products),
        "products": products,
    }

    # Additive, v2 only: lets clients and the eval confirm the version.
    if selected_reranker is not reranker:
        response["rerank_version"] = selected_reranker.version

    return response