from ai.intent_detector import IntentDetector
from ai.recommendation_engine import RecommendationEngine
from search import semantic_search
from services.semantic_reranker import SemanticReranker
from services.session_intent_service import session_intent_service
from services.budget_service import BudgetService


class ShoppingCopilot:
    """
    AI Shopping Copilot.

    Routes user requests to the appropriate
    discovery/recommendation capability.
    """

    def __init__(self):
        self.recommender = RecommendationEngine()
        self.intent_detector = IntentDetector()
        self.reranker = SemanticReranker()
        self.budget_service = BudgetService()

    async def chat(
        self,
        message: str,
        session_id: str | None = None
    ):

        # -----------------------------------------------------
        # 1. DETECT USER INTENT
        # -----------------------------------------------------

        intent = self.intent_detector.detect_intent(message)

        session_intent = None

        if session_id:
            session_intent = (
                await session_intent_service.get_session_intent(
                    session_id
                )
            )

        intent_name = intent.get(
            "intent",
            "semantic_search"
        )

        tool = intent.get(
            "tool",
            "semantic_search"
        )

        # -----------------------------------------------------
        # 2. BUDGET SEARCH
        # -----------------------------------------------------

        if intent_name == "budget_search":

            result = await self.budget_service.search(
                message,
                page_size=5
            )

            if not result.get("success"):
                return {
                    "response": result.get(
                        "message",
                        "I couldn't process your budget request."
                    ),
                    "intent": intent,
                    "session_intent": session_intent,
                    "tool": "budget",
                    "recommendations": []
                }

            products = result.get("items", [])

            response = (
                f"I found {len(products)} products "
                f"within your budget of "
                f"{result['max_price']:.0f} "
                f"{result['currency']}."
            )

            return {
                "response": response,
                "intent": intent,
                "session_intent": session_intent,
                "tool": "budget",
                "budget": {
                    "currency": result["currency"],
                    "max_price": result["max_price"]
                },
                "recommendations": products
            }

        # -----------------------------------------------------
        # 3. RECOMMENDATION REQUEST
        # -----------------------------------------------------

        if intent_name == "recommendation":

            recommendations = await self.recommender.recommend(
                message,
                limit=5
            )

            response = (
                f"I found {len(recommendations)} "
                f"personalized recommendations for you."
            )

            return {
                "response": response,
                "intent": intent,
                "session_intent": session_intent,
                "tool": "recommendation",
                "recommendations": recommendations
            }

        # -----------------------------------------------------
        # 4. SEMANTIC / OCCASION SEARCH
        # -----------------------------------------------------

        candidates = await semantic_search(
            message,
            top_k=100
        )

        products = self.reranker.rerank(
            query=message,
            results=candidates,
            limit=5,
            max_category_ratio=0.35,
            session_intent=session_intent
        )

        # -----------------------------------------------------
        # 5. RESPONSE
        # -----------------------------------------------------

        if intent_name == "occasion_search":

            response = (
                f"I found {len(products)} products "
                f"that match your occasion and style."
            )

        else:

            response = (
                f"I found {len(products)} products "
                f"that best match your request."
            )

        return {
            "response": response,
            "intent": intent,
            "session_intent": session_intent,
            "tool": tool,
            "recommendations": products
        }