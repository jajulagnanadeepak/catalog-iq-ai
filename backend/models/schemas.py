from typing import Optional
from pydantic import BaseModel, EmailStr


# ── Auth schemas ────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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
