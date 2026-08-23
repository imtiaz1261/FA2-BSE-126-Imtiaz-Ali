"""
Memory retrieval service.

Retrieves relevant memory items based on semantic similarity.
Injects memories into conversation context.
"""

import logging
from typing import Optional

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models_memory import (
    UserMemoryItem,
    UserMemorySettings,
    MemoryRetrievalLog,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Memory Retrieval Service
# ============================================================================


class MemoryRetrievalService:
    """Retrieve and inject relevant user memories into conversation context."""

    def __init__(self, embedding_service=None):
        """
        Initialize retrieval service.

        Args:
            embedding_service: Service to generate embeddings (e.g., OpenAI, Sentence Transformers)
        """
        self.embedding_service = embedding_service

    async def retrieve_relevant_memories(
        self,
        user_id: str,
        user_message: str,
        db: AsyncSession,
        conversation_id: Optional[str] = None,
    ) -> list[UserMemoryItem]:
        """
        Retrieve memory items relevant to user's current message.

        Uses semantic similarity if embeddings available, otherwise falls back to category-based retrieval.

        Args:
            user_id: User ID
            user_message: User's opening message in new conversation
            db: Database session
            conversation_id: Current conversation ID (for logging)

        Returns:
            List of relevant UserMemoryItem objects, ordered by relevance
        """
        # Get user's memory settings
        settings = await self._get_memory_settings(user_id, db)
        if not settings or not settings.memory_enabled:
            logger.info(f"Memory retrieval skipped: disabled for user {user_id}")
            return []

        # Get active memories
        memories = await db.scalars(
            select(UserMemoryItem).where(
                and_(
                    UserMemoryItem.user_id == user_id,
                    UserMemoryItem.is_active == True,
                )
            )
        )
        memories = list(memories)

        if not memories:
            logger.info(f"No active memories for user {user_id}")
            return []

        # Rank memories by relevance
        ranked_memories = await self._rank_memories(
            user_message, memories, settings
        )

        # Filter by threshold and limit
        relevant = [
            m for m, score in ranked_memories
            if score >= settings.retrieval_threshold
        ][:settings.context_injection_count]

        # Log retrieval
        if relevant:
            await self._log_retrieval(
                user_id=user_id,
                conversation_id=conversation_id,
                retrieved_memory_ids=[str(m.id) for m in relevant],
                user_message=user_message[:200],
                max_similarity_score=max(
                    score for _, score in ranked_memories
                ),
                db=db,
            )

            logger.info(
                f"Retrieved {len(relevant)} memories for user {user_id}: "
                f"{[m.fact[:50] for m in relevant]}"
            )

        return relevant

    async def _rank_memories(
        self,
        user_message: str,
        memories: list[UserMemoryItem],
        settings: UserMemorySettings,
    ) -> list[tuple[UserMemoryItem, float]]:
        """
        Rank memories by relevance to user message.

        Uses semantic similarity if embeddings available, otherwise frequency-based ranking.

        Returns:
            List of (memory, score) tuples sorted by score descending
        """
        ranked = []

        # If embeddings available, use semantic similarity
        if self.embedding_service and memories[0].embedding:
            user_embedding = await self.embedding_service.embed_text(user_message)

            for memory in memories:
                similarity = self._cosine_similarity(
                    user_embedding, memory.embedding
                )
                ranked.append((memory, similarity))

        else:
            # Fallback: frequency-based ranking (LRU)
            for memory in memories:
                # Higher score if recently used and relevant
                score = 0.5  # Base score
                
                # Boost by relevance_score (from extraction confidence)
                score += memory.relevance_score * 0.3
                
                # Boost by retrieval count (popular memories)
                score += min(memory.retrieval_count / 10.0, 0.2)

                ranked.append((memory, score))

        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def _cosine_similarity(self, vec_a: list, vec_b: list) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        if not vec_a or not vec_b:
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
        mag_a = math.sqrt(sum(a * a for a in vec_a))
        mag_b = math.sqrt(sum(b * b for b in vec_b))

        if mag_a == 0 or mag_b == 0:
            return 0.0

        return dot_product / (mag_a * mag_b)

    def build_memory_context(self, memories: list[UserMemoryItem]) -> str:
        """
        Build system prompt injection from retrieved memories.

        Returns formatted context string to inject into assistant's system prompt.
        """
        if not memories:
            return ""

        lines = ["The user has the following known preferences and information:"]
        for i, memory in enumerate(memories, 1):
            lines.append(f"• {memory.fact}")

        lines.append(
            "\nUse this information to personalize your responses. "
            "Reference these facts when relevant."
        )

        return "\n".join(lines)

    async def _get_memory_settings(
        self, user_id: str, db: AsyncSession
    ) -> Optional[UserMemorySettings]:
        """Get user's memory settings."""
        settings = await db.scalar(
            select(UserMemorySettings).where(
                UserMemorySettings.user_id == user_id
            )
        )

        if not settings:
            # Create default settings
            settings = UserMemorySettings(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return settings

    async def _log_retrieval(
        self,
        user_id: str,
        conversation_id: Optional[str],
        retrieved_memory_ids: list[str],
        user_message: str,
        max_similarity_score: float,
        db: AsyncSession,
    ):
        """Log memory retrieval event."""
        log = MemoryRetrievalLog(
            user_id=user_id,
            conversation_id=conversation_id,
            retrieved_memory_ids=retrieved_memory_ids,
            user_message=user_message,
            max_similarity_score=max_similarity_score,
        )
        db.add(log)
        await db.commit()

    async def update_memory_access_time(
        self, memory_id: str, db: AsyncSession
    ):
        """Update last_retrieved_at timestamp and increment counter."""
        from datetime import datetime

        memory = await db.get(UserMemoryItem, memory_id)
        if memory:
            memory.last_retrieved_at = datetime.utcnow()
            memory.retrieval_count += 1
            await db.commit()

    async def cleanup_old_memories(
        self, user_id: str, db: AsyncSession
    ):
        """
        Remove memories older than retention period.

        Called periodically to manage memory store size.
        """
        from datetime import datetime, timedelta

        settings = await self._get_memory_settings(user_id, db)
        if not settings or settings.retention_days == 0:
            # retention_days=0 means keep forever
            return 0

        cutoff_date = datetime.utcnow() - timedelta(days=settings.retention_days)

        # Find oldest memories when total exceeds max_memory_items
        total_count = await db.scalar(
            select(func.count(UserMemoryItem.id)).where(
                UserMemoryItem.user_id == user_id
            )
        )

        if total_count > settings.max_memory_items:
            # Delete least-recently-used memories
            to_delete = total_count - settings.max_memory_items
            old_memories = await db.scalars(
                select(UserMemoryItem)
                .where(UserMemoryItem.user_id == user_id)
                .order_by(UserMemoryItem.last_retrieved_at)
                .limit(to_delete)
            )

            for memory in old_memories:
                await db.delete(memory)

            await db.commit()
            return to_delete

        return 0

    async def get_memory_stats(self, user_id: str, db: AsyncSession) -> dict:
        """Get memory statistics for user."""
        from sqlalchemy import func

        total = await db.scalar(
            select(func.count(UserMemoryItem.id)).where(
                UserMemoryItem.user_id == user_id
            )
        )

        by_category = await db.scalars(
            select(UserMemoryItem.category, func.count(UserMemoryItem.id))
            .where(UserMemoryItem.user_id == user_id)
            .group_by(UserMemoryItem.category)
        )

        return {
            "total_memories": total or 0,
            "by_category": dict(by_category) if by_category else {},
        }
