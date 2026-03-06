"""
Render the LangGraph pipeline as a workflow diagram (PNG) to project root.
Run from project root: python -m scripts.render_langgraph_workflow

Requires: pip install graphviz
System: install Graphviz (https://graphviz.org) and add to PATH.
"""
from pathlib import Path

def main():
    try:
        import graphviz
    except ImportError:
        print("Install graphviz: pip install graphviz")
        return 1

    # Mirror structure from app/graph/langgraph_builder.build_graph()
    d = graphviz.Digraph(comment="PBM Research Agent — LangGraph Pipeline")
    d.attr(rankdir="TB", splines="ortho", nodesep="0.4", ranksep="0.5")
    d.attr("node", shape="box", style="rounded,filled", fontname="Arial", fontsize="10")
    d.attr("edge", fontname="Arial", fontsize="9")

    # Nodes
    d.node("START", "START", shape="ellipse", fillcolor="lightgray")
    d.node("DOC_TOOL", "DOC_TOOL\n(Check docs/URLs)", fillcolor="#e8f5e9")
    d.node("ROUTER", "ROUTER\n(Decide path)", fillcolor="#fff3e0")
    d.node("DIRECT_LLM", "DIRECT_LLM\n(Answer with LLM)", fillcolor="#e3f2fd")
    d.node("SQL_AGENT", "SQL_AGENT\n(Generate SQL)", fillcolor="#fce4ec")
    d.node("SQL_GUARDRAIL", "SQL_GUARDRAIL\n(Safety check)", fillcolor="#fce4ec")
    d.node("SQL_EXECUTE", "SQL_EXECUTE\n(Run query)", fillcolor="#fce4ec")
    d.node("REPORT", "REPORT\n(Analysis)", fillcolor="#fce4ec")
    d.node("FORMATTER", "FORMATTER\n(Markdown)", fillcolor="#fce4ec")
    d.node("JUDGE", "JUDGE\n(Confidence)", fillcolor="#fff8e1")
    d.node("END", "END", shape="ellipse", fillcolor="lightgray")

    # Edges (mirror langgraph_builder)
    d.edge("START", "DOC_TOOL")
    d.edge("DOC_TOOL", "ROUTER")
    d.edge("ROUTER", "DIRECT_LLM", label="DIRECT_LLM")
    d.edge("ROUTER", "SQL_AGENT", label="HYBRID_RAG")
    d.edge("DIRECT_LLM", "END", label="conf ≥ 0.85")
    d.edge("DIRECT_LLM", "JUDGE", label="else")
    d.edge("SQL_AGENT", "SQL_GUARDRAIL")
    d.edge("SQL_GUARDRAIL", "SQL_EXECUTE")
    d.edge("SQL_EXECUTE", "REPORT")
    d.edge("REPORT", "FORMATTER")
    d.edge("FORMATTER", "JUDGE")
    d.edge("JUDGE", "END")

    root = Path(__file__).resolve().parent.parent
    out_path = root / "langgraph_pipeline_workflow"
    d.render(out_path, format="png", cleanup=True)
    print(f"Rendered: {out_path}.png")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
