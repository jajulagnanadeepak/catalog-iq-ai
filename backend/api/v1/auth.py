
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from dependencies import get_db, get_required_user
from models.schemas import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    TokenData,
    UserProfile,
    UpdateProfileRequest,
)
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


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get current authenticated user profile",
)
async def get_me(
    token_data: TokenData = Depends(get_required_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = token_data.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
    user = await db["users"].find_one(query)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    return UserProfile(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        preferred_size=user.get("preferred_size"),
        style_keywords=user.get("style_keywords"),
        is_active=user.get("is_active", True),
    )


@router.put(
    "/profile",
    response_model=UserProfile,
    summary="Update current authenticated user profile",
)
async def update_profile(
    body: UpdateProfileRequest,
    token_data: TokenData = Depends(get_required_user),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    user_id = token_data.user_id
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
    user = await db["users"].find_one(query)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    update_fields = {}
    if body.full_name is not None:
        update_fields["full_name"] = body.full_name.strip()
    if body.preferred_size is not None:
        update_fields["preferred_size"] = body.preferred_size.strip()
    if body.style_keywords is not None:
        update_fields["style_keywords"] = body.style_keywords.strip()

    if update_fields:
        await db["users"].update_one(query, {"$set": update_fields})
        user = await db["users"].find_one(query)

    return UserProfile(
        id=str(user["_id"]),
        email=user["email"],
        full_name=user.get("full_name"),
        preferred_size=user.get("preferred_size"),
        style_keywords=user.get("style_keywords"),
        is_active=user.get("is_active", True),
    )
