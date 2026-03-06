"""
Doc tool node — fetch and parse URL from query into doc_text.
"""
import re

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
import io

from app.graph.agent_state import AgentState


def _fetch_and_parse_document(url: str) -> str:
    """Fetch PDF or HTML and return extracted text (truncated)."""
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "").lower()
    if "pdf" in content_type or url.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(resp.content))
        pages_text = [p.extract_text() or "" for p in reader.pages[:10]]
        text = "\n\n".join(pages_text)
    else:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(t.strip() for t in soup.get_text(separator=" ").split())
    if len(text) > 10000:
        text = text[:10000]
    return text


def _scrape_web_page(url: str) -> str:
    """Scrape web page main text (truncated)."""
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(t.strip() for t in soup.get_text(separator=" ").split())
    if len(text) > 10000:
        text = text[:10000]
    return text


def doc_tool_node(state: AgentState) -> dict:
    """If query contains a URL, fetch and store text in doc_text."""
    query = state.get("query", "")
    url_match = re.search(r"https?://\S+", query)
    if not url_match:
        return {}
    url = url_match.group(0).strip().rstrip('"\'')
    try:
        if url.lower().endswith(".pdf"):
            text = _fetch_and_parse_document(url)
        else:
            text = _scrape_web_page(url)
    except Exception:
        text = ""
    return {"doc_text": text}
