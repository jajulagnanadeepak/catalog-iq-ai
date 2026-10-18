
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId
import pytest
from fastapi import HTTPException

from api.v1.auth import signup, login
from models.schemas import SignupRequest, LoginRequest
from utils.jwt import verify_token


@pytest.fixture
def mock_db():
    db = MagicMock()
    db["users"].find_one = AsyncMock()
    db["users"].insert_one = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_signup_success(mock_db):
    user_id = ObjectId()
    mock_db["users"].find_one.return_value = None
    mock_db["users"].insert_one.return_value = SimpleNamespace(
        inserted_id=user_id
    )

    body = SignupRequest(
        email="Test@example.com",
        password="StrongPassword123!",
        full_name=" Test User ",
    )

    result = await signup(body, mock_db)

    assert result.access_token
    token_data = verify_token(result.access_token)
    assert token_data is not None
    assert token_data.user_id == str(user_id)
    assert token_data.email == "test@example.com"

    inserted_user = mock_db["users"].insert_one.call_args.args[0]
    assert inserted_user["email"] == "test@example.com"
    assert inserted_user["full_name"] == "Test User"
    assert inserted_user["hashed_password"] != body.password


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(mock_db):
    mock_db["users"].find_one.return_value = {"_id": ObjectId()}

    body = SignupRequest(
        email="test@example.com",
        password="StrongPassword123!",
    )

    with pytest.raises(HTTPException) as exc:
        await signup(body, mock_db)

    assert exc.value.status_code == 409
    mock_db["users"].insert_one.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_success(mock_db):
    user_id = ObjectId()
    from utils.security import hash_password

    mock_db["users"].find_one.return_value = {
        "_id": user_id,
        "email": "test@example.com",
        "hashed_password": hash_password("StrongPassword123!"),
        "is_active": True,
    }

    body = LoginRequest(
        email="test@example.com",
        password="StrongPassword123!",
    )

    result = await login(body, mock_db)

    assert result.access_token
    token_data = verify_token(result.access_token)
    assert token_data is not None
    assert token_data.user_id == str(user_id)


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(mock_db):
    from utils.security import hash_password

    mock_db["users"].find_one.return_value = {
        "_id": ObjectId(),
        "email": "test@example.com",
        "hashed_password": hash_password("CorrectPassword123!"),
        "is_active": True,
    }

    body = LoginRequest(
        email="test@example.com",
        password="WrongPassword123!",
    )

    with pytest.raises(HTTPException) as exc:
        await login(body, mock_db)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_rejected(mock_db):
    mock_db["users"].find_one.return_value = None

    body = LoginRequest(
        email="unknown@example.com",
        password="StrongPassword123!",
    )

    with pytest.raises(HTTPException) as exc:
        await login(body, mock_db)

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_login_inactive_account_rejected(mock_db):
    from utils.security import hash_password

    mock_db["users"].find_one.return_value = {
        "_id": ObjectId(),
        "email": "test@example.com",
        "hashed_password": hash_password("StrongPassword123!"),
        "is_active": False,
    }

    body = LoginRequest(
        email="test@example.com",
        password="StrongPassword123!",
    )

    with pytest.raises(HTTPException) as exc:
        await login(body, mock_db)

    assert exc.value.status_code == 403
