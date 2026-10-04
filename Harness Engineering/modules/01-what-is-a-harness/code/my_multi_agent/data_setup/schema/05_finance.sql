-- Finance cluster: what employees spend, the per-claim caps, and the rules that gate approval.

CREATE TABLE expense_limits (
    category    TEXT PRIMARY KEY,   -- travel | meals | equipment | training
    max_amount  REAL NOT NULL CHECK (max_amount > 0)   -- per-claim cap
);

-- Policy is code, not data: the rules that gate a claim live in the Finance tools, not in a table.
-- Only reference values (the caps above, asset_categories.max_per_employee) are stored.

CREATE TABLE expense_claims (
    claim_id           INTEGER PRIMARY KEY,
    emp_id             INTEGER NOT NULL REFERENCES employees(emp_id),
    amount             REAL NOT NULL CHECK (amount > 0),
    category           TEXT NOT NULL REFERENCES expense_limits(category),
    -- Equipment claims name the KIND of asset by catalogue id (never free text);
    -- every other category leaves it NULL.
    asset_category_id  INTEGER REFERENCES asset_categories(category_id),
    description        TEXT,
    status             TEXT NOT NULL DEFAULT 'submitted'
                       CHECK (status IN ('submitted', 'needs_review', 'approved', 'rejected', 'paid')),
    submitted_at       TEXT NOT NULL,   -- ISO datetime
    CHECK ((category = 'equipment') = (asset_category_id IS NOT NULL))
);

CREATE INDEX idx_expense_claims_emp ON expense_claims(emp_id);

-- Audit trail: which rule ran against which claim, and what it found. Starts empty.
-- rule_name is the name of the code-defined rule that was evaluated.
CREATE TABLE claim_checks (
    check_id    INTEGER PRIMARY KEY,
    claim_id    INTEGER NOT NULL REFERENCES expense_claims(claim_id),
    rule_name   TEXT NOT NULL,
    result      TEXT NOT NULL CHECK (result IN ('pass', 'fail', 'pending')),
    details     TEXT,
    checked_at  TEXT NOT NULL   -- ISO datetime
);

CREATE INDEX idx_claim_checks_claim ON claim_checks(claim_id);
