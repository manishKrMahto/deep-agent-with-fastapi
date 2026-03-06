"""
FastAPI dependencies: DB session and repositories.
"""
from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_session_factory
from app.db.repository import MessageRepository, QueryLogRepository, SessionRepository


def get_db() -> Generator[Session, None, None]:
    """Yield a DB session for the request; commit on success, rollback on error."""
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


def get_session_repo(db: Session = Depends(get_db)) -> SessionRepository:
    return SessionRepository(db)


def get_message_repo(db: Session = Depends(get_db)) -> MessageRepository:
    return MessageRepository(db)


def get_query_log_repo(db: Session = Depends(get_db)) -> QueryLogRepository:
    return QueryLogRepository(db)
