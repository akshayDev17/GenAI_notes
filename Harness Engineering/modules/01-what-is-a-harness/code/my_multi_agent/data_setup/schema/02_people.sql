-- People cluster: employee master data and the pay policy.

CREATE TABLE employees (
    emp_id      INTEGER PRIMARY KEY,
    emp_name    TEXT NOT NULL,
    salary      REAL NOT NULL CHECK (salary > 0),
    state_id    INTEGER NOT NULL REFERENCES states(state_id),
    city_id     INTEGER NOT NULL REFERENCES cities(city_id),
    profession  TEXT NOT NULL,
    company_id  INTEGER NOT NULL REFERENCES companies(company_id),
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'terminated')),
    start_date  TEXT NOT NULL,   -- ISO date
    end_date    TEXT,            -- ISO date; set if and only if terminated
    CHECK ((status = 'terminated') = (end_date IS NOT NULL))
);

CREATE INDEX idx_employees_city       ON employees(city_id);
CREATE INDEX idx_employees_company    ON employees(company_id);
CREATE INDEX idx_employees_profession ON employees(profession);

CREATE TABLE salary_bands (
    profession  TEXT PRIMARY KEY,
    min_salary  REAL NOT NULL,
    max_salary  REAL NOT NULL,
    CHECK (min_salary > 0 AND min_salary <= max_salary)
);
