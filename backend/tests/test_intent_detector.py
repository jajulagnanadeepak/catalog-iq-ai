"""WS-E3.11: direct regression tests for ai.intent_detector.IntentDetector.

The queries come from the retired print-only manual script (Phase 1 WS-E3.11).
They pin the detector's current behaviour; pure in-memory checks, no I/O.
"""

import pytest

from ai.intent_detector import IntentDetector

BUDGET = {"intent": "budget_search", "confidence": 0.95, "tool": "budget"}
OCCASION = {"intent": "occasion_search", "confidence": 0.90, "tool": "semantic_search"}
RECOMMENDATION = {"intent": "recommendation", "confidence": 0.92, "tool": "recommendation"}
SEMANTIC = {"intent": "semantic_search", "confidence": 0.80, "tool": "semantic_search"}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("shirts under $200", BUDGET),
        ("shirts under ₹2000", BUDGET),
        ("shirts below €100", BUDGET),
        ("shoes less than £150", BUDGET),
        ("shirts under 200", BUDGET),
        # "office" (occasion) is checked before "wear" (styling).
        ("black office wear", OCCASION),
        ("recommend some shirts", RECOMMENDATION),
    ],
)
def test_detect_intent_for_known_queries(query, expected):
    assert IntentDetector().detect_intent(query) == expected


def test_detect_intent_defaults_to_semantic_search():
    assert IntentDetector().detect_intent("navy linen trousers") == SEMANTIC
