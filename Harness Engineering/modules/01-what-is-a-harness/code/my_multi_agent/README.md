# Operations Desk — a multi-agent system

An internal assistant for a mid-size company. One **orchestrator** receives a request and delegates to four **domain agents**, each of which owns a cluster of tools that share a meaning: people, scheduling, IT, finance. The only key the domains share is `emp_id`.

## Contents

- [Overview](#overview)
- [Architecture at a glance](#architecture-at-a-glance)
- [Agents](#agents)
  - [Orchestrator](#orchestrator)
  - [People agent](#people-agent)
  - [Scheduling agent](#scheduling-agent)
  - [IT agent](#it-agent)
  - [Finance agent](#finance-agent)
- [Cross-agent workflows](#cross-agent-workflows)
- [Why these clusters](#why-these-clusters)
- [Policy as code](#policy-as-code)
  - [Why policy as code](#why-policy-as-code)
  - [What stays as data](#what-stays-as-data)
  - [How it works in this project](#how-it-works-in-this-project)
  - [Conflicts when several developers change policy](#conflicts-when-several-developers-change-policy)
    - [Textual conflicts](#textual-conflicts)
    - [Semantic conflicts](#semantic-conflicts)
    - [Hidden shared dependencies](#hidden-shared-dependencies)
    - [Guarding against conflicts](#guarding-against-conflicts)
  - [Status in this repository](#status-in-this-repository)
- [Data setup layout](#data-setup-layout)
- [Database setup](#database-setup)
- [Open decisions](#open-decisions)

---

## Overview

- **Goal:** a realistic, offline multi-agent system — no internet, no external APIs, everything backed by a local SQLite database.
- **Clustering rule:** tools that share the same entities, vocabulary and policy knowledge belong to one agent. Tools rarely needed together belong to different agents.
- **Wiring:** each domain agent is exposed to the orchestrator as an `AgentTool`, so the orchestrator keeps control of the conversation and receives each result back.
- **Common key:** agents exchange `emp_id` and small facts, never each other's raw tables.

## Architecture at a glance

| Agent | Domain | Tables owned | Reads / writes |
|---|---|---|---|
| Orchestrator | routing, workflows, notifications | `notifications` | writes |
| People | who works here, pay | `employees`, `salary_bands`, `states`, `cities`, `companies` | reads and writes |
| Scheduling | availability and reservations (leave, rooms) | `leave_balances`, `leave_requests`, `rooms`, `room_bookings` | reads and writes |
| IT | equipment and accounts | `asset_categories`, `assets`, `it_tickets` | reads and writes |
| Finance | employee spending | `expense_claims`, `expense_limits`, `claim_checks` | reads and writes |

## Agents

### Orchestrator

- **Purpose**
  - Interpret a request, decide which domains it touches, and combine the answers.
  - Run cross-department workflows (onboarding, offboarding) where each step belongs to a different agent.
  - Run independent steps in parallel; pass `emp_id` between agents.
- **Tools**
  - `notify(emp_id, message)` — append a message to `notifications`; cross-cutting, belongs to no single domain.
  - `current_date()` — resolve relative phrases ("next Monday") instead of letting the model guess.
- **Does not**
  - Touch domain tables directly.
  - Know any domain's policy; it asks the owning agent.

### People agent

- **Purpose**
  - Answer questions about employees and pay; create and terminate employee records.
  - Resolve names to ids (`emp_id`, `city_id`, `state_id`, `company_id`) for the other agents and the orchestrator.
- **Tools**
  - `find_employee(name)` — match by name; return candidates when ambiguous.
  - `get_employee(emp_id)` — profile (name, profession, location, company, status, dates).
  - `salary_stats(group_by, filters)` — count, mean, median, min, max; groups under 3 people are suppressed.
  - `org_headcount(filters)` — headcount by state, city, company or profession.
  - `add_employee(...)` — create a record and return the new `emp_id`.
  - `terminate_employee(emp_id, end_date)` — mark as terminated.
- **Rules**
  - Salary is exposed only through aggregates, never per person (decision to confirm — see [Open decisions](#open-decisions)).
  - A new salary must fall inside the `salary_bands` range for the profession.

### Scheduling agent

- **Purpose**
  - Check availability and reserve a resource over a time range — a person's time (leave) or a room's time (booking).
- **Tools**
  - `check_leave_balance(emp_id)` — days left per leave type.
  - `request_leave(emp_id, start, end, type)` — create a request; refuses if the balance is insufficient.
  - `find_free_room(capacity, start, end)` — rooms that fit and are unbooked for the whole range.
  - `book_room(room_id, start, end, emp_id)` — refuses on overlap with an active booking.
  - `cancel_booking(booking_id)` — mark a booking cancelled.
- **Rules**
  - A booking never overlaps another active booking for the same room.
  - A leave request never exceeds the remaining balance.

### IT agent

- **Purpose**
  - Manage equipment assignment and employee-facing IT requests.
- **Tools**
  - `list_assets(emp_id)` — assets currently assigned to the employee, with their category.
  - `assign_asset(category_id, emp_id)` — pick an in-stock asset of that category and assign it.
  - `reclaim_asset(asset_id)` — return an asset to stock.
  - `open_ticket(emp_id, category, description)` — create a ticket (account, hardware, access).
  - `ticket_status(ticket_id)` — current state of a ticket.
  - Exposed to other domains as a read-only function, not a table: `count_assets_held(emp_id, category_id)`, so Finance depends on an interface instead of IT's tables.
- **Rules**
  - An asset has at most one assignee; assigning an already-assigned asset fails.
  - Kinds of equipment are identified by `category_id` from `asset_categories`; the free-text `model` column is display only and is never used for matching.
  - An employee may hold at most `max_per_employee` active assets of a category (laptop 1, monitor 2, phone 1, headset 1, keyboard 1, standing desk 1).

### Finance agent

- **Purpose**
  - Handle employee expense claims and report spending.
- **Tools**
  - `submit_expense(emp_id, amount, category, description, asset_category_id=None)` — create a claim and evaluate the policy rules (written as code); the outcome is `approved`, `rejected` (with the rule that failed), or `needs_review`. Equipment claims must name an `asset_category_id` from the catalogue.
  - `review_claim(claim_id, decision, note)` — record a manual decision on a claim in `needs_review`, behind a human confirmation in the CLI.
  - `check_expense_limit(category, amount)` — dry-run against the cap and the rules without creating anything.
  - `claim_status(claim_id)` — current state of a claim, including which rules were evaluated.
  - `spend_by_category(filters)` — totals by category, optionally by period or employee.
- **Rules**
  - A claim's category must exist in `expense_limits`; the per-claim cap applies.
  - Policy is code, not data: rules are small classes evaluated inside the Finance tools (see [Policy as code](#policy-as-code)). Seeded examples: equipment claims of 1000 or more must not exceed the asset category's per-employee limit; training claims of 500 or more need manual approval.
  - Every rule evaluation is recorded in `claim_checks`, so any decision traces back to a rule.
  - The check reads the claim's category and amount from the stored claim, not from arguments the model supplied.

## Cross-agent workflows

- **Onboarding** ("Onboard Maya Rao, data engineer in Austin, starting Monday")
  - People: `add_employee` → `emp_id`.
  - IT: `assign_asset` (laptop), `open_ticket` (accounts).
  - Scheduling: `find_free_room` and `book_room` for orientation; `check_leave_balance`.
  - Orchestrator: `notify` the manager with a summary.
- **Offboarding**
  - People: `terminate_employee`.
  - IT: `list_assets` then `reclaim_asset` for each.
  - Scheduling: `cancel_booking` for future bookings.
  - Finance: report open claims.
  - Orchestrator: `notify` a summary.
- **Single-domain questions** go straight to one agent (for example, median pay for data engineers in Texas → People).

## Why these clusters

- **Different vocabularies.** "Limit" is a spending cap in finance, a day count in leave, and a seat count for rooms; "balance" is days in scheduling and money in finance.
- **Different policy knowledge.** Leave accrual, expense caps and asset assignment each need their own rules in the agent's instructions.
- **Smaller tool choice.** Each agent picks among four to six tools instead of about twenty.
- **Rarely co-needed.** Domains meet only at the orchestrator, through `emp_id`.
- **Honest caveat.** With roughly twenty simple tools, a single agent would also work. The split earns its place through vocabulary conflicts, per-domain policies and independent testing, and it gets stronger as the tool count grows.

## Policy as code

Every policy that code can decide from stored data is written as code. The agents do not enforce policy: they coordinate and handle judgment, while the tools that perform an action enforce the rules.

### Why policy as code

- **Scope:** every policy whose condition code can decide from stored data — caps, thresholds, per-employee limits, required checks, status transitions.
  - Policies that need judgment (is this purchase plausible? which category is it?) stay with agents or humans.
  - Code then gates the outcome of that judgment, for example by routing the claim to `needs_review`.
- **Why code:**
  - **Deterministic:** the same input gives the same decision every time, whatever the model does.
  - **Hard guarantee:** the rule runs inside the tool that performs the action, so a model cannot skip or reinterpret it.
  - **Testable:** unit tests per rule, plus a whole-policy table of boundary cases.
  - **Reviewable:** every change is a pull request with history and blame.
  - **Expressive:** one range, many ranges, lists of strings and combinations are ordinary conditions, with no schema to bend.
  - **Auditable:** every evaluation is recorded in `claim_checks` with the rule's name.
- **Alternatives considered and rejected:**
  - **Policy as data** (rules stored in database tables and evaluated by a generic engine)
    - The table's shape must change with every new kind of policy: one threshold, then a range, then several ranges, then lists of strings, then combinations. Each is a schema migration plus engine code.
    - Pushed far enough it becomes a small programming language inside the database (operators, AND/OR grouping, precedence, conflict resolution) with no type checking, debugger or tests for the engine itself. This is the inner-platform effect.
    - Rows edited in a live database bypass code review, so conflicts between rules are not caught in a pull request.
    - Still reasonable for tuning values and entity attributes (see [What stays as data](#what-stays-as-data)). A dedicated policy language (OPA, Cedar, CEL, JSON Logic) is the option to revisit if non-developers must edit policy.
  - **Policy as agent communication** (rules held in agent instructions and enforced by hand-offs between agents, such as a root instruction "equipment claims over 1000 must be checked")
    - Not deterministic: the model may skip a step, reorder steps or apply the rule to the wrong claim, and a weaker model does so more often.
    - Not verifiable: a prompt edit can be sampled but cannot be tested for a guarantee.
    - Duplicated: the rule ends up in several prompts and in tool code, and the copies drift apart.
    - Couples domains through prose: Finance's messages would have to name IT's tools and internals.
    - Agent communication is still used for coordination. A tool error such as "duplicate-asset check required" tells the model what is missing, but the enforcement is the code that raised it.

### What stays as data

- **Attributes of entities:** `asset_categories.max_per_employee` is a property of a catalogue item, not the shape of a policy.
- **Reference values the rules look up:** `expense_limits` caps and `salary_bands`.
- **Tuning values:** thresholds a rule reads by name from configuration.
- **Rule of thumb:** if changing a policy would need a schema change, it should have been code.

### How it works in this project

This is the design for the Finance tools, which are not written yet; see [Status in this repository](#status-in-this-repository).

- **Rules are small, independent classes** (the Specification pattern). Each has a name, a test for whether it applies to a claim, and an evaluation that returns pass, fail or needs-review, with a reason.
- **Self-registering:** a new rule is a new module, so there is no shared list to edit.
- **Order-independent:** every applicable rule must pass; no first-match-wins.
- **Enforced inside the Finance tools** (`submit_expense`, `check_expense_limit`), reading the claim from the stored record and never from arguments the model supplied.
- **Cross-domain facts through an interface:** Finance gets asset holdings from IT's read-only `count_assets_held(emp_id, category_id)`, never from IT's tables.
- **Every evaluation is recorded:** a `claim_checks` row with the rule name, the result and the details.
- **Failures say what is missing**, without naming another agent's tools.
- **Seeded example rules:**
  - equipment claims of 1000 or more must not exceed the asset category's `max_per_employee`;
  - training claims of 500 or more need manual approval.

### Conflicts when several developers change policy

Policy as code has the same conflicts as any collaborative codebase. A rule applies to a set of claims, and two rules conflict when those sets overlap, whether or not their code overlaps. There are three kinds.

#### Textual conflicts

- Git reports them when two developers edit the same lines, most often a shared list or registry:

  ```
  <<<<<<< dev1
  RULES = [P1, P2, P3]
  =======
  RULES = [P1, P2, P4]
  >>>>>>> dev2
  ```

- They are easy to resolve mechanically. Keeping both entries makes the order of the list matter if evaluation is order-dependent.

#### Semantic conflicts

- The merge is clean, each branch's tests pass, and the combined behaviour is wrong.
- Example:
  - Before: p1 sends equipment claims in `[800, 1000)` to the asset check, and p2 sends `[1000, ∞)` to manual approval.
  - dev1 extends p1 to `[800, 1200)`; dev2 lowers p2 to `[900, ∞)`.
  - After the merge, claims in `[900, 1200)` hit both rules. Each developer assumed the other tier had not moved.
- With first-match-wins evaluation, the outcome also depends on rule order, and a rule inserted above another can silently shadow it.
- Rules whose claim sets are disjoint (for example equipment and training) cannot conflict.

#### Hidden shared dependencies

- p1 and p2 both use a shared helper or constant, such as `HIGH_VALUE_THRESHOLD`.
- dev1 changes it for p1's sake, and p2's behaviour moves although no line in p2 changed. Git cannot see this.

#### Guarding against conflicts

- **One rule per module, self-registered**, so there is no shared list to collide on.
- **Order-independent evaluation**, so ordering cannot hide a rule.
- **A whole-policy test on the merged result in CI:** a table of boundary amounts (each boundary, plus or minus a cent) and the rules expected to apply to each. Run it on the merge commit, not only on each branch.
- **A snapshot of that table**, so any change to the policy appears as a diff the reviewer must approve.
- **No shared mutable constants:** give each rule its own parameters, and review shared helpers with their owners.

### Status in this repository

- **Done in the data setup:**
  - the earlier `policy_rules` table and its seeded rows are removed;
  - `claim_checks` records a `rule_name` (the name of the code-defined rule) instead of a `rule_id`;
  - the seeder keeps the two example rules only as constants (`_EXAMPLE_RULES` in `seed/finance.py`) to choose claim statuses consistent with them, and nothing about the policy is stored in the database.
- **Stored as reference data:** `asset_categories.max_per_employee` and the `expense_limits` caps.
- **Not written yet:** the Finance tools and the rule classes themselves. Until they exist, the policy is described only in this README and reflected in the seeded claim statuses.

## Data setup layout

All data creation lives under `data_setup/` and nothing else does:

```
my_multi_agent/
├── agent.py
├── README.md
└── data_setup/
    ├── build_db.py              # CLI entry point
    ├── builder.py               # DatabaseBuilder: schema, then seeders, then integrity check
    ├── config.py                # SeedConfig: seed, "today", row counts (immutable)
    ├── database.py              # Database: connection, pragmas, bulk insert, row counts
    ├── schema_loader.py         # SchemaLoader: applies schema/*.sql in filename order
    ├── schema/                  # DDL only, numbered so foreign keys resolve in order
    │   ├── 01_reference.sql     #   states, cities, companies
    │   ├── 02_people.sql        #   employees, salary_bands
    │   ├── 03_scheduling.sql    #   leave_balances, leave_requests, rooms, room_bookings
    │   ├── 04_it.sql            #   asset_categories, assets, it_tickets
    │   ├── 05_finance.sql       #   expense_limits, expense_claims, claim_checks
    │   └── 06_orchestrator.sql  #   notifications
    ├── seed/
    │   ├── base.py              #   Seeder (abstract) and SeedContext
    │   ├── common.py            #   pure date and rounding helpers
    │   ├── reference.py         #   ReferenceSeeder
    │   ├── people.py            #   PeopleSeeder (also owns the name pools)
    │   ├── scheduling.py        #   SchedulingSeeder
    │   ├── it.py                #   ITSeeder
    │   ├── finance.py           #   FinanceSeeder
    │   └── __init__.py          #   default_seeders(): the ordered registry
    └── generated/
        └── ops.db               # build output; gitignored
```

**Build it** (from the `my_multi_agent` directory): `python -m data_setup.build_db`, with optional `--seed`, `--employees` and `--db`.

**Design**
- **One responsibility per class:** `Database` owns the connection, `SchemaLoader` applies DDL, each `Seeder` fills one cluster, `DatabaseBuilder` orchestrates, `SeedConfig` holds the knobs.
- **Open for extension:** a new cluster is a new `Seeder` subclass, registered in `seed/__init__.py`; no existing class changes. Subclasses are interchangeable behind the `Seeder` interface.
- **Template method:** `Seeder.run` checks that the ids it needs were published, calls the subclass's `seed`, then verifies its tables are non-empty.
- **Dependency injection:** the builder receives its loader, seeders and config instead of constructing them, and seeders share ids through `SeedContext` rather than globals.

**Data guarantees**
- **Deterministic:** the same seed and config give a byte-identical database.
- **Foreign keys on:** every connection runs `PRAGMA foreign_keys = ON`, and the build fails on any violation.
- **Deliberate edge cases:**
  - an ambiguous name (two employees called Priya Shah in different cities) and a city shared by two states (Springfield);
  - salaries exactly on a band edge;
  - an employee with zero annual leave;
  - every room booked at 10:00 on the first workday, plus cancelled bookings that must not block anything;
  - terminated employees who still hold a laptop;
  - employees at their category cap (every laptop holder, and 17 monitor holders with two);
  - expense claims over their category cap, recorded as rejected;
  - laptop claims of 1000 or more from employees who already hold a laptop, recorded as rejected by the asset-limit rule;
  - large standing-desk claims from employees without one, still `submitted`;
  - training claims of 500 or more, some awaiting manual review (`needs_review`).
- **Seeded data follows the example policy:** claim statuses are chosen consistently with the two example rules (equipment claims of 1000 or more run the asset-limit check; training claims of 500 or more need manual approval), so the data can later be evaluated against the same policy without contradiction.
- **Tables left empty on purpose:** `notifications` and `claim_checks` are written by the agents at run time.

## Database setup

How to create the database after cloning or moving this folder to another location or machine.

**Prerequisites**
- Python 3.10 or newer (built and tested on 3.13).
- Nothing to install for the database itself: `data_setup/` uses only the standard library (`sqlite3`, `argparse`, `dataclasses`). The ADK packages are needed only by `agent.py`, not by the setup.

**Steps**
1. Get the folder onto the machine (clone the repo, or copy `my_multi_agent/`).
2. Open a terminal **inside `my_multi_agent/`**, the folder that contains `data_setup/`.
   - This matters: `data_setup` is imported as a package, so the command only resolves from this directory.
   - Running it from the parent folder does not work. The route through `my_multi_agent.data_setup...` would also load `my_multi_agent/__init__.py`, which imports `agent.py` and pulls in ADK and `.env`.
3. Activate whichever Python environment you use (conda, venv, or the system Python).
4. Run:

   ```
   python -m data_setup.build_db
   ```

5. Check the output: a line `Built <path>/data_setup/generated/ops.db`, the list of schema files applied, and a row count per table. The counts for a default build are:
   - `employees` 200, `cities` 15, `rooms` 12, `expense_claims` 80;
   - `notifications` 0, because it starts empty by design.

**Options**

| Flag | Default | Meaning |
|---|---|---|
| `--db PATH` | `data_setup/generated/ops.db` | where to write the database; parent folders are created if missing |
| `--seed N` | `42` | random seed; the same seed always gives the identical database |
| `--employees N` | `200` | number of employees |

Examples:

```
python -m data_setup.build_db --db /some/other/place/ops.db
python -m data_setup.build_db --seed 7 --employees 500
```

**Behavior to know about**
- **Always a rebuild:** the target file is deleted first, then recreated from the schema and seeders. Running it again is safe and gives a fresh database. Data written by the agents (notifications, new bookings and so on) is lost on a rebuild.
- **Ids always start at 1:** because the file is recreated, every primary key restarts from 1 on each build. Stop anything that has `ops.db` open (such as a running agent) before rebuilding. ADK's own `session.db` is a separate file and is not touched.
- **Reproducible:** with the same seed and settings, two machines produce byte-identical databases. The "today" date used for relative data is fixed in `data_setup/config.py` (`SeedConfig.today`); change it there if you want the data to centre on a different date.
- **Not committed:** `data_setup/generated/` is in `.gitignore`, so a fresh clone has no database until you run the command.
- **Failing loudly:** the build raises an error if any foreign key is violated or a seeder leaves one of its tables empty.

**Quick sanity check** (needs the `sqlite3` command-line tool, or any SQLite viewer):

```
sqlite3 data_setup/generated/ops.db "SELECT COUNT(*) FROM employees;"
```

**When the agents start using it**
- The default path is defined once, as `DEFAULT_DB_PATH` in `data_setup/build_db.py`. When the agent tools open the database, point them at the same location (or the path you passed to `--db`) from a single shared place, not a path copied into each tool.

## Open decisions

- **Salary visibility:** aggregates only, or per-employee salary for authorized requests too?
- **One database or one per domain:** a single `ops.db` is simpler; separate files per agent make the independence explicit.
- **Approvals:** whether leave requests need a human confirmation step in the CLI before they are applied. (For expense claims, the `needs_review` status and `review_claim` tool already cover it.)
- **Policy as data versus policy as code:** decided in favour of code; see [Policy as code](#policy-as-code). Revisit with a dedicated policy language (OPA, Cedar, CEL, JSON Logic) only if non-developers need to edit policy.
- **Where checks run:** policy is evaluated when a claim is submitted. A separate approval step for every claim is deliberately not modelled; only `needs_review` claims wait for a decision.
