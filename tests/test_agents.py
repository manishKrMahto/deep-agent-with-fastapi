"""Tests for agent state and graph (unit-style)."""
import pytest

from app.graph.agent_state import AgentOutput, AgentState


def test_agent_output_dataclass():
    """AgentOutput has expected fields."""
    out = AgentOutput(
        answer="Test answer",
        sources=["database"],
        confidence=0.9,
        reasoning="Test reasoning",
    )
    assert out.answer == "Test answer"
    assert out.sources == ["database"]
    assert out.confidence == 0.9
    assert out.reasoning == "Test reasoning"


def test_agent_state_typing():
    """AgentState can be built as a dict."""
    state: AgentState = {
        "query": "test query",
        "route": "DIRECT_LLM",
        "sources": [],
        "retry_count": 0,
    }
    assert state["query"] == "test query"
    assert state["route"] == "DIRECT_LLM"
