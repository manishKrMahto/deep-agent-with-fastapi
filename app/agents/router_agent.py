"""
Router Agent — decides Direct LLM vs Hybrid RAG.
"""
from typing import Any

from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState
from app.services.knowledge_db_service import introspect_schema


def router_agent(state: AgentState) -> dict[str, Any]:
    """Route query to DIRECT_LLM or HYBRID_RAG based on LLM decision."""
    query = state["query"]
    schema_text = introspect_schema()
    llm = get_core_llm()
    prompt = f"""
You are a routing agent for a hybrid RAG system.

User query:
\"\"\"{query}\"\"\"

Database schema (SQLite):
{schema_text}

Decide whether this query should be answered:
- DIRECT_LLM: simple conversational or general question where SQL is not needed
- HYBRID_RAG: question that clearly benefits from querying the database

Return ONLY one word: DIRECT_LLM or HYBRID_RAG.
"""
    route = llm.invoke(prompt).content.strip().upper()
    if route not in ("DIRECT_LLM", "HYBRID_RAG"):
        route = "DIRECT_LLM"
    return {
        "route": route,
        "retry_count": state.get("retry_count", 0),
        "sources": state.get("sources", []),
        "node_route": route,
    }


def route_after_router(state: AgentState) -> str:
    """Conditional edge: DIRECT_LLM or HYBRID_RAG."""
    return state.get("route", "DIRECT_LLM")
