"""
core/security.py — Authentication & Cryptography Utilities
===========================================================
Handles:
- Password hashing and verification (bcrypt)
- JWT access token creation and decoding
- JWT refresh token creation

Why bcrypt?
- It's intentionally slow — brute-forcing a stolen hash database
  is computationally expensive even with modern hardware.
- It automatically handles salting, so two identical passwords
  produce different hashes.

Why separate access + refresh tokens?
- Access tokens are short-lived (30 min) and used on every request.
- Refresh tokens are long-lived (7 days) and only used to obtain
  new access tokens.  This limits the damage window if an access
  token is intercepted.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt as _bcrypt
from jose import JWTError, jwt

from backend.core.config import settings

# ---------------------------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------------------------
# Using bcrypt directly (bypassing passlib) because passlib 1.7.4 has a
# compatibility issue with bcrypt >= 4.x where it reads __about__.__version__
# which no longer exists.  Direct bcrypt usage is simpler and equally safe.


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password from the registration form.

    Returns:
        A bcrypt hash string (includes salt + algorithm identifier).
    """
    password_bytes = plain_password.encode("utf-8")
    salt = _bcrypt.gensalt(rounds=12)
    return _bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain_password:  The password submitted by the user.
        hashed_password: The hash stored in the database.

    Returns:
        True if the password matches, False otherwise.

    Note:
        bcrypt.checkpw is timing-safe — it always takes roughly the same
        time regardless of whether the password matches, preventing
        timing-based side-channel attacks.
    """
    try:
        return _bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT Tokens
# ---------------------------------------------------------------------------

def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject:      The token subject — typically the user's UUID or ID.
        extra_claims: Optional additional claims (e.g. {"role": "admin",
                      "jti": "uuid-string"}).

    Returns:
        A signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT refresh token (longer-lived).

    Args:
        subject:      The token subject — typically the user's UUID or ID.
        extra_claims: Optional additional claims (e.g. {"jti": "uuid",
                      "role": "user"}).

    Returns:
        A signed JWT string.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": now,
        "exp": expire,
        "type": "refresh",
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: The raw JWT string.

    Returns:
        The decoded payload dictionary.

    Raises:
        JWTError: If the token is expired, tampered with, or invalid.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
