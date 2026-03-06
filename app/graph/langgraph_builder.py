"""
LangGraph pipeline builder — wires all agent nodes and conditional edges.
"""
from app.graph.agent_state import AgentState, AgentOutput
from langgraph.graph import END, StateGraph

from app.agents.chart_agent import chart_agent
from app.agents.direct_llm_agent import direct_llm_agent, route_after_direct_llm
from app.agents.doc_tool_agent import doc_tool_node
from app.agents.formatter_agent import formatter_agent
from app.agents.judge_agent import judge_agent, route_after_judge
from app.agents.report_agent import report_agent
from app.agents.router_agent import route_after_router, router_agent
from app.agents.sql_agent import sql_agent, sql_execute_node, sql_guardrail_node


def _route_after_sql_execute(state: AgentState) -> str:
    """If user asked for a chart and we have data, go to CHART; else REPORT."""
    if state.get("asked_to_create_chart") and (state.get("db_result") or []):
        return "CHART"
    return "REPORT"


def build_graph():
    """Build and compile the LangGraph state machine."""
    builder = StateGraph(AgentState)

    builder.add_node("DOC_TOOL", doc_tool_node)
    builder.add_node("ROUTER", router_agent)
    builder.add_node("DIRECT_LLM", direct_llm_agent)
    builder.add_node("SQL_AGENT", sql_agent)
    builder.add_node("SQL_GUARDRAIL", sql_guardrail_node)
    builder.add_node("SQL_EXECUTE", sql_execute_node)
    builder.add_node("CHART", chart_agent)
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
    builder.add_conditional_edges(
        "SQL_EXECUTE",
        _route_after_sql_execute,
        {"CHART": "CHART", "REPORT": "REPORT"},
    )
    builder.add_edge("CHART", "REPORT")
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


def build_initial_state(
    query: str, history: list[dict[str, str]] | None = None
) -> AgentState:
    """Build initial state for the graph (invoke or stream)."""
    return {
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
        "asked_to_create_chart": False,
        "chart_image_base64": None,
        "node_route": "DIRECT_LLM",
        "history": history or [],
        "trace": [],
    }


def run_agent(query: str, history: list[dict[str, str]] | None = None) -> AgentOutput:
    """
    Run the multi-agent hybrid RAG pipeline and return the final response.
    """
    initial_state = build_initial_state(query, history)
    graph = get_graph()
    final_state = graph.invoke(initial_state)
    return _state_to_output(final_state)


def _state_to_output(state: AgentState) -> AgentOutput:
    """Convert graph state dict to AgentOutput."""
    return AgentOutput(
        answer=state.get("answer", ""),
        sources=state.get("sources", []),
        confidence=float(state.get("confidence", 0.0)),
        reasoning=state.get("reasoning", ""),
        route=state.get("node_route", state.get("route", "DIRECT_LLM")),
        sql_query=state.get("sql_query", ""),
        db_row_count=len(state.get("db_result") or []),
        trace=state.get("trace", []),
        chart_image_base64=state.get("chart_image_base64"),
    )
