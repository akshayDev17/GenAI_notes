-- Scheduling cluster: reservations of a person's time (leave) and a room's time (bookings).

CREATE TABLE leave_balances (
    emp_id      INTEGER NOT NULL REFERENCES employees(emp_id),
    leave_type  TEXT NOT NULL CHECK (leave_type IN ('annual', 'sick', 'personal')),
    days_left   REAL NOT NULL CHECK (days_left >= 0),
    PRIMARY KEY (emp_id, leave_type)
);

CREATE TABLE leave_requests (
    request_id  INTEGER PRIMARY KEY,
    emp_id      INTEGER NOT NULL REFERENCES employees(emp_id),
    leave_type  TEXT NOT NULL CHECK (leave_type IN ('annual', 'sick', 'personal')),
    start_date  TEXT NOT NULL,   -- ISO date
    end_date    TEXT NOT NULL,   -- ISO date, inclusive
    days        REAL NOT NULL CHECK (days > 0),
    status      TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected', 'cancelled')),
    CHECK (end_date >= start_date)
);

CREATE INDEX idx_leave_requests_emp ON leave_requests(emp_id);

CREATE TABLE rooms (
    room_id    INTEGER PRIMARY KEY,
    room_name  TEXT NOT NULL UNIQUE,
    capacity   INTEGER NOT NULL CHECK (capacity > 0),
    floor      INTEGER NOT NULL
);

CREATE TABLE room_bookings (
    booking_id  INTEGER PRIMARY KEY,
    room_id     INTEGER NOT NULL REFERENCES rooms(room_id),
    booked_by   INTEGER NOT NULL REFERENCES employees(emp_id),
    start_time  TEXT NOT NULL,   -- ISO datetime, minute precision
    end_time    TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'cancelled')),
    CHECK (end_time > start_time)
);

CREATE INDEX idx_room_bookings_room_time ON room_bookings(room_id, start_time);
