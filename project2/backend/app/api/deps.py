"""Shared FastAPI dependencies."""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    subject = decode_access_token(token)
    if subject is None:
        raise CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise CREDENTIALS_EXCEPTION

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_EXCEPTION
    return user


def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency that requires the authenticated user to be an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user
