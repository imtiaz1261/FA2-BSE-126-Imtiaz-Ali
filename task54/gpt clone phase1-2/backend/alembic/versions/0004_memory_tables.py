"""Add memory & personalization tables.

Revision ID: 0004
Revises: 0003_agent_tables
Create Date: 2024-08-14 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create memory tables."""

    # Create memory category enum
    memory_category_enum = postgresql.ENUM(
        "personal_info",
        "preferences",
        "goals_and_values",
        "skills_and_expertise",
        "constraints",
        "recurring_tasks",
        "project_context",
        "other",
        name="memory_category",
    )
    memory_category_enum.create(op.get_bind())

    # Create UserMemoryItem table
    op.create_table(
        "user_memory_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fact", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "personal_info",
                "preferences",
                "goals_and_values",
                "skills_and_expertise",
                "constraints",
                "recurring_tasks",
                "project_context",
                "other",
                name="memory_category",
            ),
            default="other",
            nullable=False,
        ),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("relevance_score", sa.Float(), default=1.0, nullable=False),
        sa.Column(
            "source_conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("source_message_id", sa.String(255), nullable=True),
        sa.Column("extraction_context", sa.Text(), nullable=True),
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
        sa.Column("user_edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("last_retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieval_count", sa.Integer(), default=0, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memory_items_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_conversation_id"],
            ["conversations.id"],
            name="fk_memory_items_conversation_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_user_memory_items_user_id", "user_memory_items", ["user_id"])
    op.create_index("ix_user_memory_items_category", "user_memory_items", ["category"])
    op.create_index("ix_user_memory_items_is_active", "user_memory_items", ["is_active"])
    op.create_index(
        "ix_user_memory_items_relevance", "user_memory_items", ["relevance_score"]
    )

    # Create MemoryExtractionLog table
    op.create_table(
        "memory_extraction_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("facts_extracted_count", sa.Integer(), default=0, nullable=False),
        sa.Column("facts_rejected_count", sa.Integer(), default=0, nullable=False),
        sa.Column("rejection_reasons", postgresql.JSON(), default=list, nullable=False),
        sa.Column("llm_prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("llm_completion_tokens", sa.Integer(), nullable=True),
        sa.Column("trigger", sa.String(50), default="post_conversation", nullable=False),
        sa.Column("success", sa.Boolean(), default=True, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_extraction_logs_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_extraction_logs_conversation_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_extraction_logs_user_id", "memory_extraction_logs", ["user_id"])
    op.create_index(
        "ix_extraction_logs_conversation_id",
        "memory_extraction_logs",
        ["conversation_id"],
    )
    op.create_index("ix_extraction_logs_trigger", "memory_extraction_logs", ["trigger"])

    # Create UserMemorySettings table
    op.create_table(
        "user_memory_settings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            unique=True,
            index=True,
            nullable=False,
        ),
        sa.Column("memory_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("auto_extract_enabled", sa.Boolean(), default=True, nullable=False),
        sa.Column("max_memory_items", sa.Integer(), default=100, nullable=False),
        sa.Column("context_injection_count", sa.Integer(), default=5, nullable=False),
        sa.Column("retrieval_threshold", sa.Float(), default=0.6, nullable=False),
        sa.Column("retention_days", sa.Integer(), default=0, nullable=False),
        sa.Column("last_extraction_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_memory_settings_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_memory_settings_user_id", "user_memory_settings", ["user_id"])

    # Create MemoryRetrievalLog table
    op.create_table(
        "memory_retrieval_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "retrieved_memory_ids", postgresql.JSON(), default=list, nullable=False
        ),
        sa.Column("user_message", sa.Text(), nullable=True),
        sa.Column("max_similarity_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_retrieval_logs_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            name="fk_retrieval_logs_conversation_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_retrieval_logs_user_id", "memory_retrieval_logs", ["user_id"])
    op.create_index(
        "ix_retrieval_logs_conversation_id",
        "memory_retrieval_logs",
        ["conversation_id"],
    )


def downgrade() -> None:
    """Drop memory tables."""
    op.drop_table("memory_retrieval_logs")
    op.drop_table("user_memory_settings")
    op.drop_table("memory_extraction_logs")
    op.drop_table("user_memory_items")

    # Drop enum
    op.execute("DROP TYPE IF EXISTS memory_category")
