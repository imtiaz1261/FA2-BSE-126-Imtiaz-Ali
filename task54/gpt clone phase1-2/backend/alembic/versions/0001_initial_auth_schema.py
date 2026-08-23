"""initial auth schema

Revision ID: 0001
Revises:
Create Date: 2026-08-08

Hand-written to match app/models.py exactly. After this baseline, prefer
`alembic revision --autogenerate` for subsequent changes and just review the
diff before committing it.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

oauth_provider_enum = pg.ENUM("google", "github", "microsoft", name="oauth_provider", create_type=False)
auth_token_type_enum = pg.ENUM("email_verify", "password_reset", name="auth_token_type", create_type=False)
theme_preference_enum = pg.ENUM("light", "dark", "system", name="theme_preference", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    oauth_provider_enum.create(bind, checkfirst=True)
    auth_token_type_enum.create(bind, checkfirst=True)
    theme_preference_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("oauth_provider", oauth_provider_enum, nullable=True),
        sa.Column("oauth_subject", sa.String(255), nullable=True),
        sa.Column("use_case", sa.String(255), nullable=True),
        sa.Column(
            "theme_preference", theme_preference_enum, nullable=False, server_default="system"
        ),
        sa.Column("data_usage_opt_in", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("onboarding_completed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    op.create_table(
        "auth_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_type", auth_token_type_enum, nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_auth_tokens_token_hash", "auth_tokens", ["token_hash"])

    op.create_table(
        "login_attempts",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("success", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_login_attempts_email", "login_attempts", ["email"])


def downgrade() -> None:
    op.drop_table("login_attempts")
    op.drop_table("auth_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    theme_preference_enum.drop(op.get_bind(), checkfirst=True)
    auth_token_type_enum.drop(op.get_bind(), checkfirst=True)
    oauth_provider_enum.drop(op.get_bind(), checkfirst=True)
