"""Applies the numbered ``.sql`` files in ``schema/`` to a database."""

from __future__ import annotations

from pathlib import Path

from .database import Database


class SchemaLoader:
    """Files are applied in filename order, so the numeric prefixes encode foreign-key order."""

    def __init__(self, schema_dir: Path) -> None:
        self._schema_dir = schema_dir

    def files(self) -> list[Path]:
        files = sorted(self._schema_dir.glob("*.sql"))
        if not files:
            raise FileNotFoundError(f"No .sql files found in {self._schema_dir}")
        return files

    def apply(self, db: Database) -> list[str]:
        applied = []
        for path in self.files():
            db.execute_script(path.read_text(encoding="utf-8"))
            applied.append(path.name)
        return applied
