"""
Shared FastAPI dependencies: `get_current_user` (validates the JWT bearer
token) and the `limiter` instance used to rate-limit sensitive endpoints.
"""
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.security import decode_access_token

# Rate limiter keyed by client IP. Applied per-route via @limiter.limit(...).
limiter = Limiter(key_func=get_remote_address)

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError):
        raise unauthorized

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized
    return user


async def get_client_ip(request) -> str | None:
    return get_remote_address(request)
