"""conversation history: folders, conversations, messages

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-09

Adds full-text search via generated `tsvector` columns kept in sync by
triggers (BEFORE INSERT/UPDATE), so application code never has to remember
to re-index — see routers/conversations.py for how they're queried.
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

message_role_enum = pg.ENUM("user", "assistant", name="message_role", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    message_role_enum.create(bind, checkfirst=True)

    op.create_table(
        "folders",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_folders_user_id", "folders", ["user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("folder_id", pg.UUID(as_uuid=True), sa.ForeignKey("folders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False, server_default="New chat"),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("share_token", sa.String(43), nullable=True, unique=True),
        sa.Column("shared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("search_vector", pg.TSVECTOR, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_index("ix_conversations_user_last_message", "conversations", ["user_id", "last_message_at"])
    op.create_index(
        "ix_conversations_search_vector", "conversations", ["search_vector"], postgresql_using="gin"
    )

    op.create_table(
        "messages",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id", pg.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("role", message_role_enum, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("search_vector", pg.TSVECTOR, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_search_vector", "messages", ["search_vector"], postgresql_using="gin")

    # ---- Full-text search triggers -----------------------------------------------
    # Titles and message content are indexed with 'english' text search config;
    # switch to 'simple' if you need language-agnostic search instead.
    op.execute(
        """
        CREATE FUNCTION conversations_search_vector_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.title, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER conversations_search_vector_update
        BEFORE INSERT OR UPDATE OF title ON conversations
        FOR EACH ROW EXECUTE FUNCTION conversations_search_vector_trigger();
        """
    )

    op.execute(
        """
        CREATE FUNCTION messages_search_vector_trigger() RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := to_tsvector('english', COALESCE(NEW.content, ''));
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER messages_search_vector_update
        BEFORE INSERT OR UPDATE OF content ON messages
        FOR EACH ROW EXECUTE FUNCTION messages_search_vector_trigger();
        """
    )

    # Keep conversations.last_message_at in sync whenever a message is added,
    # so the sidebar's recency sort never needs to join messages at read time.
    op.execute(
        """
        CREATE FUNCTION conversations_touch_last_message_at() RETURNS trigger AS $$
        BEGIN
            UPDATE conversations SET last_message_at = NEW.created_at WHERE id = NEW.conversation_id;
            RETURN NEW;
        END
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER messages_touch_conversation
        AFTER INSERT ON messages
        FOR EACH ROW EXECUTE FUNCTION conversations_touch_last_message_at();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS messages_touch_conversation ON messages")
    op.execute("DROP FUNCTION IF EXISTS conversations_touch_last_message_at")
    op.execute("DROP TRIGGER IF EXISTS messages_search_vector_update ON messages")
    op.execute("DROP FUNCTION IF EXISTS messages_search_vector_trigger")
    op.execute("DROP TRIGGER IF EXISTS conversations_search_vector_update ON conversations")
    op.execute("DROP FUNCTION IF EXISTS conversations_search_vector_trigger")

    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("folders")
    message_role_enum.drop(op.get_bind(), checkfirst=True)
