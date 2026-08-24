"""
Comprehensive tests for Module 13: Project Memory & VS Code Integration

Tests cover:
- Memory system (extraction, retrieval, storage)
- Extension interface (messaging, WebSocket)
- Dashboard backend (metrics, state)
- Agent context integration (orchestrator adapter, prompt enhancement)
"""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List

# Memory tests
from code_alpha.memory import (
    ProjectMemory, MemoryEntry, MemoryCategory,
    MemoryExtractor, ConventionExtractor,
    MemoryRetriever, SemanticMatcher,
    MemoryAdapter, MemoryManager
)

# Extension tests
from code_alpha.extension import (
    ExtensionMessage, MessageType, AgentStatus, TaskPhase,
    ControlMessage, ControlCommand,
    FileEdit, DiffInfo
)

# Dashboard tests
from code_alpha.dashboard import (
    DashboardState, TaskMetrics, MemoryStats,
    DashboardService, DashboardConfig
)

# Integration tests
from code_alpha.integration import (
    ContextManager, TaskContext,
    OrchestratorAdapter,
    PromptEnhancer
)


# ==============================================================================
# Memory System Tests
# ==============================================================================

class TestMemoryCore:
    """Test core memory functionality."""
    
    def test_memory_entry_creation(self):
        """Test creating memory entries."""
        entry = MemoryEntry(
            id="test_1",
            category=MemoryCategory.NAMING,
            title="Test Entry",
            description="A test convention",
            examples=["example_one", "example_two"],
        )
        
        assert entry.title == "Test Entry"
        assert entry.category == MemoryCategory.NAMING
        assert len(entry.examples) == 2
    
    def test_project_memory_add_entry(self):
        """Test adding entries to project memory."""
        memory = ProjectMemory(repo_root="/test/repo")
        
        entry = MemoryEntry(
            id="test_1",
            category=MemoryCategory.NAMING,
            title="Snake Case Functions",
            description="Functions use snake_case",
        )
        
        memory.add_entry(entry)
        
        assert "Snake Case Functions" in memory.learned_conventions
        assert memory.get_entry("test_1") is not None
    
    def test_memory_categorization(self):
        """Test getting entries by category."""
        memory = ProjectMemory(repo_root="/test/repo")
        
        for i in range(3):
            entry = MemoryEntry(
                id=f"naming_{i}",
                category=MemoryCategory.NAMING,
                title=f"Naming Convention {i}",
                description="Test",
            )
            memory.add_entry(entry)
        
        naming_entries = memory.get_by_category(MemoryCategory.NAMING)
        assert len(naming_entries) == 3
    
    def test_memory_merge_increases_confidence(self):
        """Test that merging increases confidence."""
        memory = ProjectMemory(repo_root="/test/repo")
        
        entry1 = MemoryEntry(
            id="test_1",
            category=MemoryCategory.NAMING,
            title="Snake Case",
            description="Functions use snake_case",
            confidence=0.7,
        )
        memory.add_entry(entry1)
        
        entry2 = MemoryEntry(
            id="test_2",
            category=MemoryCategory.NAMING,
            title="Snake Case",
            description="Functions use snake_case",
            confidence=0.8,
        )
        memory.merge_entry(entry2)
        
        # Should have same entry with increased confidence
        merged = list(memory.entries.values())[0]
        assert merged.confidence > 0.7


class TestConventionExtraction:
    """Test convention extraction."""
    
    def test_extract_naming_conventions(self, tmp_path):
        """Test extracting naming conventions."""
        # Create test Python file
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def snake_case_function():
    pass

class PascalCaseClass:
    pass

CONSTANT_VALUE = 42
        """)
        
        extractor = ConventionExtractor(str(tmp_path))
        patterns = extractor.extract_naming_conventions()
        
        assert len(patterns) > 0
        assert any(p.title.startswith("Function naming") for p in patterns)


class TestMemoryRetrieval:
    """Test memory retrieval and semantic matching."""
    
    def test_semantic_similarity(self):
        """Test string similarity matching."""
        matcher = SemanticMatcher()
        
        # Exact match
        sim = matcher.similarity("naming conventions", "naming conventions")
        assert sim > 0.9
        
        # Partial match with substring
        sim = matcher.similarity("naming conventions", "naming patterns conventions")
        assert sim > 0.5
        
        # No match
        sim = matcher.similarity("database patterns", "API design")
        assert sim < 0.5
    
    def test_memory_retrieval(self):
        """Test retrieving relevant memories."""
        memory = ProjectMemory(repo_root="/test/repo")
        
        # Add some entries
        for i in range(5):
            entry = MemoryEntry(
                id=f"entry_{i}",
                category=MemoryCategory.NAMING if i < 2 else MemoryCategory.LIBRARIES,
                title=f"Convention {i}",
                description=f"Description for convention {i}",
                tags=["naming"] if i < 2 else ["libraries"],
            )
            memory.add_entry(entry)
        
        retriever = MemoryRetriever(memory)
        context = retriever.retrieve_for_task(
            "What naming conventions should I use?",
            top_k=3
        )
        
        assert len(context.relevant_entries) > 0


class TestMemoryStorage:
    """Test memory persistence."""
    
    def test_save_and_load_memory(self, tmp_path):
        """Test saving and loading memory."""
        repo_root = str(tmp_path)
        
        # Create and save memory
        memory1 = ProjectMemory(repo_root=repo_root)
        entry = MemoryEntry(
            id="test_1",
            category=MemoryCategory.NAMING,
            title="Test Convention",
            description="A test",
            human_verified=True,
        )
        memory1.add_entry(entry)
        
        adapter = MemoryAdapter(repo_root)
        adapter.save(memory1)
        
        # Load and verify
        memory2 = adapter.load()
        assert len(memory2.entries) == 1
        assert memory2.get_entry("test_1") is not None


# ==============================================================================
# Extension Interface Tests
# ==============================================================================

class TestExtensionMessages:
    """Test extension message creation and serialization."""
    
    def test_status_update_message(self):
        """Test creating status update message."""
        msg = ExtensionMessage.status_update(
            task_id="task_1",
            status=AgentStatus.GENERATING,
            phase=TaskPhase.IMPLEMENT,
            progress=50,
            current_file="test.py",
        )
        
        assert msg.type == MessageType.STATUS_UPDATE
        data = msg.to_dict()
        assert data['data']['task_id'] == "task_1"
        assert data['data']['progress'] == 50
    
    def test_file_edit_message(self):
        """Test file edit message."""
        edit = FileEdit(
            file_path="test.py",
            operation="modify",
            old_content="old",
            new_content="new",
        )
        
        msg = ExtensionMessage.file_edit("task_1", edit)
        
        assert msg.type == MessageType.FILE_EDIT
        assert "edit" in msg.data
    
    def test_diff_preview_message(self):
        """Test diff preview message."""
        diff = DiffInfo(
            file_path="test.py",
            old_content="old content",
            new_content="new content",
        )
        
        msg = ExtensionMessage.diff_preview("task_1", [diff])
        
        assert msg.type == MessageType.DIFF_PREVIEW
        assert len(msg.data['diffs']) == 1
    
    def test_control_message_parsing(self):
        """Test parsing control messages."""
        data = {
            "command": "pause",
            "task_id": "task_1",
            "reason": "User requested pause",
        }
        
        msg = ControlMessage.from_dict(data)
        
        assert msg.command == ControlCommand.PAUSE
        assert msg.task_id == "task_1"


# ==============================================================================
# Dashboard Tests
# ==============================================================================

class TestDashboardMetrics:
    """Test dashboard metrics collection."""
    
    def test_task_metrics_creation(self):
        """Test creating task metrics."""
        metrics = TaskMetrics(
            task_id="task_1",
            status="completed",
            phase="implement",
            progress=100,
            duration_seconds=300,
            files_modified=5,
            lines_added=150,
            lines_removed=30,
            tests_run=10,
            tests_passed=9,
            tests_failed=1,
            errors_encountered=2,
            errors_fixed=2,
        )
        
        assert metrics.success_rate() == 90.0
        assert metrics.fix_rate() == 100.0
    
    def test_dashboard_state_management(self):
        """Test dashboard state management."""
        state = DashboardState()
        
        state.set_agent_status("running")
        assert state.agent_status == "running"
        
        metrics = TaskMetrics(
            task_id="task_1",
            status="completed",
            phase="test",
            progress=100,
            duration_seconds=60,
            files_modified=1,
            lines_added=10,
            lines_removed=5,
            tests_run=5,
            tests_passed=5,
            tests_failed=0,
            errors_encountered=0,
            errors_fixed=0,
        )
        
        state.add_task_metrics(metrics)
        assert state.tasks_completed == 1
        assert state.total_tests_passed == 5


class TestDashboardService:
    """Test dashboard service."""
    
    def test_dashboard_service_initialization(self):
        """Test service initialization."""
        service = DashboardService()
        
        assert service.state.agent_status == "idle"
        assert service.state.tasks_completed == 0
    
    def test_update_task_progress(self):
        """Test updating task progress."""
        service = DashboardService()
        
        service.set_current_task("task_1", progress=0)
        assert service.state.current_task == "task_1"
        assert service.state.current_task_progress == 0
        
        service.update_task_progress(50)
        assert service.state.current_task_progress == 50
        
        service.update_task_progress(100)
        assert service.state.current_task_progress == 100
    
    def test_metrics_collection(self):
        """Test metrics collection."""
        service = DashboardService()
        
        service.add_metric("test_success_rate", 95.0, "%")
        service.add_metric("code_coverage", 87.5, "%")
        
        state = service.get_state()
        assert len(state.metrics) >= 2


# ==============================================================================
# Integration Tests
# ==============================================================================

class TestTaskContext:
    """Test task context management."""
    
    def test_task_context_creation(self):
        """Test creating task context."""
        context = TaskContext(
            task_id="task_1",
            task_description="Build API endpoint",
            repo_root="/test/repo",
        )
        
        assert context.task_id == "task_1"
        assert context.progress == 0
        assert context.phase == "planning"
    
    def test_task_context_tracking(self):
        """Test tracking task progress."""
        context = TaskContext(
            task_id="task_1",
            task_description="Build API",
            repo_root="/test/repo",
        )
        
        context.update_phase("implementing")
        assert context.phase == "implementing"
        
        context.update_progress(50)
        assert context.progress == 50
        
        context.record_file_edit("app.py", 10, 5)
        assert context.files_modified == 1
        assert context.lines_added == 10
        assert context.lines_removed == 5
        
        context.record_test_result(True)
        assert context.tests_run == 1
        assert context.tests_passed == 1


class TestPromptEnhancer:
    """Test prompt enhancement."""
    
    def test_enhance_prompt_with_conventions(self):
        """Test enhancing prompts with conventions."""
        memory = ProjectMemory(repo_root="/test/repo")
        
        entry = MemoryEntry(
            id="test_1",
            category=MemoryCategory.CODE_STYLE,
            title="Use snake_case",
            description="All functions should use snake_case naming",
            examples=["def my_function():"],
            human_verified=True,
        )
        memory.add_entry(entry)
        
        enhancer = PromptEnhancer(memory)
        
        base_prompt = "Write a function to process data"
        enhanced = enhancer.enhance_prompt(
            base_prompt,
            include_verified_only=True,
        )
        
        assert len(enhanced) > len(base_prompt)
        assert "snake_case" in enhanced.lower() or "function" in enhanced.lower()
    
    def test_phase_specific_enhancement(self):
        """Test phase-specific prompt enhancement."""
        memory = ProjectMemory(repo_root="/test/repo")
        
        # Add phase-specific entries
        for phase, category in [
            ("planning", MemoryCategory.ARCHITECTURE),
            ("implementing", MemoryCategory.CODE_STYLE),
            ("testing", MemoryCategory.TESTING),
        ]:
            entry = MemoryEntry(
                id=f"test_{phase}",
                category=category,
                title=f"{phase} convention",
                description=f"Convention for {phase}",
            )
            memory.add_entry(entry)
        
        enhancer = PromptEnhancer(memory)
        
        base = "Base prompt"
        
        for phase in ["planning", "implementing", "testing"]:
            enhanced = enhancer.enhance_for_phase(base, phase)
            assert len(enhanced) >= len(base)


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def tmp_repo(tmp_path):
    """Create a temporary repository."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    (repo / ".codealpha").mkdir()
    return repo


@pytest.fixture
def memory_manager(tmp_repo):
    """Create a memory manager with temp repo."""
    from code_alpha.memory import MemoryManager
    return MemoryManager(str(tmp_repo))


@pytest.fixture
def dashboard_service():
    """Create a dashboard service."""
    from code_alpha.dashboard import DashboardService
    return DashboardService()


@pytest.fixture
def context_manager(tmp_repo, memory_manager):
    """Create a context manager."""
    return ContextManager(str(tmp_repo), memory_manager=memory_manager)


# ==============================================================================
# Integration Test Suite
# ==============================================================================

class TestFullIntegration:
    """End-to-end integration tests."""
    
    def test_memory_extraction_and_retrieval(self, tmp_repo):
        """Test complete memory workflow."""
        # Create memory manager
        from code_alpha.memory import MemoryManager, MemoryExtractor
        
        manager = MemoryManager(str(tmp_repo))
        memory = manager.get_memory()
        
        # Add entries
        for i in range(3):
            from code_alpha.memory import MemoryEntry
            entry = MemoryEntry(
                id=f"entry_{i}",
                category=MemoryCategory.NAMING,
                title=f"Convention {i}",
                description="Test convention",
            )
            memory.add_entry(entry)
        
        # Save
        manager.save()
        
        # Reload
        manager.refresh()
        memory2 = manager.get_memory()
        
        assert len(memory2.entries) == 3
        
        # Retrieve
        retriever = MemoryRetriever(memory2)
        context = retriever.retrieve_for_task("naming conventions")
        
        assert len(context.relevant_entries) > 0
    
    def test_context_tracking_through_lifecycle(self, context_manager):
        """Test tracking context through task lifecycle."""
        # Create context
        context = context_manager.create_task_context(
            task_id="task_1",
            task_description="Implement feature",
        )
        
        assert context.task_id == "task_1"
        
        # Update through phases
        context.update_phase("implementing")
        context.update_progress(50)
        context.record_file_edit("feature.py", 20, 5)
        
        # Verify tracking
        assert context.files_modified == 1
        assert context.lines_added == 20
        
        # Get updated context
        retrieved = context_manager.get_task_context("task_1")
        assert retrieved is not None
        assert retrieved.phase == "implementing"
