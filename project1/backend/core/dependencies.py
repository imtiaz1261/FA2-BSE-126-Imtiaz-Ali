"""
core/dependencies.py — FastAPI Dependency Injection
====================================================
Central registry of all reusable FastAPI dependencies.

Three categories:
    1. Database  — get_db() yields an AsyncSession per request
    2. Redis     — get_redis() returns the shared client
    3. Auth      — get_current_user / get_current_active_user /
                   get_current_admin_user extract and validate identity

Usage pattern in routes:
    from backend.core.dependencies import get_current_user, get_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.db.models.user import User

    @router.get("/protected")
    async def protected(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        ...

Dependency graph:
    get_current_user
        ├── get_db          (Postgres session)
        ├── get_redis       (Redis client)
        └── OAuth2 scheme   (extracts Bearer token from header)

    get_current_active_user
        └── get_current_user

    get_current_admin_user
        └── get_current_user  (+ role check)
"""

import uuid
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from backend.core.logging import get_logger
from backend.db.session import async_session_factory, get_db  # noqa: F401
from backend.db.models.user import User, UserRole
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------
# Tells FastAPI:
#   - Requests must include "Authorization: Bearer <token>" header
#   - The token URL (used by Swagger UI "Authorize" button) is /api/v1/auth/login
#   - auto_error=True means FastAPI returns 401 automatically if the
#     header is missing — we don't have to check manually

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=True,
)

# Optional scheme — same but auto_error=False so the route can handle
# missing tokens gracefully (e.g. public endpoints that show more data
# when logged in but still work anonymously)
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


# ---------------------------------------------------------------------------
# 1. Database dependency
# ---------------------------------------------------------------------------
# Re-exported from db/session.py so routes only need to import from
# this module — one import location for all dependencies.
# get_db is already defined in db/session.py and imported above.


# ---------------------------------------------------------------------------
# 2. Redis dependency
# ---------------------------------------------------------------------------

async def get_redis() -> aioredis.Redis:
    """
    Return the shared async Redis client.

    In production: raises HTTP 503 if Redis is not available.
    In development: falls back to an in-process FakeRedis so the app
    works without a running Redis server (token blacklisting is
    in-memory only — lost on restart, not shared across workers).
    """
    from backend.main import get_redis_client
    from backend.core.config import settings
    try:
        return await get_redis_client()
    except RuntimeError:
        if settings.APP_ENV == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache service unavailable. Please try again later.",
            )
        # Dev/staging fallback — in-memory Redis substitute
        from backend.core.fake_redis import get_fake_redis
        return get_fake_redis()  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# 3. Authentication dependencies
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    """
    Extract, validate, and return the current authenticated user.

    Flow:
        1. Extract Bearer token from Authorization header (OAuth2 scheme)
        2. Verify token signature and expiry (token_service)
        3. Check JTI is not blacklisted in Redis (token_service)
        4. Load User from PostgreSQL by sub claim
        5. Verify user account is active

    Args:
        token: Raw JWT string extracted by OAuth2PasswordBearer
        db:    Injected AsyncSession
        redis: Injected Redis client

    Returns:
        Authenticated User ORM instance

    Raises:
        HTTP 401: Token missing, expired, invalid, or blacklisted
        HTTP 401: User not found in database
        HTTP 403: Account disabled
    """
    # Deferred import prevents circular dependency at module load time
    from backend.services.token_service import (
        verify_access_token,
        TokenExpiredError,
        TokenInvalidError,
        TokenBlacklistedError,
    )
    from backend.services.auth_service import get_user_by_id

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Verify token
    try:
        payload = await verify_access_token(redis, token)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired. Please refresh your token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenBlacklistedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenInvalidError:
        raise credentials_exception

    # 2. Extract user ID from sub claim
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # 3. Load user from DB
    user = await get_user_by_id(db, user_id)
    if user is None:
        logger.warning(
            "auth_user_not_found_in_db",
            user_id=user_id_str,
        )
        raise credentials_exception

    # 4. Verify account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been disabled. Please contact support.",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency alias for get_current_user.

    Explicitly names the intent: "I need an active, authenticated user."
    Use this in routes that need a logged-in user but don't care about role.

    Args:
        current_user: Injected from get_current_user

    Returns:
        The authenticated, active User
    """
    # is_active already checked in get_current_user — no duplicate check
    return current_user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Require the current user to have the admin role.

    Use this dependency on all admin-only endpoints.

    Args:
        current_user: Injected from get_current_user

    Returns:
        The authenticated User (guaranteed to be an admin)

    Raises:
        HTTP 403: User is authenticated but does not have admin role
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "admin_access_denied",
            user_id=str(current_user.id),
            email=current_user.email,
            role=current_user.role.value,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return current_user


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User | None:
    """
    Return the current user if a valid token is provided, otherwise None.

    Use this on endpoints that are public but show enriched data when
    the user is authenticated (e.g. a public document list that also
    shows ownership info when logged in).

    Args:
        token: Optional Bearer token
        db:    Injected AsyncSession
        redis: Injected Redis client

    Returns:
        User instance if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        return await get_current_user(token=token, db=db, redis=redis)
    except HTTPException:
        return None
