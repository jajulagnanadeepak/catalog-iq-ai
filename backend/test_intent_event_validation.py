import pytest
from pydantic import ValidationError
from models.schemas import IntentEventPayload


def test_valid_event_payload():
    payload = IntentEventPayload(
        session_id="session-123",
        event_type="view",
        category=" Shirts ",
        product_id="product-123",
    )
    assert payload.session_id == "session-123"
    assert payload.event_type == "view"


def test_session_id_is_trimmed():
    payload = IntentEventPayload(
        session_id="  session-123  ",
        event_type="click",
    )
    assert payload.session_id == "session-123"


@pytest.mark.parametrize("event_type", [
    "view", "click", "wishlist", "cart", "purchase"
])
def test_supported_event_types(event_type):
    payload = IntentEventPayload(
        session_id="session-123",
        event_type=event_type,
    )
    assert payload.event_type == event_type


def test_invalid_event_type_rejected():
    with pytest.raises(ValidationError):
        IntentEventPayload(
            session_id="session-123",
            event_type="admin",
        )


@pytest.mark.parametrize("session_id", ["", "   "])
def test_empty_session_id_rejected(session_id):
    with pytest.raises(ValidationError):
        IntentEventPayload(
            session_id=session_id,
            event_type="view",
        )


def test_oversized_session_id_rejected():
    with pytest.raises(ValidationError):
        IntentEventPayload(
            session_id="s" * 129,
            event_type="view",
        )


def test_oversized_category_rejected():
    with pytest.raises(ValidationError):
        IntentEventPayload(
            session_id="session-123",
            event_type="view",
            category="c" * 101,
        )


def test_oversized_product_id_rejected():
    with pytest.raises(ValidationError):
        IntentEventPayload(
            session_id="session-123",
            event_type="view",
            product_id="p" * 129,
        )
