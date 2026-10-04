"""Finance cluster: per-claim caps, policy rules and expense claims."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import timedelta
from typing import ClassVar

from .base import Seeder, SeedContext
from .common import at_hour, iso_datetime


@dataclass
class _Claim:
    emp_id: int
    category: str
    asset_category_id: int | None
    amount: float
    status: str


@dataclass(frozen=True)
class _ExampleRule:
    """An example of the policy, used only to pick claim statuses consistent with it.

    The policy itself is code in the Finance tools; nothing here is stored in the database.
    """

    category: str
    min_amount: float
    max_amount: float | None        # exclusive; None means no upper bound
    check: str

    def applies(self, category: str, amount: float) -> bool:
        return (
            self.category == category
            and amount >= self.min_amount
            and (self.max_amount is None or amount < self.max_amount)
        )


class FinanceSeeder(Seeder):
    name = "finance"
    tables = ("expense_limits", "expense_claims")
    requires = ("active_employee_ids", "asset_categories", "asset_holdings")

    _LIMITS: ClassVar[dict[str, float]] = {
        "travel": 1500.0,
        "meals": 150.0,
        "equipment": 2000.0,
        "training": 1000.0,
    }

    # Example policy, used only to choose statuses for the seeded claims, so the data is
    # consistent with the policy it will later be evaluated against:
    #   - equipment claims of 1000 or more must not exceed the asset category's per-employee limit;
    #   - training claims of 500 or more need a manual approval.
    _EXAMPLE_RULES: ClassVar[tuple[_ExampleRule, ...]] = (
        _ExampleRule("equipment", 1000.0, None, "asset_limit_check"),
        _ExampleRule("training", 500.0, None, "manual_approval"),
    )

    _DESCRIPTIONS: ClassVar[dict[str, tuple[str, ...]]] = {
        "travel": ("Flight to client site", "Train tickets for the offsite", "Hotel for two nights"),
        "meals": ("Team lunch", "Client dinner", "Working breakfast"),
        "equipment": ("Equipment purchase",),
        "training": ("Conference registration", "Online course subscription", "Certification exam fee"),
    }

    # Typical price range per kind of equipment, so amounts look plausible.
    _EQUIPMENT_PRICE: ClassVar[dict[str, tuple[float, float]]] = {
        "laptop": (900.0, 1900.0),
        "monitor": (150.0, 600.0),
        "phone": (400.0, 1100.0),
        "headset": (60.0, 300.0),
        "keyboard": (40.0, 200.0),
        "standing_desk": (300.0, 900.0),
    }

    _OVER_LIMIT_CLAIMS = 3        # above the category cap, recorded as rejected
    _DUPLICATE_CLAIMS = 3         # laptop claims from employees who already hold one
    _PENDING_CHECK_CLAIMS = 3     # large standing-desk claims awaiting a check

    def seed(self, ctx: SeedContext) -> None:
        ctx.db.insert_many(
            "expense_limits", ("category", "max_amount"), list(self._LIMITS.items())
        )
        self._seed_claims(ctx)

    def _seed_claims(self, ctx: SeedContext) -> None:
        rng, cfg = ctx.rng, ctx.config
        active: list[int] = ctx.require("active_employee_ids")
        catalogue: dict[int, tuple[str, int]] = ctx.require("asset_categories")
        holdings: dict[int, dict[int, int]] = ctx.require("asset_holdings")

        id_by_name = {name: cid for cid, (name, _) in catalogue.items()}
        equipment_ids = sorted(catalogue)

        edge_claims = self._edge_case_claims(ctx, active, id_by_name, holdings)

        random_claims: list[_Claim] = []
        while len(edge_claims) + len(random_claims) < cfg.n_expense_claims:
            category = rng.choice(list(self._LIMITS))
            asset_category_id = rng.choice(equipment_ids) if category == "equipment" else None
            amount = self._plausible_amount(rng, category, asset_category_id, catalogue)
            emp_id = rng.choice(active)
            status = self._decide_status(
                rng, emp_id, category, amount, asset_category_id, catalogue, holdings
            )
            random_claims.append(_Claim(emp_id, category, asset_category_id, amount, status))

        # Some claims are above their category cap; those are rejected whatever else is true.
        # Only random claims are touched, so the deliberate edge cases above stay as designed.
        for claim in rng.sample(random_claims, self._OVER_LIMIT_CLAIMS):
            cap = self._LIMITS[claim.category]
            claim.amount = round(cap * rng.uniform(1.1, 1.6), 2)
            claim.status = "rejected"

        claims = edge_claims + random_claims
        rng.shuffle(claims)

        rows = []
        for claim_id, claim in enumerate(claims, start=1):
            submitted = at_hour(
                cfg.today - timedelta(days=rng.randint(0, 90)),
                rng.randint(8, 18),
                rng.randint(0, 59),
            )
            rows.append(
                (
                    claim_id,
                    claim.emp_id,
                    claim.amount,
                    claim.category,
                    claim.asset_category_id,
                    rng.choice(self._DESCRIPTIONS[claim.category]),
                    claim.status,
                    iso_datetime(submitted),
                )
            )
        ctx.db.insert_many(
            "expense_claims",
            (
                "claim_id", "emp_id", "amount", "category", "asset_category_id",
                "description", "status", "submitted_at",
            ),
            rows,
        )

    def _edge_case_claims(
        self,
        ctx: SeedContext,
        active: list[int],
        id_by_name: dict[str, int],
        holdings: dict[int, dict[int, int]],
    ) -> list[_Claim]:
        rng = ctx.rng
        laptop, desk = id_by_name["laptop"], id_by_name["standing_desk"]
        claims: list[_Claim] = []

        # A second laptop for someone who already holds one: the asset-limit rule must reject it.
        holders = [e for e in active if holdings.get(e, {}).get(laptop, 0) >= 1]
        for emp_id in rng.sample(holders, self._DUPLICATE_CLAIMS):
            claims.append(
                _Claim(emp_id, "equipment", laptop, round(rng.uniform(1000, 1900), 2), "rejected")
            )

        # A large standing-desk claim from someone without one: allowed, still awaiting a decision.
        without = [e for e in active if holdings.get(e, {}).get(desk, 0) == 0]
        for emp_id in rng.sample(without, self._PENDING_CHECK_CLAIMS):
            claims.append(
                _Claim(emp_id, "equipment", desk, round(rng.uniform(1000, 1500), 2), "submitted")
            )
        return claims

    def _plausible_amount(
        self,
        rng: random.Random,
        category: str,
        asset_category_id: int | None,
        catalogue: dict[int, tuple[str, int]],
    ) -> float:
        cap = self._LIMITS[category]
        if asset_category_id is None:
            return round(rng.uniform(15.0, cap * 0.95), 2)
        low, high = self._EQUIPMENT_PRICE[catalogue[asset_category_id][0]]
        return round(rng.uniform(low, min(high, cap * 0.95)), 2)

    def _decide_status(
        self,
        rng: random.Random,
        emp_id: int,
        category: str,
        amount: float,
        asset_category_id: int | None,
        catalogue: dict[int, tuple[str, int]],
        holdings: dict[int, dict[int, int]],
    ) -> str:
        """Pick a status that is consistent with the example policy."""
        needs_manual = False
        for rule in self._EXAMPLE_RULES:
            if not rule.applies(category, amount):
                continue
            if rule.check == "asset_limit_check" and asset_category_id is not None:
                _, limit = catalogue[asset_category_id]
                if holdings.get(emp_id, {}).get(asset_category_id, 0) >= limit:
                    return "rejected"
            elif rule.check == "manual_approval":
                needs_manual = True

        if needs_manual:
            return rng.choices(("needs_review", "approved", "paid"), [3, 4, 3])[0]
        return rng.choices(("submitted", "approved", "paid", "rejected"), [30, 25, 40, 5])[0]
