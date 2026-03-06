"""
Chat service: runs the agent and persists messages.
"""
import time

from app.graph.langgraph_builder import run_agent
from app.graph.agent_state import AgentOutput


def run_chat(query: str, history: list[dict[str, str]] | None = None) -> tuple[AgentOutput, int]:
    """
    Run the LangGraph agent and return (AgentOutput, latency_ms).
    """
    start = time.perf_counter()
    result = run_agent(query, history=history or [])
    latency_ms = int((time.perf_counter() - start) * 1000)
    return result, latency_ms
