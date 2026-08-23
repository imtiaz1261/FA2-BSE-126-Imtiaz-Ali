"""
Database models.

Tables:
- users             account + profile + onboarding fields
- refresh_tokens     "sessions" table Ã¢â‚¬â€ one row per issued refresh token, hashed
- auth_tokens        single-use tokens for email verification + password reset
- login_attempts     audit log of login attempts (for the 5/min rate limit + review)
- folders            user-defined groupings for related conversations
- conversations      one row per chat thread; carries pin/archive/share state
- messages           individual turns within a conversation
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OAuthProvider(str, enum.Enum):
    google = "google"
    github = "github"
    microsoft = "microsoft"


class AuthTokenType(str, enum.Enum):
    email_verify = "email_verify"
    password_reset = "password_reset"


class ThemePreference(str, enum.Enum):
    light = "light"
    dark = "dark"
    system = "system"


class UserRole(str, enum.Enum):
    """User role for authorization."""
    user = "user"
    admin = "admin"


class UserStatus(str, enum.Enum):
    """User account status (separate from is_active)."""
    active = "active"
    suspended = "suspended"
    banned = "banned"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    name: Mapped[str | None] = mapped_column(
        String(120), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.user,
        nullable=False,
        index=True,
    )

    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        default=UserStatus.active,
        nullable=False,
        index=True,
    )

    oauth_provider: Mapped[OAuthProvider | None] = mapped_column(
        Enum(OAuthProvider, name="oauth_provider"),
        nullable=True,
    )

    oauth_subject: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    use_case: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    theme_preference: Mapped[ThemePreference] = mapped_column(
        Enum(ThemePreference, name="theme_preference"),
        default=ThemePreference.system,
        nullable=False,
    )

    data_usage_opt_in: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    auth_tokens: Mapped[list["AuthToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class RefreshToken(Base):
    """
    One row per issued refresh token ("session").
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="refresh_tokens"
    )


class AuthToken(Base):
    """Single-use token for email verification and password reset links."""

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    token_type: Mapped[AuthTokenType] = mapped_column(
        Enum(AuthTokenType, name="auth_token_type")
    )

    used: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="auth_tokens"
    )


class LoginAttempt(Base):
    """Audit log of every login attempt, successful or not."""

    __tablename__ = "login_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class MessageRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"


class Folder(Base):
    """User-defined grouping for related conversations."""

    __tablename__ = "folders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="folder"
    )

    __table_args__ = (
        Index("ix_folders_user_id", "user_id"),
    )


class Conversation(Base):
    """One row per chat thread."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )

    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("folders.id", ondelete="SET NULL"),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New chat",
    )

    pinned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    share_token: Mapped[str | None] = mapped_column(
        String(43),
        unique=True,
        nullable=True,
    )

    shared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship()

    folder: Mapped["Folder | None"] = relationship(
        back_populates="conversations"
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
        Index(
            "ix_conversations_user_last_message",
            "user_id",
            "last_message_at",
        ),
        Index(
            "ix_conversations_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )


class Message(Base):
    """A single turn within a conversation."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )

    role: Mapped[MessageRole] = mapped_column(
        Enum(MessageRole, name="message_role"),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    conversation: Mapped["Conversation"] = relationship(
        back_populates="messages"
    )

    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
        Index(
            "ix_messages_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
    )


class FontSize(str, enum.Enum):
    small = "small"
    medium = "medium"
    large = "large"


class Language(str, enum.Enum):
    en = "en"
    es = "es"
    fr = "fr"
    de = "de"
    ja = "ja"
    zh = "zh"


class UserSettings(Base):
    """User preferences stored as JSON."""

    __tablename__ = "user_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    preferences: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship()


class AvailableModel(Base):
    """Metadata about available LLM models for selection."""

    __tablename__ = "available_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        index=True,
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    tier: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    conversations: Mapped[list["ConversationModel"]] = relationship(
        back_populates="model"
    )

    __table_args__ = (
        Index("ix_available_models_tier", "tier"),
    )


class ConversationModel(Base):
    """Track which model is selected for each conversation."""

    __tablename__ = "conversation_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("available_models.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    model: Mapped["AvailableModel"] = relationship(
        back_populates="conversations"
    )

    __table_args__ = (
        Index(
            "ix_conversation_models_model_id",
            "model_id",
        ),
    )


class MessageUsage(Base):
    """Track daily message usage for rate limiting."""

    __tablename__ = "message_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    message_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_message_usage_user_date",
            "user_id",
            "date",
        ),

    )


class DataExportJob(Base):
    """Track async data export jobs."""

    __tablename__ = "data_export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    download_url: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
    )


# ============================================================================
# RAG (Document Q&A) Models
# ============================================================================


class UploadedDocument(Base):
    """Track uploaded documents for RAG."""

    __tablename__ = "uploaded_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_uploaded_documents_status",
            "status",
        ),
    )


class DocumentChunk(Base):
    """Text chunks extracted from documents."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Python attribute is chunk_metadata.
    # PostgreSQL column remains "metadata".
    chunk_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_document_chunks_page_number",
            "page_number",
        ),
    )


class DocumentEmbedding(Base):
    """Vector embeddings for document chunks."""

    __tablename__ = "document_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    embedding: Mapped[list] = mapped_column(
        Vector(1536),
        nullable=False,
    )

    embedding_model: Mapped[str] = mapped_column(
        String(100),
        default="text-embedding-3-small",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
    )


class UploadJob(Base):
    """Track async upload/ingestion jobs."""

    __tablename__ = "upload_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("uploaded_documents.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_upload_jobs_status",
            "status",
        ),
    )


# ============================================================================
# Vision (Image Understanding) Models
# ============================================================================


class VisionImage(Base):
    """Track uploaded images for vision processing."""

    __tablename__ = "vision_images"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    s3_key: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    signed_url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    signed_url_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Python attribute is image_metadata.
    # PostgreSQL column remains "metadata".
    image_metadata: Mapped[dict] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_vision_images_s3_key",
            "s3_key",
        ),
    )


class VisionRequest(Base):
    """Track vision API requests."""

    __tablename__ = "vision_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    request_type: Mapped[str] = mapped_column(
        String(50),
        default="qa",
        nullable=False,
    )

    prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    response: Mapped[str] = mapped_column(
        Text,
        nullable=True,
    )

    extraction_schema: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    extraction_result: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    image_ids: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        Index(
            "ix_vision_requests_status",
            "status",
        ),
    )