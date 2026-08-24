"""
api/v1/routes/auth.py — Authentication Endpoints
==================================================
Endpoints:
    POST   /api/v1/auth/register          Create new account
    POST   /api/v1/auth/login             Obtain token pair
    POST   /api/v1/auth/refresh           Rotate refresh token
    POST   /api/v1/auth/logout            Revoke tokens
    GET    /api/v1/auth/me                Get current user profile
    PATCH  /api/v1/auth/me                Update profile
    POST   /api/v1/auth/me/password       Change password
    GET    /api/v1/auth/ping              Health check

Design:
    - Route handlers are thin — they validate input, call services,
      return responses.  No business logic lives here.
    - Domain exceptions from services are caught here and translated
      to appropriate HTTP responses.
    - Every response uses a typed Pydantic schema — no raw dicts.
"""

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.dependencies import (
    get_db,
    get_redis,
    get_current_user,
    get_current_active_user,
)
from backend.core.logging import get_logger
from backend.db.models.user import User
from backend.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
)
from backend.services import auth_service, token_service
from backend.services.auth_service import (
    AccountDisabledError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    WrongPasswordError,
)
from backend.services.token_service import (
    RefreshTokenNotFoundError,
    TokenExpiredError,
    TokenInvalidError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helper — build UserResponse from ORM User
# ---------------------------------------------------------------------------

def _build_user_response(user: User) -> UserResponse:
    """
    Construct a UserResponse from a User ORM instance.

    Includes subscription plan/status if the relationship is loaded.
    """
    subscription_plan = None
    subscription_status = None

    if user.subscription:
        subscription_plan = user.subscription.plan.value
        subscription_status = user.subscription.status.value

    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        subscription_plan=subscription_plan,
        subscription_status=subscription_status,
    )


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    responses={
        201: {"description": "Account created successfully"},
        409: {"description": "Email already registered"},
        422: {"description": "Validation error (weak password, name too short, etc.)"},
    },
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """
    Create a new user account.

    - Validates email format and password strength (min 8 chars,
      uppercase, lowercase, digit, special character)
    - Checks the email is not already registered
    - Creates the user and a FREE subscription atomically
    - Returns the user profile (no tokens — login separately)
    """
    try:
        user = await auth_service.register_user(db, data)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    return RegisterResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        message="Registration successful. Please log in.",
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Log in and receive JWT tokens",
    responses={
        200: {"description": "Login successful — returns access + refresh tokens"},
        401: {"description": "Invalid email or password"},
        403: {"description": "Account disabled"},
    },
)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """
    Authenticate with email and password.

    Returns:
    - **access_token**: Short-lived JWT (30 min) — include in every API call
      as `Authorization: Bearer <token>`
    - **refresh_token**: Long-lived JWT (7 days) — use only to get a new
      access token via POST /auth/refresh
    - **expires_in**: Access token lifetime in seconds
    - **user**: Embedded user profile
    """
    try:
        user = await auth_service.authenticate_user(
            db, data.email, data.password
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except AccountDisabledError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        )

    # Issue token pair
    tokens = await token_service.create_tokens_for_user(
        redis=redis,
        user_id=user.id,
        role=user.role.value,
    )

    logger.info(
        "login_tokens_issued",
        user_id=str(user.id),
        email=user.email,
    )

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=_build_user_response(user),
    )


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a refresh token for a new token pair",
    responses={
        200: {"description": "New token pair issued"},
        401: {"description": "Refresh token expired, invalid, or already used"},
    },
)
async def refresh_tokens(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> TokenResponse:
    """
    Obtain a new access token using a valid refresh token.

    Implements **refresh token rotation**: the submitted refresh token
    is invalidated and a new refresh token is issued alongside the
    new access token.  Each refresh token can only be used once.
    """
    try:
        tokens = await token_service.rotate_refresh_token(
            redis=redis,
            refresh_token=data.refresh_token,
        )
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (TokenInvalidError, RefreshTokenNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load the user for the embedded profile in the response
    import uuid
    from backend.services.auth_service import get_user_by_id
    from backend.core.security import decode_token

    payload = decode_token(tokens["access_token"])
    user_id = uuid.UUID(payload["sub"])
    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return TokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_type=tokens["token_type"],
        expires_in=tokens["expires_in"],
        user=_build_user_response(user),
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out — revoke current tokens",
    responses={
        200: {"description": "Logged out successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def logout(
    data: RefreshRequest,
    request: Request,
    redis: aioredis.Redis = Depends(get_redis),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """
    Revoke the current access token and the provided refresh token.

    After calling this endpoint:
    - The access token is added to the Redis blacklist
    - The refresh token is removed from Redis
    - Both are immediately invalid — even if their expiry hasn't passed

    The client should discard both tokens and redirect to the login page.
    """
    # Extract access token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    access_token = auth_header.replace("Bearer ", "").strip()

    # Blacklist the access token
    if access_token:
        await token_service.blacklist_access_token(redis, access_token)

    # Revoke the refresh token
    await token_service.revoke_refresh_token(redis, data.refresh_token)

    logger.info(
        "user_logged_out",
        user_id=str(current_user.id),
        email=current_user.email,
    )

    return MessageResponse(message="Logged out successfully.")


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    responses={
        200: {"description": "Current user profile"},
        401: {"description": "Not authenticated or token expired"},
    },
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Return the profile of the currently authenticated user.

    Includes subscription plan and status if available.
    Use this endpoint to check who is logged in and what plan they're on.
    """
    return _build_user_response(current_user)


# ---------------------------------------------------------------------------
# PATCH /auth/me
# ---------------------------------------------------------------------------

@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
    responses={
        200: {"description": "Profile updated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def update_me(
    data: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """
    Update mutable profile fields.

    Only fields included in the request body are updated.
    Omitted fields remain unchanged (true PATCH semantics).

    Currently updatable fields:
    - **full_name**: Display name
    """
    updated_user = await auth_service.update_user_profile(
        db, current_user, data
    )
    return _build_user_response(updated_user)


# ---------------------------------------------------------------------------
# POST /auth/me/password
# ---------------------------------------------------------------------------

@router.post(
    "/me/password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password",
    responses={
        200: {"description": "Password changed successfully"},
        400: {"description": "Current password is incorrect"},
        401: {"description": "Not authenticated"},
    },
)
async def change_password(
    data: PasswordChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> MessageResponse:
    """
    Change the authenticated user's password.

    Requires the current password for verification.
    The new password must meet strength requirements:
    - Minimum 8 characters
    - At least one uppercase, lowercase, digit, and special character
    """
    try:
        await auth_service.change_password(
            db=db,
            user=current_user,
            current_password=data.current_password,
            new_password=data.new_password,
        )
    except WrongPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return MessageResponse(message="Password changed successfully.")


# ---------------------------------------------------------------------------
# GET /auth/ping  (health check)
# ---------------------------------------------------------------------------

@router.get(
    "/ping",
    include_in_schema=False,
)
async def ping():
    """Internal health check for the auth router."""
    return {"router": "auth", "status": "ok"}
