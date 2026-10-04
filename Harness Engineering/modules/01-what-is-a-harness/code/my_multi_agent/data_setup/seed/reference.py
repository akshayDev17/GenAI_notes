"""Reference cluster: states, cities, companies. Runs first; everything else points at these ids."""

from __future__ import annotations

from typing import ClassVar

from .base import Seeder, SeedContext


class ReferenceSeeder(Seeder):
    name = "reference"
    tables = ("states", "cities", "companies")

    # (city, cost_of_living_index). "Springfield" exists in two states on purpose,
    # so name resolution has a real ambiguity to deal with.
    _GEOGRAPHY: ClassVar[dict[str, tuple[tuple[str, float], ...]]] = {
        "California": (("Los Angeles", 150.0), ("San Diego", 145.0), ("San Francisco", 178.0)),
        "Illinois": (("Chicago", 120.0), ("Springfield", 88.0)),
        "Missouri": (("Kansas City", 92.0), ("Springfield", 85.0), ("St. Louis", 90.0)),
        "New York": (("Buffalo", 91.0), ("New York City", 187.0)),
        "Texas": (("Austin", 98.0), ("Dallas", 102.0), ("Houston", 100.0)),
        "Washington": (("Seattle", 152.0), ("Spokane", 94.0)),
    }

    _COMPANIES: ClassVar[tuple[tuple[str, str], ...]] = (
        ("Helix Systems", "Software"),
        ("Meridian Health", "Healthcare"),
        ("Cobalt Logistics", "Logistics"),
        ("Quanta Analytics", "Software"),
        ("Lakeshore Bank", "Finance"),
        ("Summit Retail", "Retail"),
        ("Harborlight Energy", "Energy"),
        ("Redwood Media", "Media"),
        ("Orchard Foods", "Food"),
        ("Pioneer Robotics", "Manufacturing"),
    )

    def seed(self, ctx: SeedContext) -> None:
        state_rows, city_rows = [], []
        city_state: dict[int, int] = {}
        city_index: dict[int, float] = {}

        city_id = 0
        for state_id, state_name in enumerate(sorted(self._GEOGRAPHY), start=1):
            state_rows.append((state_id, state_name))
            for city_name, index in self._GEOGRAPHY[state_name]:
                city_id += 1
                city_rows.append((city_id, city_name, state_id, index))
                city_state[city_id] = state_id
                city_index[city_id] = index

        company_rows = [
            (company_id, name, industry)
            for company_id, (name, industry) in enumerate(self._COMPANIES, start=1)
        ]

        ctx.db.insert_many("states", ("state_id", "state_name"), state_rows)
        ctx.db.insert_many(
            "cities", ("city_id", "city_name", "state_id", "cost_of_living_index"), city_rows
        )
        ctx.db.insert_many("companies", ("company_id", "company_name", "industry"), company_rows)

        ctx.publish("city_ids", [row[0] for row in city_rows])
        ctx.publish("city_state", city_state)
        ctx.publish("city_index", city_index)
        ctx.publish("company_ids", [row[0] for row in company_rows])
