"""
Chat API request and response schemas.
"""
from typing import List

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """POST /api/chat body."""

    # Session is managed by the backend; clients only send the query.
    query: str = Field(..., min_length=1, max_length=10_000, description="User question")


class ChatSendRequest(BaseModel):
    """Legacy POST /api/chat/send body: session_id + message (message used as query)."""

    session_id: str | None = Field(
        default=None,
        description="Optional existing session id; if omitted, a new session is created",
    )
    message: str = Field(default="", max_length=10_000, description="User message (used as query)")


class ChatResponse(BaseModel):
    """POST /api/chat response."""

    answer: str = Field(..., description="Final answer (Markdown)")
    sources: List[str] = Field(default_factory=list, description="Source attribution e.g. ['database','model']")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    reasoning: str = Field(default="", description="Judge reasoning")
    latency_ms: int | None = Field(default=None, description="Processing time in milliseconds")
    session_id: str | None = Field(default=None, description="Session ID (new or existing)")
    trace: List[str] = Field(default_factory=list, description="Execution steps taken by the agent")
    # Chart image when user asked for a chart and DB returned data (base64 PNG)
    chart_image_base64: str | None = Field(default=None, description="Base64-encoded PNG chart if requested")
    # Backward compatibility with existing chat UI
    final_report: str | None = Field(default=None, description="Answer with provenance footer")
    agent_message: str | None = Field(default=None, description="Same as final_report")


class SessionItem(BaseModel):
    """Single session in list."""

    id: str
    last_message: str
    created_at: str


class MessageItem(BaseModel):
    """Single message in history."""

    role: str
    content: str
    chart_image_base64: str | None = Field(default=None, description="Base64 PNG chart if assistant message included one")


class QueryLogItem(BaseModel):
    """Single query log entry for the data retriever."""

    id: int
    created_at: str
    session_id: str | None
    user_query: str
    sql_query: str | None
    response_text: str
    latency_ms: int | None
