"""The seeding abstraction.

A ``Seeder`` fills the tables of one cluster. The builder depends only on this interface, so a new
cluster is added by writing a new subclass and registering it, without modifying existing code.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from ..config import SeedConfig
from ..database import Database


@dataclass
class SeedContext:
    """Everything a seeder is handed: no globals, no hidden state.

    ``registry`` is how seeders hand ids to the seeders that run after them
    (for example, the people seeder publishes ``active_employee_ids``).
    """

    db: Database
    rng: random.Random
    config: SeedConfig
    _registry: dict[str, Any] = field(default_factory=dict)

    def publish(self, key: str, value: Any) -> None:
        if key in self._registry:
            raise KeyError(f"'{key}' was already published")
        self._registry[key] = value

    def require(self, key: str) -> Any:
        if key not in self._registry:
            raise KeyError(f"'{key}' has not been published by an earlier seeder")
        return self._registry[key]

    def has(self, key: str) -> bool:
        return key in self._registry


class Seeder(ABC):
    """Template method: ``run`` checks preconditions, calls ``seed``, then checks the postcondition."""

    name: ClassVar[str]
    tables: ClassVar[tuple[str, ...]]          # tables this seeder is responsible for filling
    requires: ClassVar[tuple[str, ...]] = ()   # registry keys that earlier seeders must publish

    def run(self, ctx: SeedContext) -> None:
        missing = [key for key in self.requires if not ctx.has(key)]
        if missing:
            raise RuntimeError(
                f"Seeder '{self.name}' needs {missing}; register the seeder that publishes them first."
            )
        self.seed(ctx)
        empty = [table for table in self.tables if ctx.db.count_rows(table) == 0]
        if empty:
            raise RuntimeError(f"Seeder '{self.name}' left these tables empty: {empty}")

    @abstractmethod
    def seed(self, ctx: SeedContext) -> None:
        """Insert rows for ``self.tables`` and publish any ids later seeders need."""
