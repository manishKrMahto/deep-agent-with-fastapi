"""
SQL Agent — generates SQL from natural language; guardrail + execution.
"""
import json
from typing import Any

from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState
from app.services.knowledge_db_service import execute_sql, introspect_schema


def sql_agent(state: AgentState) -> dict[str, Any]:
    """Generate a single SELECT query for SQLite from the user query."""
    query = state["query"]
    schema_text = introspect_schema()
    llm = get_core_llm()
    prompt = f"""
You are a SQL generation assistant for SQLite.

User query:
\"\"\"{query}\"\"\"

Database schema:
{schema_text}

Write a single safe SQL SELECT query in SQLite dialect that best answers the question.
Rules:
- SELECT only (no INSERT/UPDATE/DELETE/DDL)
- No semicolons, comments, or multiple statements
- Only use existing tables/columns from the schema.
- When using string values in WHERE clauses, use single quotes (e.g., disease_category = 'NSCLC').

Return ONLY the SQL query, nothing else.
"""
    sql = llm.invoke(prompt).content.strip()
    trace = list(state.get("trace", []))
    trace.append("Generated candidate SQL query from the user question.")
    return {"sql_query": sql, "trace": trace}


def _sql_guardrail(sql: str, schema_text: str) -> None:
    """Raise ValueError if SQL is unsafe."""
    upper = sql.upper()
    if not upper.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", ";", "--", "/*"]
    if any(token in upper for token in forbidden):
        raise ValueError("Destructive or unsafe SQL pattern detected.")


def sql_guardrail_node(state: AgentState) -> dict[str, Any]:
    """Normalize and validate SQL; return cleaned sql_query or empty + empty db_result."""
    raw_sql = state.get("sql_query", "") or ""
    schema_text = introspect_schema()
    upper = raw_sql.upper()
    select_idx = upper.find("SELECT")
    trace = list(state.get("trace", []))
    if select_idx == -1:
        trace.append("No valid SELECT found; skipping database query.")
        return {"sql_query": "", "db_result": [], "trace": trace}
    cleaned = raw_sql[select_idx:].strip()
    if ";" in cleaned:
        cleaned = cleaned.split(";", 1)[0].strip()
    try:
        _sql_guardrail(cleaned, schema_text)
    except ValueError:
        trace.append("SQL failed safety checks; skipping database query.")
        return {"sql_query": "", "db_result": [], "trace": trace}
    trace.append("SQL passed safety guardrail checks.")
    return {"sql_query": cleaned, "trace": trace}


def sql_execute_node(state: AgentState) -> dict[str, Any]:
    """Execute SQL; on failure retry once with LLM-repaired SQL."""
    sql = state.get("sql_query", "")
    retry_count = state.get("retry_count", 0)
    llm = get_core_llm()
    schema_text = introspect_schema()
    trace = list(state.get("trace", []))
    try:
        rows = execute_sql(sql)
        trace.append(f"Executed SQL against database and retrieved {len(rows)} rows.")
        return {"db_result": rows, "retry_count": retry_count, "trace": trace}
    except Exception as e:
        if retry_count >= 1:
            trace.append("SQL execution failed again after repair; aborting.")
            return {"db_result": [], "retry_count": retry_count, "trace": trace}
        repair_prompt = f"""
The following SQL query failed when executed against a SQLite database:

Original SQL:
\"\"\"{sql}\"\"\"

Error:
{e}

Database schema:
{schema_text}

Produce a corrected single SELECT query (SQLite dialect) that may fix the issue.
Rules:
- SELECT only
- No comments
- No semicolons
- Only one statement.

Return ONLY the corrected SQL, nothing else.
"""
        repaired_sql = llm.invoke(repair_prompt).content.strip()
        rows = execute_sql(repaired_sql)
        trace.append(
            f"Initial SQL failed; generated repaired SQL and retrieved {len(rows)} rows."
        )
        return {
            "db_result": rows,
            "sql_query": repaired_sql,
            "retry_count": retry_count + 1,
            "trace": trace,
        }
