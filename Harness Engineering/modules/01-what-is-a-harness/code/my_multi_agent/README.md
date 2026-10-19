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
- [Session state](#session-state)
  - [How state works in ADK](#how-state-works-in-adk)
    - [Scopes](#scopes)
    - [Writing and reading](#writing-and-reading)
    - [Setting values at config time](#setting-values-at-config-time)
    - [Who sees the conversation history](#who-sees-the-conversation-history)
  - [What qualifies as state here](#what-qualifies-as-state-here)
  - [All state variables at a glance](#all-state-variables-at-a-glance)
  - [Deferred until the tools change](#deferred-until-the-tools-change)
  - [State considered and rejected](#state-considered-and-rejected)
  - [Tensions to resolve](#tensions-to-resolve)
- [Data setup layout](#data-setup-layout)
- [Database setup](#database-setup)
- [Closed decisions](#closed-decisions)
- [Open decisions](#open-decisions)

---

## Overview

- **Goal:** a realistic, offline multi-agent system — no internet, no external APIs, everything backed by a local SQLite database.
- **Clustering rule:** tools that share the same entities, vocabulary and policy knowledge belong to one agent. Tools rarely needed together belong to different agents.
- **Wiring:** each domain agent is exposed to the orchestrator as an `AgentTool`, so the orchestrator keeps control of the conversation and receives each result back.
- **Common key:** agents exchange `emp_id` and small facts, never each other's raw tables.
- **Session state:** eleven small variables carry context the agents would otherwise lose: three are set when a session starts, and eight are written while the conversation runs. Each is defined in full where it is first used in the agent sections below, and summarised in [Session state](#session-state).
- **Tool conventions:**
  - Arguments are flat and typed; there are no free-form filter dicts.
  - Fixed sets are enums, with each value's meaning in the tool description.
  - Names are accepted and resolved by the owning agent; an ambiguous name comes back as `needs_clarification`.
  - List tools return one page at a time ([page size](#state-page_size)) and report the total.
  - Wherever a tool needs an id, a `list_*` tool exists to find one.
  - Facts the system cannot know (a date, a reason, a salary) are never defaulted. Such an argument is optional in the signature so the model does not invent a value, and when it is missing the tool returns `needs_input` naming what is missing.
  - The `needs_input` response is a fixed shape: `status`, `missing` (the argument names), `collected` (what is already known, ids included), and a `message` that names each missing field in plain words, lists the allowed values for an enum, and tells the agent to ask the user and not to guess. The call is not performed.

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
- **State**
  - <a id="state-workflow_progress"></a>**State variable `workflow_progress`** (written by tools while the conversation runs)
    - **What it is for:** records how far a multi-step request (onboarding, offboarding) has got: `{workflow, emp_id, steps: {people, it, scheduling, ...}}`, where each step is `done`, `failed` (with the reason), `waiting for input` or `not started`. It also says which request and which person.
    - **Written by:** an `after_agent_callback` on each domain agent, which is harness code, not a tool. **Read by:** the orchestrator's instruction.
    - **Chat example:**
      ```text
      User:   Onboard Maya Rao, data engineer in Austin, starting Monday 12 October.
      Agent:  I still need her salary and her company.                      (People paused: needs input)
      User:   $118,000, Helix Systems.
      Agent:  Maya Rao is added (emp 201) and has a laptop. I could not book the
              orientation room: nothing is free on Monday at 10:00.          (Scheduling failed)
      User:   Try Tuesday at 10.
      Agent:  Booked Elm for Tuesday 10:00-11:00 and told her manager.       (only the room step ran again)
      ```
    - **Why state:** it makes a partly finished request resumable and records a pause as a pause, not a failure. The orchestrator does not create a second employee, because the record shows People and IT are done.
    - **Risk:** among the weakest in value, because the orchestrator also sees each result in its own conversation. State adds exactness and survives history trimming. Tools must still be safe to retry, since state is not a transaction log.

### People agent

- **Purpose**
  - Answer questions about employees and pay; create and terminate employee records.
  - Resolve names to ids (`emp_id`, `city_id`, `state_id`, `company_id`) for the other agents and the orchestrator.
- **Tools**
  - `find_employee(name)` — match by name; return candidates when ambiguous.
    - <a id="state-page_size"></a>**State variable `page_size`** (config-time: set when the session is created; the model never writes it)
      - **What it is for:** the number of rows a list tool returns per call (an integer such as 10). Larger results are cut to one page and the total is reported.
      - **Written by:** session setup. **Read by:** every tool that returns rows: `find_employee`, `list_leave_requests`, `list_assets`, `list_tickets`, `list_claims`.
      - **Chat example:**
        ```text
        User:   Find everyone called Garcia.
        Agent:  Showing 10 of 14 people named Garcia: ... To narrow it down, give me
                a company, a city or a profession.

        User:   Who is requesting leave?
        Agent:  Showing 10 of 23 pending requests ...   (the total is always reported)
        ```
      - **Why state:** it can differ per session, so a test can run with a page size of 2 and exercise truncation without touching any tool code.
      - **Risk:** the tool result must say "showing 10 of 14"; otherwise the model assumes the list is complete. The signatures have no offset, so the rest of a truncated list is reached by narrowing with the existing filters, not by paging.
    - <a id="state-focus_employee"></a>**State variable `focus_employee`** (written by tools while the conversation runs)
      - **What it is for:** the employee the conversation is about, `{emp_id, name}`, so "her", "him" or "that person" resolves without another lookup.
      - **Written by:** `find_employee` (when the match is unique), `get_employee` and `add_employee`. **Read by:** instructions, so the model can fill an `emp_id` argument.
      - **Chat example:**
        ```text
        User:   Find Maya Rao.
        Agent:  Maya Rao, emp 201, Data Engineer at Helix Systems, Austin.
        User:   What's her salary?
        Agent:  $118,000.                                     (emp 201 taken from the focus, no second lookup)
        User:   Give her a headset.
        Agent:  Assigned headset HS-00004 to Maya Rao.
        ```
      - **Why state:** it pins the identity after disambiguation. Name lookups can be ambiguous (two employees are called Priya Shah), so re-resolving a name is both slow and risky.
      - **Risk:** stale when the user changes subject. It is overwritten on each new unique resolution, and "her" must be checked against it.
  - `get_employee(emp_id)` — profile (name, salary, profession, location, company, status, dates).
    - **State:** writes [`focus_employee`](#state-focus_employee).
  - `salary_stats(group_by=None, profession=None, state=None, city=None, company=None, status="active")` — count, mean, median, min and max per group.
    - `group_by` is one of `profession`, `state`, `city`, `company`, or none for a single overall result.
    - The filters take names; the tool resolves them to ids, and an ambiguous city comes back as `needs_clarification`.
    - <a id="state-pending_clarification"></a>**State variable `pending_clarification`** (written by tools while the conversation runs)
      - **What it is for:** holds an unanswered "which one do you mean?": `{tool, input, candidates}`, the ambiguous input and the choices offered, each with what tells it apart (ids, plus city or dates). It exists only while the question is open.
      - **Written by:** any tool that returns `needs_clarification`: `decide_leave_requests` (an ambiguous `employee_names` entry) and the People tools that resolve names (`salary_stats`, `org_headcount`, `add_employee`, for an ambiguous city). The same tool clears it when the next call resolves or abandons the question. **Read by:** the instruction of the agent that asked.
      - **Chat example:**
        ```text
        User:   What's the average pay in Springfield?
        Agent:  There are two: Springfield, Illinois and Springfield, Missouri. Which one?
        User:   The Missouri one.
        Agent:  Average pay in Springfield, Missouri is $... .      (stored choices used, entry cleared)

        User:   Approve leave for Priya Shah.
        Agent:  Two people have that name: emp 26 (Data Scientist, Spokane, leave Oct 17-20) and
                emp 126 (Software Engineer, San Diego, leave Nov 7-10). Which one?
        User:   The one in San Diego.
        Agent:  About to approve emp 126, Nov 7-10.  Confirm?   (request id taken from the stored candidates)
        ```
      - **Why state:** a fresh agent instance never saw the question. The stored candidates are exact and ordered, so "the Missouri one" or "the second one" means what the user saw.
      - **Risk:** expiry. If the user ignores the question and moves on, a stale clarification must not capture a later "the first one".
    - <a id="state-last_analytics_query"></a>**State variable `last_analytics_query`** (written by tools while the conversation runs)
      - **What it is for:** the exact arguments of the last statistics call: `{tool, group_by, profession, state, city, company, status}`. A follow-up is then the same call with one field changed.
      - **Written by:** `salary_stats` and `org_headcount`, in their own code. **Read by:** the People agent's instruction.
      - **Chat example:**
        ```text
        User:   Average pay for data engineers in Texas?
        Agent:  $... .
        User:   And in California?          (same call, only state changed)
        Agent:  $... .
        User:   Break that down by company.  (same filters, group_by = company)
        ```
      - **Why state:** the unchanged parts of the query are reused exactly instead of being re-derived from prose, and a fresh People agent call has no history to derive them from.
      - **Risk:** marginal, because the model can usually infer this from the conversation. It earns its place through exactness and through the case where the agent does not see the history.
  - `org_headcount(group_by=None, profession=None, state=None, city=None, company=None, status="active")` — headcount with the same `group_by` and filters.
    - **State:** writes [`last_analytics_query`](#state-last_analytics_query), [`pending_clarification`](#state-pending_clarification).
  - `add_employee(emp_name, profession=None, salary=None, city=None, state=None, company=None, start_date=None)` — create a record and return the new `emp_id`.
    - Everything except the name is a fact the user must supply, so none has a default. They are optional in the signature on purpose, so the model does not invent a value; any that is missing makes the tool return `needs_input` listing exactly what is missing, and the agent asks the user.
    - A request like "onboard Maya Rao in Austin" therefore gets back a request for the profession, salary, company and start date. Salary must fall in the profession's band.
    - <a id="state-last_touched"></a>**State variable `last_touched`** (written by tools while the conversation runs)
      - **What it is for:** the id of the most recent object a tool created or acted on, per type: `{emp_id, request_id, booking_id, ticket_id, claim_id, asset_id}`, so "that booking" or "that laptop" resolves.
      - **Written by:** the creating tools (`add_employee`, `request_leave`, `book_room`, `open_ticket`, `submit_expense`) and `assign_asset`, which records the asset it assigned. **Read by:** instructions.
      - **Chat example:**
        ```text
        User:   Book Elm for Tuesday 10 to 11 for Maya.
        Agent:  Booked (booking 88).
        User:   Actually, cancel that booking.
        Agent:  Booking 88 cancelled.            (booking_id taken from the stored record)
        User:   Reclaim her laptop.
        Agent:  Laptop LT-00012 returned to stock.

        User:   Open a ticket: the battery on her laptop drains.
        Agent:  Ticket 31 opened (hardware, laptop LT-00012).
        User:   What's the status of that ticket?
        Agent:  Ticket 31 is open.                (ticket_id taken from the stored record)
        ```
      - **Why state:** tools such as `cancel_booking` and `ticket_status` take explicit ids, and this is how "that one" becomes an id without the model digging through history, which the domain agents do not see.
      - **Risk:** "that" is ambiguous when several objects were touched in one turn, and one asset id per type is lossy: if a headset and a laptop are assigned in the same turn, the model must name the kind.
    - <a id="state-pending_input"></a>**State variable `pending_input`** (written by tools while the conversation runs)
      - **What it is for:** keeps a half-finished request while the user supplies what is missing: `{tool, collected, missing}`, the tool that answered `needs_input`, the arguments gathered so far (ids included), and the names of the fields still required. It is not tied to any one tool's schema. For "terminate employee 42 because of the layoff" it holds `{tool: terminate_employee, collected: {emp_id: 42, reason: layoff}, missing: [end_date]}`.
      - **Written by:** any tool that can return `needs_input`: `add_employee` and `terminate_employee` today. A tool writes it only when it answers that way, and clears it when the call succeeds or is abandoned. **Read by:** the People agent's instruction.
      - **Chat example:**
        ```text
        User:   Onboard Maya Rao, data engineer in Austin.
        Agent:  I still need her salary, her company and her start date.
        User:   Starting Monday 12 October, $118,000, at Helix Systems.
        Agent:  Maya Rao is added (emp 201).
        
        User:   Terminate employee 42 because of the layoff.
        Agent:  What is the last working day?   (stored: emp_id 42, reason layoff; missing: end_date)
        ```
      - **Why state:** a fresh People agent call has no memory of the first message, so this entry is the only place the half-finished request survives. The `emp_id` lives inside `collected`; it is not borrowed from [`last_touched`](#state-last_touched). It differs from [`pending_clarification`](#state-pending_clarification): that one chooses among values that matched several things; this one fills in values the user has not given.
      - **Risk:** the user changes their mind or drifts away, so the entry needs an expiry. The collected values are the user's words, so the tool still validates them (salary band, city and state).
    - **State:** writes [`focus_employee`](#state-focus_employee), [`pending_clarification`](#state-pending_clarification).
  - `terminate_employee(emp_id, reason=None, end_date=None, note=None)` — mark as terminated.
    - `reason` is one of `resignation`, `layoff`, `performance`, `retirement`, `other`; it is stored in `employees.end_reason` (and `note` in `end_note`).
    - The end date is never defaulted: we do not know it. Both `reason` and `end_date` are optional in the signature only so the model does not guess; a missing one returns `needs_input`. "Terminate employee 42 because of the layoff" is answered with a request for the end date, and "terminate employee 42" with a request for both the reason (listing the five allowed values) and the end date. Nothing is written until both are supplied.
    - **State:** writes [`pending_input`](#state-pending_input).
  - Exposed to other domains as a read-only function, not a table: `get_employee_summary(emp_id)` (name, profession, company, city), so other agents can show who someone is without reading People's tables.
- **Rules**
  - Per-employee salary is returned on request with no authentication (see [Closed decisions](#closed-decisions)).
  - A new salary must fall inside the `salary_bands` range for the profession.

### Scheduling agent

- **Purpose**
  - Check availability and reserve a resource over a time range — a person's time (leave) or a room's time (booking).
- **Tools**
  - `check_leave_balance(emp_id)` — days left per leave type.
  - `request_leave(emp_id, start, end, type)` — create a request; refuses if the balance is insufficient.
    - **State:** writes [`last_touched`](#state-last_touched).
  - `list_leave_requests(status="pending", emp_id=None, start=None, end=None)` — requests with their `request_id`, employee name, type, dates, days and the employee's remaining balance.
    - <a id="state-last_listing"></a>**State variable `last_listing`** (written by tools while the conversation runs)
      - **What it is for:** the ids in the order the last list was shown, `{tool, filters, shown_ids}`, so "the first three" or "all of them" means what the user was looking at. It stores ids, not rows.
      - **Written by:** the list tools: `list_leave_requests`, `list_assets`, `list_tickets` and `list_claims`. **Read by:** instructions.
      - **Chat example:**
        ```text
        User:   Who is requesting leave?
        Agent:  Showing 10 of 23 pending requests: 1. Priya Shah (Oct 17-20) 2. ...
        User:   Approve the first three.
        Agent:  About to approve: 1. Priya Shah (emp 26) 2. ... 3. ...  Confirm?   (ids taken from the stored list)
        User:   Actually, all of them.
        Agent:  About to approve all 10 requests shown.  Confirm?
        ```
      - **Why state:** re-running the query would give the data as it is now, but the order and exact set the user was looking at may have changed. The stored ids freeze what was shown, while the database stays the source of truth for everything else.
      - **Risk:** what was shown may be decided by the time the user refers to it, so the decision tool re-validates every id (`already_decided`).
    - **State:** reads [`page_size`](#state-page_size).
  - `decide_leave_request(request_id, decision, note)` — approve or reject one pending request.
    - **State:** reads [`last_listing`](#state-last_listing).
  - `decide_leave_requests(request_ids=[], employee_names=[], decision, note=None)` — the batch form.
    - `decision` is `approve` or `reject`; at least one of the two lists must be non-empty.
    - The result has one entry per input, whether it was given as a request id or as an employee name.
    - <a id="state-write_chunk_size"></a>**State variable `write_chunk_size`** (config-time: set when the session is created; the model never writes it)
      - **What it is for:** how many items the batch tool processes per chunk. It is a safety limit on blast radius: the tool loops over the chunks itself, asks for confirmation on each chunk's resolved items, and returns one aggregated result with every per-item outcome.
      - **Written by:** session setup. **Read by:** `decide_leave_requests`, the only batch tool.
      - **Chat example:**
        ```text
        User:   Approve all pending leave.
        Agent:  23 pending requests, in 3 chunks of up to 10. Chunk 1: Priya Shah (emp 26), ...  Confirm?
        User:   Yes.   (... chunks 2 and 3 follow, each confirmed)
        Agent:  Done: 20 approved; 2 need a choice (two people named Priya Shah); 1 failed: no annual leave left (emp 32).
        ```
      - **Why state:** a person can really review ten items, but not twenty-three, and a mistake is then bounded to one chunk. It is separate from [`page_size`](#state-page_size): reading is about presentation, writing is a safety limit. They may share a default value but are not the same variable.
      - **Risk:** it is a safety limit, so nothing the model can call may write it. Open: whether to also cap the total number of items per call.
    - **State:** reads [`last_listing`](#state-last_listing); writes [`pending_clarification`](#state-pending_clarification).
  - `find_free_room(capacity, start, end)` — rooms that fit and are unbooked for the whole range.
    - <a id="state-business_hours"></a>**State variable `business_hours`** (config-time: set when the session is created; the model never writes it)
      - **What it is for:** the start and end hour of the bookable working day (for example 9 and 17), one pair for every room. It is a fact only the system knows: the model cannot know when this office's rooms can be booked.
      - **Written by:** session setup. **Read by:** `find_free_room` and `book_room` as a hard rule (a search or booking outside the window is refused, with a message that states it; this is the main justification), and the Scheduling agent's instruction as a default (the model turns "this afternoon" into a proposed start and end for the user to confirm before booking).
      - **Chat example:**
        ```text
        User:   Book a room for six tomorrow at 7am.
        Agent:  Rooms can only be booked between 09:00 and 17:00.
        User:   Find one tomorrow afternoon, then.
        Agent:  I'll search 13:00-17:00 tomorrow. Free: Cedar, Dogwood, Elm.
        ```
      - **Why state:** the rule is enforced in code, not by hoping the model respects office hours, and the same window gives vague phrases a stable proposal.
      - **Risk:** the seeder has its own constants for the same window, so two sources of truth can drift.
    - <a id="state-last_room_search"></a>**State variable `last_room_search`** (written by tools while the conversation runs)
      - **What it is for:** the last room search's own parameters and results: `{capacity, start, end, results}`, where `results` are the room ids in the order shown (not rows). "The second one" and "an hour later" both depend on it. After "the second one", `book_room` is called with an explicit `room_id` taken from the stored results.
      - **Written by:** `find_free_room`. **Read by:** the Scheduling agent's instruction.
      - **Chat example:**
        ```text
        User:   Find a room for 6 tomorrow, 13:00 to 14:00.
        Agent:  Free: 1. Cedar  2. Dogwood  3. Elm.
        User:   Book the second one.         (room id of Dogwood taken from the stored results)
        
        User:   Actually make it an hour later.   (stored start and end shifted by an hour, capacity kept)
        Agent:  Free from 14:00 to 15:00: Cedar, Elm.
        ```
      - **Why state:** both follow-ups refer to something the previous message used, not something the user said again. A new search could reorder the options, and a fresh agent has not seen the first one.
      - **Risk:** availability changes between the search and the booking. `book_room` already refuses overlaps, so a stale choice fails safely.
  - `book_room(room_id, start, end, emp_id)` — refuses on overlap with an active booking, or when the time falls outside business hours.
    - **State:** reads [`business_hours`](#state-business_hours), [`last_room_search`](#state-last_room_search); writes [`last_touched`](#state-last_touched).
  - `cancel_booking(booking_id)` — mark a booking cancelled.
    - **State:** reads [`last_touched`](#state-last_touched).
- **Rules**
  - A booking never overlaps another active booking for the same room.
  - Rooms can only be searched and booked inside the business-hours window (a start and an end hour, set for the session). A request that falls outside it is refused with a message that states the window.
  - A leave request never exceeds the remaining balance.
  - **Approving leave** (the decision tools above):
    - Only `pending` requests can be decided. The balance is re-checked at approval, and the days are deducted then, in the same transaction as the status change.
    - **Per-item outcomes:** one request's result never blocks another's. Each item comes back as `approved`, `rejected`, `already_decided`, `not_found`, `needs_clarification` or `failed` (with the reason, such as an insufficient balance). Ambiguity is a normal outcome, not an error.
    - **Ambiguity is detected in code:** each entry in `employee_names` is matched exactly (ignoring case) against the pending requests. No match gives `not_found`, one match proceeds, and two or more give `needs_clarification` with the candidates. The agent never picks a candidate itself.
    - **Candidates carry what tells them apart:** request id, employee id, name, profession, company, city, leave type and dates. Names and profile details come from People through a read-only function, not from its tables.
    - **Human confirmation lives inside the tool**, before anything is written, and lists only the items that resolved. Items needing clarification are not part of it, and declining writes nothing.
    - **Repeating a batch is safe:** items already decided come back as `already_decided`.

### IT agent

- **Purpose**
  - Manage equipment assignment and employee-facing IT requests.
- **Tools**
  - `list_assets(emp_id)` — assets currently assigned to the employee, with their category.
    - **State:** reads [`page_size`](#state-page_size); writes [`last_listing`](#state-last_listing).
  - `assign_asset(category_id, emp_id)` — pick an in-stock asset of that category and assign it.
    - **State:** writes [`last_touched`](#state-last_touched).
  - `reclaim_asset(asset_id)` — return an asset to stock.
    - **State:** reads [`last_touched`](#state-last_touched).
  - `open_ticket(emp_id, category, description, asset_id=None)` — create a ticket.
    - `category` is `account` (logins, passwords, two-factor), `hardware` (a physical device) or `access` (permission to a system or resource).
    - A hardware ticket must name the unit it is about in `asset_id`, which the employee holds (the agent finds it with `list_assets(emp_id)`); account and access tickets must leave it empty.
    - **State:** reads [`last_touched`](#state-last_touched); writes [`last_touched`](#state-last_touched).
  - `ticket_status(ticket_id)` — current state of a ticket.
    - **State:** reads [`last_touched`](#state-last_touched).
  - `list_tickets(emp_id=None, status=None)` — tickets with id, category, description, status and created time; `status` is `open`, `in_progress` or `closed`.
    - **State:** reads [`page_size`](#state-page_size); writes [`last_listing`](#state-last_listing).
  - Exposed to other domains as a read-only function, not a table: `count_assets_held(emp_id, category_id)`, so Finance depends on an interface instead of IT's tables.
- **Rules**
  - An asset has at most one assignee; assigning an already-assigned asset fails.
  - Tickets link to assets by unit (`it_tickets.asset_id`), not by category: only hardware tickets have one.
  - Kinds of equipment are identified by `category_id` from `asset_categories`; the free-text `model` column is display only and is never used for matching.
  - An employee may hold at most `max_per_employee` active assets of a category (laptop 1, monitor 2, phone 1, headset 1, keyboard 1, standing desk 1).

### Finance agent

- **Purpose**
  - Handle employee expense claims and report spending.
- **Tools**
  - `submit_expense(emp_id, amount, category, description, asset_category=None, asset_id=None)` — create a claim and evaluate the policy rules (written as code); the outcome is `approved`, `rejected` (with the rule that failed), or `needs_review`.
    - `category` is `travel`, `meals`, `equipment` or `training`. A team dinner is `meals`, and a retreat is `travel`.
    - Equipment claims must name `asset_category`, a catalogue name such as `laptop` or `standing_desk`; the tool maps it to the id.
    - `asset_id` is optional and only for equipment claims about a unit the employee already holds (a repair or an accessory). Its category must match `asset_category`. A purchase of new equipment leaves it empty, because the unit does not exist yet.
    - **State:** writes [`last_touched`](#state-last_touched).
  - `review_claim(claim_id, decision, note)` — record a manual decision on a claim in `needs_review`, behind a human confirmation in the CLI.
    - **State:** reads [`last_listing`](#state-last_listing): after `list_claims(status="needs_review")`, "approve the second one" fills `claim_id` from the stored list.
  - `check_expense_limit(category, amount)` — dry-run against the cap and the rules without creating anything.
  - `claim_status(claim_id)` — current state of a claim, including which rules were evaluated.
    - **State:** reads [`last_touched`](#state-last_touched).
  - `list_claims(emp_id=None, status=None, category=None)` — claims with id, amount, category, status and submitted time; `category` is `travel`, `meals`, `equipment` or `training`.
    - **State:** reads [`page_size`](#state-page_size); writes [`last_listing`](#state-last_listing).
  - `spend_by_category(emp_id=None, since=None, until=None, statuses=["approved","paid"])` — number of claims and total amount per category.
    - By default only approved and paid claims count as spend; pass `statuses` to include others.
    - `since` and `until` are dates, with `since` inclusive and `until` exclusive.
- **Rules**
  - A claim's category must exist in `expense_limits`; the per-claim cap applies.
  - Policy is code, not data: rules are small classes evaluated inside the Finance tools (see [Policy as code](#policy-as-code)). Seeded examples: equipment purchases of 1000 or more must not exceed the asset category's per-employee limit (a claim that names an existing unit through `asset_id`, such as a repair, is not a purchase and is exempt); training claims of 500 or more need manual approval.
  - Every rule evaluation is recorded in `claim_checks`, so any decision traces back to a rule.
  - The check reads the claim's category and amount from the stored claim, not from arguments the model supplied.

## Cross-agent workflows

- **Onboarding** ("Onboard Maya Rao, data engineer in Austin, starting Monday")
  - People: `add_employee` → `emp_id`.
  - IT: `assign_asset` (laptop), `open_ticket` (accounts).
  - Scheduling: `find_free_room` and `book_room` for orientation; `check_leave_balance`.
  - Orchestrator: `notify` the manager with a summary.
  - State: hire details that are still missing wait in [`pending_input`](#state-pending_input); the steps done, failed or paused are tracked in [`workflow_progress`](#state-workflow_progress).
- **Offboarding**
  - People: `terminate_employee`.
  - IT: `list_assets` then `reclaim_asset` for each.
  - Scheduling: `cancel_booking` for future bookings.
  - Finance: report open claims.
  - Orchestrator: `notify` a summary.
  - State: a missing reason or end date waits in [`pending_input`](#state-pending_input); progress is tracked in [`workflow_progress`](#state-workflow_progress).
- **Leave approval** ("Who is requesting leave?", then "Approve leave for X, Y and Z")
  - Scheduling: `list_leave_requests` returns the pending requests; the orchestrator relays the list.
  - Scheduling: `decide_leave_requests` is called with the names given. Names that match exactly one pending request resolve; the tool shows a confirmation of just those, then approves them.
  - Names that match several pending requests, or none, are not approved. They come back as `needs_clarification` (with the candidates) or `not_found`.
  - The final reply reports who was approved and asks about each unresolved name, showing what distinguishes the candidates. The follow-up ("the one in Austin") calls the tool again with the chosen `request_id`.
  - State: the list shown is kept in [`last_listing`](#state-last_listing) ("approve the first three"), an unresolved name in [`pending_clarification`](#state-pending_clarification), and large batches are processed in chunks of [`write_chunk_size`](#state-write_chunk_size).
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

## Session state

Where `session.state` earns its place in this project as it is specified today: the tools and signatures exactly as listed above. State is not limited to tools; it can be written and read through any mechanism ADK provides (see [How state works in ADK](#how-state-works-in-adk)). Cross-session memory is out of scope, since there is no concept of a user.

- **Count:** 11 state variables qualify: 3 set when the session is configured, and 8 written while the conversation runs.
- **Where each is defined:** in full, with a chat example, at its first mention in the agent sections above. Every later mention links back to that definition. The table below lists them all.
- **Kinds:** config-time variables are set when the session is created, and the model never writes them. Conversation-time variables are pointers or parameter sets, never facts of record; they are read through instruction templating, so the domain agents, which do not see the history, can use them.
- **Evidence tags:** statements about ADK are tagged **Code** (read in the installed `google-adk 2.11.0` source), **Docs** (the [ADK state docs](https://adk.dev/sessions/state/)), or **Unverified** (plausible, not checked).
- **Nothing here is implemented.** This is a design inventory.

### How state works in ADK

#### Scopes

- **Docs and Code:** keys with no prefix belong to the session and persist with `DatabaseSessionService`. The prefixes `user:`, `app:` and `temp:` select user-wide, app-wide and single-invocation scopes.
- **Used here:** session scope only. `user:` has no meaning without users, and `app:` would make state leak between independent test sessions.

#### Writing and reading

**Writing**
- **Tool or callback context (recommended):** `context.state['key'] = value`; the change is captured into the event's `state_delta` and persisted when the event is appended.
- **`output_key`:** an agent saves its own final text response under a key. **Code:** this also goes through `state_delta`.
- **`EventActions(state_delta=...)`:** built by hand for custom agents or harness code, then appended with `append_event()`.
- **Initial state:** `create_session(..., state={...})`.
- **At run time:** `run_async` accepts a `state_delta` parameter (**Code**), so the caller can change state when starting a turn.

**Reading**
- **Instruction templating:** `{key}` in an agent's instruction is replaced with the state value before the model sees it; `{key?}` marks the key optional (**Docs**).
- **A callable instruction** receives a read-only context that exposes state (**Code**).
- **Tool or callback context,** and the session object fetched from the session service.

**Rule (Docs):** do not modify a session object fetched from the service directly; updates must go through the context or `append_event`.

**Other facts**
- Values must be JSON-serializable: ids, strings, numbers, lists and dicts.
- Sub-agents: with transfer, all agents share one session and one state. With `AgentTool`, **Code:** state is copied into the sub-agent's temporary session and its changes are forwarded back. **Unverified:** the same for task-mode sub-agents.

#### Setting values at config time

- **Code:** the runner's auto-create path (`auto_create_session=True`) calls `create_session` *without* a state argument, so config-time values need another route:
  - create the session explicitly with `state=` before the first message, in our own script;
  - `adk run` accepts initial state through its `--state` JSON option;
  - or a `before_agent_callback` that fills in any missing defaults.
- **Unverified:** how `adk web` lets a user supply initial state.

#### Who sees the conversation history

- **The orchestrator** sees the whole conversation.
- **A domain agent called through `AgentTool`** does not: it runs in a fresh temporary session that carries the parent's state but not its history (**Code**). A **task-mode** sub-agent sees only its own scoped events plus the arguments of the call that started it (**Code**).
- So for the domain agents, **state is the only continuity they get across calls.** That is the main reason conversation-time variables are worth having even though the orchestrator could, in principle, restate everything.

### What qualifies as state here

A variable is listed only if all of these hold:

- It has a **writer** among the mechanisms above (session setup, tool code, a callback, or `output_key`) and a **reader** (tool code, instruction templating, or a callback), **without adding a tool or changing a signature** in this README.
- It is a **parameter, pointer or small piece of context**, never a fact of record. The database stays the source of truth.
- It is small and JSON-serializable.
- Whatever acts on it **re-validates against the database**, so a stale value fails safely.

### All state variables at a glance

| # | Variable | Kind | Holds | Written by | Read by |
|---|---|---|---|---|---|
| 1 | [`page_size`](#state-page_size) | config-time | rows per page of a list | session setup | the list tools |
| 2 | [`business_hours`](#state-business_hours) | config-time | the bookable working day | session setup | `find_free_room`, `book_room`, the Scheduling agent's instruction |
| 3 | [`write_chunk_size`](#state-write_chunk_size) | config-time | items per confirmed chunk of a batch write | session setup | `decide_leave_requests` |
| 4 | [`focus_employee`](#state-focus_employee) | conversation | the employee being discussed | `find_employee`, `get_employee`, `add_employee` | instructions |
| 5 | [`pending_clarification`](#state-pending_clarification) | conversation | an open "which one?" and its choices | any tool returning `needs_clarification` | the asking agent's instruction |
| 6 | [`pending_input`](#state-pending_input) | conversation | a half-finished request awaiting values | any tool returning `needs_input` | the People agent's instruction |
| 7 | [`last_listing`](#state-last_listing) | conversation | ids in the order last shown | the list tools | instructions |
| 8 | [`last_room_search`](#state-last_room_search) | conversation | the last room search and its results | `find_free_room` | the Scheduling agent's instruction |
| 9 | [`last_touched`](#state-last_touched) | conversation | the latest id per object type | creating tools, `assign_asset` | instructions |
| 10 | [`workflow_progress`](#state-workflow_progress) | conversation | step-by-step state of a multi-step request | after-agent callbacks | the orchestrator's instruction |
| 11 | [`last_analytics_query`](#state-last_analytics_query) | conversation | the last statistics call's arguments | `salary_stats`, `org_headcount` | the People agent's instruction |

### Deferred until the tools change

Only one idea still needs something this README does not specify.

| Variable | What it would hold | What would have to change first |
|---|---|---|
| `pending_action` | one write awaiting a "yes", with its arguments frozen | a confirm path: a confirm tool, or harness handling of the user's reply (for example through `run_async(state_delta=...)`). Needed only if confirmation must span turns, such as under `adk web`, which has no terminal. **Unverified:** whether ADK has built-in tool confirmation. |

### State considered and rejected

- **`user:` and `app:` scopes:** there is no user concept, and cross-session memory is out of scope.
- **A stored "today" (formerly `reference_date`):** removed. `current_date()` reading the real clock on every call is correct and cannot go stale, while a persisted copy goes stale as soon as a session is resumed. If a cache within one turn is ever useful, the single-invocation `temp:` scope fits, because it is discarded afterwards. A pinned date is only a convenience for reproducible demos and tests, and rebuilding the data with the real date achieves the same without state. It can be reintroduced as an optional override if that need appears.
- **A switch for the human-confirmation step (formerly `confirmations_enabled`):** removed. It would be an off-switch for a safety gate, living in state and read by every tool that confirms. The only real need, running without a person at the keyboard (tests, scripted demos), is better met by injection: the tools are handed a confirmer when the harness starts, the normal launch passes the real prompt, and a test passes one that answers automatically. Production code then has no switch for the model, a tool or a message to flip.
- **Policy:** policy lives in code, not in state.
- **Personalization:** nothing stores per-person preferences.
- **Facts of record** (salaries, leave balances, asset holdings, claim statuses): the database is the source of truth. Copies in state go stale and invite contradictions.
- **`output_key` for the domain agents' answers:** `AgentTool` and task-mode sub-agents already return their result to the caller, so storing it again adds nothing beyond [`workflow_progress`](#state-workflow_progress).
- **`temp:` scope:** no case found where a value must pass between steps within one invocation and then vanish.
- **Counters and metrics** (turn counts, token use): that is observability, not conversational state.

### Tensions to resolve

- **Redundancy with history:** the orchestrator already sees the conversation, so several conversation-time variables duplicate it. They earn their place by being exact and ordered, by surviving history trimming, and by being the only continuity the domain agents get. If the orchestrator always restates everything in its calls, they shrink to nothing.
- **Prompt cost:** every variable read through templating adds tokens to every turn. A key that is missing raises an error unless it is written as optional (`{key?}`).
- **Delivery of config-time values differs by entry point:** `python agent.py`, `adk run` and `adk web` each start sessions differently, and the runner's auto-create path sets no state. One mechanism (a callback that fills defaults) would cover all three.
- **State as a safety lever:** [`write_chunk_size`](#state-write_chunk_size) is a guard. If any tool the model can call can write state, the guard can be changed. Only the harness may write it.
- **Config in state or in code:** the config-time values could equally be constants or settings loaded at startup. State is justified only if they must differ per session.
- **Stale pointers:** every conversation-time variable can outlive its meaning. The rule is that the tool acting on it re-validates against the database; whether to also clear them on a change of topic is open.

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
  - pending leave requests for the approval tools to work on:
    - both employees named Priya Shah have one pending request each, on different dates, so approving "Priya Shah" by name must come back as `needs_clarification`;
    - at least one employee has two pending requests, so one name can match two requests;
    - one employee with no annual leave left has a pending annual request, so approving it must fail on the balance;
  - every room booked at 10:00 on the first workday, plus cancelled bookings that must not block anything;
  - terminated employees who still hold a laptop;
  - employees at their category cap (every laptop holder, and 17 monitor holders with two);
  - expense claims over their category cap, recorded as rejected;
  - laptop claims of 1000 or more from employees who already hold a laptop, recorded as rejected by the asset-limit rule;
  - large standing-desk claims from employees without one, still `submitted`;
  - training claims of 500 or more, some awaiting manual review (`needs_review`);
  - hardware tickets, each linked to a unit held by the ticket's owner, with a description that fits the kind of equipment;
  - three repair or accessory claims that name the unit they are about (`asset_id`), held by the claimant, of the matching category.
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
   - `employees` 200, `cities` 15, `rooms` 12, `expense_claims` 83;
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

## Closed decisions

- **Salary visibility:** per-employee salary is returned on request, with no authentication. This is a dummy system, so there is no access control.
  - Consequence: `salary_stats` no longer suppresses small groups, because suppression has no privacy purpose when individual salaries are visible anyway.
- **One database:** a single `ops.db` for all domains. Separate files per agent would make the independence explicit but add complexity this project does not need.
- **Policy as code, not data:** see [Policy as code](#policy-as-code). Revisit with a dedicated policy language (OPA, Cedar, CEL, JSON Logic) only if non-developers need to edit policy.
- **Where checks run:** policy is evaluated when a claim is submitted. A separate approval step for every claim is deliberately not modelled; only `needs_review` claims wait for a decision.
- **State is per session only:** no cross-session memory, because there is no user concept. The eleven variables, the ones dropped and the reasons are in [Session state](#session-state).
- **Links to assets:** both `it_tickets.asset_id` and `expense_claims.asset_id` are nullable foreign keys, because not every ticket or claim is about an asset (account and access tickets; travel, meals and training claims; purchases of new equipment).
  - Constraints make them required or forbidden where the domain says so: a ticket has one exactly when it is a hardware ticket, and a claim may have one only if it is an equipment claim.
  - The kind of equipment (`asset_category_id`) stays on equipment claims, because the purchase rule needs the kind, while `asset_id` records which unit an existing-asset claim is about. The tool checks that the two agree.
- **Leave approval:** leave requests need a human approval.
  - Tools: `list_leave_requests`, `decide_leave_request` and the batch `decide_leave_requests`, all on the Scheduling agent.
  - Outcomes are per item, so one unresolved name never blocks the others.
  - Ambiguity (a name matching several pending requests) is detected in code and returned as `needs_clarification`; the agent asks the user and never guesses.
  - The CLI confirmation lists only the resolved items and is enforced inside the tool.
  - Statuses move `pending` → `approved` or `rejected` through these tools; a requester's own cancellation stays with `cancelled`.

## Open decisions

- **Ticket field name:** `it_tickets.category` (a kind of support request) is unrelated to `asset_categories` (a kind of equipment) apart from the similar name. Whether to rename the ticket field to `ticket_type` is undecided; `open_ticket` keeps `category` for now.
- **Optional merges:** `org_headcount` into `salary_stats` (which already returns a count), and the single `decide_leave_request` into the batch form.
- **A confirmation that spans turns:** whether a frozen pending write (`pending_action`) is needed, for example if the system ever runs where there is no terminal. See [Deferred until the tools change](#deferred-until-the-tools-change).
- **When the leave balance is charged:** proposed as deduct-at-approval with a re-check, because two pending requests can together exceed the balance. The alternative is to reserve the days when the request is made. Not yet confirmed.
