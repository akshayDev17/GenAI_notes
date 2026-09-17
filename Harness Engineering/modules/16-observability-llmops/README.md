# M16 · Observability & LLMOps

> **Module question:** When a run goes wrong, can you reconstruct exactly what happened and why?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a production research agent

---

## Opening scene — the failure nobody could see

The research agent returned a wrong answer to a user, and the on-call engineer had no way to know why. The logs showed "the agent answered," but not *what it saw*, *what it called*, or *what each tool returned*. The model's decision was a black box with a nice final sentence wrapped around it.

The postmortem stalled for two days. The fix that shipped — "tweak the prompt" — was a guess, because **the team couldn't reconstruct the run.** They had monitored the *ends* (input in, output out) and none of the *middle* — which is exactly where the failure lived.

This module is the last operational layer, and it's the one that makes every *other* layer debuggable. Observability answers the question that has hovered over the whole course: *when it goes wrong, can you see why?*

> **Failure mode (the module in one line):** monitoring only the input and output of an agent. The interesting failure is in the *middle* — which tool was called, with what, returning what, in what order — and without the middle, every incident is a guessing game.

---

## The three pillars: logs, metrics, traces

Observability is three instruments, and the division of labor is precise (ADK's own framing):

| Pillar | Answers | For an agent, that means |
|---|---|---|
| **Logs** | *What* happened | "the tool returned an error," "the model said X" |
| **Metrics** | *How long / how many* | latency, cost, error rates, escalation rates |
| **Traces** | *Where the time went* — the hierarchy | the waterfall: agent → model call → tool call → sub-call |

**Traces are the one that changes everything for agents**, because an agent's failure is usually *structural* — a wrong *path*, not a wrong *answer*. A trace captures the path.

> **ADK at a glance:** traces are **OpenTelemetry** spans, in the standard GenAI semantic conventions — `invoke_agent` (the run), `execute_tool` (each tool), `generate_content` (each model call), with `invoke_workflow` for multi-step flows. The spans nest into a "waterfall": the agent run is the root span, the model calls and tool calls are children, and *context propagates* across process boundaries (your tool's microservice spans link back into the agent's trace). Emit over OTLP to any backend — and the `adk web` Trace view shows the same run as Event / Request / Response / Graph.

---

## Reconstructing a run: replay and diff

A trace that *records* the run is necessary; the ability to *re-run* it is where debugging actually happens:

- **Context snapshot** — the trace (or the event stream) records *what the model saw* at each step — the assembled context, the tool args, the results. Without this, you know *that* it failed, not *what it was thinking from*.
- **Replay** — re-run the failed step with the *same* recorded context. (ADK's conformance tooling has a "Replay" mode; and M4's context budget + M7's state are the raw material.) Replay turns "it failed once" into "it fails *reproducibly*" — the difference between a mystery and a bug.
- **Diff two runs** — run the *changed* harness against the *same* inputs and diff the traces. Which span diverged first? That's your regression. This is the observability twin of M12's eval: evals gate *before* shipping, traces diagnose *after*.

The through-line from the M3 diagram discussion, now concrete: **observability is the passive span at both ends and everywhere between** — the input context at the top, the response at the bottom, and every tool call in the middle, connected into one replayable whole.

---

## The metrics that matter

A platform team alerts on a *small* set of signals. For agents, the load-bearing ones:

| Metric | What it catches |
|---|---|
| **Cost per run** | Budget runaways (M13) |
| **Latency percentiles** (p50/p95) | Degradation before users scream |
| **Tool error rate** | A flaky or breaking tool (M13's rung) |
| **Human-edit / override rate** | How often a human had to *fix* the agent's output — the true quality signal |
| **Escalation rate** | How often it handed off — autonomy miscalibration (M10) |

The quiet insight: **human-edit rate is the best single proxy for "is this actually working."** A low error rate means nothing if humans are silently rewriting half the outputs. Watch the *edits*, not the *errors*.

---

## Cost & latency management

Observability's twin is *doing something about* what it sees. The production cost/latency levers (each already met earlier in the course):

- **Caching** (M4) — stable prefixes cut input cost on every repeat turn.
- **Model tiering** (M13's `RoutedLlm`) — cheap model by default, escalate to expensive *only* when the task is hard (the "router by complexity" pattern). Most requests never touch the expensive model.
- **Parallelism** (M11's `single_turn` sub-agents) — independent subtasks run concurrently instead of serially.

These aren't new ideas; M16 is where they become *operational* — measured, budgeted, and alerted on as a *system*, not a set of one-off optimizations.

---

## Incident response for agentic systems

When an agent does go wrong in production, the response toolkit:

- **Rollback** — revert the instruction/model/tool to the last known-good version. (M6's instruction versioning + model version pinning make this *possible*.)
- **Kill switch** — a feature flag that turns the agent (or a specific tool) off *instantly*, without a redeploy.
- **Model version pinning** — pin the exact model version, so "the model changed under us" can't be a variable mid-incident.
- **Replay the incident** — reconstruct the failing run (above) to find the *first* diverging span.

The principle: **incident response for agents is version-controlled and replayable, or it's guesswork.** You can only roll back what you versioned, and you can only diagnose what you traced.

---

## Worked example: the production research agent

The domain spine. A research agent, in production, is instrumented end to end:

- **Trace:** root `invoke_agent` span → `generate_content` (the plan) → N× `execute_tool` (searches) → `generate_content` (the synthesis). Each span records args, results, and token counts.
- **Metrics:** cost/run, p95 latency, search-tool error rate, and — critically — *citation-edit rate* (how often a human corrects a citation).
- **Replay:** a wrong answer is re-run against its recorded context; the diff shows the *third search* returned garbage, and the model trusted it (M5's poisoned-result failure, caught by observability, not by a lucky guess).
- **Response:** roll back the search tool to the previous version, pin the model, and add the bad-search case to M12's eval set.

The point: the research agent doesn't fail *less* because it's observable — it fails *more usefully*. Every failure becomes a replayable, diffable, fixable event instead of a black box.

> **Tradeoff (the ledger entry):**
> - **Trace completeness vs. cost/privacy.** Recording full context (message content, tool args) costs storage and — in M14/M15's terms — *sensitivity* (traces can contain PII). ADK gates this explicitly (`captureMessageContent`, "use with caution in production"). Trace *structure* everywhere; trace *content* where it's safe.
> - **Metric volume vs. signal.** Alert on the five metrics that matter, not fifty dashboards. A metric nobody pages on is decoration.
> - **Instrumentation vs. velocity.** Observability is infrastructure with a tax. Pay it *before* the first incident, not during it.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the observability plan for a production agent of your choice (or the research-agent brief).

1. **The trace schema.** List the spans you'd want for one run (agent, model, each tool, any sub-agents), and for *each* span, the one attribute that matters most (args? result? tokens? finish reason?).
2. **The context snapshot.** What must be recorded so a failed run can be *replayed* — the exact input context, the tool results, the state? Name what you'd *exclude* for privacy (the M14/M15 sensitivity boundary).
3. **The five metrics.** Pick the five you'd alert on (from the table, adapted to your agent), and the threshold that pages.
4. **The replay procedure.** Write the steps to reproduce a failed run — record → re-run with the same context → diff → locate the first diverging span.
5. **The incident kit.** State your rollback (what's versioned), your kill switch (the flag), and your model pin — the three things that make response *fast*.
6. **Write the ADR.** "Observability & incident response" — what's traced, what's alerted, and the privacy/cost tradeoff you're accepting.

**Why this exercise matters.** Observability is the layer that makes every other layer *operable* — you can't fix what you can't see, and you can't see an agent's failure without a trace. This exercise is the difference between an on-call engineer who guesses and one who *reconstructs*.

---

**In DSH:** observability is `core/session` (the append-only log is the source of truth for replay, fork, and telemetry) + `runtime-diagnostics` + `spill`, under the invariant that model-visible input is always reconstructable from the log.

## Sources (ADK docs)

- [Observability for agents — logging, metrics, traces](https://adk.dev/observability/index.md)
- [Agent activity traces — OpenTelemetry spans, OTLP export, waterfall](https://adk.dev/observability/traces/index.md)
- [Evaluate with conformance — Replay mode](https://adk.dev/evaluate/index.md)

---

**Next module:** [M17 — End-to-End Harness Design](../17-end-to-end-design/README.md) — how all the layers compose into one coherent, defensible design.
