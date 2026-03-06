"""
Knowledge DB (PBM claims) access: schema introspection and read-only SQL execution.
Uses SQLite for development; can be swapped to PostgreSQL via engine from config.
"""
import sqlite3
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def _get_connection() -> sqlite3.Connection:
    """Return a connection to the knowledge DB (claims data)."""
    settings = get_settings()
    path = settings.knowledge_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def introspect_schema() -> str:
    """Return a textual description of tables/columns for the LLM."""
    try:
        conn = _get_connection()
        try:
            cur = conn.cursor()
            tables = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            parts: list[str] = []
            for (table_name,) in tables:
                cols = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
                col_list = ", ".join(str(c[1]) for c in cols)
                parts.append(f"Table {table_name}({col_list})")
            return "; ".join(parts) or "No tables defined."
        finally:
            conn.close()
    except Exception:
        return "Schema introspection failed."


def execute_sql(sql: str) -> list[dict[str, Any]]:
    """Execute a read-only SELECT and return rows as list of dicts."""
    conn = _get_connection()
    try:
        cur = conn.cursor()
        rows = cur.execute(sql).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
