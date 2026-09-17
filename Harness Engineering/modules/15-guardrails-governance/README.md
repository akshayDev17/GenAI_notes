# M15 · Guardrails, Safety & Governance

> **Module question:** Who decides what the agent may do — and how is that decision enforced and audited?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a compliance-sensitive assistant (fictional) that writes and sends messages

---

## Opening scene — the email that was "just a draft"

The assistant was supposed to *draft* responses to customers — a human always reviewed and sent. One day, a draft that was *not* reviewed went out anyway, because the "send" capability had silently been left on the assistant, and the human-in-the-loop was a process *outside* the system, not a gate *inside* it.

When the customer complained, the question was instant and uncomfortable: *"who is responsible for what this agent said?"* — and the answer, legally and operationally, was: **the company.** Not the model. Not the framework. The company that fielded the agent. (You've seen this already, in the catalog: Air Canada's "the chatbot is a separate legal entity" defense failed; iTutorGroup was held liable for its hiring AI's discrimination; Mata v. Avianca sanctioned the lawyer who trusted an unverified output.)

This module is the **governance layer** — the one that answers "who decides, who enforces, and who's accountable." It sits *above* the guardrails of M14 (which stop the *attack*) and the evals of M12 (which measure the *quality*), and asks the harder question: *when the agent acts, who owns the action?*

> **Failure mode (the module in one line):** building an agent with the *capability* to act and no *governance* over the acting. Capability without accountability is how a "drafting" assistant becomes a "sending" assistant — and how the company, not the model, ends up liable.

---

## The governance gap

There's a specific gap the term "guardrails" papers over. Guardrails (M14) filter *inputs and outputs* — they stop the model from *saying* something harmful or *reading* something it shouldn't. But an agent with *tools* doesn't just say things — it **does** things: sends, writes, refunds, deploys. And:

> **An agent action with a real-world effect needs an accountable human decision somewhere in its chain — and by default, there isn't one.**

That absence is the **governance gap**. Closing it is three things:

1. **Approval flows** — the irreversible or consequential action is *gated* by a human decision (M8's `require_confirmation`, M13's human-handoff rung). The gate is *in the system*, not a process that exists outside it.
2. **Audit trails** — every action is *recorded* with who/what/why, so that after the fact, "who did this and why" is answerable (M16's events/traces are the raw material).
3. **Ownership** — a named human or role is *accountable* for the agent's actions in each domain. The liability lives here: **the deployer owns the output, whoever wrote the model.** Governance is the harness layer that makes ownership *operational* rather than *rhetorical*.

---

## The guardrail taxonomy

Before the governance pieces, the guardrail vocabulary — and a crucial distinction from the layers you've already built:

| Guardrail | What it does | Sits where |
|---|---|---|
| **Input filter** | Screens what *enters* (injection, off-topic) | Before the model (M14) |
| **Output filter** | Screens what *leaves* (harmful content, brand violations) | After the model (M14) |
| **Policy enforcement** | Makes the *rule* the *boundary* (the tool *cannot* do X) | In the tool (M8) |
| **Refusal behavior** | The model declines within bounds | The instruction (M6) |
| **Capability gating** | The action isn't *available* without authority | The tool surface (M8/M9) |

The distinction to keep: **guardrails stop the model; governance stops the *deployment*.** A guardrail blocks a bad *output*; governance blocks a bad *action* and records it. The three governance pieces (approval, audit, ownership) are what turn a *filtered* agent into an *accountable* one.

> **ADK at a glance:** the mechanisms are already in your toolbox — `require_confirmation` (approval), `before_tool_callback`/plugins (policy enforcement, M14), and the event/trace stream (audit, M16). Governance is not a new API; it's a *discipline* layered on the mechanisms: every consequential tool has a gate, every action is logged, and every domain has a named owner.

---

## Compliance-shaped harnesses

In regulated domains (finance, healthcare, legal), governance isn't optional polish — it's the *shape of the harness*. Three forces bend the design:

1. **Retention** — what must be *kept*, for how long, and what must be *deleted*. (M7's "never store PII without policy" is the seed; here it's a regulatory requirement, not a preference.)
2. **Disclosure** — the user must *know* they're talking to an agent, and what it can do. The Vanderbilt case (M2's catalog) is the negative example: a machine-generated condolence email presented without disclosure.
3. **Consent & scope** — data used *only* for the consented purpose, within the stated scope. M7's scope prefixes (`user:`/`app:`) become a *compliance* boundary, not just a correctness one.

A compliance-shaped harness doesn't bolt these on — it *starts* from them: what may the agent read, retain, and disclose, and what's the audit record for each? The ADRs (M3) are where these live, because a compliance decision is exactly the kind of thing that must be *written down*.

---

## What remains genuinely unsolved

The humility section — because governance has real limits, and pretending otherwise is its own failure:

1. **Emergent misbehavior** — the model does something *harmful in a way no rule anticipated*. You can't enumerate rules for behavior you can't predict (M2 class 9: goal misspecification in the wild).
2. **Multi-step attacks** — a single step looks fine; the *sequence* is the attack (M14's injection chained across turns). Per-step filters miss it; only *trajectory* evaluation (M12) and audit catch it.
3. **Cascading tool abuse** — one tool's legitimate output becomes another tool's malicious input, through no single *bad* step.

The honest posture: **governance bounds the risk, it doesn't eliminate it.** The residual is what the human-in-the-loop and the audit trail are *for* — not to prevent every bad action (impossible), but to make every bad action *attributable, reversible, and learned from*.

---

## Worked example: the compliance-sensitive assistant

The domain spine. The assistant drafts and — potentially — *sends* messages to customers. The governance envelope:

- **Approval:** `require_confirmation` on the `send` tool, *always* — draft freely, send only on a human's explicit approval. The opening scene's failure is now impossible: the gate is in the tool, not in a process outside the system.
- **Audit:** every `send` is an event with author, content, and the approving human's id — replayable (M16). "Who sent this?" is answerable in seconds.
- **Ownership:** a named role (customer-ops lead) owns the send domain; the ADR records it.
- **Compliance:** retention on stored messages (delete after N days), disclosure ("this message was drafted by an assistant"), and consent scoping (only the customer's own data, `user:`-scoped).

The result: the assistant *drafts* with full autonomy, and *sends* with full accountability. That's the governance layer in one sentence: **autonomy for the reversible, accountability for the consequential.**

> **Tradeoff (the ledger entry):**
> - **Autonomy vs. accountability.** Every approval gate buys accountability and sells speed. Gate by *consequence* (M8's threshold function: confirm only above the line), not by default.
> - **Audit completeness vs. cost.** Full audit trails cost storage and engineering; partial trails cost *trust* and *liability*. In consequential domains, the audit is not optional.
> - **Rules vs. judgment.** Enumerated rules catch the *known*; only human judgment (and the residual-risk acceptance in the ADR) covers the *unknown*. Governance is the boundary between them.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the governance envelope for an agent that *writes and sends* messages (or your own consequential agent).

1. **List the consequential actions.** Name every action with a real-world effect (send, refund, write, deploy…), and rank by *irreversibility*.
2. **Assign approval flows.** For each, state the gate — always-confirm, threshold-confirm (with the threshold), or autonomous — and justify in one sentence against consequence.
3. **Design the audit trail.** What must every consequential action record (author, content, approver, timestamp)? Which events are *replayable* (M16)?
4. **Name the owner.** For each domain, who is *accountable* — and where is that recorded (the ADR)?
5. **Write the compliance items.** For a regulated domain of your choice, state the retention, disclosure, and consent rules — and the M7 memory/scope boundary each maps to.
6. **State the residual.** Name one thing your governance envelope *cannot* prevent (emergent misbehavior, a multi-step attack), and what you rely on instead (audit + human judgment).
7. **Write the ADR.** "Governance envelope" — the approval/audit/ownership design, and the residual risk you accept.

**Why this exercise matters.** This is the module where the harness stops being a *technical* artifact and becomes an *accountable* one. The governance envelope you design here is the answer to the question that opened M1 — *"who decides what the agent may do?"* — and to the one the law is now asking, with increasing force: *"who's responsible when it does something wrong?"* The answer, in both cases, is the same: **the harness, and whoever designed it.**

---

**In DSH:** governance is `guard` + `hooks` + `identity` + `feedback`, with scope *restrictions* (`tools.restrict` filters the global tool set per agent) and the goal domain's `blocked` policy code + explanation.

## Sources

- [Safety and Security for AI Agents — guardrails, identity/auth, plugins](https://adk.dev/safety/index.md)
- [Get action confirmation — require_confirmation, approval flows](https://adk.dev/tools-custom/confirmation/index.md)
- [Harness Engineering and the Governance Gap](https://www.xano.com/blog/harness-engineering-and-the-governance-gap/)

---

**Next module:** [M16 — Observability & LLMOps](../16-observability-llmops/README.md) — when a run goes wrong, can you reconstruct exactly what happened and why?
