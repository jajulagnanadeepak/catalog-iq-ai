from fastapi import APIRouter
from pydantic import BaseModel

from search import semantic_search
from ai.intent_detector import IntentDetector
from ai.recommendation_engine import RecommendationEngine

router = APIRouter(tags=["Semantic Search"])

intent_detector = IntentDetector()
recommendation_engine = RecommendationEngine()


class SearchRequest(BaseModel):
    query: str


@router.post("/semantic-search")
async def search_products(request: SearchRequest):

    # Detect user intent
    intent = intent_detector.detect_intent(request.query)

    # Use Recommendation Engine when appropriate
    if intent["intent"] == "recommendation":
        products = await recommendation_engine.recommend(request.query)
    else:
        products = await semantic_search(request.query)

    return {
        "success": True,
        "intent": intent,
        "count": len(products),
        "products": products
    }