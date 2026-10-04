"""Tunable knobs for data generation, kept in one immutable value object."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SeedConfig:
    # Same seed + same config -> byte-identical database.
    seed: int = 42

    # "Today" is fixed so relative dates (leave, bookings, tickets) are reproducible.
    today: date = date(2026, 10, 3)

    # People
    n_employees: int = 200
    n_terminated: int = 8

    # Scheduling
    n_leave_requests: int = 60
    n_bookings: int = 80

    # IT
    laptops_in_stock: int = 30
    monitors_in_stock: int = 25
    phones_in_stock: int = 10
    n_tickets: int = 30

    # Finance
    n_expense_claims: int = 80
