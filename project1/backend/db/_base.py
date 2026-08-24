"""
db/_base.py — SQLAlchemy Declarative Base (no model imports)
=============================================================
This module defines ONLY the Base class and naming convention.
It has NO imports from any model files — this breaks the circular
import chain.

Models import Base from HERE (db/_base.py).
db/base.py imports both Base and all models for Alembic discovery.

Import path:
    models/*.py         → from backend.db._base import Base
    db/base.py          → from backend.db._base import Base
                          + imports all models
    Alembic env.py      → from backend.db.base import Base  (gets everything)
    Application code    → from backend.db.base import User, etc.
"""

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base. Import from db/_base.py in model files."""
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
