"""Entry point: recreate the operations database.

Run from the ``my_multi_agent`` directory:

    python -m data_setup.build_db
    python -m data_setup.build_db --seed 7 --employees 300
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .builder import DatabaseBuilder
from .config import SeedConfig
from .schema_loader import SchemaLoader
from .seed import default_seeders

PACKAGE_DIR = Path(__file__).resolve().parent
SCHEMA_DIR = PACKAGE_DIR / "schema"
DEFAULT_DB_PATH = PACKAGE_DIR / "generated" / "ops.db"


def main(argv: list[str] | None = None) -> int:
    defaults = SeedConfig()
    parser = argparse.ArgumentParser(description="Create and seed the operations desk database.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="output database file")
    parser.add_argument("--seed", type=int, default=defaults.seed, help="random seed")
    parser.add_argument("--employees", type=int, default=defaults.n_employees, help="employee count")
    args = parser.parse_args(argv)

    config = SeedConfig(seed=args.seed, n_employees=args.employees)
    builder = DatabaseBuilder(args.db, SchemaLoader(SCHEMA_DIR), default_seeders(), config)
    report = builder.build()

    print(f"Built {report.db_path}")
    print(f"Schema files applied: {', '.join(report.schema_files)}")
    width = max(len(table) for table in report.row_counts)
    for table, count in report.row_counts.items():
        print(f"  {table:<{width}}  {count:>5}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
