"""
db/base.py — SQLAlchemy Declarative Base + Model Registry
==========================================================
ALL ORM models must be imported here so that:

  1. Alembic autogenerate can discover every table and produce
     correct migration scripts.

  2. SQLAlchemy's relationship() resolution works at import time —
     forward references like "User" in Subscription.user resolve
     correctly because all models are loaded into the same registry.

  3. Any module that needs Base.metadata (e.g. test fixtures that
     call Base.metadata.create_all()) gets the full picture by
     importing just this file.

Common mistake — models NOT imported here:
  - `alembic revision --autogenerate` silently skips the table
  - Relationships raise `InvalidRequestError` at runtime
  - Tests see empty databases

Rule: every new model file you create must have its import added here.

CIRCULAR IMPORT PREVENTION:
  - Models import Base from this file (db/base.py)
  - This file imports models AFTER the Base class is defined
  - Models must NOT import anything from db/base.py other than Base
  - The Base class itself has no imports from models
"""

from backend.db._base import Base, NAMING_CONVENTION  # noqa: F401


# ---------------------------------------------------------------------------
# Model imports — ORDER MATTERS for foreign key resolution
# ---------------------------------------------------------------------------
# These imports are intentionally AFTER the Base class definition.
# Models import Base from this file, so Base must exist before they load.
# Python handles this correctly because by the time the model files
# are imported, Base is already defined in this module's namespace.

from backend.db.models.user import User  # noqa: F401, E402
from backend.db.models.subscription import Subscription  # noqa: F401, E402
from backend.db.models.conversation import Conversation, Message  # noqa: F401, E402
from backend.db.models.document import Document  # noqa: F401, E402
from backend.db.models.usage import UsageRecord  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Public re-exports
# ---------------------------------------------------------------------------
__all__ = [
    "Base",
    "User",
    "Subscription",
    "Conversation",
    "Message",
    "Document",
    "UsageRecord",
]
