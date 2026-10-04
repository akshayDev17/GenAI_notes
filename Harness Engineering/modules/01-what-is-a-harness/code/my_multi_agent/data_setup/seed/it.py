"""IT cluster: the asset catalogue, assets and tickets."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from .base import Seeder, SeedContext
from .common import at_hour, iso_datetime


@dataclass(frozen=True)
class _CategorySpec:
    """One kind of equipment: how it is identified, limited and handed out."""

    name: str
    prefix: str                       # serial-number prefix
    max_per_employee: int
    holder_share: float               # share of active employees who hold at least one
    models: tuple[str, ...]           # display text only
    default_in_stock: int = 5
    second_unit_share: float = 0.0    # share of holders who hold a second unit (needs a cap >= 2)
    held_by_terminated: int = 0       # units still held by terminated employees (offboarding edge case)


class ITSeeder(Seeder):
    name = "it"
    tables = ("asset_categories", "assets", "it_tickets")
    requires = ("active_employee_ids", "terminated_employee_ids")

    _CATEGORIES: ClassVar[tuple[_CategorySpec, ...]] = (
        _CategorySpec("laptop", "LT", 1, 0.95, ("Atlas 14", "Orbit Air 13", "Vertex L5"),
                      held_by_terminated=3),
        _CategorySpec("monitor", "MN", 2, 0.60, ("ClearView 27", "PixelWide 24"),
                      second_unit_share=0.15),
        _CategorySpec("phone", "PH", 1, 0.40, ("Nimbus 8", "Halo S")),
        _CategorySpec("headset", "HS", 1, 0.50, ("EchoPro 65", "QuietVoice 4")),
        _CategorySpec("keyboard", "KB", 1, 0.50, ("TypeMaster K8", "ErgoSlim")),
        _CategorySpec("standing_desk", "SD", 1, 0.15, ("RiseUp E7", "LiftLine V2")),
    )
    _IN_REPAIR = 2
    _RETIRED = 1

    _TICKET_TEMPLATES: ClassVar[dict[str, tuple[str, ...]]] = {
        "account": (
            "Cannot log in to my account",
            "Password reset requested",
            "Two-factor codes are not arriving",
        ),
        "hardware": (
            "Laptop battery drains within an hour",
            "External monitor shows no signal",
            "Keyboard has stopped responding",
        ),
        "access": (
            "Need access to the shared finance drive",
            "Request access to the staging environment",
            "Cannot open the team wiki",
        ),
    }

    def seed(self, ctx: SeedContext) -> None:
        active = ctx.require("active_employee_ids")
        terminated = ctx.require("terminated_employee_ids")
        category_ids = self._seed_categories(ctx)
        self._seed_assets(ctx, category_ids, active, terminated)
        self._seed_tickets(ctx, active)

    def _seed_categories(self, ctx: SeedContext) -> dict[str, int]:
        ids = {spec.name: number for number, spec in enumerate(self._CATEGORIES, start=1)}
        ctx.db.insert_many(
            "asset_categories",
            ("category_id", "category_name", "max_per_employee"),
            [(ids[spec.name], spec.name, spec.max_per_employee) for spec in self._CATEGORIES],
        )
        # Finance needs the catalogue (to name equipment claims) and today's holdings (to decide
        # outcomes consistently with the asset-limit rule).
        ctx.publish(
            "asset_categories",
            {ids[spec.name]: (spec.name, spec.max_per_employee) for spec in self._CATEGORIES},
        )
        return ids

    def _seed_assets(
        self,
        ctx: SeedContext,
        category_ids: dict[str, int],
        active: list[int],
        terminated: list[int],
    ) -> None:
        rng, cfg = ctx.rng, ctx.config
        in_stock_override = {
            "laptop": cfg.laptops_in_stock,
            "monitor": cfg.monitors_in_stock,
            "phone": cfg.phones_in_stock,
        }

        rows: list[tuple] = []
        holdings: dict[int, dict[int, int]] = defaultdict(lambda: defaultdict(int))

        for spec in self._CATEGORIES:
            category_id = category_ids[spec.name]

            holders = rng.sample(active, round(len(active) * spec.holder_share))
            units = list(holders)
            if spec.max_per_employee >= 2 and spec.second_unit_share:
                units += rng.sample(holders, round(len(holders) * spec.second_unit_share))
            if spec.held_by_terminated:
                units += rng.sample(terminated, min(spec.held_by_terminated, len(terminated)))

            for emp_id in units:
                holdings[emp_id][category_id] += 1

            # Each entry is (assigned_emp_id, status); serials are numbered per category below.
            states = [(emp_id, "assigned") for emp_id in units]
            states += [(None, "in_stock")] * in_stock_override.get(spec.name, spec.default_in_stock)
            states += [(None, "repair")] * self._IN_REPAIR
            states += [(None, "retired")] * self._RETIRED

            for number, (emp_id, status) in enumerate(states, start=1):
                rows.append(
                    (
                        len(rows) + 1,
                        category_id,
                        rng.choice(spec.models),
                        f"{spec.prefix}-{number:05d}",
                        emp_id,
                        status,
                    )
                )

        ctx.db.insert_many(
            "assets",
            ("asset_id", "category_id", "model", "serial_no", "assigned_emp_id", "status"),
            rows,
        )
        ctx.publish("asset_holdings", {emp: dict(per_cat) for emp, per_cat in holdings.items()})

    def _seed_tickets(self, ctx: SeedContext, active: list[int]) -> None:
        rng, cfg = ctx.rng, ctx.config
        categories = list(self._TICKET_TEMPLATES)
        rows = []
        for ticket_id in range(1, cfg.n_tickets + 1):
            category = rng.choices(categories, [4, 3, 3])[0]
            created = at_hour(
                cfg.today - timedelta(days=rng.randint(0, 60)),
                rng.randint(8, 18),
                rng.randint(0, 59),
            )
            rows.append(
                (
                    ticket_id,
                    rng.choice(active),
                    category,
                    rng.choice(self._TICKET_TEMPLATES[category]),
                    rng.choices(("open", "in_progress", "closed"), [12, 8, 10])[0],
                    iso_datetime(created),
                )
            )
        ctx.db.insert_many(
            "it_tickets",
            ("ticket_id", "emp_id", "category", "description", "status", "created_at"),
            rows,
        )
