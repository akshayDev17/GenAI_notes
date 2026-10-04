"""Seeder registry. To add a cluster, write a ``Seeder`` subclass and list it here, in dependency order."""

from __future__ import annotations

from .base import Seeder, SeedContext
from .finance import FinanceSeeder
from .it import ITSeeder
from .people import PeopleSeeder
from .reference import ReferenceSeeder
from .scheduling import SchedulingSeeder


def default_seeders() -> list[Seeder]:
    return [
        ReferenceSeeder(),
        PeopleSeeder(),
        SchedulingSeeder(),
        ITSeeder(),
        FinanceSeeder(),
    ]


__all__ = ["Seeder", "SeedContext", "default_seeders"]
