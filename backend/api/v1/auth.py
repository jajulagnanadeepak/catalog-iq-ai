
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
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
    email = str(body.email).strip().lower()

    existing = await col.find_one({"email": email}, {"_id": 1})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user_doc = UserInDB(
        email=email,
        full_name=body.full_name.strip() if body.full_name else None,
        hashed_password=hash_password(body.password),
    ).model_dump()

    try:
        result = await col.insert_one(user_doc)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    token = create_access_token({
        "sub": str(result.inserted_id),
        "email": email,
    })
    return TokenResponse(access_token=token)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive a JWT",
)
async def login(body: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    email = str(body.email).strip().lower()
    user = await db["users"].find_one({"email": email})

    # Use the same error for unknown accounts and incorrect passwords.
    if not user or not verify_password(
        body.password, user.get("hashed_password", "")
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive. Please contact support.",
        )

    token = create_access_token({
        "sub": str(user["_id"]),
        "email": email,
    })
    return TokenResponse(access_token=token)
