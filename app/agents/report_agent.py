"""
Report Agent — grounded analysis from DB results (and optional doc context).
"""
from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState


def report_agent(state: AgentState) -> dict:
    """Produce analytical narrative from db_result and optional doc_text."""
    import json

    query = state["query"]
    db_result = state.get("db_result") or []
    doc_text = state.get("doc_text") or ""
    preview_rows = json.dumps(db_result[:20], indent=2, default=str)
    doc_snippet = doc_text[:2000] if doc_text else ""
    sql_query = (state.get("sql_query") or "").strip()
    llm = get_core_llm()
    prompt = f"""
You are a PBM clinical analytics AI.

Your task is to write a detailed internal analysis (not yet formatted for executives)
based ONLY on the data and document context provided.

Critical grounding rules:
- Do NOT introduce specific therapy/drug names unless they appear in the provided database rows.
- If the database rows are empty, explicitly say the database query returned no matching rows and you cannot list therapies from the dataset.

User query:
\"\"\"{query}\"\"\"

SQL query used (may be empty):
\"\"\"{sql_query}\"\"\"

Database rows (JSON, up to 20):
{preview_rows}

Additional document context (may be empty, truncated):
\"\"\"{doc_snippet}\"\"\"

Write a thorough analytical narrative that:
- Explains what the data shows about utilization, prescribing patterns, and cost.
- Connects any clinical guidance from the document (if provided) to the observed or hypothetical claims.
- Explicitly calls out important caveats and data gaps.
- Uses plain paragraphs and inline lists; do NOT worry about headings, bullets, or final presentation.

This output is an intermediate analysis that will be passed to a separate formatter.
Do not add any sign-off, author name, or date footer.
"""
    answer = llm.invoke(prompt).content.strip()
    sources = set(state.get("sources", []))
    # The report is always LLM-generated.
    sources.add("model")
    # If a SQL query ran (even if it returned 0 rows), provenance should include database.
    if sql_query:
        sources.add("database")
    if doc_snippet:
        sources.add("doc")
    return {"answer": answer, "sources": list(sorted(sources))}
