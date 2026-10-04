"""Builds the database: schema first, then each seeder in order."""

from __future__ import annotations

import random
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .config import SeedConfig
from .database import Database
from .schema_loader import SchemaLoader
from .seed.base import Seeder, SeedContext


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuildReport:
    db_path: Path
    schema_files: tuple[str, ...]
    row_counts: dict[str, int]


class DatabaseBuilder:
    """Depends on abstractions (a loader and ``Seeder`` objects), all injected by the caller."""

    def __init__(
        self,
        db_path: Path,
        schema_loader: SchemaLoader,
        seeders: Sequence[Seeder],
        config: SeedConfig,
    ) -> None:
        self._db_path = db_path
        self._schema_loader = schema_loader
        self._seeders = list(seeders)
        self._config = config

    def build(self) -> BuildReport:
        # Always start clean: the build is a pure function of (schema, seeders, config).
        self._db_path.unlink(missing_ok=True)

        with Database(self._db_path) as db:
            schema_files = self._schema_loader.apply(db)
            ctx = SeedContext(db=db, rng=random.Random(self._config.seed), config=self._config)

            for seeder in self._seeders:
                seeder.run(ctx)

            violations = db.foreign_key_violations()
            if violations:
                raise BuildError(f"Foreign key violations after seeding: {violations[:5]}")

            counts = {table: db.count_rows(table) for table in db.table_names()}

        return BuildReport(self._db_path, tuple(schema_files), counts)
