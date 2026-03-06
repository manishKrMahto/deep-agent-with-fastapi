"""
Shared LLM and prompts for agent nodes.
"""
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

_settings = get_settings()
_core_llm: ChatOpenAI | None = None


def get_core_llm() -> ChatOpenAI:
    """Lazy-initialized core LLM (gpt-4o-mini)."""
    global _core_llm
    if _core_llm is None:
        api_key = _settings.openai_api_key or None  # LangChain reads OPENAI_API_KEY from env if not set
        _core_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key or None)
    return _core_llm


FORMAT_PROMPT = """
You are a healthcare analytics assistant.

Rewrite the provided analysis into a clean, structured,
executive-friendly Markdown format using:

- Clear section headers
- Bullet points
- Short paragraphs
- Logical grouping
- No repetition
- Professional tone

You MUST output valid Markdown and you MUST use
exactly these section headings, each starting with "## ":

## Clinical Summary
## Key Findings
## Data Limitations
## Recommended Actions
## Final Conclusion

Formatting rules (VERY IMPORTANT):
- Start each section header with "## " exactly, followed by the section name.
- Put a blank line after each heading.
- Put blank lines between paragraphs.
- Use bullet lists under the *Findings*, *Limitations*, and *Recommended Actions* sections.
- Do not add any sign-off, author name, or date footer.
- Do not add any extra sections before or after these.

Analysis to format:
{analysis}
"""
