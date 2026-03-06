"""
Formatter Agent — executive-friendly Markdown structure.
"""
import re

from app.agents.llm import FORMAT_PROMPT, get_core_llm
from app.graph.agent_state import AgentState


def _normalize_report_markdown(text: str) -> str:
    """Ensure ## headers and - bullets for UI."""
    if not text or not text.strip():
        return text
    formatted = text.strip()
    sections = [
        "Clinical Summary",
        "Key Findings",
        "Data Limitations",
        "Recommended Actions",
        "Final Conclusion",
    ]
    for name in sections:
        if f"## {name}" in formatted:
            continue
        pattern = rf"(^|\n)\s*{re.escape(name)}\s*\n"
        replacement = rf"\1## {name}\n\n"
        formatted = re.sub(pattern, replacement, formatted)
        pattern2 = rf"(^|\n)(\s*{re.escape(name)}\s*)$"
        formatted = re.sub(pattern2, replacement, formatted)
    formatted = re.sub(r"^(\s*)[•]\s+", r"\1- ", formatted, flags=re.MULTILINE)
    formatted = re.sub(r"^(\s*)[▪]\s+", r"\1- ", formatted, flags=re.MULTILINE)
    for name in sections:
        formatted = re.sub(
            rf"(## {re.escape(name)}\n)(?!\n)",
            r"\1\n",
            formatted,
        )
    return formatted


def formatter_agent(state: AgentState) -> dict:
    """Format analysis into executive Markdown using FORMAT_PROMPT."""
    raw_analysis = state.get("answer", "") or ""
    if not raw_analysis.strip():
        return {}
    llm = get_core_llm()
    prompt = FORMAT_PROMPT.format(analysis=raw_analysis)
    formatted = llm.invoke(prompt).content.strip()
    formatted = _normalize_report_markdown(formatted)
    return {"answer": formatted}
