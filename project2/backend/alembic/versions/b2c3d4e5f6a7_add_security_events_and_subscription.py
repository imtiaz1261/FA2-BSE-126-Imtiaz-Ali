"""add security_events table and subscription columns

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-04 12:00:00

Phase 14: security_events table for guardrail audit log.
Phase 15: stripe subscription columns on users.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str      = "b2c3d4e5f6a7"
down_revision      = "a1b2c3d4e5f6"
branch_labels      = None
depends_on         = None


def upgrade() -> None:
    # ── security_events (Phase 14) ────────────────────────────────────────────
    op.create_table(
        "security_events",
        sa.Column("id",            sa.UUID(),                              nullable=False),
        sa.Column("user_id",       sa.UUID(),                              nullable=True),
        sa.Column("category",      sa.String(64),                          nullable=False),
        sa.Column("severity",
                  sa.Enum("low", "medium", "high", "critical",
                          name="eventseverity"),                           nullable=False),
        sa.Column("action",        sa.String(32),   server_default="blocked", nullable=False),
        sa.Column("reason",        sa.Text(),        server_default="",    nullable=False),
        sa.Column("input_snippet", sa.String(300),   server_default="",    nullable=False),
        sa.Column("endpoint",      sa.String(128),   server_default="",    nullable=False),
        sa.Column("created_at",    sa.DateTime(timezone=True),
                  server_default=sa.text("now()"),                        nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_security_events_user_id",    "security_events", ["user_id"])
    op.create_index("ix_security_events_category",   "security_events", ["category"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])

    # ── subscription columns on users (Phase 15) ──────────────────────────────
    op.add_column("users", sa.Column("stripe_customer_id",
                  sa.String(128), nullable=True))
    op.add_column("users", sa.Column("stripe_subscription_id",
                  sa.String(128), nullable=True))
    op.add_column("users", sa.Column("plan_expires_at",
                  sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "plan_expires_at")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_category",   table_name="security_events")
    op.drop_index("ix_security_events_user_id",    table_name="security_events")
    op.drop_table("security_events")
    op.execute("DROP TYPE IF EXISTS eventseverity")
