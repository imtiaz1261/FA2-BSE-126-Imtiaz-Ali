"""
Memory extraction service.

Identifies durable, non-sensitive facts from conversation history using LLM.
Runs after conversations end or periodically.
"""

import json
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm_service import get_llm_client
from app.models import Message, MessageRole
from app.models_memory import (
    MemoryCategory,
    MemoryExtractionLog,
    UserMemoryItem,
    UserMemorySettings,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Extraction Prompt
# ============================================================================


MEMORY_EXTRACTION_PROMPT = """You are analyzing a conversation to identify durable, personally identifiable facts worth remembering about the user.

IMPORTANT GUIDELINES:
1. Extract ONLY factual, non-sensitive information (name, role, stated preferences, skills, constraints, goals)
2. NEVER extract: passwords, credentials, financial details, medical info, personally identifiable addresses
3. Each fact should be self-contained and understandable without conversation context
4. Prefer specific, actionable facts over generic statements
5. Avoid speculation; only extract explicitly stated information
6. Categorize each fact appropriately

CATEGORIES:
- personal_info: Name, title, location, age
- preferences: Communication style, work preferences, learning style
- goals_and_values: Career goals, values, stated objectives
- skills_and_expertise: Technical skills, domain knowledge, languages
- constraints: Time zone, availability, limitations
- recurring_tasks: Patterns in work, repeated requests
- project_context: Active projects, ongoing initiatives
- other: Miscellaneous facts

CONVERSATION:
{conversation}

OUTPUT FORMAT:
Return a JSON object with this exact structure:
{{
  "facts": [
    {{
      "fact": "Specific, concise statement of the fact",
      "category": "one of the categories above",
      "confidence": 0.95,
      "source_context": "Brief quote or reference from conversation"
    }}
  ],
  "rejected_facts": [
    {{
      "draft_fact": "What we considered but rejected",
      "reason": "Why it was rejected (sensitive, unclear, generic, duplicate, etc.)"
    }}
  ],
  "summary": "Brief assessment of what we learned about the user"
}}

Extract 0-10 facts. Prefer quality over quantity. Only include high-confidence extractions."""


# ============================================================================
# Memory Extraction Service
# ============================================================================


class MemoryExtractionService:
    """Extract durable facts from conversation history."""

    def __init__(self, llm_client=None):
        """Initialize extraction service."""
        self.llm_client = llm_client or get_llm_client()

    async def extract_from_conversation(
        self,
        user_id: str,
        messages: list[Message],
        conversation_id: str,
        db: AsyncSession,
        trigger: str = "post_conversation",
    ) -> Optional[MemoryExtractionLog]:
        """
        Extract facts from a complete conversation.

        Args:
            user_id: User ID
            messages: List of Message objects from conversation
            conversation_id: Conversation ID (for source tracking)
            db: Database session
            trigger: Extraction trigger (post_conversation, manual, periodic)

        Returns:
            MemoryExtractionLog with results, or None if extraction failed
        """
        if not messages:
            logger.warning(f"No messages to extract from conversation {conversation_id}")
            return None

        # Check memory settings
        memory_settings = await self._get_memory_settings(user_id, db)
        if not memory_settings or not memory_settings.memory_enabled:
            logger.info(f"Memory disabled for user {user_id}")
            return None

        # Format conversation for LLM
        conversation_text = self._format_conversation(messages)

        # Call LLM to extract facts
        try:
            extraction_result = await self._call_extraction_llm(conversation_text)
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Log the failure
            log = MemoryExtractionLog(
                user_id=user_id,
                conversation_id=conversation_id,
                facts_extracted_count=0,
                facts_rejected_count=0,
                trigger=trigger,
                success=False,
                error_message=str(e),
            )
            db.add(log)
            await db.commit()
            return log

        # Process extracted facts
        facts_stored = 0
        facts_rejected = 0
        rejection_reasons = []

        for fact_data in extraction_result.get("facts", []):
            # Validate fact
            if not self._is_valid_fact(fact_data.get("fact")):
                facts_rejected += 1
                rejection_reasons.append("Invalid or sensitive fact")
                continue

            # Check for duplicates
            if await self._is_duplicate(user_id, fact_data.get("fact"), db):
                facts_rejected += 1
                rejection_reasons.append("Duplicate")
                continue

            # Store the fact
            try:
                memory_item = await self._store_memory_item(
                    user_id=user_id,
                    fact=fact_data.get("fact"),
                    category=fact_data.get("category", "other"),
                    confidence=fact_data.get("confidence", 0.8),
                    source_conversation_id=conversation_id,
                    extraction_context=fact_data.get("source_context"),
                    db=db,
                )
                if memory_item:
                    facts_stored += 1
            except Exception as e:
                logger.error(f"Failed to store memory item: {e}")
                facts_rejected += 1
                rejection_reasons.append("Storage error")

        # Log the extraction event
        log = MemoryExtractionLog(
            user_id=user_id,
            conversation_id=conversation_id,
            facts_extracted_count=facts_stored,
            facts_rejected_count=facts_rejected,
            rejection_reasons=rejection_reasons[:10],  # Limit reasons
            trigger=trigger,
            success=True,
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        logger.info(
            f"Extracted {facts_stored} facts, rejected {facts_rejected} for user {user_id}"
        )
        return log

    def _format_conversation(self, messages: list[Message]) -> str:
        """Format messages as readable conversation."""
        lines = []
        for msg in messages:
            role = "User" if msg.role == MessageRole.user else "Assistant"
            lines.append(f"{role}: {msg.content[:500]}")  # Truncate long messages

        return "\n".join(lines)

    async def _call_extraction_llm(self, conversation_text: str) -> dict:
        """Call LLM to extract facts."""
        prompt = MEMORY_EXTRACTION_PROMPT.format(conversation=conversation_text)

        response = await self.llm_client.create_message(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4",  # Use capable model for extraction
            temperature=0.3,  # Lower temperature for consistency
        )

        # Parse JSON response
        content = response.choices[0].message.content
        
        # Extract JSON from response (handle markdown code blocks)
        if "```" in content:
            json_str = content.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        else:
            json_str = content

        result = json.loads(json_str.strip())
        return result

    def _is_valid_fact(self, fact: str) -> bool:
        """Validate fact is not sensitive/invalid."""
        if not fact or len(fact) < 10 or len(fact) > 500:
            return False

        # Blacklist sensitive patterns
        sensitive_patterns = [
            "password",
            "token",
            "credit card",
            "ssn",
            "api key",
            "secret",
            "confidential",
        ]

        fact_lower = fact.lower()
        if any(pattern in fact_lower for pattern in sensitive_patterns):
            return False

        return True

    async def _is_duplicate(self, user_id: str, fact: str, db: AsyncSession) -> bool:
        """Check if similar fact already exists."""
        from sqlalchemy import select

        # Simple substring match for now; could use embeddings for fuzzy match
        existing = await db.scalar(
            select(UserMemoryItem).where(
                UserMemoryItem.user_id == user_id,
                UserMemoryItem.fact.ilike(f"%{fact[:50]}%"),
            )
        )
        return existing is not None

    async def _store_memory_item(
        self,
        user_id: str,
        fact: str,
        category: str,
        confidence: float,
        source_conversation_id: str,
        extraction_context: str,
        db: AsyncSession,
    ) -> Optional[UserMemoryItem]:
        """Store extracted fact as memory item."""
        try:
            # TODO: Generate embedding using sentence transformer or OpenAI embeddings
            # embedding = await self._generate_embedding(fact)

            item = UserMemoryItem(
                user_id=user_id,
                fact=fact,
                category=MemoryCategory(category),
                embedding=None,  # TODO: add embedding
                relevance_score=min(confidence, 1.0),
                source_conversation_id=source_conversation_id,
                extraction_context=extraction_context,
                is_active=True,
            )

            db.add(item)
            await db.commit()
            await db.refresh(item)
            return item

        except Exception as e:
            logger.error(f"Error storing memory item: {e}")
            return None

    async def _get_memory_settings(
        self, user_id: str, db: AsyncSession
    ) -> Optional[UserMemorySettings]:
        """Get user's memory settings, creating defaults if needed."""
        from sqlalchemy import select

        settings = await db.scalar(
            select(UserMemorySettings).where(UserMemorySettings.user_id == user_id)
        )

        if not settings:
            # Create default settings
            settings = UserMemorySettings(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return settings

    async def extract_from_recent_conversations(
        self, user_id: str, db: AsyncSession, limit: int = 10
    ) -> list[MemoryExtractionLog]:
        """
        Extract facts from user's recent conversations.

        Useful for periodic re-indexing or user request.
        """
        from sqlalchemy import select, desc

        logs = []

        # Get recent conversations
        conversations = await db.scalars(
            select("Conversation")
            .where("Conversation.user_id == user_id")
            .order_by(desc("Conversation.created_at"))
            .limit(limit)
        )

        for conversation in conversations:
            # Get messages
            messages = await db.scalars(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at)
            )

            # Extract
            log = await self.extract_from_conversation(
                user_id=user_id,
                messages=list(messages),
                conversation_id=str(conversation.id),
                db=db,
                trigger="periodic",
            )

            if log:
                logs.append(log)

        return logs
