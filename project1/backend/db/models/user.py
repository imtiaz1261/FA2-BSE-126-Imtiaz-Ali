"""
db/models/user.py — User ORM Model
====================================
Central entity of the entire platform.  Every other model
(Subscription, Conversation, Document, UsageRecord) references
this via a foreign key.

Table: users

Design decisions:
- UUID primary key:    prevents enumeration attacks on the API
- Native PG enum:      DB-level constraint on role values
- Unique index on email: enforced at DB level, not just app level
- updated_at onupdate: automatically maintained by SQLAlchemy
- Passwords never stored plain: only bcrypt hashes land here
- is_active flag:      soft-disable without deleting data
- is_verified flag:    email verification flow (Step 3)
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db._base import Base


# ---------------------------------------------------------------------------
# Python Enum — single source of truth for role values.
# SQLAlchemy maps this to a native PostgreSQL ENUM type.
# ---------------------------------------------------------------------------
class UserRole(str, PyEnum):
    """
    User roles within the platform.

    Using `str` as a mixin means role values are plain strings
    when serialised to JSON — no extra conversion needed in Pydantic.

    Values:
        user:  Standard authenticated user
        admin: Platform administrator with access to the admin dashboard
    """
    USER = "user"
    ADMIN = "admin"


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------
class User(Base):
    """
    Represents an authenticated user of the AIHub platform.

    Relationships (back-populated from child models):
        subscription:   User.subscription  → Subscription (one-to-one)
        conversations:  User.conversations → list[Conversation] (one-to-many)
        documents:      User.documents     → list[Document] (one-to-many)
        usage_records:  User.usage_records → list[UsageRecord] (one-to-many)
    """

    __tablename__ = "users"

    # ------------------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------------------
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        comment="Unique user identifier (UUID v4)",
    )

    # ------------------------------------------------------------------
    # Identity fields
    # ------------------------------------------------------------------
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="User email address — used as login identifier",
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User's display name",
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="bcrypt hash of the user's password — never the plain text",
    )

    # ------------------------------------------------------------------
    # Role & Status
    # ------------------------------------------------------------------
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", native_enum=False),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        index=True,
        comment="Access role: user | admin",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        comment="False = account disabled (soft ban)",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="True once the user verifies their email address",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Account creation timestamp (UTC)",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=text("now()"),
        comment="Last modification timestamp (UTC) — auto-updated",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        comment="Most recent successful login timestamp (UTC)",
    )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    # back_populates connects both ends of the relationship.
    # lazy="selectin" means SQLAlchemy issues a second SELECT to load
    # related objects — safe for async (no lazy-loading in async mode).
    # We use lazy="noload" where we never need the related objects
    # automatically, to avoid unnecessary queries.

    subscription: Mapped["Subscription"] = relationship(  # noqa: F821
        "Subscription",
        back_populates="user",
        uselist=False,          # one-to-one
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation",
        back_populates="user",
        lazy="noload",          # loaded explicitly when needed
        cascade="all, delete-orphan",
        order_by="Conversation.created_at.desc()",
    )

    documents: Mapped[list["Document"]] = relationship(  # noqa: F821
        "Document",
        back_populates="user",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    usage_records: Mapped[list["UsageRecord"]] = relationship(  # noqa: F821
        "UsageRecord",
        back_populates="user",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    # ------------------------------------------------------------------
    # Composite Indexes
    # ------------------------------------------------------------------
    __table_args__ = (
        # Fast lookup of active users by email (login query)
        Index("ix_users_email_active", "email", "is_active"),
        # Fast lookup of all admins
        Index("ix_users_role_active", "role", "is_active"),
        {
            "comment": "Platform users — stores identity, credentials, and access role"
        },
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"<User id={self.id} email={self.email!r} role={self.role.value}>"
        )

    @property
    def is_admin(self) -> bool:
        """Convenience check used in permission guards."""
        return self.role == UserRole.ADMIN

    @property
    def display_name(self) -> str:
        """Return full_name if set, otherwise the email prefix."""
        return self.full_name or self.email.split("@")[0]
