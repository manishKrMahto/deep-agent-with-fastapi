"""
FastAPI application entry point — PBM Deep Research Agent.
"""
import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging_config import request_id_ctx, setup_logging
from app.db.database import init_chat_db
from app.services.knowledge_db_init import ensure_knowledge_db_initialized

settings = get_settings()
setup_logging(level=settings.log_level)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler (startup/shutdown)."""
    # Startup logic
    init_chat_db()
    logger.info("Chat DB initialized")

    if settings.auto_init_knowledge_db:
        try:
            did_init = ensure_knowledge_db_initialized(table_name="dataset")
            if did_init:
                logger.info("Knowledge DB initialized")
        except Exception:
            logger.exception("Knowledge DB initialization failed")

    # Hand control back to FastAPI application
    yield

    # Place shutdown logic here if needed in future


app = FastAPI(
    title=settings.app_name,
    description="Multi-agent Hybrid RAG research agent for PBM analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_and_latency(request: Request, call_next):
    """Add X-Request-ID and log latency."""
    request_id = request.headers.get(settings.request_id_header) or str(uuid.uuid4())
    request_id_ctx.set(request_id)
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(latency_ms)
    logger.info(
        "%s %s %s %s",
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
        extra={"request_id": request_id, "latency_ms": latency_ms},
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# Serve chat UI: static assets and index
_base_dir = Path(__file__).resolve().parent.parent
_templates_dir = _base_dir / "templates"
_assets_dir = _base_dir / "assets"
_chat_index = _templates_dir / "chat" / "index.html"

# Mount /assets for optional static files (if folder exists)
if _assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/")
async def index():
    """Serve the chat UI."""
    if _chat_index.exists():
        return FileResponse(_chat_index)
    return {"message": "PBM Research Agent API", "docs": "/docs"}
