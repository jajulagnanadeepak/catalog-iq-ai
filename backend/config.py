
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB
    mongodb_url: str = Field(
        default="mongodb://localhost:27017",
        alias="MONGODB_URL",
    )

    database_name: str = Field(
        default="CatalogIQ",
        alias="DATABASE_NAME",
    )

    # JWT
    jwt_secret: str = Field(
        default="change-me-secret",
        alias="JWT_SECRET",
    )

    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # App
    app_env: str = Field(
        default="development",
        alias="APP_ENV",
    )

    allowed_origins: list[str] = [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


settings = Settings()
