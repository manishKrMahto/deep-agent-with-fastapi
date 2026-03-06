"""
LangGraph pipeline builder — wires all agent nodes and conditional edges.
"""
from app.graph.agent_state import AgentState, AgentOutput
from langgraph.graph import END, StateGraph

from app.agents.direct_llm_agent import direct_llm_agent, route_after_direct_llm
from app.agents.doc_tool_agent import doc_tool_node
from app.agents.formatter_agent import formatter_agent
from app.agents.judge_agent import judge_agent, route_after_judge
from app.agents.report_agent import report_agent
from app.agents.router_agent import route_after_router, router_agent
from app.agents.sql_agent import sql_agent, sql_execute_node, sql_guardrail_node


def build_graph():
    """Build and compile the LangGraph state machine."""
    builder = StateGraph(AgentState)

    builder.add_node("DOC_TOOL", doc_tool_node)
    builder.add_node("ROUTER", router_agent)
    builder.add_node("DIRECT_LLM", direct_llm_agent)
    builder.add_node("SQL_AGENT", sql_agent)
    builder.add_node("SQL_GUARDRAIL", sql_guardrail_node)
    builder.add_node("SQL_EXECUTE", sql_execute_node)
    builder.add_node("REPORT", report_agent)
    builder.add_node("FORMATTER", formatter_agent)
    builder.add_node("JUDGE", judge_agent)

    builder.set_entry_point("DOC_TOOL")
    builder.add_conditional_edges("DOC_TOOL", lambda s: "ROUTER", {"ROUTER": "ROUTER"})
    builder.add_conditional_edges(
        "ROUTER",
        route_after_router,
        {"DIRECT_LLM": "DIRECT_LLM", "HYBRID_RAG": "SQL_AGENT"},
    )
    builder.add_conditional_edges(
        "DIRECT_LLM",
        route_after_direct_llm,
        {"END": END, "JUDGE": "JUDGE"},
    )
    builder.add_edge("SQL_AGENT", "SQL_GUARDRAIL")
    builder.add_edge("SQL_GUARDRAIL", "SQL_EXECUTE")
    builder.add_edge("SQL_EXECUTE", "REPORT")
    builder.add_edge("REPORT", "FORMATTER")
    builder.add_edge("FORMATTER", "JUDGE")
    builder.add_conditional_edges("JUDGE", route_after_judge, {"END": END})

    return builder.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    """Return the compiled graph (lazy)."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def run_agent(query: str, history: list[dict[str, str]] | None = None) -> AgentOutput:
    """
    Run the multi-agent hybrid RAG pipeline and return the final response.
    """
    initial_state: AgentState = {
        "query": query,
        "route": "DIRECT_LLM",
        "sql_query": "",
        "db_result": None,
        "web_context": None,
        "answer": "",
        "sources": [],
        "confidence": 0.0,
        "reasoning": "",
        "retry_count": 0,
        "escalated_to_research": False,
        "node_route": "DIRECT_LLM",
        "history": history or [],
    }
    graph = get_graph()
    final_state = graph.invoke(initial_state)
    return AgentOutput(
        answer=final_state.get("answer", ""),
        sources=final_state.get("sources", []),
        confidence=float(final_state.get("confidence", 0.0)),
        reasoning=final_state.get("reasoning", ""),
        route=final_state.get("node_route", final_state.get("route", "DIRECT_LLM")),
        sql_query=final_state.get("sql_query", ""),
        db_row_count=len(final_state.get("db_result") or []),
    )
