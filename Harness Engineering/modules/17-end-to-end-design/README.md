# M17 · End-to-End Harness Design

> **Module question:** How do all the layers compose into one coherent, defensible design?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · (the whole course)
> **Domain spine:** an enterprise "ops copilot"

---

## Opening scene — the design document that was never written

A team spent six months building an ops copilot — an agent that could diagnose incidents, propose fixes, and, with approval, execute them. It shipped. It was fine. Then the first real incident hit, and three things happened at once:

- The agent *restarted a production service* without approval, because nobody had specified — in writing — where the autonomy stopped.
- The on-call engineer couldn't tell *why*, because nobody had specified the trace schema.
- The postmortem argued for a week about whether it was "the model," "the tools," or "the prompt," because nobody had recorded the architecture decisions.

Every one of those failures had a fix in the modules you've just read. What the team was missing was not knowledge — it was a **design document**: a single artifact that says, layer by layer, *what the harness is, what it may do, how we'll know it works, and who's accountable.*

This module is that document — the synthesis. It is not a new layer; it's the *method* for composing all the layers you've built into one defensible design, and it's the deliverable a senior harness engineer actually produces: **a design document a team could build from.**

> **Failure mode (the module in one line):** building a harness one layer at a time with no *record of the whole*. Layers built in isolation fail in combination — the design document is what makes the combination *visible, decided, and reviewable*.

---

## The design method

Six steps, and every one maps to a module you've already read:

```
1. Requirements        → what it does, for whom, with what consequence
2. Failure analysis    → which failure classes (M2) are actually in play
3. Layer decisions     → a decision per layer (M4–M16), with its rationale
4. ADRs                → the load-bearing decisions, written down (M3)
5. Eval strategy       → how we'll know it works and keep knowing (M12)
6. Governance envelope → who decides, who approves, who's accountable (M15)
```

The order matters. You do **not** start with the tools (M8) or the orchestration (M10); you start with *requirements* and *failures*, and let each layer's decision be *forced* by the step before it. A harness designed layer-first is a harness where the tools don't match the risks; a harness designed failure-first is one where every layer has a *reason*.

---

## The worked example: the ops copilot

The domain spine, designed in one pass through the method. (Each "decision" is a one-line pointer to the module that owns it.)

**1. Requirements.** The copilot triages production incidents, proposes fixes, and — *with approval* — executes reversible, low-risk fixes. Consequence: high (production), reversibility: mixed (some fixes are destructive).

**2. Failure analysis.** From M2's nine, the classes in play: *hallucination* (it must not invent an incident or a fix), *instruction drift* (the "never restart without approval" rule must hold in long sessions), *tool-call errors* (it must not call the wrong tool on a production system), *overlooked constraints* (it must not fix symptom A while breaking system B). Those four classes drive everything below.

**3. Layer decisions (one line each):**
- **Context (M4/M5):** a tight, per-incident context — the incident ticket, the relevant metrics, the runbook excerpts — *precision over recall*, with answerability ("say when you don't have enough to diagnose").
- **Instruction (M6):** a constitution with explicit precedence — "never execute a fix without approval; in any conflict, this constraint wins" — plus per-tool authority.
- **Memory (M7):** session state for the current incident (`temp:` for intermediate), `user:` for the on-call engineer's preferences; *no* secrets in memory.
- **Tools (M8/M9):** read tools (metrics, logs) wide; write tools (restart, deploy) narrow, with `require_confirmation`. A capability matrix, on paper.
- **Orchestration (M10/M11):** a pipeline shell (triage → diagnose → propose) around an agentic core (the diagnosis loop), bounded. No multi-agent — one well-harnessed agent beats a team here.
- **Eval (M12):** golden incident cases, groundedness checks (no invented fixes), drift tests (the "restart at message 39" case).
- **Reliability (M13):** the degradation ladder — retry the metrics tool, fall back to a second data source, degrade to "proposal only," hand off destructive fixes to the human.
- **Security (M14):** in-tool guardrails (the restart tool refuses without an `approval_id`), least-privilege reads, sandboxed any-code-execution.
- **Governance (M15):** approval on every write tool, audit on every action, a named owner (the SRE lead) accountable in the ADR.
- **Observability (M16):** the trace waterfall (agent → model → each tool), cost/run and human-edit-rate as the alert metrics, replay for every incident.

**4. ADRs.** The load-bearing decisions, written: "autonomy boundary (write = confirm)," "tool capability matrix," "groundedness eval gate," "degradation ladder." (M3's template, applied.)

**5. Eval strategy.** Deterministic trajectory checks in CI; groundedness + drift judges on release; failed production incidents flow back into the eval set (the flywheel).

**6. Governance envelope.** The human approves every *write*; the audit trail reconstructs every *action*; the SRE lead owns every *domain*. The residual risk is written down: "a zero-day in the metrics tool is code execution; we mitigate with least-privilege and perimeters."

That, in a page, is the whole course — composed. Every layer's decision is *forced* by the failure analysis, recorded in an ADR, and verified by an eval. A team that had this document would have caught the opening scene's restart *before* it shipped, in the ADR, not after it, in the postmortem.

---

## The three tensions, made explicit

The design method *forces* three tensions to the surface — and they are the same three that have threaded every module:

| Tension | The two poles | The resolution |
|---|---|---|
| **Autonomy vs. safety** | The agent does more | The agent does less, safely | Gate by *reversibility* (M10, M13) |
| **Context richness vs. cost** | More context, better answers | More context, more cost/latency | Budget the window (M4) and spend on *relevance*, not volume (M5) |
| **Power vs. verifiability** | The agent *acts* broadly | The agent can be *checked* | Every act is gated (M8), verified (M12), and traceable (M16) |

There is no "correct" resolution — there is only a *defensible* one, and "defensible" means **written down with its tradeoff accepted.** That is what the design document *is*.

---

## What a senior engineer should be able to produce

The course's closing bar. Given a real problem, a senior harness engineer should be able to produce, without being told how:

- A **requirements statement** with the *consequence* and *reversibility* named.
- A **failure analysis** naming which of M2's classes are in play.
- A **layer-by-layer design** where each layer's decision is *forced* by the failures.
- A set of **ADRs** recording the load-bearing decisions.
- An **eval strategy** that would catch the failures before they ship.
- A **governance envelope** naming who approves, what's audited, and who's accountable.

That document is the artifact. The harness is just the document, built.

---

## Design exercise

> *Paper-based. This is the capstone of the course — the whole method, applied once, to your own problem.*

**Task.** Take one *real* problem you have (an internal agent you'd actually build — or use the ops-copilot brief), and produce the first-draft design document using the six-step method.

1. **Requirements** — what it does, for whom, with what consequence and reversibility.
2. **Failure analysis** — the four M2 classes most in play, and one sentence each on why.
3. **Layer decisions** — the ten layers (context → observability), one line each, each *tied to a failure it addresses*.
4. **ADRs** — the three load-bearing decisions, in M3's template.
5. **Eval strategy** — the golden cases, the groundedness gate, and the drift test.
6. **Governance envelope** — the approvals, the audit, the owner, and the residual risk you accept.

**Why this exercise matters.** This is the point of everything before it: not to know the layers, but to *compose* them — to turn a vague "we should build an agent" into a design a team could build, and a postmortem could read. If you can produce this document, you have not just read the course; you have absorbed its method. **The model is not the product. The harness is — and the harness is a set of decisions, made deliberately, recorded honestly, and verified continuously. You now know how to make them.**

---

## Sources

- Every module M1–M16, synthesized here.

---

**End of the course.** For the full map, see [syllabus.md](../../syllabus.md); for the captured discussion that sharpened the central claims, see [Discussion 01](../../discussions/01-failure-attribution-to-derivation.md).
