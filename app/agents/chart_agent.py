"""
Chart Agent — builds a visualization from db_result when user asked for a chart.
Uses a small LLM to pick chart type and columns, then seaborn to render.
"""
import base64
import json
import logging
from io import BytesIO
from typing import Any

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt

from app.agents.llm import get_core_llm
from app.graph.agent_state import AgentState

logger = logging.getLogger(__name__)

# Chart types we support
CHART_TYPES = ("bar", "line", "pie", "horizontal_bar")


def _get_chart_params_from_llm(
    user_query: str, columns: list[str], sample_json: str
) -> dict[str, Any]:
    """Use LLM to decide chart_type, x_column, y_column, title from query and data."""
    llm = get_core_llm()
    prompt = f"""You are a chart design assistant. Given a user request and the available data, choose the best chart type and which columns to use.

User request: "{user_query}"

Available columns in the data: {columns}

Sample of the data (first few rows, JSON): {sample_json}

Respond with a single JSON object only, no other text. Use exactly these keys:
- chart_type: one of bar, line, pie, horizontal_bar
  - bar: vertical bars (good for categories vs one value)
  - horizontal_bar: horizontal bars (good for many categories or long labels)
  - line: line plot (good for trends over ordered x, e.g. time)
  - pie: pie chart (good for parts of a whole; use one category column and one numeric column)
- x_column: exact column name from the list to use for categories / x-axis (or first series for pie)
- y_column: exact column name for values / y-axis (or second series for pie). If only one numeric column exists, use it.
- title: short chart title (e.g. "Total rebate by region")

Use only column names that appear in "Available columns". If unsure, pick the first string-like column for x and first numeric for y.
"""
    raw = llm.invoke(prompt).content.strip()
    # Strip markdown code block if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Chart LLM returned invalid JSON, using defaults: %s", raw[:200])
        return {
            "chart_type": "bar",
            "x_column": columns[0] if columns else "",
            "y_column": columns[1] if len(columns) > 1 else (columns[0] if columns else ""),
            "title": "Chart",
        }


def _plot_bar(df: pd.DataFrame, x: str, y: str, title: str, horizontal: bool = False) -> None:
    if horizontal:
        sns.barplot(data=df, y=x, x=y, orient="h", palette="viridis")
        plt.ylabel(x)
        plt.xlabel(y)
    else:
        sns.barplot(data=df, x=x, y=y, palette="viridis")
        plt.xlabel(x)
        plt.ylabel(y)
    plt.title(title)
    plt.tight_layout()


def _plot_line(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    sns.lineplot(data=df, x=x, y=y)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.title(title)
    plt.tight_layout()


def _plot_pie(df: pd.DataFrame, x: str, y: str, title: str) -> None:
    # x = labels, y = values
    labels = df[x].astype(str).tolist()
    values = pd.to_numeric(df[y], errors="coerce").fillna(0).tolist()
    plt.figure(figsize=(8, 8))
    plt.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    plt.title(title)
    plt.axis("equal")
    plt.tight_layout()


def _render_chart(
    df: pd.DataFrame, chart_type: str, x_column: str, y_column: str, title: str
) -> bytes:
    """Render chart to PNG bytes using seaborn/matplotlib."""
    plt.close("all")
    fig, ax = plt.subplots(figsize=(10, 6))
    chart_type = (chart_type or "bar").lower()
    if chart_type == "horizontal_bar":
        _plot_bar(df, x_column, y_column, title, horizontal=True)
    elif chart_type == "line":
        _plot_line(df, x_column, y_column, title)
    elif chart_type == "pie":
        _plot_pie(df, x_column, y_column, title)
    else:
        _plot_bar(df, x_column, y_column, title, horizontal=False)
    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close("all")
    buf.seek(0)
    return buf.read()


def chart_agent(state: AgentState) -> dict[str, Any]:
    """
    Build a chart from db_result using LLM-selected type/columns and seaborn.
    Writes PNG to state as base64 (chart_image_base64).
    """
    db_result = state.get("db_result") or []
    query = state.get("query") or ""
    trace = list(state.get("trace", []))

    if not db_result:
        trace.append("Chart skipped: no database rows to plot.")
        return {"trace": trace}

    df = pd.DataFrame(db_result)
    if df.empty or len(df.columns) == 0:
        trace.append("Chart skipped: empty result set.")
        return {"trace": trace}

    columns = list(df.columns)
    # Use json.dumps for compatibility across pandas versions (to_json's default_str is 2.1+)
    sample = json.dumps(df.head(5).to_dict(orient="records"), default=str)

    try:
        params = _get_chart_params_from_llm(query, columns, sample)
        chart_type = (params.get("chart_type") or "bar").lower()
        if chart_type not in CHART_TYPES:
            chart_type = "bar"
        x_col = params.get("x_column") or columns[0]
        y_col = params.get("y_column") or (columns[1] if len(columns) > 1 else columns[0])
        title = params.get("title") or "Chart"

        if x_col not in columns:
            x_col = columns[0]
        if y_col not in columns:
            y_col = columns[1] if len(columns) > 1 else columns[0]

        # Ensure y is numeric for bar/line
        df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
        df = df.dropna(subset=[y_col])
        if df.empty:
            trace.append("Chart skipped: no numeric data to plot.")
            return {"trace": trace}

        png_bytes = _render_chart(df, chart_type, x_col, y_col, title)
        b64 = base64.b64encode(png_bytes).decode("ascii")
        trace.append("Generated chart from database results (seaborn).")
        return {"chart_image_base64": b64, "trace": trace}
    except Exception as e:
        logger.exception("Chart generation failed")
        trace.append(f"Chart generation failed: {e!s}.")
        return {"trace": trace}
