"""
Database engine and session management.
Supports SQLite (development) and PostgreSQL (production) via DATABASE_URL.
"""
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Base

# Lazy engines (created on first use)
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Create or return the chat DB engine."""
    global _engine
    if _engine is not None:
        return _engine
    settings = get_settings()
    url = settings.database_url
    if not url or url == "sqlite:///":
        path = settings.chat_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    _engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return session factory (creates engine if needed)."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine()
    _session_factory = sessionmaker(engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope for the chat DB."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_chat_db() -> None:
    """Create chat tables if they do not exist (development convenience)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db_session_generator():
    """FastAPI dependency: yield a DB session and commit/rollback on exit."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
