"""Database connection, engine configuration, and session management."""

import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL
from src.database.base import Base
# Import models to register them with Base.metadata
import src.database.models  # noqa: F401

logger = logging.getLogger(__name__)


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints for SQLite connections."""
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    except Exception as exc:
        logger.warning("Could not set SQLite foreign_keys PRAGMA: %s", exc)


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Create and return a SQLAlchemy database engine."""
    url = db_url or DATABASE_URL
    is_sqlite = url.startswith("sqlite")
    
    engine_kwargs = {
        "echo": False,
        "future": True,
    }
    
    # Handle check_same_thread for SQLite
    if is_sqlite and "check_same_thread" not in url:
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    return create_engine(url, **engine_kwargs)


def get_session_factory(engine: Optional[Engine] = None) -> sessionmaker[Session]:
    """Create a thread-safe Session factory bound to engine."""
    eng = engine or get_engine()
    return sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db(engine: Optional[Engine] = None) -> None:
    """Initialize database tables according to declared schema."""
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    logger.info("Initialized database tables using engine: %s", eng.url)


def drop_db(engine: Optional[Engine] = None) -> None:
    """Drop all tables in database. Use with caution."""
    eng = engine or get_engine()
    Base.metadata.drop_all(bind=eng)
    logger.warning("Dropped database tables using engine: %s", eng.url)


@contextmanager
def get_db_session(session_factory: Optional[sessionmaker[Session]] = None) -> Generator[Session, None, None]:
    """Context manager yielding a database session with automatic commit/rollback."""
    factory = session_factory or get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

