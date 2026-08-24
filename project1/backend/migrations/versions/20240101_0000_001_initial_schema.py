"""Initial schema — all tables, enums, indexes

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00 UTC

Creates:
    Extensions:  uuid-ossp, pg_trgm, vector
    Enum types:  userrole, subscriptionplan, subscriptionstatus,
                 messagerole, aifeature, requeststatus,
                 documenttype, documentstatus
    Tables:      users, subscriptions, conversations, messages,
                 documents, usage_records
    Indexes:     all composite and single-column indexes
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_enum(name: str, *values: str) -> postgresql.ENUM:
    """Create a PostgreSQL ENUM type and return the type object."""
    enum_type = postgresql.ENUM(*values, name=name, create_type=False)
    op.execute(
        f"CREATE TYPE {name} AS ENUM ({', '.join(repr(v) for v in values)})"
    )
    return enum_type


def _drop_enum(name: str) -> None:
    """Drop a PostgreSQL ENUM type."""
    op.execute(f"DROP TYPE IF EXISTS {name}")


# ---------------------------------------------------------------------------
# Upgrade — apply the schema
# ---------------------------------------------------------------------------

def upgrade() -> None:

    # ------------------------------------------------------------------
    # 1. PostgreSQL extensions
    # ------------------------------------------------------------------
    # uuid-ossp:  gen_random_uuid() server default for UUID PKs
    # pg_trgm:    trigram GIN index for conversation title search
    # vector:     pgvector extension for embeddings (production)
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # 2. ENUM types  (must exist before tables that use them)
    # ------------------------------------------------------------------

    # users.role
    _create_enum("userrole", "user", "admin")

    # subscriptions.plan
    _create_enum("subscriptionplan", "free", "pro", "enterprise")

    # subscriptions.status
    _create_enum(
        "subscriptionstatus",
        "active", "trialing", "past_due", "cancelled", "expired",
    )

    # messages.role
    _create_enum("messagerole", "system", "user", "assistant", "tool")

    # usage_records.feature
    _create_enum("aifeature", "chat", "rag", "agent", "tool_call")

    # usage_records.status
    _create_enum(
        "requeststatus",
        "success", "error", "blocked", "guardrail_blocked",
    )

    # documents.type
    _create_enum("documenttype", "pdf", "docx", "txt", "md", "csv")

    # documents.status
    _create_enum(
        "documentstatus",
        "pending", "processing", "ready", "failed",
    )

    # ------------------------------------------------------------------
    # 3. users table
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
            comment="Unique user identifier (UUID v4)",
        ),
        sa.Column("email", sa.String(255), nullable=False,
                  comment="User email address — used as login identifier"),
        sa.Column("full_name", sa.String(255), nullable=False,
                  comment="User's display name"),
        sa.Column("hashed_password", sa.String(255), nullable=False,
                  comment="bcrypt hash of the user's password"),
        sa.Column(
            "role",
            postgresql.ENUM(name="userrole", create_type=False),
            server_default="user",
            nullable=False,
            comment="Access role: user | admin",
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"),
                  nullable=False, comment="False = account disabled"),
        sa.Column("is_verified", sa.Boolean(), server_default=sa.text("false"),
                  nullable=False, comment="Email verification status"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        comment="Platform users — identity, credentials, and access role",
    )
    # Single-column indexes
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    # Composite indexes
    op.create_index("ix_users_email_active", "users", ["email", "is_active"])
    op.create_index("ix_users_role_active", "users", ["role", "is_active"])

    # ------------------------------------------------------------------
    # 4. subscriptions table
    # ------------------------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False,
                  comment="Owner of this subscription"),
        sa.Column(
            "plan",
            postgresql.ENUM(name="subscriptionplan", create_type=False),
            server_default="free", nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="subscriptionstatus", create_type=False),
            server_default="active", nullable=False,
        ),
        sa.Column("current_period_start", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True),
                  server_default=sa.text("now() + interval '30 days'"),
                  nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_subscriptions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
        sa.UniqueConstraint("stripe_customer_id",
                            name="uq_subscriptions_stripe_customer_id"),
        sa.UniqueConstraint("stripe_subscription_id",
                            name="uq_subscriptions_stripe_subscription_id"),
        comment="User subscription plans and billing state",
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_plan_status", "subscriptions",
                    ["plan", "status"])
    op.create_index("ix_subscriptions_period_end", "subscriptions",
                    ["current_period_end"])

    # ------------------------------------------------------------------
    # 5. conversations table
    # ------------------------------------------------------------------
    op.create_table(
        "conversations",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500),
                  server_default=sa.text("'New Conversation'"), nullable=False),
        sa.Column("feature", sa.String(50),
                  server_default=sa.text("'chat'"), nullable=False),
        sa.Column("message_count", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_conversations_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_conversations"),
        comment="Chat sessions — metadata container for messages",
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_user_updated", "conversations",
                    ["user_id", "updated_at"])
    # GIN trigram index for fast title search (requires pg_trgm)
    op.create_index(
        "ix_conversations_title_trgm",
        "conversations",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )

    # ------------------------------------------------------------------
    # 6. messages table
    # ------------------------------------------------------------------
    op.create_table(
        "messages",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM(name="messagerole", create_type=False),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6),
                  server_default=sa.text("0.000000"), nullable=False),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("is_streaming", sa.Boolean(),
                  server_default=sa.text("false"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name="fk_messages_conversation_id_conversations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_messages"),
        comment="Individual chat turns — user and assistant messages",
    )
    op.create_index("ix_messages_conversation_id", "messages",
                    ["conversation_id"])
    op.create_index("ix_messages_conversation_created", "messages",
                    ["conversation_id", "created_at"])
    op.create_index("ix_messages_conversation_role", "messages",
                    ["conversation_id", "role"])

    # ------------------------------------------------------------------
    # 7. documents table
    # ------------------------------------------------------------------
    op.create_table(
        "documents",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
            comment="Unique document ID — also used as vector store namespace",
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False,
                  server_default=sa.text("'application/octet-stream'")),
        sa.Column(
            "document_type",
            postgresql.ENUM(name="documenttype", create_type=False),
            nullable=False,
        ),
        sa.Column("file_hash", sa.String(64), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="documentstatus", create_type=False),
            server_default="pending", nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("page_count", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("collection_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_documents_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
        comment="Uploaded documents and their RAG processing state",
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_user_status", "documents",
                    ["user_id", "status"])
    op.create_index("ix_documents_user_hash", "documents",
                    ["user_id", "file_hash"])
    op.create_index("ix_documents_status_created", "documents",
                    ["status", "created_at"])

    # ------------------------------------------------------------------
    # 8. usage_records table
    # ------------------------------------------------------------------
    op.create_table(
        "usage_records",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"), nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True),
                  nullable=True),
        sa.Column(
            "feature",
            postgresql.ENUM(name="aifeature", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="requeststatus", create_type=False),
            server_default="success", nullable=False,
        ),
        sa.Column("prompt_tokens", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(precision=10, scale=6),
                  server_default=sa.text("0.000000"), nullable=False),
        sa.Column("model", sa.String(100),
                  server_default=sa.text("''"), nullable=False),
        sa.Column("latency_ms", sa.Integer(),
                  server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_usage_records_user_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"],
            name="fk_usage_records_conversation_id_conversations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_usage_records"),
        comment="Per-request AI usage log for enforcement and billing analytics",
    )
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"])
    op.create_index("ix_usage_records_conversation_id", "usage_records",
                    ["conversation_id"])
    op.create_index("ix_usage_records_feature", "usage_records", ["feature"])
    op.create_index("ix_usage_records_status", "usage_records", ["status"])
    op.create_index("ix_usage_records_created_at", "usage_records",
                    ["created_at"])
    op.create_index("ix_usage_user_created", "usage_records",
                    ["user_id", "created_at"])
    op.create_index("ix_usage_user_feature_created", "usage_records",
                    ["user_id", "feature", "created_at"])
    op.create_index("ix_usage_feature_status_created", "usage_records",
                    ["feature", "status", "created_at"])


# ---------------------------------------------------------------------------
# Downgrade — remove the schema (reverse order)
# ---------------------------------------------------------------------------

def downgrade() -> None:

    # Drop tables in reverse dependency order
    # (child tables before parent tables to avoid FK constraint errors)
    op.drop_table("usage_records")
    op.drop_table("messages")
    op.drop_table("documents")
    op.drop_table("conversations")
    op.drop_table("subscriptions")
    op.drop_table("users")

    # Drop ENUM types after tables (enums can't be dropped while in use)
    _drop_enum("documentstatus")
    _drop_enum("documenttype")
    _drop_enum("requeststatus")
    _drop_enum("aifeature")
    _drop_enum("messagerole")
    _drop_enum("subscriptionstatus")
    _drop_enum("subscriptionplan")
    _drop_enum("userrole")

    # Note: We do NOT drop extensions in downgrade.
    # Dropping uuid-ossp or pg_trgm could break other databases
    # sharing this PostgreSQL instance.
