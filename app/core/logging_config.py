"""
Structured logging with request IDs and JSON-friendly output.
Enterprise observability best practices.
"""
import logging
import sys
from contextvars import ContextVar
from typing import Any

# Context variable for request ID (set by middleware)
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return request_id_ctx.get()


class RequestIdFilter(logging.Filter):
    """Inject request_id into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
) -> None:
    """
    Configure root logger with optional JSON format.
    Use json_logs=True in production for log aggregators.
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    if root.handlers:
        for h in root.handlers[:]:
            root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if json_logs:
        try:
            import json_log_formatter

            handler.setFormatter(json_log_formatter.JSONFormatter())
        except ImportError:
            fmt = "%(asctime)s [%(levelname)s] request_id=%(request_id)s %(name)s: %(message)s"
            handler.setFormatter(logging.Formatter(fmt))
    else:
        fmt = "%(asctime)s [%(levelname)s] request_id=%(request_id)s %(name)s: %(message)s"
        handler.setFormatter(logging.Formatter(fmt))

    root.addHandler(handler)


def bind_extra(extra: dict[str, Any]) -> dict[str, Any]:
    """Add request_id to extra dict for structured logging."""
    rid = get_request_id()
    if rid:
        extra["request_id"] = rid
    return extra
