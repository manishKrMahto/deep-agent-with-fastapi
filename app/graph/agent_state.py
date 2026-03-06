"""
Shared LangGraph state — single source of truth for the multi-agent pipeline.
"""
from dataclasses import dataclass
from typing import Any, Literal, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """State passed between graph nodes."""

    query: str
    route: Literal["DIRECT_LLM", "HYBRID_RAG"]
    sql_query: str
    db_result: Optional[list[dict[str, Any]]]
    doc_text: Optional[str]
    web_context: Optional[str]
    answer: str
    sources: list[str]
    confidence: float
    reasoning: str
    retry_count: int
    escalated_to_research: bool
    # Observability fields
    node_route: str  # "DIRECT_LLM" or "HYBRID_RAG"
    sql_query: str
    # Short-term memory: recent messages in the session (excluding current turn).
    # Shape: [{ "role": "user"|"assistant", "content": "..." }, ...]
    history: list[dict[str, str]]


@dataclass
class AgentOutput:
    """Final output returned to the API."""

    answer: str
    sources: list[str]
    confidence: float
    reasoning: str
    route: str
    sql_query: str
    db_row_count: int
