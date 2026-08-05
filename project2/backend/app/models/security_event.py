"""SecurityEvent model — Phase 14. Logs every blocked/flagged guardrail decision."""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class EventSeverity(str, enum.Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category:  Mapped[str] = mapped_column(String(64),  nullable=False, index=True)
    severity:  Mapped[EventSeverity] = mapped_column(
        Enum(EventSeverity), default=EventSeverity.MEDIUM, nullable=False
    )
    action:    Mapped[str]  = mapped_column(String(32),  nullable=False, default="blocked")
    reason:    Mapped[str]  = mapped_column(Text,        nullable=False, default="")
    input_snippet: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    endpoint:  Mapped[str]  = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
