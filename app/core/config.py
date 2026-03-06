"""
Enterprise configuration via Pydantic Settings.
Environment-based; supports .env and 12-factor app principles.
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="PBM Research Agent", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Deployment environment"
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Bind host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")

    # Paths: project root = pbm_research_agent (when you cd pbm_research_agent); data in data/
    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    data_dir: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "data"
    )

    # Knowledge DB bootstrap (PBM claims)
    auto_init_knowledge_db: bool = Field(
        default=True,
        description="If true, build data/knowledge.db from a CSV when missing/empty",
    )
    knowledge_csv_path: Path | None = Field(
        default=None,
        description="Optional path to PBM claims CSV used to initialize the knowledge DB",
    )

    @property
    def chat_db_path(self) -> Path:
        return self.data_dir / "chat.db"

    @property
    def knowledge_db_path(self) -> Path:
        return self.data_dir / "knowledge.db"

    # Database (production: PostgreSQL URL; dev: SQLite)
    database_url: str = Field(
        default="",
        description="Database URL. Empty = SQLite in data_dir/chat.db",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def default_sqlite_url(cls, v: str, info) -> str:
        if v:
            return v
        # Lazy: will be set in dependency using settings.data_dir
        return "sqlite:///"

    # OpenAI
    openai_api_key: str = Field(default="", description="OpenAI API key")

    # Observability
    log_level: str = Field(default="INFO", description="Log level")
    request_id_header: str = Field(default="X-Request-ID", description="Request ID header")

    # Security (placeholders for enterprise)
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    rate_limit_requests: int = Field(default=100, description="Rate limit per window")
    rate_limit_window_seconds: int = Field(default=60, description="Rate limit window")

    # Optional: Tavily for web retrieval (future)
    tavily_api_key: str = Field(default="", description="Tavily API key for web search")


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
