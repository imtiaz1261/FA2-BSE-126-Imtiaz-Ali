"""Add agent tables for coding agent module.

Revision ID: 0003
Revises: 0002_conversation_history
Create Date: 2024-08-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002_conversation_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create agent tables."""
    
    # Create AgentSession table
    op.create_table(
        "agent_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_description", sa.Text(), nullable=False),
        sa.Column("repo_path", sa.String(512), nullable=False),
        sa.Column("git_branch", sa.String(255), nullable=False, server_default="main"),
        sa.Column(
            "phase",
            sa.Enum(
                "planning",
                "reading_files",
                "proposing_changes",
                "awaiting_approval",
                "executing",
                "testing",
                "self_correcting",
                "complete",
                "failed",
                name="agentphase",
            ),
            nullable=False,
            server_default="planning",
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="in_progress"),
        sa.Column("total_iterations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("self_corrections", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_self_corrections", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("container_id", sa.String(255), nullable=True),
        sa.Column("container_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_agent_sessions_user_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_agent_sessions_conversation_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_agent_sessions_user_id", "agent_sessions", ["user_id"])
    op.create_index("ix_agent_sessions_conversation_id", "agent_sessions", ["conversation_id"])
    op.create_index("ix_agent_sessions_status", "agent_sessions", ["status"])

    # Create ProposedCodeChange table
    op.create_table(
        "proposed_code_changes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("proposed_content", sa.Text(), nullable=True),
        sa.Column("diff", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("staged", "approved", "rejected", "applied", "reverted", name="changestatus"),
            nullable=False,
            server_default="staged",
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("user_edit", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["agent_sessions.id"],
            name="fk_proposed_changes_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_proposed_code_changes_session_id", "proposed_code_changes", ["session_id"])
    op.create_index("ix_proposed_code_changes_status", "proposed_code_changes", ["status"])

    # Create AgentReasoningStep table
    op.create_table(
        "agent_reasoning_steps",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column("tool_input", postgresql.JSON(), nullable=True),
        sa.Column("tool_output", sa.Text(), nullable=True),
        sa.Column("tool_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["agent_sessions.id"],
            name="fk_reasoning_steps_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_agent_reasoning_steps_session_id", "agent_reasoning_steps", ["session_id"])
    op.create_index("ix_agent_reasoning_steps_iteration", "agent_reasoning_steps", ["iteration"])

    # Create AgentTestExecution table
    op.create_table(
        "agent_test_executions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("iteration", sa.Integer(), nullable=False),
        sa.Column("test_command", sa.String(512), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("stdout", sa.Text(), nullable=False),
        sa.Column("stderr", sa.Text(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["agent_sessions.id"],
            name="fk_test_executions_session_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_agent_test_executions_session_id", "agent_test_executions", ["session_id"])


def downgrade() -> None:
    """Drop agent tables."""
    op.drop_table("agent_test_executions")
    op.drop_table("agent_reasoning_steps")
    op.drop_table("proposed_code_changes")
    op.drop_table("agent_sessions")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS changestatus")
    op.execute("DROP TYPE IF EXISTS agentphase")
