"""Database base declarative class and helpers."""

import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase


def generate_uuid() -> str:
    """Generate a 36-character UUIDv4 string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Return current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy declarative models."""
    pass

