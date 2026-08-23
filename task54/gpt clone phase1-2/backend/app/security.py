"""
Security primitives: password hashing (bcrypt), JWT access tokens, and the
opaque-token scheme used for refresh tokens / email-verify / password-reset
links (generated with secrets.token_urlsafe, stored only as a SHA-256 hash).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---- Passwords ----------------------------------------------------------------


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)


# ---- Opaque tokens (refresh tokens, email-verify, password-reset) -------------
# We generate a high-entropy random string, return the RAW value to the caller
# (to embed in a link or cookie), and persist only its SHA-256 hash. This
# means a stolen database dump cannot be used to forge sessions or reset
# links, since the raw token can't be recovered from the hash.


def generate_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


# ---- JWT access tokens ----------------------------------------------------------


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """Returns (token, expires_in_seconds)."""
    expire_delta = timedelta(minutes=settings.access_token_expire_minutes)
    expire_at = datetime.now(timezone.utc) + expire_delta
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire_at,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expire_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    """Raises jose.JWTError if invalid/expired — caller converts to HTTP 401."""
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)


def auth_token_expiry(minutes: int) -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)
