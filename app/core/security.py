"""
Security utilities: API key validation, rate limiting placeholders, input validation.
"""
import re
from typing import Annotated

from fastapi import Header, HTTPException, status

# Maximum lengths for API inputs (prevent abuse)
MAX_QUERY_LENGTH = 10_000
MAX_SESSION_ID_LENGTH = 128
QUERY_SANITIZE_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def validate_query(query: str | None) -> str:
    """Validate and sanitize user query."""
    if not query or not isinstance(query, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required and must be a non-empty string",
        )
    q = query.strip()
    if len(q) > MAX_QUERY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"query must be at most {MAX_QUERY_LENGTH} characters",
        )
    # Strip control characters
    q = QUERY_SANITIZE_PATTERN.sub("", q)
    if not q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="query is required",
        )
    return q


def validate_session_id(session_id: str | None) -> str | None:
    """Validate optional session ID."""
    if session_id is None or session_id == "":
        return None
    if not isinstance(session_id, str) or len(session_id) > MAX_SESSION_ID_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="session_id must be a string with at most 128 characters",
        )
    return session_id.strip() or None


# Optional: API key dependency (enable when API_KEY is set in env)
async def verify_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    """
    Placeholder: verify X-API-Key if API_KEY env is set.
    In production, use a secrets manager or vault.
    """
    # If you set API_KEY in env, uncomment and use:
    # from app.core.config import get_settings
    # settings = get_settings()
    # if settings.api_key and (not x_api_key or x_api_key != settings.api_key):
    #     raise HTTPException(status_code=401, detail="Invalid or missing API key")
    pass
