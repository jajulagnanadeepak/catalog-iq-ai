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
            "session_id",
            name="session_id_idx",
        )

        await collection.create_index(
            [
                ("session_id", 1),
                ("created_at", -1),
            ],
            name="session_created_at_idx",
        )

        await collection.create_index(
            "created_at",
            expireAfterSeconds=30 * 24 * 60 * 60,
            name="session_events_ttl_30_days",
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

    
    async def get_session_intent(self, session_id: str):
        db = get_database()
        collection = db[self.collection_name]

        pipeline = [
            {"$match": {"session_id": session_id}},
            {
                "$group": {
                    "_id": "$category",
                    "score": {"$sum": "$score"},
                    "event_count": {"$sum": 1},
                }
            },
        ]

        results = await collection.aggregate(pipeline).to_list(length=1000)

        total = 0.0
        category_scores = {}
        event_count = 0

        for item in results:
            total += float(item.get("score", 0))
            event_count += int(item.get("event_count", 0))

            category = item.get("_id")
            if category:
                category_scores[category] = float(item.get("score", 0))

        primary_category = None
        primary_score = 0.0

        if category_scores:
            primary_category, primary_score = max(
                category_scores.items(),
                key=lambda item: item[1],
            )

        confidence = 0.0
        if total > 0 and primary_score > 0:
            confidence = min(primary_score / total, 0.99)

        return {
            "session_id": session_id,
            "total_intent_score": total,
            "primary_category": primary_category,
            "primary_category_score": primary_score,
            "confidence": round(confidence, 2),
            "category_scores": category_scores,
            "event_count": event_count,
        }



session_intent_service = SessionIntentService()