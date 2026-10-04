-- Orchestrator cluster: the cross-cutting notify() tool writes here. Starts empty.

CREATE TABLE notifications (
    notification_id  INTEGER PRIMARY KEY,
    emp_id           INTEGER NOT NULL REFERENCES employees(emp_id),
    message          TEXT NOT NULL,
    created_at       TEXT NOT NULL   -- ISO datetime
);
