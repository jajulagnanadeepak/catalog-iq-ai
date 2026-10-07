from ai.intent_detector import IntentDetector


detector = IntentDetector()

queries = [
    "shirts under $200",
    "shirts under ₹2000",
    "shirts below €100",
    "shoes less than £150",
    "shirts under 200",
    "black office wear",
    "recommend some shirts",
]

for query in queries:
    print(f"\nQuery: {query}")
    print(detector.detect_intent(query))