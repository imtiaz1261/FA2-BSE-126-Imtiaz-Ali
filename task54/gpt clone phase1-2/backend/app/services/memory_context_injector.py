"""
Memory Context Injector Service

Handles injection of retrieved user memories into LLM system prompts.
Integrates with memory retrieval to provide personalized context.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.models_memory import UserMemoryItem
from app.services.memory_retrieval import MemoryRetrievalService
from app.schemas_chat import ChatMessage

logger = logging.getLogger(__name__)


class MemoryContextInjector:
    """Inject retrieved memories into LLM context as hidden system prompts."""

    def __init__(self, embedding_service=None):
        """
        Initialize context injector.

        Args:
            embedding_service: Service for generating embeddings (optional)
        """
        self.retrieval_service = MemoryRetrievalService(embedding_service)

    async def inject_memory_context(
        self,
        messages: list[dict | ChatMessage],
        user_id: str,
        db: AsyncSession,
        conversation_id: Optional[str] = None,
    ) -> list[dict | ChatMessage]:
        """
        Retrieve relevant memories and inject into message context.

        Retrieves memories based on the user's opening message and injects them
        as hidden system context. This personalizes the LLM response without
        making memories visible to the user in the message history.

        Args:
            messages: List of chat messages (dicts or ChatMessage objects)
            user_id: User ID to retrieve memories for
            db: Database session
            conversation_id: Current conversation ID (for logging)

        Returns:
            Messages list with memory context injected (or original if no memories)
        """
        if not messages:
            return messages

        try:
            # Find user's opening message to retrieve contextually relevant memories
            first_user_message = self._get_first_user_message(messages)

            if not first_user_message:
                return messages

            # Retrieve memories relevant to this conversation
            relevant_memories = (
                await self.retrieval_service.retrieve_relevant_memories(
                    user_id=user_id,
                    user_message=first_user_message,
                    db=db,
                    conversation_id=conversation_id,
                )
            )

            if not relevant_memories:
                logger.debug(f"No relevant memories found for user {user_id}")
                return messages

            # Build memory context injection
            memory_context = (
                self.retrieval_service.build_memory_context(relevant_memories)
            )

            # Inject into system prompt
            updated_messages = self._inject_into_system_prompt(
                messages, memory_context
            )

            # Update memory access timestamps
            for memory in relevant_memories:
                await self.retrieval_service.update_memory_access_time(
                    str(memory.id), db
                )

            logger.info(
                f"Injected {len(relevant_memories)} memories "
                f"for user {user_id} in conversation {conversation_id}"
            )

            return updated_messages

        except Exception as e:
            # Don't fail the chat if memory injection errors
            logger.error(f"Memory injection failed: {e}", exc_info=True)
            return messages

    def _get_first_user_message(
        self, messages: list[dict | ChatMessage]
    ) -> Optional[str]:
        """Extract the first user message from the conversation."""
        for msg in messages:
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    return msg.get("content", "")
            else:
                # ChatMessage object
                if msg.role == "user":
                    return msg.content
        return None

    def _inject_into_system_prompt(
        self, messages: list[dict | ChatMessage], memory_context: str
    ) -> list[dict | ChatMessage]:
        """
        Inject memory context into the system prompt.

        If a system message exists, appends memory context to it.
        Otherwise, inserts a new system message at the beginning.

        Args:
            messages: Original messages list
            memory_context: Formatted memory context string

        Returns:
            Updated messages list with memory context injected
        """
        if not memory_context:
            return messages

        updated_messages = messages.copy()

        # Find existing system message
        system_msg_idx = None
        for i, msg in enumerate(updated_messages):
            if isinstance(msg, dict):
                if msg.get("role") == "system":
                    system_msg_idx = i
                    break
            else:
                # ChatMessage object
                if msg.role == "system":
                    system_msg_idx = i
                    break

        if system_msg_idx is not None:
            # Append memory context to existing system message
            if isinstance(updated_messages[system_msg_idx], dict):
                updated_messages[system_msg_idx]["content"] += (
                    f"\n\n{memory_context}"
                )
            else:
                # ChatMessage object
                updated_messages[system_msg_idx] = ChatMessage(
                    role="system",
                    content=updated_messages[system_msg_idx].content
                    + f"\n\n{memory_context}",
                )
        else:
            # Insert new system message at the beginning
            if updated_messages and isinstance(updated_messages[0], dict):
                updated_messages.insert(
                    0, {"role": "system", "content": memory_context}
                )
            else:
                updated_messages.insert(0, ChatMessage(role="system", content=memory_context))

        return updated_messages

    async def cleanup_old_memories(self, user_id: str, db: AsyncSession) -> int:
        """
        Clean up old or excess memories for a user.

        Called periodically to manage memory store size and retention.

        Args:
            user_id: User ID to clean up memories for
            db: Database session

        Returns:
            Number of memories deleted
        """
        return await self.retrieval_service.cleanup_old_memories(user_id, db)

    async def get_memory_stats(self, user_id: str, db: AsyncSession) -> dict:
        """Get memory statistics for a user."""
        return await self.retrieval_service.get_memory_stats(user_id, db)
