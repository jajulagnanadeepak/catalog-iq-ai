from fastapi import APIRouter, HTTPException

from models.schemas import (
    IntentPayload,
    IntentEventPayload,
)

from services.intent_service import IntentService

from services.session_intent_service import (
    session_intent_service,
)


router = APIRouter(
    prefix="/intent",
    tags=["Intent"],
)

_service = IntentService()


@router.post(
    "",
    summary="Classify user query intent",
)
async def classify_intent(
    payload: IntentPayload,
):
    result = _service.classify(payload)

    return result.model_dump()


@router.post(
    "/event",
    summary="Record user behavior event",
)
async def record_intent_event(
    payload: IntentEventPayload,
):

    try:

        result = await session_intent_service.record_event(
            session_id=payload.session_id,
            event_type=payload.event_type,
            category=payload.category,
            product_id=payload.product_id,
        )

        return {
            "success": True,
            "event": {
                "type": payload.event_type,
                "category": payload.category,
                "product_id": payload.product_id,
            },
            "intent": result,
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )