"""People cluster: salary bands and employees."""

from __future__ import annotations

from dataclasses import astuple, dataclass
from datetime import timedelta
from typing import ClassVar

from .base import Seeder, SeedContext
from .common import iso_date, round_to


@dataclass
class _Employee:
    emp_id: int
    emp_name: str
    salary: float
    state_id: int
    city_id: int
    profession: str
    company_id: int
    status: str
    start_date: str
    end_date: str | None


class PeopleSeeder(Seeder):
    name = "people"
    tables = ("salary_bands", "employees")
    requires = ("city_ids", "city_state", "city_index", "company_ids")

    # profession -> (min_salary, max_salary, hiring weight)
    _BANDS: ClassVar[dict[str, tuple[int, int, float]]] = {
        "Software Engineer": (85_000, 160_000, 4.0),
        "Data Engineer": (90_000, 165_000, 2.5),
        "Data Scientist": (95_000, 170_000, 2.0),
        "Product Manager": (100_000, 175_000, 1.5),
        "Designer": (70_000, 130_000, 1.0),
        "HR Specialist": (55_000, 95_000, 1.0),
        "Accountant": (60_000, 105_000, 1.0),
        "Sales Representative": (50_000, 110_000, 2.0),
        "IT Support Specialist": (50_000, 90_000, 1.5),
        "Operations Manager": (80_000, 140_000, 1.0),
    }

    _FIRST_NAMES: ClassVar[tuple[str, ...]] = (
        "Aarav", "Ana", "Ben", "Carla", "Dev", "Elena", "Farid", "Grace", "Hiro", "Isabel",
        "Jamal", "Kavya", "Liam", "Mei", "Noah", "Olivia", "Priya", "Quinn", "Rohan", "Sara",
        "Tomas", "Uma", "Victor", "Wen", "Xavier", "Yara", "Zane", "Amira", "Bruno", "Chloe",
        "Daniel", "Emma", "Felix", "Gita", "Hassan", "Ines", "Jonas", "Keiko", "Leila", "Marco",
    )
    _LAST_NAMES: ClassVar[tuple[str, ...]] = (
        "Patel", "Nguyen", "Garcia", "Kim", "Okafor", "Silva", "Cohen", "Ito", "Novak", "Shah",
        "Mehta", "Rossi", "Haddad", "Larsen", "Reyes", "Chen", "Dubois", "Ivanov", "Khan", "Lopez",
        "Murphy", "Nair", "Ortiz", "Petrov", "Quinn", "Rao", "Santos", "Tanaka", "Usman", "Varga",
        "Walker", "Xu", "Yilmaz", "Zhang", "Adams", "Brooks", "Carter", "Diaz", "Evans", "Foster",
    )

    # Names the other parts of the system rely on. "Maya Rao" is the new hire in the onboarding
    # example, so she must not already exist; "Priya Shah" is the deliberate duplicate.
    _RESERVED_NAMES: ClassVar[frozenset[str]] = frozenset({"Maya Rao", "Priya Shah"})
    _DUPLICATE_NAME: ClassVar[str] = "Priya Shah"

    def seed(self, ctx: SeedContext) -> None:
        self._seed_salary_bands(ctx)
        employees = self._build_employees(ctx)
        self._apply_edge_cases(ctx, employees)

        ctx.db.insert_many(
            "employees",
            (
                "emp_id", "emp_name", "salary", "state_id", "city_id",
                "profession", "company_id", "status", "start_date", "end_date",
            ),
            [astuple(employee) for employee in employees],
        )

        ctx.publish("employee_ids", [e.emp_id for e in employees])
        ctx.publish("active_employee_ids", [e.emp_id for e in employees if e.status == "active"])
        ctx.publish(
            "terminated_employee_ids", [e.emp_id for e in employees if e.status == "terminated"]
        )

    def _seed_salary_bands(self, ctx: SeedContext) -> None:
        rows = [(prof, low, high) for prof, (low, high, _) in self._BANDS.items()]
        ctx.db.insert_many("salary_bands", ("profession", "min_salary", "max_salary"), rows)

    def _build_employees(self, ctx: SeedContext) -> list[_Employee]:
        rng, cfg = ctx.rng, ctx.config
        city_ids = ctx.require("city_ids")
        city_state = ctx.require("city_state")
        city_index = ctx.require("city_index")
        company_ids = ctx.require("company_ids")

        professions = list(self._BANDS)
        weights = [self._BANDS[p][2] for p in professions]
        names = self._unique_names(ctx, cfg.n_employees)
        terminated = set(rng.sample(range(1, cfg.n_employees + 1), cfg.n_terminated))

        employees = []
        for emp_id in range(1, cfg.n_employees + 1):
            profession = rng.choices(professions, weights)[0]
            low, high, _ = self._BANDS[profession]
            city_id = rng.choice(city_ids)

            # Pay drifts up with the local cost of living, but never leaves the band.
            raw = rng.triangular(low, high, (low + high) / 2)
            raw *= 1 + (city_index[city_id] - 100) / 100 * 0.15
            salary = min(max(round_to(raw, 500), low), high)

            if emp_id in terminated:
                start = cfg.today - timedelta(days=rng.randint(400, 3000))
                end = cfg.today - timedelta(days=rng.randint(10, 180))
                status, end_date = "terminated", iso_date(end)
            else:
                start = cfg.today - timedelta(days=rng.randint(30, 3000))
                status, end_date = "active", None

            employees.append(
                _Employee(
                    emp_id=emp_id,
                    emp_name=names[emp_id - 1],
                    salary=float(salary),
                    state_id=city_state[city_id],   # state always agrees with the city
                    city_id=city_id,
                    profession=profession,
                    company_id=rng.choice(company_ids),
                    status=status,
                    start_date=iso_date(start),
                    end_date=end_date,
                )
            )
        return employees

    def _unique_names(self, ctx: SeedContext, count: int) -> list[str]:
        rng = ctx.rng
        names: list[str] = []
        seen = set(self._RESERVED_NAMES)
        while len(names) < count:
            candidate = f"{rng.choice(self._FIRST_NAMES)} {rng.choice(self._LAST_NAMES)}"
            if candidate not in seen:
                seen.add(candidate)
                names.append(candidate)
        return names

    def _apply_edge_cases(self, ctx: SeedContext, employees: list[_Employee]) -> None:
        """Rows that tools and agents need to be tested against."""
        rng = ctx.rng

        # Two different people with the same name, in different cities.
        first, second = employees[len(employees) // 8], employees[(5 * len(employees)) // 8]
        first.emp_name = second.emp_name = self._DUPLICATE_NAME
        if second.city_id == first.city_id:
            other_city = next(c for c in ctx.require("city_ids") if c != first.city_id)
            second.city_id = other_city
            second.state_id = ctx.require("city_state")[other_city]

        # A few salaries sitting exactly on a band edge.
        active = [e for e in employees if e.status == "active" and e is not first and e is not second]
        for employee in rng.sample(active, 3):
            employee.salary = float(self._BANDS[employee.profession][1])
        for employee in rng.sample([e for e in active if e.salary > self._BANDS[e.profession][0]], 2):
            employee.salary = float(self._BANDS[employee.profession][0])
