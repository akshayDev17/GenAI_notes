"""Scheduling cluster: leave balances and requests, rooms and bookings."""

from __future__ import annotations

from datetime import timedelta
from typing import ClassVar

from .base import Seeder, SeedContext
from .common import at_hour, iso_date, iso_datetime, next_workdays, round_to


class SchedulingSeeder(Seeder):
    name = "scheduling"
    tables = ("leave_balances", "leave_requests", "rooms", "room_bookings")
    requires = ("active_employee_ids",)

    _LEAVE_TYPES: ClassVar[tuple[str, ...]] = ("annual", "sick", "personal")
    _LEAVE_MAX_DAYS: ClassVar[dict[str, int]] = {"annual": 20, "sick": 10, "personal": 3}
    _LEAVE_LENGTH: ClassVar[dict[str, int]] = {"annual": 10, "sick": 3, "personal": 2}

    # (room name, capacity, floor)
    _ROOMS: ClassVar[tuple[tuple[str, int, int], ...]] = (
        ("Aspen", 4, 1), ("Birch", 4, 1), ("Cedar", 6, 2), ("Dogwood", 6, 2),
        ("Elm", 8, 2), ("Fir", 8, 3), ("Ginkgo", 10, 3), ("Hazel", 12, 3),
        ("Ivy", 12, 4), ("Juniper", 16, 4), ("Kestrel", 20, 4), ("Linden", 30, 1),
    )

    _BOOKING_DAYS = 10          # bookings fall in the next 10 workdays
    _FIRST_HOUR, _LAST_HOUR = 9, 17

    def seed(self, ctx: SeedContext) -> None:
        active = ctx.require("active_employee_ids")
        self._seed_leave_balances(ctx, active)
        self._seed_leave_requests(ctx, active)
        room_ids = self._seed_rooms(ctx)
        self._seed_room_bookings(ctx, active, room_ids)

    def _seed_leave_balances(self, ctx: SeedContext, active: list[int]) -> None:
        rng = ctx.rng
        out_of_leave = set(rng.sample(active, 3))   # edge case: nothing left to take
        rows = []
        for emp_id in active:
            for leave_type in self._LEAVE_TYPES:
                if leave_type == "annual" and emp_id in out_of_leave:
                    days_left = 0.0
                else:
                    days_left = round_to(rng.uniform(0, self._LEAVE_MAX_DAYS[leave_type]), 0.5)
                rows.append((emp_id, leave_type, days_left))
        ctx.db.insert_many("leave_balances", ("emp_id", "leave_type", "days_left"), rows)

    def _seed_leave_requests(self, ctx: SeedContext, active: list[int]) -> None:
        rng, today = ctx.rng, ctx.config.today
        rows = []
        for request_id in range(1, ctx.config.n_leave_requests + 1):
            leave_type = rng.choices(self._LEAVE_TYPES, [6, 3, 1])[0]
            length = rng.randint(1, self._LEAVE_LENGTH[leave_type])
            start = today + timedelta(days=rng.randint(-120, 90))
            end = start + timedelta(days=length - 1)
            if end < today:
                status = rng.choices(("approved", "cancelled"), [8, 2])[0]
            else:
                status = rng.choices(
                    ("pending", "approved", "rejected", "cancelled"), [50, 35, 10, 5]
                )[0]
            rows.append(
                (request_id, rng.choice(active), leave_type,
                 iso_date(start), iso_date(end), float(length), status)
            )
        ctx.db.insert_many(
            "leave_requests",
            ("request_id", "emp_id", "leave_type", "start_date", "end_date", "days", "status"),
            rows,
        )

    def _seed_rooms(self, ctx: SeedContext) -> list[int]:
        rows = [
            (room_id, name, capacity, floor)
            for room_id, (name, capacity, floor) in enumerate(self._ROOMS, start=1)
        ]
        ctx.db.insert_many("rooms", ("room_id", "room_name", "capacity", "floor"), rows)
        return [row[0] for row in rows]

    def _seed_room_bookings(
        self, ctx: SeedContext, active: list[int], room_ids: list[int]
    ) -> None:
        rng = ctx.rng
        days = next_workdays(ctx.config.today, self._BOOKING_DAYS)
        occupied: set[tuple[int, object, int]] = set()   # (room, day, hour) held by active bookings
        rows: list[tuple] = []

        def add(room_id: int, day, hour: int, hours: int, status: str) -> None:
            start = at_hour(day, hour)
            end = at_hour(day, hour + hours)
            rows.append(
                (len(rows) + 1, room_id, rng.choice(active),
                 iso_datetime(start), iso_datetime(end), status)
            )
            if status == "active":
                for h in range(hour, hour + hours):
                    occupied.add((room_id, day, h))

        def is_free(room_id: int, day, hour: int, hours: int) -> bool:
            return all((room_id, day, h) not in occupied for h in range(hour, hour + hours))

        # Edge case: every room is taken at 10:00 on the first workday, so a search there finds nothing.
        for room_id in room_ids:
            add(room_id, days[0], 10, 1, "active")

        attempts = 0
        while len(rows) < ctx.config.n_bookings and attempts < ctx.config.n_bookings * 20:
            attempts += 1
            room_id, day = rng.choice(room_ids), rng.choice(days)
            hours = rng.choice((1, 1, 2))
            hour = rng.randint(self._FIRST_HOUR, self._LAST_HOUR - hours)
            if is_free(room_id, day, hour, hours):
                add(room_id, day, hour, hours, "active")

        # A few cancelled bookings, which must not block anything.
        cancelled = 0
        while cancelled < 6 and attempts < ctx.config.n_bookings * 40:
            attempts += 1
            room_id, day = rng.choice(room_ids), rng.choice(days)
            hour = rng.randint(self._FIRST_HOUR, self._LAST_HOUR - 1)
            if is_free(room_id, day, hour, 1):
                add(room_id, day, hour, 1, "cancelled")
                cancelled += 1

        ctx.db.insert_many(
            "room_bookings",
            ("booking_id", "room_id", "booked_by", "start_time", "end_time", "status"),
            rows,
        )
