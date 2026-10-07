import re


class IntentDetector:

    def detect_intent(self, query: str) -> dict:

        query = query.lower().strip()

        # -----------------------------------------------------
        # BUDGET
        # -----------------------------------------------------

        budget_pattern = (
            r"(?:"
            r"under|below|less than"
            r")\s*"
            r"(?:₹|\$|€|£|rs\.?|usd|eur|gbp|rupees?)?\s*"
            r"\d[\d,]*(?:\.\d+)?"
        )

        currency_pattern = (
            r"(?:₹|\$|€|£|rs\.?|usd|eur|gbp|rupees?)\s*"
            r"\d[\d,]*(?:\.\d+)?"
        )

        if (
            re.search(budget_pattern, query)
            or re.search(currency_pattern, query)
        ):
            return {
                "intent": "budget_search",
                "confidence": 0.95,
                "tool": "budget"
            }

        # -----------------------------------------------------
        # VISUAL SEARCH
        # -----------------------------------------------------

        if any(
            word in query
            for word in [
                "similar to this",
                "similar product",
                "similar item",
                "like this",
                "look like this"
            ]
        ):
            return {
                "intent": "visual_search",
                "confidence": 0.94,
                "tool": "visual_search"
            }

        # -----------------------------------------------------
        # RECOMMENDATION
        # -----------------------------------------------------

        if any(
            word in query
            for word in [
                "recommend",
                "suggest",
                "best",
                "popular"
            ]
        ):
            return {
                "intent": "recommendation",
                "confidence": 0.92,
                "tool": "recommendation"
            }

        # -----------------------------------------------------
        # OCCASION
        # -----------------------------------------------------

        if any(
            word in query
            for word in [
                "office",
                "formal",
                "business",
                "professional",
                "casual",
                "party",
                "wedding",
                "gym"
            ]
        ):
            return {
                "intent": "occasion_search",
                "confidence": 0.90,
                "tool": "semantic_search"
            }

        # -----------------------------------------------------
        # SEASONAL
        # -----------------------------------------------------

        if any(
            word in query
            for word in [
                "summer",
                "winter",
                "rain",
                "monsoon"
            ]
        ):
            return {
                "intent": "seasonal_search",
                "confidence": 0.90,
                "tool": "seasonal"
            }

        # -----------------------------------------------------
        # STYLING
        # -----------------------------------------------------

        if any(
            word in query
            for word in [
                "wear",
                "outfit",
                "style",
                "match",
                "pair"
            ]
        ):
            return {
                "intent": "styling",
                "confidence": 0.93,
                "tool": "stylist"
            }

        # -----------------------------------------------------
        # DEFAULT
        # -----------------------------------------------------

        return {
            "intent": "semantic_search",
            "confidence": 0.80,
            "tool": "semantic_search"
        }