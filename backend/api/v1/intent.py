from fastapi import APIRouter
from models.schemas import IntentPayload
from services.intent_service import IntentService

router = APIRouter(prefix="/intent", tags=["Intent"])

_service = IntentService()  # No DB dependency — pure rule-based logic


@router.post(
    "",
    summary="Classify user query intent",
    description=(
        "Extracts intent label, confidence score, and named entities (category, budget) "
        "from a natural-language query string. "
        "Phase 3 will replace rule-based logic with an LLM call."
    ),
)
async def classify_intent(payload: IntentPayload):
    result = _service.classify(payload)
    return result.model_dump()
