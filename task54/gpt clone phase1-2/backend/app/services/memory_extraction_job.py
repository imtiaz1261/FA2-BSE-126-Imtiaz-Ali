"""
Memory Extraction Background Job Service

Handles post-conversation memory extraction and periodic batch processing.
Can be triggered manually or run on a schedule.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Conversation, Message, User
from app.models_memory import MemoryExtractionLog, UserMemorySettings
from app.services.memory_extraction import MemoryExtractionService

logger = logging.getLogger(__name__)


class MemoryExtractionJob:
    """Background job for memory extraction."""

    def __init__(self, extraction_service: Optional[MemoryExtractionService] = None):
        """Initialize job."""
        self.extraction_service = extraction_service or MemoryExtractionService()

    async def extract_from_conversation(
        self,
        user_id: str,
        conversation_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[MemoryExtractionLog]:
        """
        Extract facts from a conversation (post-conversation trigger).

        This is called after a user finishes a conversation session to identify
        and store relevant facts for future personalization.

        Args:
            user_id: User ID
            conversation_id: Conversation ID to extract from
            db: Optional database session; creates one if not provided

        Returns:
            MemoryExtractionLog with extraction results, or None on error
        """
        if not db:
            async with async_session() as session:
                return await self.extract_from_conversation(user_id, conversation_id, session)

        try:
            # Fetch conversation with messages
            conversation = await db.get(Conversation, UUID(conversation_id))
            if not conversation or str(conversation.user_id) != user_id:
                logger.warning(
                    f"Conversation {conversation_id} not found or unauthorized for user {user_id}"
                )
                return None

            # Get all messages in conversation
            messages = await db.scalars(
                select(Message)
                .where(Message.conversation_id == UUID(conversation_id))
                .order_by(Message.created_at)
            )
            messages_list = list(messages)

            if not messages_list:
                logger.info(f"No messages in conversation {conversation_id}")
                return None

            # Run extraction
            result = await self.extraction_service.extract_from_conversation(
                user_id=user_id,
                messages=messages_list,
                conversation_id=conversation_id,
                db=db,
                trigger="post_conversation",
            )

            logger.info(
                f"Extracted facts from conversation {conversation_id} for user {user_id}: {result}"
            )
            return result

        except Exception as e:
            logger.error(
                f"Error extracting from conversation {conversation_id}: {e}",
                exc_info=True,
            )
            return None

    async def extract_from_recent_conversations(
        self,
        user_id: str,
        hours_back: int = 24,
        max_conversations: int = 5,
        db: Optional[AsyncSession] = None,
    ) -> list[MemoryExtractionLog]:
        """
        Extract facts from recent conversations (batch/periodic trigger).

        Called periodically or manually to process multiple recent conversations
        and identify patterns and recurring facts.

        Args:
            user_id: User ID
            hours_back: Look back N hours for conversations (default 24)
            max_conversations: Max conversations to process (default 5)
            db: Optional database session

        Returns:
            List of MemoryExtractionLog results
        """
        if not db:
            async with async_session() as session:
                return await self.extract_from_recent_conversations(
                    user_id, hours_back, max_conversations, session
                )

        results = []

        try:
            # Find recent conversations that haven't been extracted yet
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            recent = await db.scalars(
                select(Conversation)
                .where(
                    and_(
                        Conversation.user_id == UUID(user_id),
                        Conversation.updated_at >= cutoff_time,
                    )
                )
                .order_by(desc(Conversation.updated_at))
                .limit(max_conversations)
            )

            for conversation in recent:
                # Check if already extracted recently
                if await self._was_recently_extracted(
                    user_id=user_id,
                    conversation_id=str(conversation.id),
                    db=db,
                ):
                    logger.debug(f"Conversation {conversation.id} already extracted recently")
                    continue

                # Extract from this conversation
                log = await self.extract_from_conversation(
                    user_id=user_id,
                    conversation_id=str(conversation.id),
                    db=db,
                )

                if log:
                    results.append(log)

                # Small delay to avoid hammering LLM
                await asyncio.sleep(0.5)

            logger.info(f"Batch extraction complete for user {user_id}: {len(results)} logs")
            return results

        except Exception as e:
            logger.error(f"Error in batch extraction for user {user_id}: {e}", exc_info=True)
            return results

    async def extract_for_all_active_users(
        self,
        hours_back: int = 24,
        max_conversations_per_user: int = 3,
        db: Optional[AsyncSession] = None,
    ) -> dict[str, list[MemoryExtractionLog]]:
        """
        Run periodic batch extraction for all active users.

        Called by a scheduled background job (e.g., Celery, APScheduler) to
        periodically process memory extraction across all users.

        Args:
            hours_back: Look back N hours for conversations
            max_conversations_per_user: Max conversations per user to process
            db: Optional database session

        Returns:
            Dict mapping user_id -> list of extraction results
        """
        if not db:
            async with async_session() as session:
                return await self.extract_for_all_active_users(
                    hours_back, max_conversations_per_user, session
                )

        results = {}

        try:
            # Find users with memory enabled and recent activity
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)

            active_users = await db.scalars(
                select(User)
                .join(UserMemorySettings, UserMemorySettings.user_id == User.id)
                .join(Conversation, Conversation.user_id == User.id)
                .where(
                    and_(
                        UserMemorySettings.memory_enabled == True,
                        UserMemorySettings.auto_extract_enabled == True,
                        Conversation.updated_at >= cutoff_time,
                    )
                )
                .distinct()
            )

            for user in active_users:
                user_id = str(user.id)
                logs = await self.extract_from_recent_conversations(
                    user_id=user_id,
                    hours_back=hours_back,
                    max_conversations=max_conversations_per_user,
                    db=db,
                )

                if logs:
                    results[user_id] = logs

                # Delay between users
                await asyncio.sleep(1)

            logger.info(
                f"Periodic extraction complete: {len(results)} users processed"
            )
            return results

        except Exception as e:
            logger.error(f"Error in periodic extraction: {e}", exc_info=True)
            return results

    async def _was_recently_extracted(
        self,
        user_id: str,
        conversation_id: str,
        db: AsyncSession,
        hours: int = 1,
    ) -> bool:
        """Check if conversation was extracted recently."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        existing = await db.scalar(
            select(MemoryExtractionLog).where(
                and_(
                    MemoryExtractionLog.user_id == user_id,
                    MemoryExtractionLog.conversation_id == conversation_id,
                    MemoryExtractionLog.created_at >= cutoff,
                )
            )
        )

        return existing is not None

    async def cleanup_old_extraction_logs(
        self,
        days_back: int = 90,
        db: Optional[AsyncSession] = None,
    ) -> int:
        """
        Clean up old extraction logs for storage efficiency.

        Called periodically to remove historical extraction logs beyond retention.

        Args:
            days_back: Delete logs older than N days
            db: Optional database session

        Returns:
            Number of logs deleted
        """
        if not db:
            async with async_session() as session:
                return await self.cleanup_old_extraction_logs(days_back, session)

        try:
            cutoff = datetime.utcnow() - timedelta(days=days_back)

            # Find logs to delete
            old_logs = await db.scalars(
                select(MemoryExtractionLog).where(
                    MemoryExtractionLog.created_at < cutoff
                )
            )

            count = 0
            for log in old_logs:
                await db.delete(log)
                count += 1

            await db.commit()

            logger.info(f"Cleaned up {count} old extraction logs")
            return count

        except Exception as e:
            logger.error(f"Error cleaning extraction logs: {e}", exc_info=True)
            return 0
