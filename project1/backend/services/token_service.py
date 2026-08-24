"""
services/token_service.py — JWT Lifecycle + Redis Token Management
===================================================================
Handles the complete token lifecycle:

    Issue          → create_tokens_for_user()
    Validate       → verify_access_token()
    Refresh        → rotate_refresh_token()
    Revoke/Logout  → blacklist_access_token(), revoke_refresh_token()
    Check          → is_token_blacklisted()

Redis key schema:
    blacklist:{jti}          → "1"   (TTL = remaining token lifetime)
    refresh:{user_id}:{jti}  → "1"   (TTL = refresh token lifetime)

Why store JTI instead of the full token?
    - JTI is a short UUID — much smaller than the full JWT string
    - We only need to know "was this specific token revoked?"
    - The full token can be reconstructed/verified without Redis

Why TTL on blacklist entries?
    - Redis auto-expires them when the token would have expired anyway
    - No cleanup job needed — Redis is self-maintaining
    - Memory usage stays bounded even under heavy logout traffic
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis
from jose import JWTError

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Redis key prefixes — centralised here so they never diverge
# ---------------------------------------------------------------------------
_BLACKLIST_PREFIX = "auth:blacklist:"
_REFRESH_PREFIX = "auth:refresh:"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class TokenExpiredError(Exception):
    """The token's exp claim is in the past."""
    pass


class TokenInvalidError(Exception):
    """The token signature is invalid, malformed, or missing required claims."""
    pass


class TokenBlacklistedError(Exception):
    """The token has been explicitly revoked (user logged out)."""
    pass


class RefreshTokenNotFoundError(Exception):
    """The refresh token does not exist in Redis (expired or never issued)."""
    pass


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def _make_jti() -> str:
    """Generate a unique JWT ID (jti claim)."""
    return str(uuid.uuid4())


async def create_tokens_for_user(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    role: str,
) -> dict:
    """
    Issue a new access token + refresh token pair for a user.

    Both tokens embed a unique `jti` claim so they can be individually
    revoked without affecting the other.

    Steps:
        1. Generate unique JTIs for both tokens
        2. Create signed JWTs with jti + role embedded
        3. Store refresh token JTI in Redis (with TTL)
        4. Return token strings + metadata

    Args:
        redis:   Async Redis client
        user_id: The user's UUID (becomes the `sub` claim)
        role:    The user's role string (embedded as extra claim)

    Returns:
        Dict with access_token, refresh_token, expires_in
    """
    access_jti = _make_jti()
    refresh_jti = _make_jti()

    # Create signed JWTs — jti and role embedded as extra claims
    access_token = create_access_token(
        subject=str(user_id),
        extra_claims={"jti": access_jti, "role": role},
    )
    refresh_token = create_refresh_token(
        subject=str(user_id),
        extra_claims={"jti": refresh_jti, "role": role},
    )

    # Store refresh JTI in Redis so we can validate and rotate it
    refresh_ttl_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86_400
    redis_key = f"{_REFRESH_PREFIX}{user_id}:{refresh_jti}"
    await redis.setex(redis_key, refresh_ttl_seconds, "1")

    logger.info(
        "tokens_issued",
        user_id=str(user_id),
        role=role,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------

async def verify_access_token(
    redis: aioredis.Redis,
    token: str,
) -> dict:
    """
    Fully validate an access token:
        1. Decode and verify JWT signature + expiry
        2. Confirm token type is "access"
        3. Check JTI is not blacklisted in Redis

    Args:
        redis: Async Redis client
        token: Raw JWT string from Authorization header

    Returns:
        Decoded payload dict (includes sub, jti, role, exp, iat)

    Raises:
        TokenExpiredError:     exp is in the past
        TokenInvalidError:     signature invalid, malformed, wrong type
        TokenBlacklistedError: JTI found in Redis blacklist
    """
    # 1. Decode JWT
    try:
        payload = decode_token(token)
    except JWTError as exc:
        error_str = str(exc).lower()
        if "expired" in error_str:
            raise TokenExpiredError("Access token has expired") from exc
        raise TokenInvalidError(f"Invalid access token: {exc}") from exc

    # 2. Confirm token type
    if payload.get("type") != "access":
        raise TokenInvalidError("Token is not an access token")

    # 3. Check blacklist
    jti = payload.get("jti")
    if jti and await is_token_blacklisted(redis, jti):
        logger.warning(
            "token_blacklisted_access_attempt",
            jti=jti,
            sub=payload.get("sub"),
        )
        raise TokenBlacklistedError("Token has been revoked")

    return payload


async def verify_refresh_token(
    redis: aioredis.Redis,
    token: str,
) -> dict:
    """
    Validate a refresh token:
        1. Decode JWT and verify signature + expiry
        2. Confirm token type is "refresh"
        3. Confirm JTI exists in Redis (was issued by us)

    Args:
        redis: Async Redis client
        token: Raw refresh JWT string

    Returns:
        Decoded payload dict

    Raises:
        TokenExpiredError:          Token expired
        TokenInvalidError:          Bad signature / wrong type
        RefreshTokenNotFoundError:  JTI not in Redis (already used or revoked)
    """
    # 1. Decode
    try:
        payload = decode_token(token)
    except JWTError as exc:
        error_str = str(exc).lower()
        if "expired" in error_str:
            raise TokenExpiredError("Refresh token has expired") from exc
        raise TokenInvalidError(f"Invalid refresh token: {exc}") from exc

    # 2. Confirm type
    if payload.get("type") != "refresh":
        raise TokenInvalidError("Token is not a refresh token")

    # 3. Confirm existence in Redis
    user_id = payload.get("sub")
    jti = payload.get("jti")

    if not user_id or not jti:
        raise TokenInvalidError("Refresh token missing required claims")

    redis_key = f"{_REFRESH_PREFIX}{user_id}:{jti}"
    exists = await redis.exists(redis_key)
    if not exists:
        logger.warning(
            "refresh_token_not_in_redis",
            user_id=user_id,
            jti=jti,
        )
        raise RefreshTokenNotFoundError(
            "Refresh token not found or already used"
        )

    return payload


# ---------------------------------------------------------------------------
# Token rotation (refresh flow)
# ---------------------------------------------------------------------------

async def rotate_refresh_token(
    redis: aioredis.Redis,
    refresh_token: str,
) -> dict:
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    Implements refresh token rotation:
        1. Validate the incoming refresh token
        2. Delete the old refresh JTI from Redis (one-time use)
        3. Issue a new access + refresh token pair

    This means a refresh token can only be used once.  If an attacker
    steals and uses a refresh token before the legitimate user does,
    the legitimate user's next refresh attempt will fail — alerting
    them that their token was compromised.

    Args:
        redis:         Async Redis client
        refresh_token: The current refresh JWT string

    Returns:
        New token pair dict (same structure as create_tokens_for_user)

    Raises:
        TokenExpiredError, TokenInvalidError, RefreshTokenNotFoundError
    """
    # 1. Validate
    payload = await verify_refresh_token(redis, refresh_token)

    user_id_str = payload["sub"]
    old_jti = payload["jti"]
    role = payload.get("role", "user")

    # 2. Delete old refresh JTI (invalidate one-time token)
    old_redis_key = f"{_REFRESH_PREFIX}{user_id_str}:{old_jti}"
    await redis.delete(old_redis_key)

    logger.info(
        "refresh_token_rotated",
        user_id=user_id_str,
        old_jti=old_jti,
    )

    # 3. Issue new token pair
    user_id = uuid.UUID(user_id_str)
    return await create_tokens_for_user(redis, user_id, role)


# ---------------------------------------------------------------------------
# Token revocation (logout)
# ---------------------------------------------------------------------------

async def blacklist_access_token(
    redis: aioredis.Redis,
    token: str,
) -> None:
    """
    Add an access token's JTI to the Redis blacklist.

    The blacklist entry TTL is set to the token's remaining lifetime so
    Redis automatically cleans it up after the token would have expired
    anyway — no orphaned entries accumulate.

    Args:
        redis: Async Redis client
        token: The raw access JWT string to revoke
    """
    try:
        payload = decode_token(token)
    except JWTError:
        # Already invalid — nothing to blacklist
        return

    jti = payload.get("jti")
    if not jti:
        return

    # Calculate remaining lifetime
    exp = payload.get("exp")
    if exp:
        now = int(datetime.now(timezone.utc).timestamp())
        remaining_seconds = max(exp - now, 1)
    else:
        # Fallback: use full token lifetime
        remaining_seconds = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    blacklist_key = f"{_BLACKLIST_PREFIX}{jti}"
    await redis.setex(blacklist_key, remaining_seconds, "1")

    logger.info(
        "access_token_blacklisted",
        jti=jti,
        ttl_seconds=remaining_seconds,
    )


async def revoke_refresh_token(
    redis: aioredis.Redis,
    token: str,
) -> None:
    """
    Remove a refresh token's JTI from Redis, invalidating it immediately.

    Args:
        redis: Async Redis client
        token: The raw refresh JWT string to revoke
    """
    try:
        payload = decode_token(token)
    except JWTError:
        return

    user_id = payload.get("sub")
    jti = payload.get("jti")

    if user_id and jti:
        redis_key = f"{_REFRESH_PREFIX}{user_id}:{jti}"
        await redis.delete(redis_key)
        logger.info(
            "refresh_token_revoked",
            user_id=user_id,
            jti=jti,
        )


# ---------------------------------------------------------------------------
# Blacklist check
# ---------------------------------------------------------------------------

async def is_token_blacklisted(
    redis: aioredis.Redis,
    jti: str,
) -> bool:
    """
    Check whether a JTI is in the Redis blacklist.

    Args:
        redis: Async Redis client
        jti:   The JWT ID claim to check

    Returns:
        True if blacklisted, False if clean
    """
    key = f"{_BLACKLIST_PREFIX}{jti}"
    return bool(await redis.exists(key))
