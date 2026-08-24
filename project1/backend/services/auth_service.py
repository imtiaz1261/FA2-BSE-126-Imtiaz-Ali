"""
services/auth_service.py — Authentication Business Logic
=========================================================
Handles all user identity operations:
    - Registration (creates User + Subscription atomically)
    - Authentication (verifies credentials, updates last_login_at)
    - User lookup by ID and email
    - Profile updates
    - Password changes

Design principles applied here:
    1. Single responsibility — each method does exactly one thing
    2. No HTTP awareness — raises ValueError/PermissionError,
       never HTTPException (that's the route layer's job)
    3. Atomic operations — register creates user + subscription
       in the same DB transaction so we never have a userless
       subscription or a subscriptionless user
    4. Explicit over implicit — every method documents what it
       reads, writes, and can raise
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.security import hash_password, verify_password
from backend.db.models.user import User, UserRole
from backend.db.models.subscription import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)
from backend.schemas.auth import RegisterRequest, UserUpdateRequest

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
# Using domain exceptions (not HTTP exceptions) keeps the service layer
# independent of FastAPI.  The route handler translates these to HTTP
# responses.  This matters when you later want to call these services
# from background tasks, CLI scripts, or tests — no FastAPI needed.

class EmailAlreadyRegisteredError(Exception):
    """Raised when a registration attempt uses an already-taken email."""
    pass


class InvalidCredentialsError(Exception):
    """Raised when email/password combination does not match."""
    pass


class UserNotFoundError(Exception):
    """Raised when a user lookup returns no result."""
    pass


class AccountDisabledError(Exception):
    """Raised when an inactive/banned user attempts to authenticate."""
    pass


class WrongPasswordError(Exception):
    """Raised when the current password is incorrect during a change."""
    pass


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

async def register_user(
    db: AsyncSession,
    data: RegisterRequest,
) -> User:
    """
    Create a new user account and a FREE subscription atomically.

    Steps:
        1. Check email is not already registered
        2. Hash the password
        3. Create User row
        4. Create Subscription row (FREE plan, 30-day period)
        5. Flush both to DB (single transaction — committed by get_db())

    Args:
        db:   The active async database session (from Depends(get_db))
        data: Validated RegisterRequest schema

    Returns:
        The newly created User ORM instance (with id populated after flush)

    Raises:
        EmailAlreadyRegisteredError: If the email is already in use
    """
    # 1. Check for duplicate email
    existing = await get_user_by_email(db, data.email)
    if existing:
        logger.warning(
            "register_email_taken",
            email=data.email,
        )
        raise EmailAlreadyRegisteredError(
            f"An account with email '{data.email}' already exists"
        )

    # 2. Hash password
    hashed = hash_password(data.password)

    # 3. Create User
    user = User(
        email=data.email.lower().strip(),
        full_name=data.full_name.strip(),
        hashed_password=hashed,
        role=UserRole.USER,
        is_active=True,
        is_verified=False,      # Email verification in a future step
    )
    db.add(user)

    try:
        # Flush to get the user.id assigned (needed for subscription FK)
        # This does NOT commit — get_db() commits on success
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise EmailAlreadyRegisteredError(
            f"An account with email '{data.email}' already exists"
        )

    # 4. Create FREE subscription
    now = datetime.now(timezone.utc)
    subscription = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(subscription)
    await db.flush()

    logger.info(
        "user_registered",
        user_id=str(user.id),
        email=user.email,
        plan="free",
    )

    return user


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User:
    """
    Verify email + password and return the authenticated User.

    Steps:
        1. Look up user by email
        2. Check account is active
        3. Verify password (timing-safe bcrypt comparison)
        4. Update last_login_at timestamp
        5. Flush the timestamp update

    Args:
        db:       Active database session
        email:    The submitted email address
        password: The submitted plain-text password

    Returns:
        The authenticated User ORM instance

    Raises:
        InvalidCredentialsError: Email not found OR password mismatch
                                 (same exception prevents user enumeration)
        AccountDisabledError:    Account exists but is_active=False
    """
    # Use a generic message for both "not found" and "wrong password"
    # to prevent user enumeration attacks
    GENERIC_ERROR = "Invalid email or password"

    # 1. Look up user
    user = await get_user_by_email(db, email)
    if not user:
        # Still call verify_password with a dummy hash to consume
        # the same amount of time — prevents timing-based enumeration
        verify_password(password, "$2b$12$dummy_hash_to_prevent_timing_attack")
        logger.warning("login_user_not_found", email=email)
        raise InvalidCredentialsError(GENERIC_ERROR)

    # 2. Check account status (BEFORE verifying password)
    if not user.is_active:
        logger.warning(
            "login_account_disabled",
            user_id=str(user.id),
            email=email,
        )
        raise AccountDisabledError(
            "Your account has been disabled. Please contact support."
        )

    # 3. Verify password
    if not verify_password(password, user.hashed_password):
        logger.warning(
            "login_wrong_password",
            user_id=str(user.id),
            email=email,
        )
        raise InvalidCredentialsError(GENERIC_ERROR)

    # 4. Update last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        "login_success",
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
    )

    return user


# ---------------------------------------------------------------------------
# User lookups
# ---------------------------------------------------------------------------

async def get_user_by_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[User]:
    """
    Fetch a user by their UUID primary key.

    Args:
        db:      Active database session
        user_id: The user's UUID

    Returns:
        User instance or None if not found
    """
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> Optional[User]:
    """
    Fetch a user by their email address (case-insensitive).

    Args:
        db:    Active database session
        email: Email address to look up

    Returns:
        User instance or None if not found
    """
    result = await db.execute(
        select(User).where(
            User.email == email.lower().strip()
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Profile updates
# ---------------------------------------------------------------------------

async def update_user_profile(
    db: AsyncSession,
    user: User,
    data: UserUpdateRequest,
) -> User:
    """
    Update mutable profile fields.

    Only updates fields that are explicitly provided (not None).
    This implements proper PATCH semantics — omitted fields are unchanged.

    Args:
        db:   Active database session
        user: The User ORM instance to update
        data: Validated UserUpdateRequest (all fields optional)

    Returns:
        The updated User instance
    """
    changed = False

    if data.full_name is not None:
        user.full_name = data.full_name.strip()
        changed = True

    if changed:
        user.updated_at = datetime.now(timezone.utc)
        await db.flush()
        logger.info(
            "user_profile_updated",
            user_id=str(user.id),
        )

    return user


async def change_password(
    db: AsyncSession,
    user: User,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change a user's password after verifying the current one.

    Args:
        db:               Active database session
        user:             The authenticated User
        current_password: The user's existing password (plain text)
        new_password:     The desired new password (plain text, pre-validated)

    Raises:
        WrongPasswordError: If current_password does not match the stored hash
    """
    if not verify_password(current_password, user.hashed_password):
        logger.warning(
            "password_change_wrong_current",
            user_id=str(user.id),
        )
        raise WrongPasswordError("Current password is incorrect")

    user.hashed_password = hash_password(new_password)
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()

    logger.info(
        "password_changed",
        user_id=str(user.id),
    )
