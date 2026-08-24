"""
db/seeder.py — Database Seeder
================================
Populates the database with essential bootstrap data on first run.

What it seeds:
    1. Create tables from SQLAlchemy models (via Base.metadata.create_all)
    2. Admin user   — the platform superuser (credentials from settings)
    3. Free subscription — created automatically for the admin account

Why this exists:
    After applying migrations to a fresh database, no users exist.
    The seeder creates the minimum data needed to:
    - Log into the admin dashboard
    - Test authentication without manual SQL inserts
    - Confirm the full stack works end-to-end

Idempotency:
    Every seed operation checks whether the data already exists before
    inserting.  Running the seeder multiple times is safe — it will
    log "already exists" and skip, never raise a duplicate key error.

Usage:
    # From application startup (main.py lifespan):
    await run_seeder()

    # From command line:
    python -m backend.db.seeder
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.logging import get_logger
from backend.core.security import hash_password
from backend.db.session import async_session_factory, engine
from backend.db.base import Base  # Imports all models
from backend.db.models.user import User, UserRole
from backend.db.models.subscription import (
    Subscription,
    SubscriptionPlan,
    SubscriptionStatus,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Individual seed functions
# ---------------------------------------------------------------------------

async def seed_admin_user(db: AsyncSession) -> User:
    """
    Create the platform admin user if one doesn't already exist.

    The admin email and password come from settings (ADMIN_EMAIL,
    ADMIN_PASSWORD).  In production, change these immediately after
    first login and store them in a secrets manager.

    Args:
        db: Active database session.

    Returns:
        The existing or newly created admin User instance.
    """
    # Check if admin already exists
    result = await db.execute(
        select(User).where(User.email == settings.ADMIN_EMAIL)
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        logger.info(
            "seed_admin_already_exists",
            email=settings.ADMIN_EMAIL,
        )
        return existing_admin

    # Create admin user
    admin = User(
        email=settings.ADMIN_EMAIL,
        full_name="Platform Administrator",
        hashed_password=hash_password(settings.ADMIN_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,       # Admin is pre-verified
    )
    db.add(admin)
    await db.flush()            # Assign the UUID without committing yet

    logger.info(
        "seed_admin_created",
        email=admin.email,
        user_id=str(admin.id),
    )
    return admin


async def seed_admin_subscription(db: AsyncSession, admin: User) -> Subscription:
    """
    Create an enterprise subscription for the admin user.

    Admin accounts get the enterprise plan so they can test all
    features without hitting limits during development.

    Args:
        db:    Active database session.
        admin: The admin User instance (must already be flushed/have an id).

    Returns:
        The existing or newly created Subscription instance.
    """
    # Check if subscription already exists
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == admin.id)
    )
    existing_sub = result.scalar_one_or_none()

    if existing_sub:
        logger.info(
            "seed_admin_subscription_already_exists",
            user_id=str(admin.id),
            plan=existing_sub.plan.value,
        )
        return existing_sub

    now = datetime.now(timezone.utc)
    # Give admin a 10-year billing period — effectively unlimited
    period_end = now + timedelta(days=3650)

    subscription = Subscription(
        user_id=admin.id,
        plan=SubscriptionPlan.ENTERPRISE,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=period_end,
    )
    db.add(subscription)
    await db.flush()

    logger.info(
        "seed_admin_subscription_created",
        user_id=str(admin.id),
        plan=subscription.plan.value,
        period_end=period_end.isoformat(),
    )
    return subscription


async def seed_test_user(db: AsyncSession) -> User | None:
    """
    Create a standard test user in development mode only.

    Credentials:
        email:    test@aihub.local
        password: Test@12345

    This user starts on the FREE plan so you can test limit enforcement
    without needing to create a new account manually.

    Only created when APP_ENV=development.

    Args:
        db: Active database session.

    Returns:
        The test User or None if not in development mode.
    """
    if settings.APP_ENV != "development":
        return None

    test_email = "test@aihub.local"
    result = await db.execute(
        select(User).where(User.email == test_email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("seed_test_user_already_exists", email=test_email)
        return existing

    test_user = User(
        email=test_email,
        full_name="Test User",
        hashed_password=hash_password("Test@12345"),
        role=UserRole.USER,
        is_active=True,
        is_verified=True,
    )
    db.add(test_user)
    await db.flush()

    # Free subscription for the test user
    now = datetime.now(timezone.utc)
    test_sub = Subscription(
        user_id=test_user.id,
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=now,
        current_period_end=now + timedelta(days=30),
    )
    db.add(test_sub)
    await db.flush()

    logger.info(
        "seed_test_user_created",
        email=test_user.email,
        user_id=str(test_user.id),
        plan="free",
    )
    return test_user


# ---------------------------------------------------------------------------
# Master seeder — runs all seed functions in a single transaction
# ---------------------------------------------------------------------------

async def run_seeder() -> None:
    """
    Run all seed functions within a single database transaction.

    If any seed function fails, the entire transaction is rolled back —
    no partial state is left in the database.

    Called from:
        - main.py lifespan (on every startup — idempotent)
        - Command line: python -m backend.db.seeder
    """
    logger.info("seeder_starting")

    # ===================================================================
    # 1. Create tables from SQLAlchemy models (idempotent)
    # ===================================================================
    logger.info("seeder_creating_tables")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("seeder_tables_created")
    except Exception as exc:
        logger.error(
            "seeder_table_creation_failed",
            error=str(exc),
            exc_info=True,
        )
        raise

    # ===================================================================
    # 2. Seed data (admin user, subscriptions, etc.)
    # ===================================================================
    async with async_session_factory() as db:
        try:
            # 1. Admin user
            admin = await seed_admin_user(db)

            # 2. Admin subscription
            await seed_admin_subscription(db, admin)

            # 3. Test user (development only)
            await seed_test_user(db)

            # Commit all seed data in one transaction
            await db.commit()

            logger.info("seeder_completed_successfully")

        except Exception as exc:
            await db.rollback()
            logger.error(
                "seeder_failed",
                error=str(exc),
                exc_info=True,
            )
            raise


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def _main() -> None:
    """Entry point when running as a script."""
    print("Running AIHub database seeder...")
    await run_seeder()
    print("Seeder completed.")


if __name__ == "__main__":
    asyncio.run(_main())
