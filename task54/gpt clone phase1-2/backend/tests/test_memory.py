"""
Comprehensive tests for Memory & Personalization module.

Tests:
- Memory extraction (LLM calls, duplicate detection, storage)
- Memory retrieval (semantic similarity, frequency-based ranking)
- CRUD operations
- Context injection
- Cleanup and maintenance
"""

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Conversation, Message, MessageRole
from app.models_memory import (
    UserMemoryItem,
    MemoryCategory,
    MemoryExtractionLog,
    UserMemorySettings,
    MemoryRetrievalLog,
)
from app.services.memory_extraction import MemoryExtractionService
from app.services.memory_retrieval import MemoryRetrievalService
from app.services.memory_jobs import MemoryJobsService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=uuid.uuid4(),
        email="memory-test@example.com",
        username="memory-tester",
        hashed_password="fake",
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_conversation(db_session: AsyncSession, test_user: User) -> Conversation:
    """Create test conversation."""
    conv = Conversation(
        id=uuid.uuid4(),
        user_id=test_user.id,
        title="Memory Test",
    )
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    return conv


@pytest.fixture
async def test_messages(
    db_session: AsyncSession, test_conversation: Conversation
) -> list[Message]:
    """Create test messages."""
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=test_conversation.id,
            role=MessageRole.user,
            content="My name is Alice and I work as a software engineer at TechCorp",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=test_conversation.id,
            role=MessageRole.assistant,
            content="Nice to meet you, Alice! I'm here to help with any technical questions.",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=test_conversation.id,
            role=MessageRole.user,
            content="I prefer concise, technical explanations. I work in Python and Go.",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=test_conversation.id,
            role=MessageRole.assistant,
            content="Got it! I'll keep explanations concise and technical.",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=test_conversation.id,
            role=MessageRole.user,
            content="I'm currently working on a microservices project using Docker and Kubernetes.",
        ),
    ]

    for msg in messages:
        db_session.add(msg)

    await db_session.commit()
    for msg in messages:
        await db_session.refresh(msg)

    return messages


@pytest.fixture
async def memory_settings(db_session: AsyncSession, test_user: User) -> UserMemorySettings:
    """Create memory settings."""
    settings = UserMemorySettings(
        user_id=test_user.id,
        memory_enabled=True,
        auto_extract_enabled=True,
        max_memory_items=50,
        context_injection_count=5,
        retrieval_threshold=0.6,
    )
    db_session.add(settings)
    await db_session.commit()
    await db_session.refresh(settings)
    return settings


# ============================================================================
# Extraction Tests
# ============================================================================


@pytest.mark.asyncio
async def test_memory_extraction_service_init():
    """Test extraction service initialization."""
    service = MemoryExtractionService()
    assert service is not None
    assert service.llm_client is not None


@pytest.mark.asyncio
async def test_is_valid_fact():
    """Test fact validation."""
    service = MemoryExtractionService()

    # Valid facts
    assert service._is_valid_fact("Alice is a software engineer at TechCorp")
    assert service._is_valid_fact("Prefers Python and Go for development")

    # Invalid facts
    assert not service._is_valid_fact("")  # Empty
    assert not service._is_valid_fact("short")  # Too short
    assert not service._is_valid_fact("a" * 501)  # Too long
    assert not service._is_valid_fact("my password is 123456")  # Sensitive
    assert not service._is_valid_fact("api key: sk_live_123456")  # Sensitive


@pytest.mark.asyncio
async def test_format_conversation():
    """Test conversation formatting."""
    service = MemoryExtractionService()
    messages = [
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            role=MessageRole.user,
            content="Hello, how are you?",
        ),
        Message(
            id=uuid.uuid4(),
            conversation_id=uuid.uuid4(),
            role=MessageRole.assistant,
            content="I'm doing great, thanks for asking!",
        ),
    ]

    formatted = service._format_conversation(messages)

    assert "User: Hello, how are you?" in formatted
    assert "Assistant: I'm doing great, thanks for asking!" in formatted


@pytest.mark.asyncio
async def test_store_memory_item(db_session: AsyncSession, test_user: User):
    """Test storing a memory item."""
    service = MemoryExtractionService()

    item = await service._store_memory_item(
        user_id=test_user.id,
        fact="Alice works as a software engineer",
        category="personal_info",
        confidence=0.95,
        source_conversation_id=uuid.uuid4(),
        extraction_context="My name is Alice and I work as a software engineer",
        db=db_session,
    )

    assert item is not None
    assert item.fact == "Alice works as a software engineer"
    assert item.category == MemoryCategory.personal_info
    assert item.relevance_score == 0.95
    assert item.is_active


@pytest.mark.asyncio
async def test_duplicate_detection(db_session: AsyncSession, test_user: User):
    """Test duplicate memory detection."""
    service = MemoryExtractionService()

    # Create first memory
    item1 = await service._store_memory_item(
        user_id=test_user.id,
        fact="Alice is a software engineer",
        category="personal_info",
        confidence=0.95,
        source_conversation_id=uuid.uuid4(),
        extraction_context="Test",
        db=db_session,
    )

    assert item1 is not None

    # Check for duplicate
    is_dup = await service._is_duplicate(test_user.id, "Alice is a software engineer", db_session)
    assert is_dup


@pytest.mark.asyncio
async def test_extraction_with_mock_llm(
    db_session: AsyncSession, test_user: User, test_messages: list[Message]
):
    """Test extraction with mock LLM (simplified - in real tests use mocking library)."""
    service = MemoryExtractionService()

    # For this test, we'll manually create extraction results
    # In production, this would call actual LLM
    facts = [
        {
            "fact": "Alice works as a software engineer at TechCorp",
            "category": "personal_info",
            "confidence": 0.95,
            "source_context": "My name is Alice and I work as a software engineer",
        },
        {
            "fact": "Prefers concise, technical explanations",
            "category": "preferences",
            "confidence": 0.9,
            "source_context": "I prefer concise, technical explanations",
        },
        {
            "fact": "Skilled in Python and Go programming",
            "category": "skills_and_expertise",
            "confidence": 0.95,
            "source_context": "I work in Python and Go",
        },
        {
            "fact": "Currently working on microservices project with Docker/Kubernetes",
            "category": "project_context",
            "confidence": 0.9,
            "source_context": "I'm currently working on a microservices project using Docker and Kubernetes",
        },
    ]

    # Store each fact
    for fact_data in facts:
        await service._store_memory_item(
            user_id=test_user.id,
            fact=fact_data["fact"],
            category=fact_data["category"],
            confidence=fact_data["confidence"],
            source_conversation_id=test_messages[0].conversation_id,
            extraction_context=fact_data["source_context"],
            db=db_session,
        )

    # Verify all stored
    all_memories = await db_session.scalars(
        select(UserMemoryItem).where(UserMemoryItem.user_id == test_user.id)
    )
    stored_memories = list(all_memories)

    assert len(stored_memories) == len(facts)
    assert any("Alice" in m.fact for m in stored_memories)
    assert any("Python" in m.fact for m in stored_memories)


# ============================================================================
# Retrieval Tests
# ============================================================================


@pytest.mark.asyncio
async def test_memory_retrieval_service_init():
    """Test retrieval service initialization."""
    service = MemoryRetrievalService()
    assert service is not None


@pytest.mark.asyncio
async def test_cosine_similarity():
    """Test cosine similarity calculation."""
    service = MemoryRetrievalService()

    # Identical vectors
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    assert service._cosine_similarity(vec1, vec2) == 1.0

    # Orthogonal vectors
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    assert service._cosine_similarity(vec1, vec2) == 0.0

    # Opposite vectors
    vec1 = [1.0, 0.0]
    vec2 = [-1.0, 0.0]
    assert service._cosine_similarity(vec1, vec2) == -1.0


@pytest.mark.asyncio
async def test_build_memory_context(db_session: AsyncSession, test_user: User):
    """Test memory context building."""
    service = MemoryRetrievalService()

    # Create test memories
    memories = [
        UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact="Alice works as a software engineer",
            category=MemoryCategory.personal_info,
            is_active=True,
        ),
        UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact="Prefers Python and Go",
            category=MemoryCategory.skills_and_expertise,
            is_active=True,
        ),
    ]

    context = service.build_memory_context(memories)

    assert "Alice works as a software engineer" in context
    assert "Prefers Python and Go" in context
    assert "personalize your responses" in context


@pytest.mark.asyncio
async def test_retrieve_with_empty_memory(
    db_session: AsyncSession, test_user: User, memory_settings: UserMemorySettings
):
    """Test retrieval with no memories stored."""
    service = MemoryRetrievalService()

    memories = await service.retrieve_relevant_memories(
        user_id=test_user.id,
        user_message="Tell me about Python",
        db=db_session,
    )

    assert memories == []


@pytest.mark.asyncio
async def test_retrieve_disabled_memory(
    db_session: AsyncSession, test_user: User, memory_settings: UserMemorySettings
):
    """Test retrieval when memory is disabled."""
    # Disable memory
    memory_settings.memory_enabled = False
    await db_session.commit()

    service = MemoryRetrievalService()

    memories = await service.retrieve_relevant_memories(
        user_id=test_user.id,
        user_message="Tell me about Python",
        db=db_session,
    )

    assert memories == []


@pytest.mark.asyncio
async def test_frequency_based_ranking(
    db_session: AsyncSession, test_user: User, memory_settings: UserMemorySettings
):
    """Test frequency-based memory ranking (fallback when no embeddings)."""
    service = MemoryRetrievalService()

    # Create memories with different retrieval counts
    memories = [
        UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact="Frequently used memory",
            category=MemoryCategory.preferences,
            relevance_score=0.8,
            retrieval_count=10,
            is_active=True,
        ),
        UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact="Rarely used memory",
            category=MemoryCategory.preferences,
            relevance_score=0.7,
            retrieval_count=0,
            is_active=True,
        ),
    ]

    # Rank them
    ranked = await service._rank_memories("test query", memories, memory_settings)

    # Frequently used should rank higher
    assert ranked[0][0].retrieval_count > ranked[1][0].retrieval_count


# ============================================================================
# CRUD Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_memory_item(db_session: AsyncSession, test_user: User):
    """Test creating a memory item via CRUD."""
    item = UserMemoryItem(
        id=uuid.uuid4(),
        user_id=test_user.id,
        fact="Test memory fact",
        category=MemoryCategory.personal_info,
        is_active=True,
    )

    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    assert item.id is not None
    assert item.user_id == test_user.id
    assert item.fact == "Test memory fact"


@pytest.mark.asyncio
async def test_update_memory_item(db_session: AsyncSession, test_user: User):
    """Test updating a memory item."""
    item = UserMemoryItem(
        id=uuid.uuid4(),
        user_id=test_user.id,
        fact="Original fact",
        category=MemoryCategory.personal_info,
        is_active=True,
    )

    db_session.add(item)
    await db_session.commit()

    # Update
    item.fact = "Updated fact"
    item.is_active = False
    await db_session.commit()

    # Verify
    fetched = await db_session.get(UserMemoryItem, item.id)
    assert fetched.fact == "Updated fact"
    assert fetched.is_active == False


@pytest.mark.asyncio
async def test_delete_memory_item(db_session: AsyncSession, test_user: User):
    """Test deleting a memory item."""
    item = UserMemoryItem(
        id=uuid.uuid4(),
        user_id=test_user.id,
        fact="To be deleted",
        category=MemoryCategory.personal_info,
        is_active=True,
    )

    db_session.add(item)
    await db_session.commit()

    item_id = item.id

    # Delete
    await db_session.delete(item)
    await db_session.commit()

    # Verify deleted
    fetched = await db_session.get(UserMemoryItem, item_id)
    assert fetched is None


@pytest.mark.asyncio
async def test_list_memories_by_category(db_session: AsyncSession, test_user: User):
    """Test listing memories filtered by category."""
    # Create memories in different categories
    for i in range(3):
        item = UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact=f"Skill {i}",
            category=MemoryCategory.skills_and_expertise,
            is_active=True,
        )
        db_session.add(item)

    for i in range(2):
        item = UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact=f"Preference {i}",
            category=MemoryCategory.preferences,
            is_active=True,
        )
        db_session.add(item)

    await db_session.commit()

    # Query by category
    skills = await db_session.scalars(
        select(UserMemoryItem).where(
            UserMemoryItem.user_id == test_user.id,
            UserMemoryItem.category == MemoryCategory.skills_and_expertise,
        )
    )

    assert len(list(skills)) == 3


# ============================================================================
# Jobs/Maintenance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_enforce_memory_limits(db_session: AsyncSession, test_user: User):
    """Test enforcing memory item limits."""
    # Set limit to 5
    settings = UserMemorySettings(
        user_id=test_user.id,
        memory_enabled=True,
        max_memory_items=5,
    )
    db_session.add(settings)
    await db_session.commit()

    # Create 10 items
    for i in range(10):
        item = UserMemoryItem(
            id=uuid.uuid4(),
            user_id=test_user.id,
            fact=f"Memory {i}",
            category=MemoryCategory.other,
            is_active=True,
        )
        db_session.add(item)

    await db_session.commit()

    # Run enforce
    jobs = MemoryJobsService(db_session)
    evicted = await jobs.enforce_memory_limits(test_user.id)

    # Should have evicted 5 (10 - 5 limit)
    assert evicted == 5

    # Verify count
    total = await db_session.scalar(
        select(func.count(UserMemoryItem.id)).where(
            UserMemoryItem.user_id == test_user.id
        )
    )
    assert total == 5


@pytest.mark.asyncio
async def test_memory_retrieval_logging(db_session: AsyncSession, test_user: User):
    """Test that memory retrievals are logged."""
    service = MemoryRetrievalService()

    memory_ids = [str(uuid.uuid4()), str(uuid.uuid4())]

    await service._log_retrieval(
        user_id=test_user.id,
        conversation_id=uuid.uuid4(),
        retrieved_memory_ids=memory_ids,
        user_message="Test message",
        max_similarity_score=0.85,
        db=db_session,
    )

    # Verify log was created
    log = await db_session.scalar(
        select(MemoryRetrievalLog).where(MemoryRetrievalLog.user_id == test_user.id)
    )

    assert log is not None
    assert log.retrieved_memory_ids == memory_ids
    assert log.max_similarity_score == 0.85


# ============================================================================
# Settings Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_or_create_settings(db_session: AsyncSession, test_user: User):
    """Test getting or creating memory settings."""
    service = MemoryExtractionService()

    settings = await service._get_memory_settings(test_user.id, db_session)

    assert settings is not None
    assert settings.user_id == test_user.id
    assert settings.memory_enabled == True  # Default


@pytest.mark.asyncio
async def test_memory_disabled_skip_extraction(
    db_session: AsyncSession, test_user: User, test_messages: list[Message]
):
    """Test that extraction is skipped when memory is disabled."""
    # Disable memory
    settings = UserMemorySettings(user_id=test_user.id, memory_enabled=False)
    db_session.add(settings)
    await db_session.commit()

    service = MemoryExtractionService()

    log = await service.extract_from_conversation(
        user_id=test_user.id,
        messages=test_messages,
        conversation_id=str(test_messages[0].conversation_id),
        db=db_session,
    )

    # Should return None when disabled
    assert log is None
