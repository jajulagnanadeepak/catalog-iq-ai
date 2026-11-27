"""Configuration parsing and production safety guards (C-06, H-13a)."""

import pytest
from pydantic import ValidationError

from config import Settings, parse_origins

STRONG_SECRET = "x" * 48

ENV_KEYS = [
    "APP_ENV",
    "JWT_SECRET",
    "ALLOWED_ORIGINS",
    "DATABASE_NAME",
    "MONGODB_URL",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    # Never let a developer's real environment leak into these tests.
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def make(**env):
    return Settings(_env_file=None, **env)


def test_comma_separated_origins_parse():
    s = make(ALLOWED_ORIGINS="http://a.test, http://b.test/ ,")
    assert s.allowed_origins == ["http://a.test", "http://b.test"]


def test_json_list_origins_still_parse():
    s = make(ALLOWED_ORIGINS='["http://a.test", "http://b.test"]')
    assert s.allowed_origins == ["http://a.test", "http://b.test"]


def test_origins_from_environment_variable(monkeypatch):
    # The exact form documented in .env.example (previously crashed startup).
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
    s = Settings(_env_file=None)
    assert s.allowed_origins == ["http://localhost:5173", "http://localhost:3000"]


def test_default_origins_unchanged():
    s = make()
    assert "http://localhost:8080" in s.allowed_origins
    assert "http://localhost:5173" in s.allowed_origins
    assert len(s.allowed_origins) == 8


def test_database_name_default_unchanged():
    assert make().database_name == "CatalogIQ"


def test_development_tolerates_default_secret():
    s = make()
    assert s.app_env == "development"
    assert s.jwt_secret == "change-me-secret"


@pytest.mark.parametrize(
    "secret",
    ["change-me-secret", "change-me-to-a-long-random-secret", "short-secret"],
)
def test_production_rejects_weak_or_placeholder_secret(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        make(APP_ENV="production", JWT_SECRET=secret, ALLOWED_ORIGINS="https://shop.test")


def test_production_rejects_missing_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        make(APP_ENV="production", ALLOWED_ORIGINS="https://shop.test")


def test_production_rejects_wildcard_origin():
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        make(APP_ENV="production", JWT_SECRET=STRONG_SECRET, ALLOWED_ORIGINS="*")


def test_production_accepts_strong_config():
    s = make(
        APP_ENV="production",
        JWT_SECRET=STRONG_SECRET,
        ALLOWED_ORIGINS="https://shop.test",
    )
    assert s.allowed_origins == ["https://shop.test"]
    assert not s.is_development


def test_error_message_does_not_leak_secret():
    with pytest.raises(ValidationError) as exc:
        make(APP_ENV="staging", JWT_SECRET="tiny-leaky-value", ALLOWED_ORIGINS="https://s.test")
    assert "tiny-leaky-value" not in str(exc.value)


def test_parse_origins_rejects_non_list_json():
    with pytest.raises(ValueError):
        parse_origins('{"a": 1}')


@pytest.mark.parametrize("bad", ["localhost:5173", "ftp://x.test", "http://ok.test,shop.test"])
def test_malformed_origins_fail_fast(bad):
    with pytest.raises(ValueError):
        parse_origins(bad)


def test_malformed_origins_rejected_by_settings():
    with pytest.raises(ValidationError):
        make(ALLOWED_ORIGINS="localhost:5173")
