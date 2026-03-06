from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.services.knowledge_db_init import build_knowledge_db_from_csv, detect_claims_csv_path


def main() -> None:
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Initialize data/knowledge.db from a PBM claims CSV.")
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=None,
        help="Path to pbm_claims_full.csv (defaults to auto-detect / settings).",
    )
    parser.add_argument(
        "--db",
        dest="db_path",
        default=None,
        help="Output DB path (default: settings.knowledge_db_path).",
    )
    parser.add_argument(
        "--table",
        dest="table_name",
        default="dataset",
        help='Destination table name (default: "dataset").',
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop/recreate destination table before importing.",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv_path) if args.csv_path else detect_claims_csv_path()
    if csv_path is None:
        raise SystemExit(
            "Could not find a claims CSV. Provide --csv or set KNOWLEDGE_CSV_PATH, or place pbm_claims_full.csv in the project root."
        )

    db_path = Path(args.db_path) if args.db_path else settings.knowledge_db_path

    stats = build_knowledge_db_from_csv(
        csv_path=csv_path,
        db_path=db_path,
        table_name=args.table_name,
        recreate=args.recreate,
    )
    print(f"Initialized {db_path} from {csv_path}. {stats}")


if __name__ == "__main__":
    main()

