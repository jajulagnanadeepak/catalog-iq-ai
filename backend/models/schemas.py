from typing import Optional,Literal
from pydantic import BaseModel, EmailStr,Field, field_validator


# ── Auth schemas ────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=100)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None



# ── Product query schemas ────────────────────────────────────────────────────

class ProductQuery(BaseModel):
    page: int = 1
    page_size: int = 8
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    sort: Optional[str] = None  # "relevance" | "price-asc" | "price-desc" | "rating"


# ── Search schemas ───────────────────────────────────────────────────────────

class SearchPayload(BaseModel):
    query: str
    page: int = 1
    page_size: int = 8
    category: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    sort: Optional[str] = None


class SearchMatch(BaseModel):
    product_id: str
    score: float


# ── Intent schemas ───────────────────────────────────────────────────────────

class IntentPayload(BaseModel):
    query: str


class IntentEntity(BaseModel):
    label: str
    value: str


class IntentResult(BaseModel):
    intent: str
    confidence: float
    entities: list[IntentEntity]

class IntentEventPayload(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    event_type: Literal["view", "click", "wishlist", "cart", "purchase"]
    category: Optional[str] = Field(default=None, max_length=100)
    product_id: Optional[str] = Field(default=None, max_length=128)

    @field_validator("session_id", mode="before")
    @classmethod
    def normalize_session_id(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value:
                raise ValueError("Session ID cannot be empty")
        return value

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("product_id", mode="before")
    @classmethod
    def normalize_product_id(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

