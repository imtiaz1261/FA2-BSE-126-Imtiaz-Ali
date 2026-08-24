"""
db/session.py — Async Database Session Factory
===============================================
Creates the SQLAlchemy async engine and session factory.

Key decisions:
- pool_size=10, max_overflow=20:
    Up to 30 simultaneous DB connections.  Tune for your server.
- pool_pre_ping=True:
    Tests each connection before using it.  Prevents "connection
    closed" errors after PostgreSQL restarts or idle timeouts.
- expire_on_commit=False:
    ORM objects remain accessible after commit without re-querying.
    This matters in async code where lazy-loading is not available.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from sqlalchemy.pool import NullPool

from backend.core.config import settings


def _build_engine(test_mode: bool = False) -> AsyncEngine:
    """
    Build the SQLAlchemy async engine.

    Args:
        test_mode: If True, use NullPool (no connection pooling).
                   Useful for test suites that create/drop tables
                   between tests.
    """
    kwargs = {
        "echo": settings.DEBUG,          # Log all SQL in development
        "pool_pre_ping": True,
        "pool_recycle": 3600,            # Recycle connections every hour
    }

    if test_mode:
        # NullPool creates a new connection per request — safe for tests
        kwargs["poolclass"] = NullPool
    else:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    return create_async_engine(settings.database_url, **kwargs)


# Module-level engine — shared across the entire application lifetime
engine: AsyncEngine = _build_engine()

# Session factory — call this to get an AsyncSession
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session.

    Usage in a route:
        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()

    The session is automatically committed on success and
    rolled back on exception, then closed in the finally block.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db_connection() -> bool:
    """
    Verify the database is reachable.
    Used by the /health endpoint and startup checks.

    Returns:
        True if the connection succeeds, False otherwise.
    """
    try:
        async with engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
