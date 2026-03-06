"""
Session list and history endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.deps import get_db, get_message_repo, get_session_repo
from app.db.repository import MessageRepository, SessionRepository
from app.schemas.chat_schema import MessageItem, SessionItem
from app.services.pdf_export_service import export_chat_history_to_pdf_bytes

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Legacy paths for existing chat UI: /api/chat/sessions/ and /api/chat/history/<id>/
legacy_router = APIRouter(prefix="/api/chat", tags=["sessions"])


@router.get("", response_model=list[SessionItem])
async def list_sessions(
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """Return all chat sessions (newest first)."""
    items = session_repo.list_sessions()
    return [SessionItem(**x) for x in items]


@router.post("", response_model=SessionItem)
async def create_session(
    session_repo: SessionRepository = Depends(get_session_repo),
):
    """Create a new session; returns session id and metadata."""
    new_id = session_repo.get_or_create(None)
    items = session_repo.list_sessions()
    created = next((s for s in items if s["id"] == new_id), None)
    if not created:
        created = {"id": new_id, "last_message": "New conversation", "created_at": ""}
    return SessionItem(**created)


@router.get("/{session_id}/history", response_model=list[MessageItem])
async def get_history(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
):
    """Return messages for a session."""
    if not session_repo.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    messages = message_repo.get_messages(session_id)
    return [MessageItem(**m) for m in messages]


@router.get("/{session_id}/export/pdf")
async def export_history_pdf(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
):
    """Download a PDF export of the chat history for a session."""
    if not session_repo.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    messages = message_repo.get_messages(session_id)
    pdf_bytes = export_chat_history_to_pdf_bytes(
        messages,
        title="Deep Research Agent",
        session_id=session_id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="chat_{session_id}.pdf"'},
    )


@legacy_router.get("/sessions/", response_model=list[SessionItem])
async def list_sessions_legacy(session_repo: SessionRepository = Depends(get_session_repo)):
    """Legacy: GET /api/chat/sessions/."""
    items = session_repo.list_sessions()
    return [SessionItem(**x) for x in items]


@legacy_router.get("/history/{session_id}/", response_model=list[MessageItem])
async def get_history_legacy(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
):
    """Legacy: GET /api/chat/history/<session_id>/."""
    if not session_repo.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    messages = message_repo.get_messages(session_id)
    return [MessageItem(**m) for m in messages]


@legacy_router.get("/history/{session_id}/export/pdf")
async def export_history_pdf_legacy(
    session_id: str,
    session_repo: SessionRepository = Depends(get_session_repo),
    message_repo: MessageRepository = Depends(get_message_repo),
):
    """Legacy: download PDF for GET /api/chat/history/<session_id>/export/pdf."""
    if not session_repo.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    messages = message_repo.get_messages(session_id)
    pdf_bytes = export_chat_history_to_pdf_bytes(
        messages,
        title="Deep Research Agent",
        session_id=session_id,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="chat_{session_id}.pdf"'},
    )
