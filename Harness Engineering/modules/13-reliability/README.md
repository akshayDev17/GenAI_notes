# M13 · Reliability Engineering for Agents

> **Module question:** How do we make an agent that degrades gracefully instead of failing hard?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** payments-adjacent automation (fictional)

---

## Opening scene — the agent that died at the first hiccup

The payments agent was mid-task — it had looked up the order, drafted the refund, and was calling the approval service — when that service timed out. The agent, unencumbered by any notion of "try again" or "fall back," reported a cryptic failure and *stopped*. The customer waited, re-asked, and got the same failure. Three retries later (all from the *customer*), the task was abandoned, and a human had to redo the whole thing by hand.

The failure wasn't the timeout. Timeouts happen. The failure was that the agent had **one mode: succeed or die.** There was no ladder between "it worked" and "it crashed" — no retry, no fallback, no graceful handoff, no safe stop.

This module is about building that ladder. Reliability engineering for agents is the classic discipline — retries, timeouts, fallbacks, circuit breakers — moved *up the stack*: not protecting a database from a flaky network, but protecting a *task* from a flaky model, a flaky tool, and a flaky world.

> **Failure mode (the module in one line):** designing the agent for the happy path and treating every failure as an exception to crash on. The happy path is the rare case; the degradation ladder is the system.

---

## The degradation ladder

The core artifact of this module. When a step fails, the agent climbs a ladder — each rung degrades *less gracefully* but *never* fails hard:

```
retry → fallback → degrade → human handoff → safe fail
```

1. **Retry** — the same call again. Cheap, right for *transient* failures (a timeout, a rate limit). Wrong for *deterministic* failures (the tool says "not found" — retrying won't help). M8's error semantics told you which is which: `retryable: true` vs. `false`. (ADK's `RetryConfig(max_attempts=3)` does this automatically — and, from the 2.0 notes, it's why you should *let exceptions propagate* out of tools rather than swallowing them in a broad `except`, which disables the framework's own retry.)
2. **Fallback** — a different model, or a different path. A cheap model that times out falls back to a different provider (ADK's `RoutedLlm`: the router returns `primary`, and on error is re-called to pick `fallback`). A primary tool that's down falls back to a secondary data source.
3. **Degrade** — do *less*, but finish. Can't get the live price? Answer with the *cached* price and a "as of" caveat. Can't summarize the full contract? Summarize the first three sections and flag the omission.
4. **Human handoff** — stop the machine, hand to a person. The right rung for anything *irreversible* or *ambiguous* (M8's confirmation, M6's escalation).
5. **Safe fail** — stop *safely*: leave state consistent, log the full context (M16), tell the user clearly what happened and what's next. Failing safe is a *designed outcome*, not a crash.

**The design principle:** the rung you land on is a function of *failure type* and *consequence* — not a single global policy. A timeout gets retries; a "not found" gets degradation or safe-fail; an irreversible action gets human handoff *before* it executes, not after.

---

## Budget governance is reliability

Cost and token budgets are usually filed under "ops," but they're *reliability* controls: an unbounded run is a *failure* (the AutoGPT loops, M2's catalog) that burns money and never completes. The budgets:

- **Cost cap** — a ceiling on spend per run; hit it → stop.
- **Token cap** — a ceiling on context/iteration size (M4's per-turn budget, M10's loop budget).
- **Run limit** — a ceiling on iterations/steps (M10's `max_iterations`).

These are the *governor* on the engine. An agent without a cost cap isn't "more capable" — it's a runaway with a credit card.

---

## Failure recovery: checkpoints and partial completion

Reliability also means *not losing work when a long task fails*:

- **Checkpointing** — persist intermediate state (M7's state) so a mid-task failure can *resume* rather than restart. ADK's runtime supports **resume** (`runtime/resume`) — re-enter a stopped run from where it was.
- **Partial completion** — when a multi-step task fails at step 6 of 9, *return* the completed 5 steps with a clear "here's what's done, here's what's left," instead of discarding everything. The user gets value; the failure is scoped, not total.

The point of both: **failure should cost the *remaining* work, not the *completed* work.**

---

## Testing reliability: chaos drills

You can't *assume* the ladder works; you *drill* it. The reliability-testing move is the same as chaos engineering for distributed systems:

- **Tool outage drill** — kill the approval service; verify the agent lands on the right rung (fallback or human handoff), not a crash.
- **Model degradation drill** — point the agent at a slower, dumber model; verify it degrades gracefully.
- **Budget-exhaustion drill** — force the run to hit its cap; verify it safe-fails with a clear message and consistent state.

Each drill is a *test that the ladder exists and the rungs are in the right order*. If a drill shows the agent crashing instead of climbing, that's a reliability bug — and it's exactly what the opening scene's team never checked for.

---

## Worked example: the payments-adjacent automation

The domain spine, as a ladder. The agent approves refunds (with M6's $50 boundary). Here's the full ladder for one refund task:

- **Retry:** the order-lookup tool times out → `RetryConfig` retries twice (transient).
- **Fallback:** the primary pricing model errors before output → `RoutedLlm` falls back to the secondary model.
- **Degrade:** the live balance API is down → the agent reports the *last known* balance, clearly flagged.
- **Human handoff:** refund > $50 → `require_confirmation` *before* the refund tool executes (irreversible).
- **Safe fail:** approval service unreachable after all retries → the agent leaves the ticket in "pending," records the full context, and tells the user "I couldn't complete this; it's queued for review."

No rung crashes. Every failure lands somewhere *intentional*. That's the whole module: **graceful degradation is a ladder you design, not a property the model has.**

> **Tradeoff (the ledger entry):**
> - **Resilience vs. latency.** Every retry and fallback costs time. Bound them (max attempts, timeouts) so resilience doesn't become slowness.
> - **Degradation vs. fidelity.** "Do less but finish" trades correctness for completion — right when a *caveated* answer beats a *crash*.
> - **Autonomy vs. safety at the boundary.** The human-handoff rung is where reliability and governance meet: irreversible actions climb *up* to the human, not *down* to a retry.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Write the degradation ladder for a mission-critical agent of your choice (or the payments brief).

1. **Name the failure classes.** List the three most likely failures (tool timeout, model error, upstream outage, budget exhaustion…) and, for each, whether it's *transient* or *deterministic* (M8's retryable-vs-fatal split).
2. **Write the ladder.** For each failure, specify the rung it lands on — retry → fallback → degrade → human handoff → safe fail — with the *concrete* action at that rung (which model/tool, what the user sees).
3. **Set the budgets.** State the cost cap, token cap, and run limit — as concrete numbers, and where each triggers a safe-fail.
4. **Design the checkpoint.** Which intermediate state do you persist so a mid-task failure can *resume* instead of restart? Name the state keys (M7's prefixes).
5. **Write one chaos drill.** Pick a failure, write the drill (what you kill, what "pass" looks like), and state which rung you expect the agent to land on.
6. **Write the ADR.** "Reliability & degradation policy" — the ladder, the budgets, and the residual risk you're accepting (e.g., "a total approval-service outage queues tasks for review rather than completing them").

**Why this exercise matters.** Reliability is where the harness earns its keep in production — the difference between an agent that *works until it doesn't* and one that *degrades along a designed path*. The ladder you write here is the thing that turns "the model failed" into "the system handled it."

---

**In DSH:** reliability lives in `guard` (repeat-tool guard, budgets) + `sandbox` (resource confinement) + `runtime-diagnostics` — the containment and degradation surface.

## Sources (ADK docs)

- [Model routing — RoutedLlm, fallback on error](https://adk.dev/agents/models/routing/index.md)
- [Welcome to ADK 2.0 — RetryConfig, automatic retries](https://adk.dev/2.0/index.md)
- [Runtime — cancel, resume](https://adk.dev/runtime/index.md)

---

**Next module:** [M14 — Security & Injection Defense](../14-security-injection/README.md) — how to stop the environment from weaponizing the model.
