
import pytest
from pydantic import ValidationError

from routes.copilot import ChatRequest


def test_valid_chat_request():
    request = ChatRequest(
        message="  Find white sneakers  ",
        session_id=" session-123 ",
    )
    assert request.message == "Find white sneakers"
    assert request.session_id == "session-123"


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message_rejected(message):
    with pytest.raises(ValidationError):
        ChatRequest(message=message)


def test_oversized_message_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(message="a" * 2001)


@pytest.mark.parametrize("session_id", ["", "   "])
def test_empty_session_id_rejected(session_id):
    with pytest.raises(ValidationError):
        ChatRequest(message="Find shoes", session_id=session_id)


def test_oversized_session_id_rejected():
    with pytest.raises(ValidationError):
        ChatRequest(
            message="Find shoes",
            session_id="s" * 129,
        )


def test_session_id_can_be_omitted():
    request = ChatRequest(message="Find shoes")
    assert request.session_id is None
