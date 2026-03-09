"""
Database engine and session management.
Supports SQLite (development) and PostgreSQL (production) via DATABASE_URL.
"""
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.models import Base

# Lazy engines (created on first use)
_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Create or return the chat DB engine."""
    global _engine
    if _engine is not None:
        return _engine
    settings = get_settings()
    url = settings.database_url
    if not url or url == "sqlite:///":
        path = settings.chat_db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{path}"
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    _engine = create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=settings.debug,
    )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return session factory (creates engine if needed)."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory
    engine = get_engine()
    _session_factory = sessionmaker(engine, autocommit=False, autoflush=False, expire_on_commit=False)
    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope for the chat DB."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_chat_db() -> None:
    """Create chat tables if they do not exist (development convenience)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    # Lightweight schema patching for development.
    # Older databases may have a 'users' table without 'hashed_password'
    # or with an incorrectly defined 'id' column. Fix both cases.
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(users);"))
            rows = list(result)
            if not rows:
                return

            columns = {row[1] for row in rows}  # row[1] is column name

            # 1) Ensure hashed_password column exists.
            if "hashed_password" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE users "
                        "ADD COLUMN hashed_password VARCHAR(255) NOT NULL DEFAULT ''"
                    )
                )

            # 2) Ensure id column is an INTEGER PRIMARY KEY so SQLite can autoincrement.
            id_row = next((row for row in rows if row[1] == "id"), None)
            if id_row is not None:
                col_type = str(id_row[2] or "").upper()
                is_pk = bool(id_row[5])
                # If id is not an INTEGER primary key, recreate the table using ORM metadata.
                if col_type not in {"INTEGER", "INT"} or not is_pk:
                    conn.execute(text("DROP TABLE IF EXISTS users"))
                    # Recreate with the correct schema from SQLAlchemy models.
                    Base.metadata.create_all(bind=engine)
        except Exception:
            # If the users table does not exist yet or PRAGMA fails, ignore;
            # it will be created by Base.metadata.create_all above.
            pass


def get_db_session_generator():
    """FastAPI dependency: yield a DB session and commit/rollback on exit."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
