"""
Router Agent — decides Direct LLM vs Hybrid RAG.
"""
from typing import Any

from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState
from app.services.knowledge_db_service import introspect_schema


def router_agent(state: AgentState) -> dict[str, Any]:
    """Route query to DIRECT_LLM or HYBRID_RAG; detect if user asked to create a chart."""
    query = state["query"]
    schema_text = introspect_schema()
    llm = get_core_llm()
    prompt = f"""
You are a routing agent for a hybrid RAG system.

User query:
\"\"\"{query}\"\"\"

Database schema (SQLite):
{schema_text}

Tasks:
1) Decide whether this query should be answered via:
   - DIRECT_LLM: simple conversational or general question where SQL is not needed
   - HYBRID_RAG: question that clearly benefits from querying the database

2) Decide if the user explicitly asked to create/plot/visualize a chart or graph (e.g. "create a chart", "plot", "visualize", "show me a graph for...").

Respond with exactly two lines:
Line 1: DIRECT_LLM or HYBRID_RAG
Line 2: CHART or NO_CHART
"""
    response = llm.invoke(prompt).content.strip().upper()
    lines = [ln.strip() for ln in response.splitlines() if ln.strip()]
    route = lines[0] if lines else "DIRECT_LLM"
    if route not in ("DIRECT_LLM", "HYBRID_RAG"):
        route = "DIRECT_LLM"
    create_chart = len(lines) > 1 and lines[1] == "CHART"
    trace = list(state.get("trace", []))
    if route == "DIRECT_LLM":
        trace.append("Routing agent chose Direct LLM path (no database needed).")
    else:
        trace.append("Routing agent chose Hybrid RAG path (will query database).")
    if create_chart:
        trace.append("User requested a chart; chart will be generated if database returns data.")
    return {
        "route": route,
        "asked_to_create_chart": create_chart,
        "retry_count": state.get("retry_count", 0),
        "sources": state.get("sources", []),
        "node_route": route,
        "trace": trace,
    }


def route_after_router(state: AgentState) -> str:
    """Conditional edge: DIRECT_LLM or HYBRID_RAG."""
    return state.get("route", "DIRECT_LLM")
