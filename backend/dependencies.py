"""
FastAPI dependency injection helpers.
- get_db: provides an AsyncIOMotorDatabase per request
- get_current_user: optional JWT auth — raises 401 if token is invalid
"""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorDatabase
from database.connection import get_database
from utils.jwt import verify_token
from models.schemas import TokenData

bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> AsyncIOMotorDatabase:
    """Inject the shared MongoDB database instance."""
    return get_database()


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(bearer_scheme)],
) -> Optional[TokenData]:
    """
    Optional auth dependency.
    Returns TokenData if a valid Bearer token is provided, otherwise None.
    Use `get_required_user` for protected endpoints.
    """
    if credentials is None:
        return None
    token_data = verify_token(credentials.credentials)
    return token_data


async def get_required_user(
    token_data: Annotated[Optional[TokenData], Depends(get_current_user)],
) -> TokenData:
    """Auth dependency that enforces authentication — raises 401 if missing/invalid."""
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token_data
