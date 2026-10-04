-- Shared lookup tables. Everything else points at these ids, so this file runs first.

CREATE TABLE states (
    state_id    INTEGER PRIMARY KEY,
    state_name  TEXT NOT NULL UNIQUE
);

CREATE TABLE cities (
    city_id               INTEGER PRIMARY KEY,
    city_name             TEXT NOT NULL,
    state_id              INTEGER NOT NULL REFERENCES states(state_id),
    cost_of_living_index  REAL NOT NULL CHECK (cost_of_living_index > 0),  -- 100 = baseline
    UNIQUE (city_name, state_id)
);

CREATE TABLE companies (
    company_id    INTEGER PRIMARY KEY,
    company_name  TEXT NOT NULL UNIQUE,
    industry      TEXT NOT NULL
);
