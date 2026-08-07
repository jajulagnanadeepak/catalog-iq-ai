"""
Auth routes — POST /auth/signup and POST /auth/login.
Provided as part of the clean backend scaffold.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from dependencies import get_db
from models.schemas import SignupRequest, LoginRequest, TokenResponse
from models.user import UserInDB
from utils.security import hash_password, verify_password
from utils.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
async def signup(body: SignupRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    col = db["users"]
    existing = await col.find_one({"email": body.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user_doc = UserInDB(
        email=body.email,
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
    ).model_dump()

    result = await col.insert_one(user_doc)
    token = create_access_token({"sub": str(result.inserted_id), "email": body.email})
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT",
)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    col = db["users"]
    user = await col.find_one({"email": body.email})

    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": str(user["_id"]), "email": user["email"]})
    return TokenResponse(access_token=token)
