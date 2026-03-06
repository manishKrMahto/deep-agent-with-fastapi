"""
Direct LLM Agent — answers simple/general questions without DB.
"""
from typing import Any

from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState


def direct_llm_agent(state: AgentState) -> dict[str, Any]:
    """Answer using LLM only; early-exit heuristics for confidence."""
    query = state["query"]
    history = state.get("history") or []
    history_snippet = ""
    if history:
        # Use the last few turns as short-term memory.
        recent = history[-6:]
        transcript_lines = []
        for msg in recent:
            role = msg.get("role", "user")
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            transcript_lines.append(f"{role}: {content}")
        if transcript_lines:
            joined = "\n".join(transcript_lines)
            # Guard against over-long context.
            history_snippet = joined[-2000:]
    llm = get_core_llm()
    prompt = f"""
You are an expert analyst.
You are conversing in a multi-turn chat.

Conversation history (may be empty, most recent last):
{history_snippet or "[no prior messages]"}

Decide first whether the user is asking for:
- A casual greeting or small-talk question (e.g., "hello", "hi", "what are you doing?", "how are you?", "thanks").
- Or a substantive question that deserves an in-depth analysis or report.

If it is a casual greeting / small-talk query:
- Respond in a friendly, conversational tone.
- Keep the response SHORT (1–3 sentences).
- Do NOT write a report, headings, or long sections.

If it is a substantive question:
Write an in-depth, well-structured report in response to the user's query.

Formatting requirements (very important) for substantive questions:
- Use Markdown headings (##, ###) for sections.
- Put a blank line after each heading.
- Put blank lines between paragraphs.
- Use bullet lists where helpful, with a blank line before and after each list.
- Do not add any sign-off, author name, or "Prepared by" / date footer.
- Do not reference this instruction block or say that you are an AI model.

User query:
\"\"\"{query}\"\"\"

Respond with either:
- A short conversational reply (for casual queries), OR
- A full report (for substantive queries).
"""
    answer = llm.invoke(prompt).content.strip()
    simple = len(query) < 120 and not any(
        kw in query.lower()
        for kw in ["join", "group by", "sum(", "average", "count(", "trend", "time series"]
    )
    confidence = 0.9 if simple else 0.75
    return {
        "answer": answer,
        "sources": ["model"],
        "confidence": confidence,
        "reasoning": "Direct LLM path with heuristic high confidence.",
    }


def route_after_direct_llm(state: AgentState) -> str:
    """Early exit: skip judge if confidence >= 0.85."""
    if state.get("confidence", 0.0) >= 0.85:
        return "END"
    return "JUDGE"
