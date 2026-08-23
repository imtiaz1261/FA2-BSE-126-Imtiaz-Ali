"""
Background jobs for memory extraction and maintenance.

- Post-conversation extraction: Extract facts after conversation ends
- Periodic re-indexing: Re-extract from recent conversations
- Cleanup: Remove old memories based on retention policy
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.models import User, Conversation, Message
from app.models_memory import UserMemorySettings, UserMemoryItem, MemoryExtractionLog
from app.services.memory_extraction import MemoryExtractionService
from app.services.memory_retrieval import MemoryRetrievalService

logger = logging.getLogger(__name__)


# ============================================================================
# Memory Jobs Service
# ============================================================================


class MemoryJobsService:
    """Manages background memory extraction and maintenance jobs."""

    def __init__(self, db_session: AsyncSession):
        """Initialize with database session."""
        self.db = db_session
        self.extraction_service = MemoryExtractionService()
        self.retrieval_service = MemoryRetrievalService()

    async def extract_from_conversation(
        self, user_id: str, conversation_id: str
    ) -> Optional[MemoryExtractionLog]:
        """
        Extract facts from a completed conversation.

        Called automatically after a conversation ends or user closes chat.

        Args:
            user_id: User ID
            conversation_id: Conversation ID

        Returns:
            MemoryExtractionLog with results
        """
        from app.models import Conversation as ConvModel

        try:
            # Get conversation and messages
            conversation = await self.db.get(ConvModel, conversation_id)
            if not conversation or conversation.user_id != user_id:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                return None

            # Get all messages from conversation
            messages = await self.db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
            messages_list = list(messages)

            if not messages_list:
                logger.info(f"No messages in conversation {conversation_id}")
                return None

            # Extract facts
            log = await self.extraction_service.extract_from_conversation(
                user_id=user_id,
                messages=messages_list,
                conversation_id=str(conversation_id),
                db=self.db,
                trigger="post_conversation",
            )

            if log:
                logger.info(
                    f"Extracted {log.facts_extracted_count} facts from conversation {conversation_id}"
                )

            return log

        except Exception as e:
            logger.error(f"Error extracting from conversation {conversation_id}: {e}")
            return None

    async def periodic_reindex(self, user_id: str, limit: int = 10) -> int:
        """
        Periodically re-extract facts from recent conversations.

        Useful for catching facts that may have been missed in initial extraction.

        Args:
            user_id: User ID
            limit: Number of recent conversations to re-process

        Returns:
            Total facts extracted
        """
        try:
            # Get user's recent conversations
            conversations = await self.db.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(desc(Conversation.created_at))
                .limit(limit)
            )

            total_extracted = 0

            for conv in conversations:
                log = await self.extract_from_conversation(
                    user_id=user_id,
                    conversation_id=str(conv.id),
                )

                if log:
                    total_extracted += log.facts_extracted_count

            # Update last_extraction_at in settings
            settings = await self.db.scalar(
                select(UserMemorySettings).where(UserMemorySettings.user_id == user_id)
            )
            if settings:
                settings.last_extraction_at = datetime.utcnow()
                await self.db.commit()

            logger.info(f"Periodic reindex for user {user_id}: extracted {total_extracted} facts")
            return total_extracted

        except Exception as e:
            logger.error(f"Error in periodic reindex for user {user_id}: {e}")
            return 0

    async def cleanup_old_memories(self, user_id: str) -> int:
        """
        Remove memories older than retention period.

        Called periodically to maintain memory store size.

        Args:
            user_id: User ID

        Returns:
            Number of memories deleted
        """
        try:
            # Get user's settings
            settings = await self.db.scalar(
                select(UserMemorySettings).where(UserMemorySettings.user_id == user_id)
            )

            if not settings:
                return 0

            # If retention_days is 0, keep forever
            if settings.retention_days == 0:
                return 0

            cutoff_date = datetime.utcnow() - timedelta(days=settings.retention_days)

            # Find memories older than cutoff that haven't been accessed recently
            old_memories = await self.db.scalars(
                select(UserMemoryItem)
                .where(
                    UserMemoryItem.user_id == user_id,
                    UserMemoryItem.created_at < cutoff_date,
                )
                .order_by(UserMemoryItem.retrieval_count)
                .limit(50)  # Batch delete
            )

            deleted_count = 0
            for memory in old_memories:
                await self.db.delete(memory)
                deleted_count += 1

            await self.db.commit()

            logger.info(f"Cleaned up {deleted_count} old memories for user {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up memories for user {user_id}: {e}")
            return 0

    async def enforce_memory_limits(self, user_id: str) -> int:
        """
        Enforce max_memory_items limit by evicting least-recently-used memories.

        Args:
            user_id: User ID

        Returns:
            Number of memories evicted
        """
        try:
            settings = await self.db.scalar(
                select(UserMemorySettings).where(UserMemorySettings.user_id == user_id)
            )

            if not settings:
                return 0

            # Count total memories
            from sqlalchemy import func

            total = await self.db.scalar(
                select(func.count(UserMemoryItem.id)).where(
                    UserMemoryItem.user_id == user_id
                )
            )

            if total is None or total <= settings.max_memory_items:
                return 0

            # Find LRU memories to delete
            to_delete = total - settings.max_memory_items
            lru_memories = await self.db.scalars(
                select(UserMemoryItem)
                .where(UserMemoryItem.user_id == user_id)
                .order_by(UserMemoryItem.last_retrieved_at)
                .limit(to_delete)
            )

            deleted_count = 0
            for memory in lru_memories:
                await self.db.delete(memory)
                deleted_count += 1

            await self.db.commit()

            logger.info(f"Evicted {deleted_count} LRU memories for user {user_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error enforcing memory limits for user {user_id}: {e}")
            return 0


# ============================================================================
# Scheduled Job Runners (for Celery/APScheduler)
# ============================================================================


async def run_post_conversation_extraction(
    user_id: str,
    conversation_id: str,
    db_url: str,
) -> dict:
    """
    Run post-conversation extraction job.

    Designed to be called by Celery task or APScheduler.

    Args:
        user_id: User ID
        conversation_id: Conversation ID
        db_url: Database URL string

    Returns:
        Job result dict
    """
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            jobs_service = MemoryJobsService(session)
            log = await jobs_service.extract_from_conversation(user_id, conversation_id)

            return {
                "status": "success",
                "facts_extracted": log.facts_extracted_count if log else 0,
                "facts_rejected": log.facts_rejected_count if log else 0,
            }

        except Exception as e:
            logger.error(f"Post-conversation extraction failed: {e}")
            return {"status": "failed", "error": str(e)}

        finally:
            await engine.dispose()


async def run_periodic_reindex_for_user(
    user_id: str,
    db_url: str,
    limit: int = 10,
) -> dict:
    """Run periodic reindex job for a single user."""
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            jobs_service = MemoryJobsService(session)
            total = await jobs_service.periodic_reindex(user_id, limit)

            return {
                "status": "success",
                "facts_extracted": total,
            }

        except Exception as e:
            logger.error(f"Periodic reindex failed for user {user_id}: {e}")
            return {"status": "failed", "error": str(e)}

        finally:
            await engine.dispose()


async def run_cleanup_for_user(
    user_id: str,
    db_url: str,
) -> dict:
    """Run memory cleanup job for a single user."""
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            jobs_service = MemoryJobsService(session)
            cleaned = await jobs_service.cleanup_old_memories(user_id)
            evicted = await jobs_service.enforce_memory_limits(user_id)

            return {
                "status": "success",
                "cleaned": cleaned,
                "evicted": evicted,
            }

        except Exception as e:
            logger.error(f"Cleanup failed for user {user_id}: {e}")
            return {"status": "failed", "error": str(e)}

        finally:
            await engine.dispose()


# ============================================================================
# Batch Jobs (for scheduled execution)
# ============================================================================


async def batch_periodic_reindex(db_url: str, limit: int = 10) -> dict:
    """
    Run periodic reindex for all active users.

    Call this via APScheduler (daily) or similar.

    Returns:
        Summary of job results
    """
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    processed = 0
    total_extracted = 0

    try:
        async with async_session() as session:
            # Get all users with memory enabled
            users = await session.scalars(
                select(User).where(User.is_active == True)
            )

            for user in users:
                jobs_service = MemoryJobsService(session)
                extracted = await jobs_service.periodic_reindex(str(user.id), limit)
                total_extracted += extracted
                processed += 1

                # Commit per-user to avoid large transaction
                await session.commit()

        logger.info(
            f"Batch periodic reindex complete: {processed} users, {total_extracted} facts"
        )
        return {
            "status": "success",
            "users_processed": processed,
            "total_extracted": total_extracted,
        }

    except Exception as e:
        logger.error(f"Batch periodic reindex failed: {e}")
        return {"status": "failed", "error": str(e)}

    finally:
        await engine.dispose()


async def batch_cleanup(db_url: str) -> dict:
    """
    Run memory cleanup for all users.

    Call this via APScheduler (weekly) or similar.

    Returns:
        Summary of cleanup results
    """
    engine = create_async_engine(db_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    processed = 0
    total_cleaned = 0
    total_evicted = 0

    try:
        async with async_session() as session:
            users = await session.scalars(
                select(User).where(User.is_active == True)
            )

            for user in users:
                jobs_service = MemoryJobsService(session)
                cleaned = await jobs_service.cleanup_old_memories(str(user.id))
                evicted = await jobs_service.enforce_memory_limits(str(user.id))

                total_cleaned += cleaned
                total_evicted += evicted
                processed += 1

                await session.commit()

        logger.info(
            f"Batch cleanup complete: {processed} users, "
            f"{total_cleaned} cleaned, {total_evicted} evicted"
        )
        return {
            "status": "success",
            "users_processed": processed,
            "cleaned": total_cleaned,
            "evicted": total_evicted,
        }

    except Exception as e:
        logger.error(f"Batch cleanup failed: {e}")
        return {"status": "failed", "error": str(e)}

    finally:
        await engine.dispose()
