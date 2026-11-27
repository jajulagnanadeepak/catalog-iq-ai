
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent

# Environments in which the insecure development defaults are tolerated.
DEV_ENVIRONMENTS = {"development", "dev", "local", "test"}

# Placeholder secrets shipped in code or in .env.example. Never valid outside dev.
KNOWN_PLACEHOLDER_SECRETS = {
    "change-me-secret",
    "change-me-to-a-long-random-secret",
}

MIN_JWT_SECRET_LENGTH = 32

DEFAULT_ALLOWED_ORIGINS = ",".join(
    [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
)


def parse_origins(raw: str) -> list[str]:
    """
    Parse ALLOWED_ORIGINS.

    Accepts the comma-separated form documented in .env.example
    ("http://a,http://b") and, for backwards compatibility, a JSON list
    ('["http://a", "http://b"]'). Blank entries and trailing slashes are removed.
    """
    value = (raw or "").strip()

    if value.startswith("["):
        import json

        items = json.loads(value)
        if not isinstance(items, list):
            raise ValueError("ALLOWED_ORIGINS JSON value must be a list")
    else:
        items = value.split(",")

    origins = []
    for item in items:
        origin = str(item).strip().rstrip("/")
        if not origin:
            continue
        if origin != "*" and not origin.startswith(("http://", "https://")):
            raise ValueError(
                f"ALLOWED_ORIGINS entry {origin!r} must start with http:// or https://"
            )
        origins.append(origin)
    return origins


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
        # Never echo configuration values (secrets, DB URLs) in error messages.
        hide_input_in_errors=True,
    )

    # MongoDB
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        alias="MONGODB_URL",
    )

    # NOTE: MongoDB database names are case-sensitive and Atlas refuses two
    # names that differ only by case. The code default is unchanged on purpose;
    # set DATABASE_NAME explicitly to the database that holds your data.
    database_name: str = Field(
        default="CatalogIQ",
        alias="DATABASE_NAME",
    )

    # JWT
    jwt_secret: str = Field(
        default="change-me-secret",
        alias="JWT_SECRET",
    )

    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    # App
    app_env: str = Field(
        default="development",
        alias="APP_ENV",
    )

    # Stored as a raw string so the comma-separated form in .env.example
    # parses (pydantic-settings would otherwise require JSON for list fields).
    allowed_origins_raw: str = Field(
        default=DEFAULT_ALLOWED_ORIGINS,
        alias="ALLOWED_ORIGINS",
    )

    @property
    def allowed_origins(self) -> list[str]:
        return parse_origins(self.allowed_origins_raw)

    @property
    def is_development(self) -> bool:
        return self.app_env.strip().lower() in DEV_ENVIRONMENTS

    @model_validator(mode="after")
    def _validate_for_environment(self) -> "Settings":
        # Fail fast on malformed origins in every environment.
        origins = parse_origins(self.allowed_origins_raw)

        if self.is_development:
            return self

        problems = []

        if self.jwt_secret in KNOWN_PLACEHOLDER_SECRETS:
            problems.append("JWT_SECRET is a placeholder value")
        elif len(self.jwt_secret) < MIN_JWT_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters"
            )

        if "*" in origins:
            problems.append("ALLOWED_ORIGINS must not contain '*' outside development")

        if not origins:
            problems.append("ALLOWED_ORIGINS must list at least one origin")

        if problems:
            raise ValueError(
                f"Unsafe configuration for APP_ENV={self.app_env!r}: "
                + "; ".join(problems)
                + ". Generate a secret with: openssl rand -base64 48"
            )

        return self


settings = Settings()
