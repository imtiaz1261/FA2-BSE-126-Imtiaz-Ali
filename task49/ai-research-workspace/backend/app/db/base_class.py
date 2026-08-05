"""Shared declarative base — every model inherits from this."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
