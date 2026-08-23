"""Add admin system: roles, audit logs, moderation, analytics tables.

Revision ID: 0006
Revises: 0005_billing_tables
Create Date: 2026-08-14 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create admin system tables and add role to users."""

    # Add role column to users table
    op.add_column(
        "users",
        sa.Column("role", sa.String(50), nullable=False, server_default="user"),
    )
    op.add_index(op.f("ix_users_role"), "users", ["role"])

    # Add status column to users (for suspension/banning)
    op.add_column(
        "users",
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
    )
    op.add_index(op.f("ix_users_status"), "users", ["status"])

    # Create user_status enum for clarity
    user_status_enum = postgresql.ENUM(
        "active", "suspended", "banned", name="user_status"
    )
    user_status_enum.create(op.get_bind())

    # Create admin_audit_logs table
    op.create_table(
        "admin_audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["admin_user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_admin_audit_logs_admin_user_id"),
        "admin_audit_logs",
        ["admin_user_id"],
    )
    op.create_index(
        op.f("ix_admin_audit_logs_target_user_id"),
        "admin_audit_logs",
        ["target_user_id"],
    )
    op.create_index(
        op.f("ix_admin_audit_logs_action"), "admin_audit_logs", ["action"]
    )
    op.create_index(
        op.f("ix_admin_audit_logs_created_at"), "admin_audit_logs", ["created_at"]
    )

    # Create moderation_flags table
    op.create_table(
        "moderation_flags",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["message_id"], ["messages.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_moderation_flags_status"), "moderation_flags", ["status"]
    )
    op.create_index(
        op.f("ix_moderation_flags_user_id"), "moderation_flags", ["user_id"]
    )
    op.create_index(
        op.f("ix_moderation_flags_conversation_id"),
        "moderation_flags",
        ["conversation_id"],
    )
    op.create_index(
        op.f("ix_moderation_flags_created_at"), "moderation_flags", ["created_at"]
    )
    op.create_index(
        op.f("ix_moderation_flags_severity"), "moderation_flags", ["severity"]
    )

    # Create model_request_logs table
    op.create_table(
        "model_request_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "estimated_cost",
            sa.Numeric(12, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column("error_code", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_request_logs_model"), "model_request_logs", ["model"]
    )
    op.create_index(
        op.f("ix_model_request_logs_created_at"), "model_request_logs", ["created_at"]
    )
    op.create_index(
        op.f("ix_model_request_logs_status"), "model_request_logs", ["status"]
    )
    op.create_index(
        op.f("ix_model_request_logs_user_id"), "model_request_logs", ["user_id"]
    )

    # Create daily_platform_metrics table
    op.create_table(
        "daily_platform_metrics",
        sa.Column("date", sa.Date, nullable=False),
        sa.Column("dau", sa.Integer, nullable=False, server_default="0"),
        sa.Column("messages", sa.Integer, nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.BigInteger, nullable=False, server_default="0"),
        sa.Column(
            "estimated_cost",
            sa.Numeric(14, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column("new_users", sa.Integer, nullable=False, server_default="0"),
        sa.Column("paid_users", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("date"),
    )
    op.create_index(
        op.f("ix_daily_platform_metrics_date"),
        "daily_platform_metrics",
        ["date"],
    )


def downgrade() -> None:
    """Downgrade admin system tables."""

    # Drop daily_platform_metrics
    op.drop_index(
        op.f("ix_daily_platform_metrics_date"),
        table_name="daily_platform_metrics",
    )
    op.drop_table("daily_platform_metrics")

    # Drop model_request_logs
    op.drop_index(
        op.f("ix_model_request_logs_user_id"),
        table_name="model_request_logs",
    )
    op.drop_index(
        op.f("ix_model_request_logs_status"), table_name="model_request_logs"
    )
    op.drop_index(
        op.f("ix_model_request_logs_created_at"),
        table_name="model_request_logs",
    )
    op.drop_index(
        op.f("ix_model_request_logs_model"), table_name="model_request_logs"
    )
    op.drop_table("model_request_logs")

    # Drop moderation_flags
    op.drop_index(
        op.f("ix_moderation_flags_severity"), table_name="moderation_flags"
    )
    op.drop_index(
        op.f("ix_moderation_flags_created_at"), table_name="moderation_flags"
    )
    op.drop_index(
        op.f("ix_moderation_flags_conversation_id"),
        table_name="moderation_flags",
    )
    op.drop_index(
        op.f("ix_moderation_flags_user_id"), table_name="moderation_flags"
    )
    op.drop_index(op.f("ix_moderation_flags_status"), table_name="moderation_flags")
    op.drop_table("moderation_flags")

    # Drop admin_audit_logs
    op.drop_index(
        op.f("ix_admin_audit_logs_created_at"), table_name="admin_audit_logs"
    )
    op.drop_index(op.f("ix_admin_audit_logs_action"), table_name="admin_audit_logs")
    op.drop_index(
        op.f("ix_admin_audit_logs_target_user_id"), table_name="admin_audit_logs"
    )
    op.drop_index(
        op.f("ix_admin_audit_logs_admin_user_id"), table_name="admin_audit_logs"
    )
    op.drop_table("admin_audit_logs")

    # Drop status column from users
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_column("users", "status")

    # Drop role column from users
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_column("users", "role")

    # Drop user_status enum
    user_status_enum = postgresql.ENUM(
        "active", "suspended", "banned", name="user_status"
    )
    user_status_enum.drop(op.get_bind())
