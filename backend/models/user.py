from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


class User(BaseModel):
    id: str = Field(alias="_id")
    email: EmailStr
    full_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    model_config = {"populate_by_name": True}


class UserInDB(BaseModel):
    """Stored in MongoDB — includes hashed password."""

    email: str
    full_name: Optional[str] = None
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
