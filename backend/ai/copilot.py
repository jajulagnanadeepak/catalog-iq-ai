from ai.recommendation_engine import RecommendationEngine


class ShoppingCopilot:
    """
    AI Shopping Copilot.
    Uses the Recommendation Engine and generates a helpful response.
    """

    def __init__(self):
        self.recommender = RecommendationEngine()

    async def chat(self, message: str):

        recommendations = await self.recommender.recommend(
            message,
            limit=5
        )

        response = (
            f"I found {len(recommendations)} products that best match your request."
        )

        return {
            "response": response,
            "recommendations": recommendations
        }