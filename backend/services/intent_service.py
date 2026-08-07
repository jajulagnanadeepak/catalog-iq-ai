"""
IntentService — rule-based NLU intent classification.
Placeholder for future LLM-powered intent extraction (Phase 3).
The interface is stable — swap _classify() with an LLM call when ready.
"""

import re
from models.schemas import IntentPayload, IntentResult, IntentEntity


# Intent keyword mappings
_INTENT_RULES = [
    ("product_discovery", ["find", "show", "search", "looking for", "need", "want", "recommend"]),
    ("price_inquiry", ["cheap", "affordable", "expensive", "budget", "price", "cost", "under", "less than"]),
    ("style_advice", ["outfit", "style", "wear", "occasion", "capsule", "wardrobe", "match"]),
    ("category_browse", ["jacket", "shirt", "shoes", "bag", "trousers", "coat", "top", "knitwear"]),
    ("comparison", ["compare", "vs", "versus", "difference", "better", "best"]),
]

# Category extraction keywords
_CATEGORIES = ["outerwear", "tops", "trousers", "footwear", "bags", "swimwear", "knitwear"]

# Budget pattern: "under $300", "less than 150", "$200"
_BUDGET_PATTERN = re.compile(r"(?:under|less than|below|around|up to)?\s*\$?\s*(\d+)", re.IGNORECASE)


class IntentService:
    def classify(self, payload: IntentPayload) -> IntentResult:
        """
        Classify user query intent using keyword rules.
        Returns intent label, confidence, and extracted entities.
        TODO (Phase 3): Replace with LLM-based NLU for higher accuracy.
        """
        query = payload.query.lower()
        intent, confidence = self._classify_intent(query)
        entities = self._extract_entities(query)

        return IntentResult(
            intent=intent,
            confidence=confidence,
            entities=entities,
        )

    @staticmethod
    def _classify_intent(query: str) -> tuple[str, float]:
        """Match query against rule keyword sets. Returns (intent, confidence)."""
        scores: dict[str, int] = {}
        for intent, keywords in _INTENT_RULES:
            hits = sum(1 for kw in keywords if kw in query)
            if hits:
                scores[intent] = hits

        if not scores:
            return "general_browse", 0.55

        best = max(scores, key=lambda k: scores[k])
        # Cap confidence: more keyword hits = higher confidence, max 0.96
        confidence = min(0.55 + scores[best] * 0.12, 0.96)
        return best, round(confidence, 2)

    @staticmethod
    def _extract_entities(query: str) -> list[IntentEntity]:
        """Extract category and budget entities from the query."""
        entities: list[IntentEntity] = [IntentEntity(label="query", value=query)]

        # Category entity
        for cat in _CATEGORIES:
            if cat in query:
                entities.append(IntentEntity(label="category", value=cat.title()))
                break

        # Budget entity
        match = _BUDGET_PATTERN.search(query)
        if match:
            entities.append(IntentEntity(label="budget", value=f"under ${match.group(1)}"))

        return entities
