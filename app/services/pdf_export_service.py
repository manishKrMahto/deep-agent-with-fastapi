from __future__ import annotations

import html
import io
from datetime import datetime
from typing import Any

import markdown as md
from xhtml2pdf import pisa


def _split_report_and_footer(content: str) -> tuple[str, str]:
    """
    Mirrors the frontend behavior:
    - assistant `content` is `report + "\\n\\nSources: ...\\nConfidence: ..."`
    - footer begins at the first occurrence of "\\n\\nSources:"
    """
    idx = content.find("\n\nSources:")
    if idx == -1:
        return content, ""
    return content[:idx].strip(), content[idx:].strip()


def _render_markdown(markdown_text: str) -> str:
    # Close enough to the frontend marked.js (gfm + breaks).
    # nl2br makes single newlines render as <br/>.
    return md.markdown(
        markdown_text or "",
        extensions=[
            "extra",
            "sane_lists",
            "nl2br",
            "fenced_code",
            "tables",
        ],
        output_format="html5",
    )


def _chat_history_to_html(
    messages: list[dict[str, Any]],
    *,
    title: str = "Deep Research Agent",
    session_id: str | None = None,
    generated_at: datetime | None = None,
) -> str:
    generated_at = generated_at or datetime.utcnow()
    safe_title = html.escape(title)
    safe_session = html.escape(session_id or "")
    safe_generated = html.escape(generated_at.isoformat() + "Z")

    parts: list[str] = []
    parts.append(
        f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>{safe_title}</title>
    <style>
      @page {{ size: A4; margin: 22mm 18mm; }}
      body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; color: #111827; }}
      .meta {{ color: #6b7280; font-size: 9pt; margin-bottom: 12pt; }}
      .meta b {{ color: #111827; font-weight: 700; }}

      .message-row {{ width: 100%; margin: 0 0 10pt 0; }}
      .message-table {{ width: 100%; border-collapse: collapse; }}
      .col {{ vertical-align: top; width: 50%; }}
      .bubble {{
        padding: 10pt 12pt;
        border-radius: 14pt;
        line-height: 1.35;
        word-break: break-word;
      }}
      .bubble.user {{
        background: #059669;
        color: #ffffff;
        border-bottom-right-radius: 6pt;
        white-space: pre-wrap;
      }}
      .bubble.assistant {{
        background: #f3f4f6;
        color: #111827;
        border-bottom-left-radius: 6pt;
      }}
      .assistant-report h2 {{ font-size: 12pt; font-weight: 700; margin: 10pt 0 6pt 0; }}
      .assistant-report h2:first-child {{ margin-top: 0; }}
      .assistant-report p {{ margin: 6pt 0; }}
      .assistant-report ul {{ margin: 6pt 0 6pt 16pt; }}
      .assistant-report li {{ margin: 2pt 0; }}
      .assistant-report pre {{
        background: #111827;
        color: #f9fafb;
        padding: 8pt 10pt;
        border-radius: 8pt;
        white-space: pre-wrap;
        font-family: Consolas, "Courier New", monospace;
        font-size: 9.5pt;
      }}
      .assistant-report code {{ font-family: Consolas, "Courier New", monospace; }}

      .chart {{ margin-top: 8pt; border: 1px solid #d1d5db; border-radius: 8pt; overflow: hidden; background: #ffffff; }}
      .chart img {{ width: 100%; height: auto; display: block; }}

      .footer {{
        margin-top: 8pt;
        padding-top: 6pt;
        border-top: 1px solid #d1d5db;
        font-size: 8.5pt;
        color: #6b7280;
        white-space: pre-wrap;
      }}
    </style>
  </head>
  <body>
    <div class="meta">
      <b>{safe_title}</b><br/>
      Session: {safe_session if safe_session else "-"}<br/>
      Generated at: {safe_generated}
    </div>
"""
    )

    for msg in messages or []:
        role = (msg.get("role") or "").strip().lower()
        content = msg.get("content") or ""
        chart_image_base64 = msg.get("chart_image_base64") or None

        if role == "user":
            user_text = html.escape(str(content))
            parts.append(
                f"""
    <div class="message-row">
      <table class="message-table">
        <tr>
          <td class="col"></td>
          <td class="col" align="right">
            <div class="bubble user">{user_text}</div>
          </td>
        </tr>
      </table>
    </div>
"""
            )
            continue

        # assistant (or unknown) — treat as assistant bubble
        report, footer = _split_report_and_footer(str(content))
        report_html = _render_markdown(report or str(content))
        footer_text = html.escape(footer) if footer else ""

        chart_html = ""
        if chart_image_base64:
            safe_b64 = html.escape(str(chart_image_base64))
            chart_html = f"""
            <div class="chart">
              <img src="data:image/png;base64,{safe_b64}" alt="Generated chart" />
            </div>
"""

        footer_html = f'<div class="footer">{footer_text}</div>' if footer_text else ""

        parts.append(
            f"""
    <div class="message-row">
      <table class="message-table">
        <tr>
          <td class="col" align="left">
            <div class="bubble assistant">
              <div class="assistant-report">{report_html}</div>
              {chart_html}
              {footer_html}
            </div>
          </td>
          <td class="col"></td>
        </tr>
      </table>
    </div>
"""
        )

    parts.append(
        """
  </body>
</html>
"""
    )
    return "".join(parts)


def export_chat_history_to_pdf_bytes(
    messages: list[dict[str, Any]],
    *,
    title: str = "Deep Research Agent",
    session_id: str | None = None,
) -> bytes:
    """
    Create a PDF that matches the chat UI layout (bubbles, Markdown, images).

    Expected message shape (compatible with your existing `MessageRepository.get_messages()`):
      - { "role": "user"|"assistant", "content": "..." }

    To include images like the frontend's chart rendering, pass:
      - { "role": "assistant", "content": "...", "chart_image_base64": "<...>" }
    """
    html_doc = _chat_history_to_html(messages, title=title, session_id=session_id)
    out = io.BytesIO()
    pdf_status = pisa.CreatePDF(src=io.StringIO(html_doc), dest=out, encoding="utf-8")
    if pdf_status.err:
        raise RuntimeError("Failed to render PDF")
    return out.getvalue()

