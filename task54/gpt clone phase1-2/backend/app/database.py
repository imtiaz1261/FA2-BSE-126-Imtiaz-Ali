"""
Async SQLAlchemy setup. `get_db` is the FastAPI dependency every router uses
to obtain a request-scoped session.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import event, text

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, expire_on_commit=False, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            # Enable pgvector extension on first connection
            await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await session.commit()
        except Exception:
            # Extension might already exist or be created by migration
            await session.rollback()
        
        try:
            yield session
        finally:
            await session.close()

