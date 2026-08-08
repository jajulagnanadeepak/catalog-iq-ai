import re


class IntentDetector:
    """
    Detects what the user is trying to do from a search query.
    """

    def detect_intent(self, query: str) -> dict:
        query = query.lower().strip()

        budget_pattern = r"(under|below|less than|₹|rs|rupees)\s*\d+"

        if re.search(budget_pattern, query):
            return {
                "intent": "budget_search",
                "confidence": 0.95
            }

        if any(word in query for word in [
            "recommend",
            "suggest",
            "best",
            "popular"
        ]):
            return {
                "intent": "recommendation",
                "confidence": 0.92
            }

        if any(word in query for word in [
            "office",
            "formal",
            "casual",
            "party",
            "wedding",
            "gym"
        ]):
            return {
                "intent": "occasion_search",
                "confidence": 0.90
            }

        if any(word in query for word in [
            "summer",
            "winter",
            "rain",
            "monsoon"
        ]):
            return {
                "intent": "seasonal_search",
                "confidence": 0.90
            }

        if any(word in query for word in [
            "wear",
            "outfit",
            "style",
            "match"
        ]):
            return {
                "intent": "styling",
                "confidence": 0.93
            }

        return {
            "intent": "semantic_search",
            "confidence": 0.80
        }