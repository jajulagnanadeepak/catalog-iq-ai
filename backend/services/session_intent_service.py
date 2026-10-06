from datetime import datetime, timezone

from database.connection import get_database


EVENT_WEIGHTS = {
    "view": 2,
    "click": 5,
    "wishlist": 6,
    "cart": 8,
    "purchase": 10,
}


class SessionIntentService:

    def __init__(self):
        self.collection_name = "session_events"

    async def _ensure_indexes(self):
        db = get_database()
        collection = db[self.collection_name]

        await collection.create_index(
            "session_id"
        )

        await collection.create_index(
            [
                ("session_id", 1),
                ("created_at", -1),
            ]
        )

    async def record_event(
        self,
        session_id: str,
        event_type: str,
        category: str | None = None,
        product_id: str | None = None,
    ):
        event_type = event_type.lower().strip()

        if event_type not in EVENT_WEIGHTS:
            raise ValueError(
                f"Unsupported event type: {event_type}"
            )

        score = EVENT_WEIGHTS[event_type]

        category_normalized = None

        if category:
            category_normalized = (
                category.lower().strip()
            )

        event = {
            "session_id": session_id,
            "event_type": event_type,
            "score": score,
            "category": category_normalized,
            "product_id": product_id,
            "created_at": datetime.now(
                timezone.utc
            ),
        }

        db = get_database()

        await db[
            self.collection_name
        ].insert_one(event)

        return await self.get_session_intent(
            session_id
        )

    async def get_session_intent(
        self,
        session_id: str,
    ):
        db = get_database()

        collection = db[
            self.collection_name
        ]

        events = await collection.find(
            {
                "session_id": session_id
            }
        ).to_list(length=None)

        total = 0
        category_scores = {}

        for event in events:

            score = float(
                event.get("score", 0)
            )

            total += score

            category = event.get(
                "category"
            )

            if category:
                category_scores[category] = (
                    category_scores.get(
                        category,
                        0,
                    )
                    + score
                )

        primary_category = None
        primary_score = 0

        if category_scores:

            primary_category, primary_score = max(
                category_scores.items(),
                key=lambda item: item[1],
            )

        confidence = 0.0

        if total > 0 and primary_score > 0:
            confidence = min(
                primary_score / total,
                0.99,
            )

        return {
            "session_id": session_id,
            "total_intent_score": total,
            "primary_category": primary_category,
            "primary_category_score": primary_score,
            "confidence": round(
                confidence,
                2,
            ),
            "category_scores": category_scores,
        }


session_intent_service = SessionIntentService()