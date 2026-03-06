"""
Repository layer for chat sessions and messages.
Single place for all chat DB access.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import Message, QueryLog, Session as SessionModel


class SessionRepository:
    """Repository for chat sessions."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_or_create(self, session_id: str | None) -> str:
        """Return existing session id or create a new one. Always returns a valid id."""
        if session_id:
            stmt = select(SessionModel).where(SessionModel.id == session_id)
            existing = self._db.execute(stmt).scalars().one_or_none()
            if existing:
                return existing.id
        new_id = str(uuid4())
        session = SessionModel(id=new_id, last_message="")
        self._db.add(session)
        self._db.flush()
        return new_id

    def update_last_message(self, session_id: str, last_message: str) -> None:
        """Update the last_message preview (truncated to 500 chars)."""
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        row = self._db.execute(stmt).scalars().one_or_none()
        if row:
            row.last_message = (last_message or "")[:500]
            self._db.add(row)

    def list_sessions(self) -> list[dict]:
        """Return list of sessions, newest first: [{ id, last_message, created_at }, ...]."""
        stmt = select(SessionModel).order_by(desc(SessionModel.created_at))
        rows = self._db.execute(stmt).scalars().all()
        return [
            {
                "id": r.id,
                "last_message": (r.last_message or "New conversation")[:500],
                "created_at": r.created_at.isoformat() + "Z" if r.created_at else "",
            }
            for r in rows
        ]

    def exists(self, session_id: str) -> bool:
        """Return True if the session exists."""
        stmt = select(SessionModel.id).where(SessionModel.id == session_id)
        return self._db.execute(stmt).scalars().one_or_none() is not None


class MessageRepository:
    """Repository for chat messages."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add(
        self,
        session_id: str,
        role: str,
        content: str,
        *,
        chart_image_base64: str | None = None,
    ) -> None:
        """Append a message to a session. chart_image_base64 is stored for assistant messages with charts."""
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            chart_image_base64=chart_image_base64,
        )
        self._db.add(msg)
        self._db.flush()

    def get_messages(self, session_id: str) -> list[dict]:
        """Return messages for a session: [{ role, content, chart_image_base64? }, ...]."""
        stmt = select(Message).where(Message.session_id == session_id).order_by(Message.id)
        rows = self._db.execute(stmt).scalars().all()
        return [
            {
                "role": r.role,
                "content": r.content,
                "chart_image_base64": getattr(r, "chart_image_base64", None),
            }
            for r in rows
        ]


class QueryLogRepository:
    """Repository for per-request data retriever logs."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def add(
        self,
        *,
        session_id: str | None,
        user_query: str,
        sql_query: str | None,
        response_text: str,
        latency_ms: int | None,
    ) -> None:
        """Insert a new log row focused on SQL + response."""
        log = QueryLog(
            session_id=session_id,
            user_query=(user_query or "")[:10_000],
            sql_query=sql_query if sql_query else None,
            response_text=(response_text or "")[:10_000],
            latency_ms=int(latency_ms) if latency_ms is not None else None,
        )
        self._db.add(log)
        self._db.flush()

    def list_recent(self, limit: int = 50) -> list[dict]:
        """Return most recent logs (newest first)."""
        stmt = select(QueryLog).order_by(desc(QueryLog.created_at)).limit(max(1, limit))
        rows = self._db.execute(stmt).scalars().all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() + "Z" if r.created_at else "",
                "session_id": r.session_id,
                "user_query": r.user_query,
                "sql_query": r.sql_query,
                "response_text": r.response_text,
                "latency_ms": r.latency_ms,
            }
            for r in rows
        ]
