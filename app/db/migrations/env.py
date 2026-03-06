"""
Alembic environment: use app config for database URL.
"""
import os
import sys
from pathlib import Path

# Project root = parent of app (env.py -> migrations -> db -> app -> pbm_research_agent)
package_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(package_root))

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic.config import Config

# Import app models and config
from app.db.models import Base
from app.core.config import get_settings

config = context.config
if config.config_file_name is not None:
    sys.path.insert(0, str(Path(config.config_file_name).resolve().parent))

target_metadata = Base.metadata


def get_url() -> str:
    settings = get_settings()
    url = settings.database_url
    if not url or url == "sqlite:///":
        path = settings.chat_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path}"
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
