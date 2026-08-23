"""
Database models for Coding Agent module.

Tracks agent sessions, proposed changes, and execution history.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ============================================================================
# Enums
# ============================================================================


class AgentPhase(str, enum.Enum):
    """Agent execution phase."""

    planning = "planning"
    reading_files = "reading_files"
    proposing_changes = "proposing_changes"
    awaiting_approval = "awaiting_approval"
    executing = "executing"
    testing = "testing"
    self_correcting = "self_correcting"
    complete = "complete"
    failed = "failed"


class ChangeStatus(str, enum.Enum):
    """Status of a proposed code change."""

    staged = "staged"
    approved = "approved"
    rejected = "rejected"
    applied = "applied"
    reverted = "reverted"


# ============================================================================
# Agent Session
# ============================================================================


class AgentSession(Base):
    """Track a single coding agent session."""

    __tablename__ = "agent_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Task and repo context
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    repo_path: Mapped[str] = mapped_column(String(512), nullable=False)  # Local repo path
    git_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    
    # Execution tracking
    phase: Mapped[AgentPhase] = mapped_column(
        Enum(AgentPhase), default=AgentPhase.planning, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="in_progress", nullable=False
    )  # in_progress, completed, failed
    
    # Agent metadata
    total_iterations: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    self_corrections: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_self_corrections: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    
    # Docker container
    container_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    container_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # Summary
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_agent_sessions_status", "status"),
    )


# ============================================================================
# Proposed Code Change
# ============================================================================


class ProposedCodeChange(Base):
    """A proposed file change by the agent."""

    __tablename__ = "proposed_code_changes"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # File info
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    operation: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # create, update, delete
    
    # Content
    original_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # For updates/deletes
    proposed_content: Mapped[str | None] = mapped_column(Text, nullable=True)  # For creates/updates
    diff: Mapped[str] = mapped_column(Text, nullable=False)  # Unified diff format
    
    # Status
    status: Mapped[ChangeStatus] = mapped_column(
        Enum(ChangeStatus), default=ChangeStatus.staged, nullable=False
    )
    
    # Approval
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_edit: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # If user edited the change
    
    # Application
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_proposed_code_changes_status", "status"),
    )


# ============================================================================
# Agent Reasoning Step (for streaming)
# ============================================================================


class AgentReasoningStep(Base):
    """Store agent reasoning steps for streaming and replay."""

    __tablename__ = "agent_reasoning_steps"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Step info
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # thought, action, observation, result
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Tool execution
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_agent_reasoning_steps_iteration", "iteration"),
    )


# ============================================================================
# Test Execution
# ============================================================================


class AgentTestExecution(Base):
    """Track test execution during agent session."""

    __tablename__ = "agent_test_executions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    
    # Test info
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    test_command: Mapped[str] = mapped_column(String(512), nullable=False)
    
    # Results
    exit_code: Mapped[int] = mapped_column(Integer, nullable=False)
    stdout: Mapped[str] = mapped_column(Text, nullable=False)
    stderr: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(default=False, nullable=False)
    
    # Timing
    duration_seconds: Mapped[float] = mapped_column(nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
    )
