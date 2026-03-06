"""
Knowledge DB initializer.

Builds the SQLite knowledge database (data/knowledge.db) from a CSV file so the
SQL agent can query PBM claims via database access.
"""

from __future__ import annotations

import csv
import logging
import sqlite3
from pathlib import Path
from typing import Iterable

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DID_INIT_CHECK = False


_REAL_COLUMNS = {
    "ingredient_cost",
    "dispensing_fee",
    "copay",
    "plan_paid_amount",
    "rebate_estimate",
}

_INT_COLUMNS = {
    "id",
    "quantity",
    "days_supply",
    "refill_number",
    "specialty_drug_flag",
}


def _first_existing_path(candidates: Iterable[Path]) -> Path | None:
    for p in candidates:
        try:
            if p.exists():
                return p
        except OSError:
            continue
    return None


def detect_claims_csv_path() -> Path | None:
    """Find the claims CSV path from settings or common locations."""
    settings = get_settings()
    candidates: list[Path] = []
    if settings.knowledge_csv_path is not None:
        candidates.append(settings.knowledge_csv_path)
    candidates.extend(
        [
            settings.project_root / "pbm_claims_full.csv",
            settings.data_dir / "pbm_claims_full.csv",
        ]
    )
    return _first_existing_path(candidates)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _infer_sqlite_type(column: str) -> str:
    if column in _INT_COLUMNS:
        return "INTEGER"
    if column in _REAL_COLUMNS:
        return "REAL"
    return "TEXT"


def _create_dataset_table(conn: sqlite3.Connection, table_name: str, columns: list[str]) -> None:
    col_defs = ", ".join(f'"{c}" {_infer_sqlite_type(c)}' for c in columns)
    conn.execute(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({col_defs})')

    # Helpful indexes for common analytics filters.
    index_cols = [
        "claim_id",
        "patient_id",
        "drug_name",
        "disease_category",
        "fill_date",
        "region",
        "plan_id",
        "pharmacy_type",
    ]
    for c in index_cols:
        if c in columns:
            conn.execute(
                f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_{c}" ON "{table_name}"("{c}")'
            )


def _coerce_value(column: str, raw: str | None) -> object | None:
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "":
        return None
    if column in _INT_COLUMNS:
        try:
            return int(raw)
        except ValueError:
            return None
    if column in _REAL_COLUMNS:
        try:
            return float(raw)
        except ValueError:
            return None
    return raw


def build_knowledge_db_from_csv(
    *,
    csv_path: Path,
    db_path: Path,
    table_name: str = "dataset",
    recreate: bool = False,
    batch_size: int = 5000,
) -> dict[str, int]:
    """
    Create or rebuild the knowledge DB from a claims CSV.

    Returns a small stats dict, e.g. {"rows_inserted": 50000}.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")

        if recreate:
            conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError("CSV has no header row.")
            columns = [c.strip() for c in reader.fieldnames if c and c.strip()]
            if not columns:
                raise ValueError("CSV header has no usable columns.")

            _create_dataset_table(conn, table_name, columns)

            cols_sql = ", ".join(f'"{c}"' for c in columns)
            placeholders = ", ".join("?" for _ in columns)
            insert_sql = f'INSERT INTO "{table_name}" ({cols_sql}) VALUES ({placeholders})'

            rows_inserted = 0
            batch: list[tuple[object | None, ...]] = []
            for row in reader:
                batch.append(tuple(_coerce_value(c, row.get(c)) for c in columns))
                if len(batch) >= batch_size:
                    conn.executemany(insert_sql, batch)
                    conn.commit()
                    rows_inserted += len(batch)
                    batch.clear()

            if batch:
                conn.executemany(insert_sql, batch)
                conn.commit()
                rows_inserted += len(batch)

        return {"rows_inserted": rows_inserted}
    finally:
        conn.close()


def ensure_knowledge_db_initialized(*, table_name: str = "dataset") -> bool:
    """
    Ensure knowledge.db has a dataset table.

    If knowledge DB is missing/empty and pbm_claims_full.csv is present, it will
    build the DB once per process.

    Returns True if initialization was performed; otherwise False.
    """
    global _DID_INIT_CHECK
    if _DID_INIT_CHECK:
        return False
    _DID_INIT_CHECK = True

    settings = get_settings()
    csv_path = detect_claims_csv_path()
    if csv_path is None:
        logger.info("No claims CSV found; skipping knowledge DB initialization.")
        return False

    db_path = settings.knowledge_db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                if _table_exists(conn, table_name):
                    row = conn.execute(f'SELECT COUNT(1) AS n FROM "{table_name}"').fetchone()
                    if row and int(row[0]) > 0:
                        logger.info("Knowledge DB already initialized at %s", db_path)
                        return False
            finally:
                conn.close()
        except Exception:
            # If the DB is corrupted or unreadable, we'll attempt to rebuild it.
            logger.warning("Existing knowledge DB unreadable; rebuilding from CSV.")

    logger.info("Initializing knowledge DB from %s -> %s (table=%s)", csv_path, db_path, table_name)
    stats = build_knowledge_db_from_csv(csv_path=csv_path, db_path=db_path, table_name=table_name, recreate=True)
    logger.info("Knowledge DB initialized (%s)", stats)
    return True

