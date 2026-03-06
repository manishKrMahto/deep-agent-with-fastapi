"""
Judge Agent — confidence score and reasoning over answer + context.
"""
import json
from typing import Any

from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState


def judge_agent(state: AgentState) -> dict[str, Any]:
    """Evaluate answer grounding; output confidence and reasoning."""
    query = state["query"]
    answer = state.get("answer", "")
    db_result = state.get("db_result") or []
    web_context = state.get("web_context")
    context_snippet = {
        "db_result": db_result[:10],
        "has_more_db_rows": len(db_result) > 10,
        "web_context_preview": (web_context[:2000] + "…") if web_context else None,
    }
    llm = get_core_llm()
    prompt = f"""
You are an evaluation agent.
You will receive a user query, an answer, and the context that was used to produce it.

You must:
- Judge whether the answer is well grounded in the context
- Provide a confidence score between 0.0 and 1.0
- Explain your reasoning briefly.

Respond strictly as raw JSON with keys: confidence (float), reasoning (string).
Do NOT wrap the JSON in Markdown code fences.

User query:
\"\"\"{query}\"\"\"

Answer:
\"\"\"{answer}\"\"\"

Context (JSON):
{json.dumps(context_snippet, indent=2, default=str)}
"""
    raw = llm.invoke(prompt).content.strip()
    # Some models occasionally wrap JSON in ```json fences; strip defensively.
    cleaned = raw.strip()
    if "```" in cleaned:
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace : last_brace + 1]
    try:
        parsed = json.loads(cleaned)
        confidence = float(parsed.get("confidence", 0.0))
        reasoning = str(parsed.get("reasoning", "")).strip()
    except Exception:
        confidence = 0.6
        reasoning = f"Failed to parse judge JSON. Raw: {raw!r}"
    return {"confidence": confidence, "reasoning": reasoning}


def route_after_judge(state: AgentState) -> str:
    """Currently always END; can add WEB augmentation when Tavily is enabled."""
    return "END"
