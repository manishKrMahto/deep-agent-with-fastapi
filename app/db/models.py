"""
SQLAlchemy ORM models for chat persistence (sessions, messages).
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


class Session(Base):
    """Chat session (conversation)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_message: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    messages: Mapped[list["Message"]] = relationship("Message", back_populates="session", order_by="Message.id")


class Message(Base):
    """Single message in a chat session."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # 'user' | 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chart_image_base64: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session: Mapped["Session"] = relationship("Session", back_populates="messages")

    __table_args__ = (Index("ix_messages_session_id", "session_id"),)


class QueryLog(Base):
    """
    Per-request log focused on the data retriever.

    Stores:
    - creation time
    - latency (time taken)
    - user query
    - generated SQL (if any)
    - final response text
    """

    __tablename__ = "query_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_query: Mapped[str] = mapped_column(Text, nullable=False)
    sql_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)

    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
