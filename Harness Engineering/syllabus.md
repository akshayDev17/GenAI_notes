# Harness Engineering — Course Blueprint (v0.3)

**Course title:** Harness Engineering: Designing the Systems Around AI Agents \
**Audience:** Senior working professional, self-study (~6 years experience; has experimented with LLM/agent APIs, not yet built production agent systems) \
**Format:** Rich written Markdown lessons — broad, deep, vivid. No time constraint. No lab infrastructure for now (code examples yes, labs deferred). Design exercises end every module. \
**Reference stack:** Google ADK (Agent Development Kit) at API level; models served via **LiteLLM / Azure OpenAI endpoints** (GPT-4o/4.1, o-series, DeepSeek, Claude — no Gemini assumption). Grounded against official ADK docs.\
**Out of scope:** model training/fine-tuning, RL, basic prompt-engineering tutorials, deployment/infra ops.\

---

## 1. Why this course exists

The model is not the product — the harness is. A frontier LLM is a capability, not a system. What turns it into a reliable, governed, observable product is the **harness**: the deliberately engineered operating environment around the model — context construction, tool interfaces, orchestration, memory, evaluation, guardrails, and telemetry.

This course teaches you to think like a harness engineer: treat the scaffolding around the model as the primary engineering artifact, and make deliberate, reviewable decisions about every layer — the same rigor you already apply to distributed systems, applied now to agentic systems.

### What a harness is (and isn't)
- **Is:** the set of systems *you design* to elicit, constrain, and verify model behavior — context assembly, tool APIs, control flow, memory, evals, guardrails, observability.
- **Isn't:** "everything that isn't the model." Leaving things undesigned is not harness engineering. (See: [A harness is not "everything that isn't the model"](https://www.futurice.com/blog/harness-engineering))

---

## 2. Learning outcomes

By the end of this course, the learner will be able to:

1. **Articulate** the harness-engineering stack and justify each layer with reference to failure modes, not buzzwords.
2. **Design** context pipelines that decide *what* enters the context window, *in what form*, and *when* — with measurable token/cost budgets.
3. **Architect** tool interfaces (including MCP-style tool servers) with API-grade rigor: contracts, versioning, error semantics, capability boundaries.
4. **Choose and justify** an orchestration pattern — linear workflow, agentic loop, supervisor/multi-agent — from requirements (reliability, cost, latency, autonomy).
5. **Build** an evaluation harness: golden sets, scenario tests, judges, regression gates — and know what evals cannot tell you.
6. **Harden** a harness: guardrails, injection defense, budget governance, audit trails — and know which risks remain genuinely unsolved.
7. **Operate** agentic systems: tracing, replay, cost/latency management, incident response.

---

## 3. Module map — 17 modules in 6 parts

> Every module carries three cross-cutting threads: **(1) Failure modes** — how this layer breaks in production; **(2) The tradeoff ledger** — the decisions and their costs; **(3) ADK at a glance** — the API-level surface that implements the concepts. Example domains vary per module.

**Status legend:** ✅ written · 🚧 in progress · ⬜ planned

| Module | Status | Module | Status |
|---|---|---|---|
| M1 · What Is a Harness | ✅ | M10 · Orchestration I — Control Flow | ✅ |
| M2 · Model Failure Science | ✅ | M11 · Orchestration II — Multi-Agent | ✅ |
| M3 · Harness Architecture & ADK | ✅ | M12 · Evaluation Harnesses | ✅ |
| M4 · Context Engineering I | ✅ | M13 · Reliability Engineering | ✅ |
| M5 · Context Engineering II | ✅ | M14 · Security & Injection Defense | ✅ |
| M6 · The Instruction Layer | ✅ | M15 · Guardrails, Safety & Governance | ✅ |
| M7 · Memory & State | ✅ | M16 · Observability & LLMOps | ✅ |
| M8 · Tool Interfaces | ✅ | M17 · End-to-End Harness Design | ✅ |
| M9 · Tool Platforms (MCP) | ✅ | | |

### Part 0 — Foundations (what we're building and why)

**M1 · What Is a Harness?**
- *Core question:* What exactly is the engineering artifact we're designing?
- The model-is-not-the-product thesis; history: prompting → RAG → agents → harnesses
- The harness stack in one picture: context · tools · control flow · memory · evals · guardrails · observability
- Workflow vs. agent vs. harness vs. platform — the vocabulary trap
- A taxonomy of agent failure modes (the [why-agents-fail](https://github.com/RasaHQ/why-agents-fail) framing): bad instructions, bad context, bad tools, bad orchestration, bad verification, bad containment
- *Domain:* survey across support / coding / research products; *Exercise:* dissect one product you know into the stack, locate where value and risk live

**M2 · Model Failure Science**
- *Core question:* What does the model actually do wrong, and why — before we design anything around it?
- Hallucination, sycophancy, brittleness, instruction drift, position/ordering bias, reasoning degradation under load
- Why "the model failed" is almost always "the harness set it up to fail" — failure attribution
- Failure classes as design inputs: each class maps to a harness layer (this mapping recurs through the whole course)
- Real incident postmortems of agent failures (public ones)
- *Domain:* failure case studies across domains; *Exercise:* for each failure class, name the harness layer that should have caught it

**M3 · Harness Architecture & the ADK Surface**
- *Core question:* What are the parts of a harness, and how do we talk about architecture decisions?
- The layer diagram in detail; coupling and seams between layers
- ADR (architecture decision record) discipline — every module's tradeoffs get recorded this way
- ADK at API level: `Agent`, `Model` (incl. LiteLLM backend), `Tool`, `Session`, `Runner` — how the framework maps to the stack
- Why ADK with a LiteLLM/Azure model backend (provider-agnostic code for the rest of the course)
- *Domain:* a minimal "ticket triage" agent; *Exercise:* write the first ADR — "why this stack, why this seam structure"

### Part 1 — The Cognitive Layer (what the model sees)

**M4 · Context Engineering I — Assembly & Budgets**
- *Core question:* What goes into the context window, in what form, and what does it cost?
- The context window as a constrained resource: token math, context as live currency
- Context anatomy: system instructions, tool definitions, retrieved material, conversation state, intermediate results
- Assembly discipline: stable prefixes, ordering effects, formatting as information
- Prompt caching: what it is, what it costs, how to design for cache hits
- Context budgeting: per-turn budgets, eviction, summarization-in-the-loop
- *Domain:* research agent (context-hungry); *Exercise:* design a context budget for a 3-hour research session, with cache strategy

**M5 · Context Engineering II — Retrieval & Grounding**
- *Core question:* How does the harness get the *right* facts into context, and how do we know they're right?
- RAG as a context-engineering discipline, not a feature: chunking, indexing, retrieval quality
- Retrieval failure modes: missing, stale, contradictory, out-of-scope information
- Citation discipline and answerability: making the model say "I don't have that"
- Grounding beyond RAG: database queries, API lookups, structured fact retrieval
- When retrieval is the wrong tool: tabular, graph, and tool-mediated grounding
- *Domain:* support agent over a knowledge base; *Exercise:* design the grounding strategy for a regulated-domain support agent; list what could go wrong per strategy

**M6 · The Instruction Layer**
- *Core question:* How is the agent's standing policy encoded, versioned, and tested?
- System instructions as a *designed artifact* — policy, escalation rules, constraints, tone — not prose
- Instruction vs. retrieved context vs. tool descriptions: who wins conflicts, and how to make it deterministic
- Instruction testing: how do you regression-test a policy change?
- Common failure: instructions that over-specify, under-specify, or contradict each other
- *Domain:* ops-automation agent with strict escalation policy; *Exercise:* write and adversarially review an instruction set for a policy-driven agent

**M7 · Memory & State**
- *Core question:* What does the agent remember, across what scope, and how is it kept correct?
- Memory taxonomy: working/short-term (session), episodic, semantic, procedural
- State as a correctness issue: staleness, contradiction, leakage across sessions
- Session architecture in ADK: sessions, state, and multi-turn continuity
- Long-term memory design: what to store, retrieval of memories, compaction, memory hygiene
- What memory should never hold: secrets, unverified facts, PII without policy
- *Domain:* multi-turn onboarding/sales agent; *Exercise:* design a session + long-term memory schema with explicit read/write policies and eviction

### Part 2 — The Action Layer (what the model does)

**M8 · Tool Interfaces**
- *Core question:* How do we give the model an API to the world that is safe, correct, and debuggable?
- Tools as APIs for models: contracts, schemas, descriptions — API design discipline applied to model-facing surfaces
- Function-calling semantics: argument validation, required vs. optional, enums, types
- Error semantics: what a tool failure *means* to the model; retryable vs. fatal; partial results
- Capability boundaries and least privilege: scoped credentials, per-tool auth, sandboxing
- Tool-call failure modes: hallucinated args, tool loops, over-eager invocation, poisoned results
- *Domain:* data-analysis agent calling internal APIs; *Exercise:* write a tool contract + capability matrix for an internal API; adversarially review it

**M9 · Tool Platforms: MCP & Tool Servers**
- *Core question:* How do tools become a *platform* — discovered, versioned, shared, and governed?
- The tool-server architecture: why models talk to a server, not a function
- MCP (Model Context Protocol): what it standardizes, what it leaves to you
- Tool discovery, namespacing, versioning, and deprecation across tool surfaces
- Hosting and ops concerns: tool server as an attack surface, rate limiting, credential handling
- ADK's tool surface: native tools, MCP connectors, and when to use which
- *Domain:* coding agent with a growing MCP tool ecosystem; *Exercise:* design a tool-server registry with versioning + access policy for an org with 40+ tools

**M10 · Orchestration I — Control Flow**
- *Core question:* How much autonomy should this agent have, and how is that encoded?
- The autonomy spectrum: linear pipeline → router → agentic loop → autonomous agent
- Choosing the pattern from requirements: reliability, cost, latency, task complexity, reversibility of actions
- The agentic loop in detail: plan → act → observe; stop conditions; budget caps; loop pathologies (looping, thrashing)
- Hybrid designs: workflow shells around agentic cores, human handoff points
- *Domain:* e-commerce order-handling (from scripted to agentic); *Exercise:* given a requirements table, choose and justify the autonomy level per task class

**M11 · Orchestration II — Multi-Agent Patterns**
- *Core question:* When is one agent not enough — and when is "more agents" just more failure modes?
- Multi-agent topology: supervisor, peer, hierarchical, debate/verification pairs
- What multi-agent actually buys you: specialization, verification, parallelism — and what it costs: latency, tokens, coordination bugs
- Handoff and message contracts between agents; shared state vs. isolated state
- Sub-agent delegation in ADK; supervisor patterns at API level
- The honest test: "would one well-harnessed agent do this better?"
- *Domain:* enterprise assistant with specialized sub-agents; *Exercise:* design a supervisor topology with handoff contracts; identify its top 3 failure modes

### Part 3 — The Verification Layer (how we trust it)

**M12 · Evaluation Harnesses**
- *Core question:* How do we know the harness works — and how do we keep knowing it?
- The eval harness is itself a harness: generators, scenarios, judges, aggregators, gates
- Eval taxonomy: golden sets, scenario tests, unit evals (per tool/instruction), end-to-end task evals, guardrail evals
- Judge design: LLM-as-judge, rubrics, pairwise comparison, human review queues; judge failure modes
- Evals in the development loop: regression gates, eval drift, the production→eval data flywheel
- Honest measurement: what evals can and cannot tell you; overfitting to evals
- *Domain:* support agent eval suite; *Exercise:* design an eval harness for one agent you know: cases, judges, and the gate policy

**M13 · Reliability Engineering for Agents**
- *Core question:* How do we make an agent that degrades gracefully instead of failing hard?
- Classic reliability moved up the stack: retries, timeouts, fallback models, circuit breakers for tools
- Budget governance as reliability: cost caps, token caps, per-task run limits
- Degradation design: when the model should hand off to a human, not fail
- Failure recovery: checkpointing, resumable runs, partial-completion handling
- Testing reliability: chaos-style drills for tool outages and model degradation
- *Domain:* payments-adjacent automation (fictional); *Exercise:* write the degradation ladder for a mission-critical agent — retries → fallback → human handoff → safe fail

### Part 4 — The Governance Layer (how we contain it)

**M14 · Security & Injection Defense**
- *Core question:* How do we stop the environment from weaponizing the model?
- Prompt injection: direct vs. indirect; why it is the defining security problem of agentic systems
- Data exfiltration paths: tool results, retrieval, outputs; the "read → act" chain
- Defense in depth: input filtering, output filtering, tool-level least privilege, sandboxing, human approval on irreversible actions
- The trusted-channel problem: how does the model distinguish instructions from data?
- Real injection incidents and their root causes
- *Domain:* browser-automation agent (high exposure); *Exercise:* threat-model an agent: list injection + exfiltration paths and the control for each

**M15 · Guardrails, Safety & Governance**
- *Core question:* Who decides what the agent may do, and how is that decision enforced and audited?
- Guardrails taxonomy: input/output filters, policy enforcement, refusal behavior, capability gating
- The governance gap: agent actions with real-world effects need accountability — approval flows, audit trails, ownership
- Compliance-shaped harnesses: regulated domains (fictional healthcare/finance examples), retention, disclosure
- What remains genuinely unsolved: emergent misbehavior, multi-step attacks, cascading tool abuse
- *Domain:* compliance-sensitive assistant (fictional); *Exercise:* design the governance envelope — approvals, audit, retention — for an agent that writes and sends messages

### Part 5 — The Operational Layer (how we run it)

**M16 · Observability & LLMOps**
- *Core question:* When a run goes wrong, can you reconstruct exactly what happened and why?
- Tracing agent runs: spans for model calls, tool calls, context snapshots; state reconstruction
- Replay: re-running a failed run with the same context; diffing two runs
- Metrics that matter: cost/run, latency percentiles, tool error rates, human-edit rate, escalation rate
- Cost & latency management in production: caching, model tiering (cheap→expensive escalation), parallel calls
- Incident response for agentic systems: rollback, kill switches, feature flags, model version pinning
- Platform survey: ADK tooling, LiteLLM observability hooks, tracing vendors (conceptual, API-level)
- *Domain:* production research agent; *Exercise:* design the trace schema and the 5 metrics a platform team should alert on

### Part 6 — Synthesis

**M17 · End-to-End Harness Design (worked example)**
- *Core question:* How do all the layers compose into one coherent, defensible design?
- A complete worked example — an enterprise "ops copilot" — designed layer by layer
- The design method: requirements → failure-mode analysis → layer decisions → ADRs → eval strategy → governance envelope
- Tradeoff tension points made explicit: autonomy vs. safety, richness of context vs. cost, agentic power vs. verifiability
- What a senior engineer should be able to *produce*: a design document a team could build from
- *Exercise:* take one of your own real problems and produce the first-draft design document using the course method

---

## 4. Writing conventions

- **Vividness:** narrative-driven lessons; each module opens with a concrete scenario, uses recurring characters/cases, and closes with the design exercise
- **Diagrams:** Mermaid for stack/layer/flow diagrams
- **Code:** Python + ADK, model-agnostic via LiteLLM (Azure OpenAI / DeepSeek / Claude backends), API-level depth only
- **Callouts:** `Failure mode` (how this breaks), `Tradeoff` (decision ledger), `ADK at a glance` (framework surface), `Design exercise` (end of module)
- **Grounding:** all ADK-specific claims verified against the official ADK docs (ADK docs MCP server)
- **Versioning:** pin ADK + LiteLLM minor versions used in examples; note upgrade caveats

## 5. Proposed repo structure

```
Harness Engineering/
├── syllabus.md              ← this blueprint (the map)
├── README.md                ← course landing page (TBD)
├── modules/                 ← one folder per module
│   ├── 01-what-is-a-harness/README.md
│   ├── ...
│   └── 17-end-to-end-design/README.md
├── discussions/             ← captured Q&A / deep-dives
└── frameworks/              ← open-source framework → module map
    └── README.md
```

Each module is a single rich `README.md` (or split into chapters if it outgrows one file).

---

## 6. References

- [A harness is not "everything that isn't the model"](https://www.futurice.com/blog/harness-engineering)
- [RasaHQ / why-agents-fail](https://github.com/RasaHQ/why-agents-fail) — failure-mode-driven harness course
- [harness-engineering-templates (Camilool8)](https://github.com/camilool8/harness-engineering-templates/blob/main/docs/explanation/why-harness.md)
- [Harness Engineering and the Governance Gap](https://www.xano.com/blog/harness-engineering-and-the-governance-gap/)
- Google ADK official docs (via MCP) — API grounding
- LiteLLM docs — model-provider abstraction
- [vectara / awesome-agent-failures](https://github.com/vectara/awesome-agent-failures) — maintained catalog of public agent failures

### Captured discussions

- [01 · From "the model hallucinated" to derivable vs. interpretive](discussions/01-failure-attribution-to-derivation.md) — fault-barrier analysis, guardrail provenance design, caching vs. grounding, entailment engine architecture, and the derivable/interpretive boundary

### Framework reference

- [Agent Orchestration Frameworks — Reference Map](frameworks/README.md) — open-source status + source URLs for 17 frameworks, mapped module-by-module (ADK, DSH, LangGraph, CrewAI, AutoGen/Agent Framework, and more)

---

## 7. Decisions so far

- **Stack:** Google ADK at API level; LiteLLM/Azure OpenAI model backends (no Gemini assumption)
- **Depth:** all 8 areas get deep treatment; maximal 17-module structure; no time constraint
- **Format:** rich written Markdown lessons for personal self-study; no lab infrastructure yet
- **Exercises:** design exercises (paper-based) end every module; labs deferred
- **Assessment:** deferred
- **Capstone:** removed (breadth/depth prioritized)
- **Examples:** domains vary per module; real-world + ADK-native texture
- **DSH:** out of the material for now — evaluate this coursework first
- **Out of scope:** model training/fine-tuning, prompt-engineering basics, deployment infra

## 8. Status — complete draft

**All 17 modules (M1–M17) are written** — grounded against the live ADK docs, with sourced incident links in M2, a captured discussion in `discussions/`, and a full failure-class → layer map carried through every module. This is a complete first draft, ready for your review pass.
