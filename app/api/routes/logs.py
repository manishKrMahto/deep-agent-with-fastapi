"""
Endpoints for inspecting data retriever SQL/query logs.
"""
from typing import List

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_query_log_repo
from app.db.repository import QueryLogRepository
from app.schemas.chat_schema import QueryLogItem


router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=List[QueryLogItem])
async def list_query_logs(
    limit: int = Query(50, ge=1, le=500),
    log_repo: QueryLogRepository = Depends(get_query_log_repo),
) -> list[QueryLogItem]:
    """
    Return recent data retriever logs (newest first).
    Each log includes created time, latency, user query, generated SQL, and response text.
    """
    rows = log_repo.list_recent(limit=limit)
    return [QueryLogItem(**row) for row in rows]

