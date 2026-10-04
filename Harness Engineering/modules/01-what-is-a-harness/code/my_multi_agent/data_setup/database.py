"""A thin wrapper over a SQLite connection.

Owns the connection lifecycle and the pragmas, so no other module touches ``sqlite3`` directly.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


class Database:
    """Context manager: commits on a clean exit, rolls back on an exception."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> Database:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        # SQLite does not enforce foreign keys unless asked, per connection.
        self._conn.execute("PRAGMA foreign_keys = ON")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        conn = self._require_conn()
        if exc_type is None:
            conn.commit()
        else:
            conn.rollback()
        conn.close()
        self._conn = None

    def execute_script(self, sql: str) -> None:
        self._require_conn().executescript(sql)

    def insert_many(
        self, table: str, columns: Sequence[str], rows: Iterable[Sequence[Any]]
    ) -> int:
        """Bulk-insert ``rows`` and return how many were written.

        ``table`` and ``columns`` come from code constants, never from user input.
        """
        materialized = list(rows)
        placeholders = ", ".join("?" for _ in columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        self._require_conn().executemany(sql, materialized)
        return len(materialized)

    def count_rows(self, table: str) -> int:
        cursor = self._require_conn().execute(f"SELECT COUNT(*) FROM {table}")
        return int(cursor.fetchone()[0])

    def table_names(self) -> list[str]:
        cursor = self._require_conn().execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY rowid"
        )
        return [row[0] for row in cursor.fetchall()]

    def foreign_key_violations(self) -> list[tuple]:
        return self._require_conn().execute("PRAGMA foreign_key_check").fetchall()

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not open; use it as a context manager.")
        return self._conn
