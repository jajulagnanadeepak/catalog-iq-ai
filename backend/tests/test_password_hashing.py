"""WS-B: password hashing with the bcrypt library directly (no Passlib).

No MongoDB: the auth endpoints run in a bare FastAPI app with ``get_db``
overridden by an in-memory mock. All passwords are throwaway fixtures.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import bcrypt
import pytest
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.auth import router as auth_router
from dependencies import get_db
from utils.jwt import verify_token
from utils.security import (
    BCRYPT_MAX_PASSWORD_BYTES,
    hash_password,
    password_byte_length,
    verify_password,
)

# ---------------------------------------------------------------------------
# Legacy hashes created by the previous implementation, i.e. Passlib 1.7.4
# CryptContext(schemes=["bcrypt"]) with bcrypt 4.0.1 (the old backend/.venv).
# Passlib + bcrypt 4 hashed only the first 72 UTF-8 bytes of a password.
# ---------------------------------------------------------------------------

LEGACY_SHORT_PW = "Legacy-Fixture-Pass-01"
LEGACY_SHORT_HASH = "$2b$12$oL2DKV2kZ90SrIdJnUKxCeM49r034UqmseHNbQNnP.8J2uvWL1BSq"

LEGACY_LONG_PW = "L" * 100  # 100 bytes; stored hash covers "L" * 72
LEGACY_LONG_HASH = "$2b$12$XGBOBmoqHWL2CNFVJjDBROyDR4X667AArKnmVHHcB3nDEwQ02DDi6"

LEGACY_UNICODE_PW = "pässwörd-тест-密码-🔐"
LEGACY_UNICODE_HASH = "$2b$12$B8du1.bT67CLb/b37z3R7uZmpfdlwUau1bsuCCBX9CT4QoqYWjyQ2"

# 81 bytes; byte 72 is the first byte of a two-byte "é", so the legacy hash
# covers "a" + "é" * 35 + b"\xc3".
LEGACY_SPLIT_PW = "a" + "é" * 40
LEGACY_SPLIT_HASH = "$2b$12$Y2CrOY0JvHGc2alMBBXnK.YjoRXiFtE9JhmXZ0P3WHG/woXKWWyiO"

LEGACY_VECTORS = [
    (LEGACY_SHORT_PW, LEGACY_SHORT_HASH),
    (LEGACY_LONG_PW, LEGACY_LONG_HASH),
    (LEGACY_UNICODE_PW, LEGACY_UNICODE_HASH),
    (LEGACY_SPLIT_PW, LEGACY_SPLIT_HASH),
]
LEGACY_IDS = ["short", "long-ascii-100B", "unicode", "unicode-split-at-72"]

VALID_PW = "Fixture-Password-123!"


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------

def test_hash_is_bcrypt_2b_with_cost_12():
    hashed = hash_password(VALID_PW)

    assert hashed.startswith("$2b$12$")
    assert len(hashed) == 60
    assert hashed != VALID_PW
    assert bcrypt.checkpw(VALID_PW.encode("utf-8"), hashed.encode("ascii"))


def test_hashes_use_random_salts():
    first, second = hash_password(VALID_PW), hash_password(VALID_PW)

    assert first != second
    assert first[:29] != second[:29]  # "$2b$12$" + 22-char salt
    assert verify_password(VALID_PW, first)
    assert verify_password(VALID_PW, second)


def test_correct_password_verifies():
    assert verify_password(VALID_PW, hash_password(VALID_PW)) is True


def test_incorrect_password_fails():
    hashed = hash_password(VALID_PW)

    assert verify_password("Fixture-Password-124!", hashed) is False
    assert verify_password("", hashed) is False


@pytest.mark.parametrize("password,legacy_hash", LEGACY_VECTORS, ids=LEGACY_IDS)
def test_existing_passlib_hashes_still_verify(password, legacy_hash):
    assert verify_password(password, legacy_hash) is True
    assert verify_password(password + "x", legacy_hash) is (
        password_byte_length(password) >= BCRYPT_MAX_PASSWORD_BYTES
    )
    assert verify_password("Wrong-" + password, legacy_hash) is False


def test_72_byte_password_is_hashed_and_verified():
    password = "a" * 72
    assert password_byte_length(password) == BCRYPT_MAX_PASSWORD_BYTES

    hashed = hash_password(password)

    assert verify_password(password, hashed) is True
    assert verify_password("a" * 71, hashed) is False


def test_73_byte_password_cannot_be_hashed():
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("a" * 73)


def test_73_byte_password_verifies_against_its_72_byte_prefix():
    # Legacy-compatible login: only the first 72 bytes take part.
    hashed = hash_password("a" * 72)

    assert verify_password("a" * 73, hashed) is True


def test_128_character_password():
    password = "L" * 128

    with pytest.raises(ValueError):
        hash_password(password)
    # A legacy user whose password was longer than 72 bytes can still log in.
    assert verify_password(password, LEGACY_LONG_HASH) is True


def test_length_is_measured_in_utf8_bytes_not_characters():
    assert password_byte_length("é" * 36) == 72
    assert password_byte_length("é" * 37) == 74
    assert password_byte_length("🔐" * 18) == 72

    hashed = hash_password("é" * 36)
    assert verify_password("é" * 36, hashed) is True

    with pytest.raises(ValueError):
        hash_password("é" * 37)  # 37 characters, 74 bytes
    with pytest.raises(ValueError):
        hash_password("🔐" * 19)  # 19 characters, 76 bytes


def test_passwords_differing_only_after_byte_72_are_equivalent():
    assert verify_password("L" * 72 + "completely different tail", LEGACY_LONG_HASH)

    # Same first 72 bytes, even though byte 72 splits a character.
    assert verify_password("a" + "é" * 35 + "éZZZZ", LEGACY_SPLIT_HASH)


def test_passwords_differing_before_byte_72_are_not_equivalent():
    assert not verify_password("L" * 71 + "M" + "L" * 28, LEGACY_LONG_HASH)
    assert not verify_password("b" + "é" * 40, LEGACY_SPLIT_HASH)


@pytest.mark.parametrize(
    "stored",
    [
        "",
        None,
        "not-a-bcrypt-hash",
        "$2b$12$tooshort",
        "$2b$12$" + "!" * 53,
        "$2b$12$" + "é" * 53,  # non-ASCII
        LEGACY_SHORT_HASH[:-1],
        "pbkdf2_sha256$600000$salt$digest",
        123,
        b"$2b$12$bytes-are-not-stored",
    ],
    ids=["empty", "none", "garbage", "truncated-prefix", "bad-chars", "non-ascii",
         "one-char-short", "other-scheme", "int", "bytes"],
)
def test_malformed_empty_or_missing_hash_fails_without_raising(stored):
    assert verify_password(LEGACY_SHORT_PW, stored) is False


def test_non_string_password_fails_without_raising():
    assert verify_password(None, LEGACY_SHORT_HASH) is False


@pytest.mark.parametrize(
    "password",
    ["ab\ud800cd", "\udfff", "Fixture-\udc80-1"],
    ids=["high-surrogate", "low-surrogate-only", "lone-low-surrogate"],
)
def test_password_that_is_not_valid_utf8_fails_without_raising(password):
    # Lone surrogates cannot be UTF-8 encoded; verification must fail closed.
    assert verify_password(password, LEGACY_SHORT_HASH) is False


@pytest.mark.parametrize(
    "error",
    [RuntimeError("unexpected"), OSError("backend"), MemoryError()],
    ids=["runtime-error", "os-error", "memory-error"],
)
def test_unexpected_bcrypt_error_fails_closed(monkeypatch, error):
    def broken_checkpw(password, hashed_password):
        raise error

    monkeypatch.setattr(bcrypt, "checkpw", broken_checkpw)

    assert verify_password(LEGACY_SHORT_PW, LEGACY_SHORT_HASH) is False


# ---------------------------------------------------------------------------
# Endpoints (HTTP status codes, no MongoDB)
# ---------------------------------------------------------------------------

@pytest.fixture
def users():
    collection = MagicMock()
    collection.find_one = AsyncMock(return_value=None)
    collection.insert_one = AsyncMock(
        return_value=SimpleNamespace(inserted_id=ObjectId())
    )
    return collection


@pytest.fixture
def client(users):
    app = FastAPI()
    app.include_router(auth_router)
    app.dependency_overrides[get_db] = lambda: {"users": users}
    return TestClient(app)


@pytest.mark.parametrize(
    "password",
    [
        "a" * 73,             # 73 bytes
        "L" * 128,            # 128 characters (allowed by max_length)
        "é" * 37,             # 37 characters, 74 bytes
        "Pass-" + "🔐" * 17,  # 22 characters, 73 bytes
    ],
    ids=["73-bytes", "128-chars", "37-chars-74-bytes", "22-chars-73-bytes"],
)
def test_signup_rejects_passwords_over_72_bytes_with_422(client, users, password):
    response = client.post(
        "/auth/signup",
        json={"email": "fixture@example.com", "password": password},
    )

    assert response.status_code == 422
    assert "72 bytes" in response.text
    users.insert_one.assert_not_awaited()


@pytest.mark.parametrize(
    "password", [VALID_PW, "a" * 72, "é" * 36], ids=["typical", "72-bytes", "36-chars-72-bytes"]
)
def test_signup_valid_password_succeeds(client, users, password):
    response = client.post(
        "/auth/signup",
        json={"email": "Fixture@Example.com", "password": password},
    )

    assert response.status_code == 201
    assert verify_token(response.json()["access_token"]).email == "fixture@example.com"

    stored = users.insert_one.call_args.args[0]["hashed_password"]
    assert stored.startswith("$2b$12$")
    assert verify_password(password, stored)


@pytest.mark.parametrize("password,legacy_hash", LEGACY_VECTORS, ids=LEGACY_IDS)
def test_login_with_existing_hash_succeeds(client, users, password, legacy_hash):
    user_id = ObjectId()
    users.find_one.return_value = {
        "_id": user_id,
        "email": "fixture@example.com",
        "hashed_password": legacy_hash,
        "is_active": True,
    }

    response = client.post(
        "/auth/login",
        json={"email": "fixture@example.com", "password": password},
    )

    assert response.status_code == 200
    assert verify_token(response.json()["access_token"]).user_id == str(user_id)


def test_login_with_wrong_password_for_existing_hash_is_401(client, users):
    users.find_one.return_value = {
        "_id": ObjectId(),
        "email": "fixture@example.com",
        "hashed_password": LEGACY_SHORT_HASH,
        "is_active": True,
    }

    response = client.post(
        "/auth/login",
        json={"email": "fixture@example.com", "password": "Wrong-Password-1"},
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "stored",
    ["", None, "not-a-bcrypt-hash", "$2b$12$tooshort"],
    ids=["empty", "none", "garbage", "truncated"],
)
def test_login_with_malformed_stored_hash_is_401_not_500(client, users, stored):
    users.find_one.return_value = {
        "_id": ObjectId(),
        "email": "fixture@example.com",
        "hashed_password": stored,
        "is_active": True,
    }

    response = client.post(
        "/auth/login",
        json={"email": "fixture@example.com", "password": LEGACY_SHORT_PW},
    )

    assert response.status_code == 401


def test_login_with_missing_stored_hash_is_401_not_500(client, users):
    users.find_one.return_value = {
        "_id": ObjectId(),
        "email": "fixture@example.com",
        "is_active": True,
    }

    response = client.post(
        "/auth/login",
        json={"email": "fixture@example.com", "password": LEGACY_SHORT_PW},
    )

    assert response.status_code == 401
