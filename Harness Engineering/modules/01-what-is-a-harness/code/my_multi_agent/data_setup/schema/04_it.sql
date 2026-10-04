-- IT cluster: equipment and employee-facing requests.

-- The catalogue of kinds of equipment. IT owns it; other domains reference category_id,
-- never free text, so that "is this the same kind of thing?" is an exact comparison.
CREATE TABLE asset_categories (
    category_id       INTEGER PRIMARY KEY,
    category_name     TEXT NOT NULL UNIQUE,
    max_per_employee  INTEGER NOT NULL CHECK (max_per_employee > 0)   -- policy as data
);

CREATE TABLE assets (
    asset_id         INTEGER PRIMARY KEY,
    category_id      INTEGER NOT NULL REFERENCES asset_categories(category_id),
    model            TEXT NOT NULL,   -- display only; never used for matching
    serial_no        TEXT NOT NULL UNIQUE,
    assigned_emp_id  INTEGER REFERENCES employees(emp_id),   -- NULL unless assigned
    status           TEXT NOT NULL DEFAULT 'in_stock'
                     CHECK (status IN ('in_stock', 'assigned', 'repair', 'retired')),
    CHECK ((status = 'assigned') = (assigned_emp_id IS NOT NULL))
);

CREATE INDEX idx_assets_assignee ON assets(assigned_emp_id);
CREATE INDEX idx_assets_category ON assets(category_id);

CREATE TABLE it_tickets (
    ticket_id    INTEGER PRIMARY KEY,
    emp_id       INTEGER NOT NULL REFERENCES employees(emp_id),
    category     TEXT NOT NULL CHECK (category IN ('account', 'hardware', 'access')),
    description  TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'closed')),
    created_at   TEXT NOT NULL   -- ISO datetime
);

CREATE INDEX idx_it_tickets_emp ON it_tickets(emp_id);
