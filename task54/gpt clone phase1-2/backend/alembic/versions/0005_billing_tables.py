"""Add billing & subscription tables.

Revision ID: 0005
Revises: 0004_memory_tables
Create Date: 2024-08-14 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create billing tables."""

    # Create subscription_plan enum
    subscription_plan_enum = postgresql.ENUM(
        "free", "plus", "pro", name="subscription_plan"
    )
    subscription_plan_enum.create(op.get_bind())

    # Create subscription_status enum
    subscription_status_enum = postgresql.ENUM(
        "active",
        "trialing",
        "past_due",
        "canceled",
        "unpaid",
        "incomplete",
        "incomplete_expired",
        name="subscription_status",
    )
    subscription_status_enum.create(op.get_bind())

    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
        sa.Column(
            "plan",
            sa.Enum("free", "plus", "pro", name="subscription_plan"),
            default="free",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "trialing",
                "past_due",
                "canceled",
                "unpaid",
                "incomplete",
                "incomplete_expired",
                name="subscription_status",
            ),
            default="active",
            nullable=False,
        ),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), default=False, nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_subscriptions_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.UniqueConstraint("user_id", name="uq_subscriptions_user_id"),
    )

    # Create indexes on subscriptions
    op.create_index(
        "ix_subscriptions_user_id",
        "subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_stripe_customer_id",
        "subscriptions",
        ["stripe_customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_plan",
        "subscriptions",
        ["plan"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_status",
        "subscriptions",
        ["status"],
        unique=False,
    )

    # Create stripe_webhook_events table
    op.create_table(
        "stripe_webhook_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("stripe_event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("processed", sa.Boolean(), default=False, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_stripe_webhook_events"),
        sa.UniqueConstraint(
            "stripe_event_id", name="uq_stripe_webhook_events_stripe_event_id"
        ),
    )

    # Create indexes on stripe_webhook_events
    op.create_index(
        "ix_stripe_webhook_events_stripe_event_id",
        "stripe_webhook_events",
        ["stripe_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_stripe_webhook_events_event_type",
        "stripe_webhook_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_stripe_webhook_events_processed",
        "stripe_webhook_events",
        ["processed"],
        unique=False,
    )


def downgrade() -> None:
    """Drop billing tables."""

    # Drop indexes
    op.drop_index("ix_stripe_webhook_events_processed", table_name="stripe_webhook_events")
    op.drop_index("ix_stripe_webhook_events_event_type", table_name="stripe_webhook_events")
    op.drop_index("ix_stripe_webhook_events_stripe_event_id", table_name="stripe_webhook_events")

    # Drop stripe_webhook_events table
    op.drop_table("stripe_webhook_events")

    # Drop subscriptions indexes
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_plan", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")

    # Drop subscriptions table
    op.drop_table("subscriptions")

    # Drop enums
    subscription_status_enum = postgresql.ENUM(name="subscription_status")
    subscription_status_enum.drop(op.get_bind())

    subscription_plan_enum = postgresql.ENUM(name="subscription_plan")
    subscription_plan_enum.drop(op.get_bind())
