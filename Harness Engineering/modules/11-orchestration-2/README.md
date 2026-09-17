# M11 · Orchestration II: Multi-Agent Patterns

> **Module question:** When is one agent not enough — and when is "more agents" just more failure modes?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** an enterprise assistant with specialized sub-agents

---

## Opening scene — the seven-agent monolith

A team, having read that "multi-agent is the future," split their assistant into seven agents: a router, a greeter, a billing specialist, a shipping specialist, an escalation specialist, a summarizer, and a "coordinator." The result: every request bounced through four or five agents, latency tripled, cost quintupled, and the *answers were no better* — because the handoffs between agents dropped context the way a broken bucket drops water.

The postmortem question, again, was one nobody had asked: *"what did the seven agents buy us that one well-harnessed agent wouldn't have?"* There was no answer. The team had added agents the way the M10 team added autonomy — because it sounded advanced, not because the task demanded it.

This module is the second half of orchestration, and its whole argument is a restraint: **multi-agent is a *specialization* pattern with real costs, not a default architecture.** It pays off only when the task genuinely *demands* it — and even then, the hard part is not the agents, it's the *boundaries between them*.

> **Failure mode (the module in one line):** mistaking "more agents" for "more capability." Each agent boundary is a place where context is lost, latency is added, and a coordination bug can hide — the default should be one agent, and every additional agent must *earn its place*.

---

## The honest test, first

Before the topology, the question that prevents most multi-agent systems:

> **"Would one well-harnessed agent do this better?"**

One agent with good context engineering (M4/M5), good instruction design (M6), and good tools (M8) beats seven under-specified agents every time — because it has *no handoff boundaries to lose context across*. Multi-agent becomes the right answer only when one of these is true:

- **Context isolation helps.** Different subtasks need *different, disjoint* context — and mixing them in one window dilutes attention (M4). Splitting is then a *context* decision, not an ego decision.
- **Verification needs independence.** A separate agent that *checks* another's work is worth more than self-checking (the debate/verification pattern).
- **Specialization is load-bearing.** One subtask genuinely needs a different model, tools, or instruction than the rest.
- **Parallelism matters.** Independent subtasks that can run concurrently.

If none of those is true, you don't have a multi-agent problem — you have a single agent that needs better tooling.

---

## The topologies

When multi-agent *is* warranted, four shapes:

| Topology | Shape | What it's for |
|---|---|---|
| **Supervisor (coordinator)** | One agent delegates to specialists, collects results | The common case: a generalist front door + specialists |
| **Peer** | Agents route to each other directly | Flat teams with overlapping responsibilities |
| **Hierarchical** | Supervisors of supervisors | Deep task decomposition, large systems |
| **Debate / verification** | One agent proposes, another criticizes/verifies | Where correctness matters more than speed |

The supervisor is the workhorse, and it maps directly to ADK's **collaborative team**: a *coordinator* agent with `sub_agents=[...]`, each sub-agent getting a **delegation tool** named after itself, so the coordinator can hand off by *calling the sub-agent like a tool*. The sub-agent runs, returns, and the coordinator resumes.

The critical knob is the sub-agent's **mode** — how much it interacts, and how it returns:

| Mode | User interaction | Return to parent | Parallel? |
|---|---|---|---|
| `single_turn` | none | automatic, with result | yes |
| `task` | clarification only | automatic (`finish_task`) | no |
| `chat` | full | manual (`transfer_to_agent`) | no |

Read the table as *autonomy scoping* (M10's spectrum, applied to sub-agents): a `single_turn` sub-agent is a bounded function-call-with-a-brain — no user chat, runs, returns. A `task` sub-agent may ask clarifying questions but auto-returns. A `chat` sub-agent is a full peer that you must explicitly hand back. Choosing the mode is choosing *how much autonomy the sub-agent gets*, and it's a design decision, not a default.

---

## What multi-agent buys — and what it costs

The ledger, honestly:

**Buys:**
- **Context isolation** — each sub-agent sees only its own branch (ADK's `task`/`single_turn` modes run each in an *isolated session branch*; parallel agents literally cannot see their peers). That's a *feature* when context would otherwise drown.
- **Verification** — a critic that's structurally separate from the writer catches what self-review misses (M2's sycophancy).
- **Parallelism** — `single_turn` sub-agents can run concurrently.

**Costs:**
- **Context loss at the boundary.** Every handoff must serialize what one agent knows into a message another agent receives — and that serialization is *lossy*. The opening scene's seven agents bled context at every hop.
- **Latency & tokens.** Each hop is another model call, another context assembly.
- **Coordination bugs.** Who's responsible when agent C fails after agent B succeeded? The *handoff contract* — what each agent receives, what it returns, what "done" means — is where multi-agent systems actually break.

> **ADK at a glance:** the handoff is a *contract*, not a chat. In the collaborative team, the sub-agent receives a defined input (often an `input_schema`) and returns a defined output (an `output_schema`, or the delegation tool's result). **Structure the handoff** — typed input/output — so context doesn't cross the boundary as loose prose. Loose prose is how context dies in transit. (And a `RoutedAgent` gives you *deterministic* routing — an explicit function, not LLM whimsy — with fallback-on-error: try `primary`, and if it fails before producing output, the router is called again to pick `fallback`.)

### Across boundaries: A2A

Everything above is *within one process* — sub-agents, handoffs, routers. When the "peer" is a **separate service, a different team, or a different framework**, the handoff contract must be a *protocol* — and that protocol is **A2A (Agent2Agent)**.

- **Use it when** the other agent is a standalone service, owned by another team/org, in another language/framework, or you need a formal, versioned contract. **Don't** use it for in-process decomposition — that's the local sub-agents above (faster, shared memory, simpler).
- **In ADK:** expose an agent via `A2AServer`, consume a remote one via `RemoteA2aAgent` — which then *feels like a local tool* to the caller. A2A preserves what a handoff needs across the wire: reasoning traces, long-running tool calls, and file artifacts.
- **Not free.** A network handoff adds everything a local one lacks: a task lifecycle (submitted → working → done/failed/canceled), state across turns, serialization, auth/delegation — and, at the transport layer, long-running tasks over HTTP (polling/streaming/webhooks), idempotency, and retry/timeout semantics. A2A standardizes the *shape* of the handoff; it doesn't make the handoff *cheap*.

---

## The honest test, revisited (now as a rule)

The module's decision rule, in one sentence:

> **Start with one agent. Split when — and only when — you can name *which* of the four payoffs (context isolation, independent verification, specialization, parallelism) the split buys, and you accept the handoff cost.**

Every additional agent is a boundary you must *maintain* — a contract to specify, a context to serialize, a failure mode to own. The seven-agent monolith didn't fail because multi-agent is bad; it failed because nobody could name what the seventh agent was *for*.

---

## Worked example: the enterprise assistant

The domain spine, done *restrained*. A support assistant could be seven agents; it needs, at most, two:

- **The coordinator** — the front door. Understands the request, routes, collects, answers.
- **One specialist sub-agent** — a billing investigator (`task` mode: may ask for the order number, then returns a structured finding).

Why not seven? Because the other five "specialists" don't need disjoint context or a different model — they need *tools* (M8) and *instructions* (M6) on the coordinator. Splitting them would add five context-bleeding boundaries for zero isolation payoff.

Where a *third* agent earns its place: a **verifier** that checks the billing investigator's finding before the coordinator states it to the user — the debate pattern, justified because *correctness* (a billing claim) matters more than speed. That's the test applied honestly: each extra agent names its payoff.

> **Tradeoff (the ledger entry):**
> - **Isolation vs. integration.** Splitting isolates context (good) and fragments it (bad). The payoff is real only when the isolation *itself* is the goal.
> - **Verification vs. cost.** A verifier agent doubles the cost of the step it checks — worth it exactly where wrongness is expensive (billing, legal, irreversible actions).
> - **Autonomy of the sub-agent vs. predictability of the system.** The mode knob (`single_turn` / `task` / `chat`) is the dial; turn it up only where the sub-agent genuinely needs to converse.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design a supervisor topology for a product of your choice (or the enterprise-assistant brief). Then defend it against the honest test.

1. **Start with one agent.** Write down what a single, well-harnessed agent (good instruction + tools) could already do. Be generous — the bar for splitting is high.
2. **Propose splits — each with a named payoff.** For any sub-agent you'd add, write the *specific* payoff it buys (context isolation / independent verification / specialization / parallelism) and its mode (`single_turn` / `task` / `chat`). If you can't name the payoff, delete the agent.
3. **Write the handoff contracts.** For each sub-agent, specify its `input_schema` and `output_schema` — what it receives and what it returns, *structured*, not prose.
4. **Name the top 3 failure modes.** For your topology, write the three most likely breaks (context lost at a handoff, coordination deadlock, a sub-agent failing silently) and the control for each.
5. **Write the ADR.** "Agent decomposition & handoff contracts" — which agents exist, each with its named payoff, and the handoff cost you're accepting.

**Why this exercise matters.** Multi-agent is the most over-adopted pattern in the field, and its cost is invisible in demos (short, clean handoffs) and catastrophic in production (long, context-bleeding chains). The discipline here is the discipline of the whole course, applied to topology: *name the reason, specify the boundary, accept the cost.*

---

**In DSH:** multi-agent is the `subagent` package (continuable children, many providers behind one interface) plus `workflow` (which composes the Ralph fresh-agent loop), with an experimental `agentTeams` coordination seam.

## Sources (ADK docs)

- [Collaborative agent teams — coordinator, sub-agents, modes, context isolation](https://adk.dev/workflows/collaboration/index.md)
- [Routing between agents — RoutedAgent, fallback, planning mode, complexity routing](https://adk.dev/agents/routing/index.md)

---

**Next module:** [M12 — Evaluation Harnesses](../12-evaluation/README.md) — how we know the harness works, and how we keep knowing it.
