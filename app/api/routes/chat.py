"""
Chat endpoint: send message, run agent, persist and return response.
"""
import logging

from fastapi import APIRouter, Depends

from app.api.deps import get_message_repo, get_query_log_repo, get_session_repo
from app.core.security import validate_query, validate_session_id
from app.db.repository import MessageRepository, QueryLogRepository, SessionRepository
from app.schemas.chat_schema import ChatRequest, ChatResponse, ChatSendRequest
from app.services.chat_service import run_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _process_chat(
    query: str,
    session_id: str | None,
    session_repo: SessionRepository,
    message_repo: MessageRepository,
    log_repo: QueryLogRepository,
) -> ChatResponse:
    """Shared logic for chat and send endpoints."""
    query = validate_query(query)
    session_id = validate_session_id(session_id)
    session_id = session_repo.get_or_create(session_id)
    # Fetch short-term history before appending the new user message.
    # Use the last few turns as memory context for the agent.
    full_history = message_repo.get_messages(session_id)
    short_history = full_history[-10:] if len(full_history) > 10 else full_history
    result, latency_ms = run_chat(query, history=short_history)
    sources_list = result.sources or []
    confidence_value = result.confidence or 0.0
    provenance_footer = f"\n\nSources: {sources_list}\nConfidence: {round(confidence_value, 3)}"
    final_report = (result.answer or "") + provenance_footer
    message_repo.add(session_id, "user", query)
    message_repo.add(session_id, "assistant", final_report)
    last_preview = (query[:80] + "...") if len(query) > 80 else query
    session_repo.update_last_message(session_id, last_preview)

    # Persist data-retriever–focused log
    try:
        log_repo.add(
            session_id=session_id,
            user_query=query,
            sql_query=result.sql_query or None,
            latency_ms=latency_ms,
            response_text=result.answer or "",
        )
    except Exception:
        logger.exception("Failed to persist agent run log")
    return ChatResponse(
        answer=result.answer or "",
        sources=result.sources or [],
        confidence=result.confidence,
        reasoning=result.reasoning or "",
        latency_ms=latency_ms,
        session_id=session_id,
        final_report=final_report,
        agent_message=final_report,
    )


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
    log_repo: QueryLogRepository = Depends(get_query_log_repo),
):
    """
    Process a user message: run the PBM research agent, persist messages, return answer.
    Body: { "query": "user question" }. Session management is handled by the backend.
    """
    # Session is fully managed server-side; ignore any client notion of session.
    return _process_chat(body.query, None, session_repo, message_repo, log_repo)


@router.post("/send", response_model=ChatResponse)
async def chat_send(
    body: ChatSendRequest,
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
    log_repo: QueryLogRepository = Depends(get_query_log_repo),
):
    """
    Legacy endpoint: body { "session_id", "message" }.
    Same behavior as POST /api/chat, but allows the client to continue
    an existing session by passing session_id.
    """
    query = (body.message or "").strip()
    if not query:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="message is required")
    return _process_chat(query, body.session_id, session_repo, message_repo, log_repo)
