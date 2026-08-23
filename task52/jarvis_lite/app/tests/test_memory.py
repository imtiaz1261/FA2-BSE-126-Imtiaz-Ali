"""Tests for memory module (buffer and summary memory)."""

import pytest

from app.memory.buffer_memory import ConversationBufferMemory
from app.memory.summary_memory import ConversationSummaryMemory
from app.memory.memory_service import MemoryService


class TestConversationBufferMemory:
    """Test ConversationBufferMemory."""

    def test_add_message(self):
        """Test adding a message."""
        memory = ConversationBufferMemory(max_messages=5)
        memory.add_message("user", "Hello")
        
        context = memory.get_context()
        assert len(context.messages) == 1
        assert context.messages[0].role == "user"
        assert context.messages[0].content == "Hello"

    def test_max_messages_enforced(self):
        """Test that max_messages limit is enforced."""
        memory = ConversationBufferMemory(max_messages=3)
        
        # Add 5 messages
        for i in range(5):
            memory.add_message("user", f"Message {i}")
        
        # Should only have last 3
        context = memory.get_context()
        assert len(context.messages) == 3
        assert context.messages[0].content == "Message 2"
        assert context.messages[-1].content == "Message 4"

    def test_message_ordering(self):
        """Test that messages are in correct order."""
        memory = ConversationBufferMemory(max_messages=10)
        
        memory.add_message("user", "Q1")
        memory.add_message("assistant", "A1")
        memory.add_message("user", "Q2")
        
        context = memory.get_context()
        assert context.messages[0].content == "Q1"
        assert context.messages[1].content == "A1"
        assert context.messages[2].content == "Q2"

    def test_metadata_preservation(self):
        """Test that metadata is preserved."""
        memory = ConversationBufferMemory(max_messages=5)
        metadata = {"source": "test", "timestamp": "2024-01-01"}
        
        memory.add_message("user", "Hello", metadata=metadata)
        
        context = memory.get_context()
        assert context.messages[0].metadata == metadata

    def test_clear(self):
        """Test clearing memory."""
        memory = ConversationBufferMemory(max_messages=5)
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi")
        
        memory.clear()
        
        context = memory.get_context()
        assert len(context.messages) == 0

    def test_get_summary_returns_none(self):
        """Test that buffer memory returns None for summary."""
        memory = ConversationBufferMemory(max_messages=5)
        memory.add_message("user", "Hello")
        
        assert memory.get_summary() is None

    def test_len(self):
        """Test __len__ method."""
        memory = ConversationBufferMemory(max_messages=5)
        
        assert len(memory) == 0
        
        memory.add_message("user", "Hello")
        assert len(memory) == 1
        
        memory.add_message("assistant", "Hi")
        assert len(memory) == 2


class TestConversationSummaryMemory:
    """Test ConversationSummaryMemory."""

    def test_keeps_recent_messages(self):
        """Test that recent messages are kept."""
        memory = ConversationSummaryMemory(recent_messages=2)
        
        memory.add_message("user", "Message 1")
        memory.add_message("assistant", "Reply 1")
        memory.add_message("user", "Message 2")
        
        context = memory.get_context()
        assert len(context.messages) == 2
        assert context.messages[0].content == "Reply 1"
        assert context.messages[1].content == "Message 2"

    def test_creates_summary(self):
        """Test that summary is created when exceeding recent_messages."""
        memory = ConversationSummaryMemory(recent_messages=2)
        
        memory.add_message("user", "Q1")
        memory.add_message("assistant", "A1")
        memory.add_message("user", "Q2")  # This triggers summarization
        memory.add_message("assistant", "A2")
        
        context = memory.get_context()
        assert context.summary is not None
        assert len(context.messages) == 2  # Only recent 2

    def test_summary_includes_old_messages(self):
        """Test that summary contains information from old messages."""
        memory = ConversationSummaryMemory(recent_messages=1)
        
        memory.add_message("user", "What is Python?")
        memory.add_message("assistant", "Python is a programming language")
        memory.add_message("user", "Tell me more")  # Triggers summary
        
        summary = memory.get_summary()
        assert summary is not None
        assert len(summary) > 0

    def test_clear(self):
        """Test clearing summary memory."""
        memory = ConversationSummaryMemory(recent_messages=2)
        
        memory.add_message("user", "Q1")
        memory.add_message("assistant", "A1")
        memory.add_message("user", "Q2")
        memory.add_message("assistant", "A2")
        
        memory.clear()
        
        context = memory.get_context()
        assert len(context.messages) == 0
        assert memory.get_summary() is None

    def test_metadata_preserved_in_summary(self):
        """Test that metadata is preserved in recent messages."""
        memory = ConversationSummaryMemory(recent_messages=2)
        
        memory.add_message("user", "Q1", metadata={"id": 1})
        memory.add_message("assistant", "A1", metadata={"id": 2})
        memory.add_message("user", "Q2", metadata={"id": 3})  # Triggers summary
        
        context = memory.get_context()
        # Recent messages should be A1 and Q2
        recent_metadata = [m.metadata for m in context.messages]
        assert {"id": 3} in recent_metadata


class TestMemoryService:
    """Test MemoryService orchestration."""

    def test_buffer_memory_service(self):
        """Test memory service with buffer memory."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        service.add_user_message("Hello")
        service.add_assistant_message("Hi there!")
        
        context = service.get_context()
        assert len(context.messages) == 2

    def test_summary_memory_service(self):
        """Test memory service with summary memory."""
        service = MemoryService(memory_type="summary", max_context=2)
        
        service.add_user_message("Q1")
        service.add_assistant_message("A1")
        service.add_user_message("Q2")
        
        context = service.get_context()
        assert len(context.messages) == 2

    def test_get_context_for_prompt(self):
        """Test getting context formatted for LLM prompt."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        service.add_user_message("Hello")
        service.add_assistant_message("Hi!")
        
        prompt_messages = service.get_context_for_prompt()
        
        # Should be formatted as OpenAI message dicts
        assert len(prompt_messages) == 2
        assert prompt_messages[0]["role"] == "user"
        assert prompt_messages[1]["role"] == "assistant"

    def test_get_last_user_message(self):
        """Test retrieving last user message."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        service.add_user_message("First question")
        service.add_assistant_message("Answer")
        service.add_user_message("Second question")
        
        last = service.get_last_user_message()
        assert last == "Second question"

    def test_clear_memory(self):
        """Test clearing memory via service."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        service.add_user_message("Hello")
        service.add_assistant_message("Hi")
        
        assert service.get_message_count() == 2
        
        service.clear()
        
        assert service.get_message_count() == 0

    def test_message_count(self):
        """Test getting message count."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        assert service.get_message_count() == 0
        
        service.add_user_message("Q")
        assert service.get_message_count() == 1
        
        service.add_assistant_message("A")
        assert service.get_message_count() == 2

    def test_to_dict(self):
        """Test exporting memory state."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        service.add_user_message("Hello")
        service.add_assistant_message("Hi")
        
        state = service.to_dict()
        
        assert "conversation_id" in state
        assert state["memory_type"] == "buffer"
        assert state["message_count"] == 2
        assert len(state["messages"]) == 2

    def test_invalid_memory_type(self):
        """Test that invalid memory type raises error."""
        with pytest.raises(Exception):
            MemoryService(memory_type="invalid", max_context=5)

    def test_conversation_id_consistency(self):
        """Test that conversation ID is consistent."""
        service = MemoryService(memory_type="buffer", max_context=5)
        
        conv_id_1 = service.get_context().conversation_id
        conv_id_2 = service.get_context().conversation_id
        
        assert conv_id_1 == conv_id_2

    def test_summary_included_in_prompt(self):
        """Test that summary is included in prompt messages when available."""
        service = MemoryService(memory_type="summary", max_context=1)
        
        service.add_user_message("Old question")
        service.add_assistant_message("Old answer")
        service.add_user_message("New question")  # Triggers summarization
        
        prompt = service.get_context_for_prompt()
        
        # Should have system message with summary
        has_summary = any(msg.get("role") == "system" for msg in prompt)
        assert has_summary
