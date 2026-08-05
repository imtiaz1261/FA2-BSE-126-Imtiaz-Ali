"""
Import every model here so `Base.metadata` is complete for Alembic
autogenerate and for any code that does `from app.models import *`.
"""

from app.db.base_class import Base  # noqa: F401
from app.models.user import User, PlanTier  # noqa: F401
from app.models.conversation import Conversation  # noqa: F401
from app.models.message import Message, MessageRole  # noqa: F401
from app.models.document import Document, DocumentStatus  # noqa: F401
from app.models.usage import UsageRecord  # noqa: F401
from app.models.chunk import DocumentChunk  # noqa: F401
from app.models.security_event import SecurityEvent, EventSeverity  # noqa: F401
