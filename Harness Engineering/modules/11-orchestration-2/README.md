# M11 · Orchestration II: Multi-Agent Patterns

> **Module question:** When is one agent not enough — and when is "more agents" just more failure modes?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** an enterprise assistant with specialized sub-agents

---

## Opening scene — the seven-agent monolith

A team, having read that "multi-agent is the future," split their assistant into seven agents: a router, a greeter, a billing specialist, a shipping specialist, an escalation specialist, a summarizer, and a "coordinator." The result: every request bounced through four or five agents, latency tripled, cost quintupled, and the *answers were no better* — because the handoffs between agents dropped context the way a broken bucket drops water.

The postmortem question, again, was one nobody had asked: *"what did the seven agents buy us that one well-harnessed agent wouldn't have?"* There was no answer. The team had added agents the way the M10 team added autonomy — because it sounded advanced, not because the task demanded it.

*The scene above is a composite illustration, not a reported case study — the team, the seven agents, the latencies, and the costs are invented to show the shape of the failure. The mechanisms it names are sourced below.*

This module is the second half of orchestration, and its whole argument is a restraint: **multi-agent is a *specialization* pattern with real costs, not a default architecture.** It pays off only when the task genuinely *demands* it — and even then, the hard part is not the agents, it's the *boundaries between them*.[anthropic-building-effective-agents](#anthropic-building-effective-agents), [cemri-mast](#cemri-mast), [cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents)

> **Failure mode (the module in one line):** mistaking "more agents" for "more capability." Each agent boundary is a place where context is lost, latency is added, and a coordination bug can hide[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents), [cemri-mast](#cemri-mast) — the default should be one agent, and every additional agent must *earn its place*.[anthropic-building-effective-agents](#anthropic-building-effective-agents)

---

## The honest test, first

Before the topology, the question that prevents most multi-agent systems:

> **"Would one well-harnessed agent do this better?"**

One agent with good context engineering (M4/M5), good instruction design (M6), and good tools (M8) beats seven under-specified agents every time[cemri-mast](#cemri-mast) — because it has *no handoff boundaries to lose context across*.[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) *(The "every time" is the module's confidence, not a measured result[own-synthesis](#own-synthesis) — see [disagreement §1](#1-the-modules-headline-restraint-claim-is-cut-by-the-frontier-labs-own-number).)* Multi-agent becomes the right answer only when one of these is true:

- **Context isolation helps.** Different subtasks need *different, disjoint* context — and mixing them in one window dilutes attention (M4).[liu-lost-in-the-middle](#liu-lost-in-the-middle), [shi-irrelevant-context](#shi-irrelevant-context) Splitting is then a *context* decision, not an ego decision. Isolation is one of the reasons multi-agent systems get built in the first place.[cemri-mast](#cemri-mast)
- **Verification needs independence.** A separate agent that *checks* another's work is worth more than self-checking (the debate/verification pattern).[huang-cannot-self-correct](#huang-cannot-self-correct), [mcaleese-criticgpt](#mcaleese-criticgpt) *(Contested — see [disagreement §2](#2-separate-verification-is-not-reliably-better-than-cheaper-alternatives).)*
- **Specialization is load-bearing.** One subtask genuinely needs a different model, tools, or instruction than the rest.[tran-collaboration-survey](#tran-collaboration-survey), [cemri-mast](#cemri-mast)
- **Parallelism matters.** Independent subtasks that can run concurrently.[anthropic-multi-agent-research](#anthropic-multi-agent-research), [wang-mixture-of-agents](#wang-mixture-of-agents)

If none of those is true, you don't have a multi-agent problem — you have a single agent that needs better tooling.

---

## The topologies

When multi-agent *is* warranted, four shapes:

| Topology | Shape | What it's for |
|---|---|---|
| **Supervisor (coordinator)** | One agent delegates to specialists, collects results | The common case: a generalist front door + specialists[anthropic-building-effective-agents](#anthropic-building-effective-agents), [wu-autogen](#wu-autogen) |
| **Peer** | Agents route to each other directly | Flat teams with overlapping responsibilities[li-camel](#li-camel), [tran-collaboration-survey](#tran-collaboration-survey) |
| **Hierarchical** | Supervisors of supervisors | Deep task decomposition, large systems[hong-metagpt](#hong-metagpt) |
| **Debate / verification** | One agent proposes, another criticizes/verifies | Where correctness matters more than speed[du-multiagent-debate](#du-multiagent-debate), [mcaleese-criticgpt](#mcaleese-criticgpt) |

*(The four shapes are one cut through the design space, not an exhaustive enumeration[tran-collaboration-survey](#tran-collaboration-survey) — see [disagreement §6](#6-the-topology-table-is-one-taxonomy-among-several).)*

The supervisor is the workhorse, and it maps directly to ADK's **collaborative team**: a *coordinator* agent with `sub_agents=[...]`, each sub-agent getting a **delegation tool** named after itself, so the coordinator can hand off by *calling the sub-agent like a tool*. The sub-agent runs, returns, and the coordinator resumes.[adk-collaboration](#adk-collaboration)

The critical knob is the sub-agent's **mode** — how much it interacts, and how it returns:[adk-collaboration](#adk-collaboration)

| Mode | User interaction | Return to parent | Parallel? |
|---|---|---|---|
| `single_turn` | none | automatic, with result | yes |
| `task` | clarification only | automatic (`finish_task`) | no |
| `chat` | full | manual (`transfer_to_agent`) | no |

Read the table as *autonomy scoping* (M10's spectrum, applied to sub-agents): a `single_turn` sub-agent is a bounded function-call-with-a-brain — no user chat, runs, returns. A `task` sub-agent may ask clarifying questions but auto-returns. A `chat` sub-agent is a full peer that you must explicitly hand back. Choosing the mode is choosing *how much autonomy the sub-agent gets*, and it's a design decision, not a default.[adk-collaboration](#adk-collaboration) *(Three caveats the table omits — `chat` is the default, `mode` is for sub-agents only, and `task` mode is disabled in graph workflows — are recorded in [disagreement §7](#7-framework-and-protocol-claims-verified-against-the-docs-with-four-corrections).)*

---

## What multi-agent buys — and what it costs

The ledger, honestly:

**Buys:**
- **Context isolation** — each sub-agent sees only its own branch (ADK's `task`/`single_turn` modes run each in an *isolated session branch*; parallel agents literally cannot see their peers).[adk-collaboration](#adk-collaboration), [cemri-mast](#cemri-mast) That's a *feature* when context would otherwise drown.[liu-lost-in-the-middle](#liu-lost-in-the-middle) *(The same property is the module's sharpest liability — see [disagreement §4](#4-context-isolation-is-the-payoff-and-the-sharpest-liability).)*
- **Verification** — a critic that's structurally separate from the writer catches what self-review misses (M2's sycophancy).[mcaleese-criticgpt](#mcaleese-criticgpt), [huang-cannot-self-correct](#huang-cannot-self-correct)
- **Parallelism** — `single_turn` sub-agents can run concurrently,[adk-collaboration](#adk-collaboration) and parallel exploration is where the measured gains live.[anthropic-multi-agent-research](#anthropic-multi-agent-research), [wang-mixture-of-agents](#wang-mixture-of-agents)

**Costs:**
- **Context loss at the boundary.** Every handoff must serialize what one agent knows into a message another agent receives — and that serialization is *lossy*.[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) The failure taxonomy has named rows for it: *loss of conversation history*, *conversation reset*, and *information withholding*.[cemri-mast](#cemri-mast) The opening scene's seven agents bled context at every hop.
- **Latency & tokens.** Each hop is another model call, another context assembly — and in production the multiplier is measured, not hypothetical.[anthropic-multi-agent-research](#anthropic-multi-agent-research), [kapoor-ai-agents-matter](#kapoor-ai-agents-matter)
- **Coordination bugs.** Who's responsible when agent C fails after agent B succeeded? The *handoff contract* — what each agent receives, what it returns, what "done" means — is where multi-agent systems actually break.[cemri-mast](#cemri-mast)

> **ADK at a glance:** the handoff is a *contract*, not a chat. In the collaborative team, the sub-agent receives a defined input (often an `input_schema`) and returns a defined output (an `output_schema`, or the delegation tool's result).[adk-collaboration](#adk-collaboration) **Structure the handoff** — typed input/output — so context doesn't cross the boundary as loose prose. Loose prose is how context dies in transit.[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) (And a `RoutedAgent` gives you *deterministic* routing — an explicit function, not LLM whimsy — with fallback-on-error: try `primary`, and if it fails before producing output, the router is called again to pick `fallback`.)[adk-routing](#adk-routing)

### Across boundaries: A2A

Everything above is *within one process* — sub-agents, handoffs, routers. When the "peer" is a **separate service, a different team, or a different framework**, the handoff contract must be a *protocol* — and that protocol is **A2A (Agent2Agent)**.[a2a-spec](#a2a-spec)

- **Use it when** the other agent is a standalone service, owned by another team/org, in another language/framework, or you need a formal, versioned contract. **Don't** use it for in-process decomposition — that's the local sub-agents above (faster, shared memory, simpler).[adk-a2a](#adk-a2a)
- **In ADK:** expose an agent via `A2AServer`, consume a remote one via `RemoteA2aAgent` — which then *feels like a local tool* to the caller.[adk-a2a](#adk-a2a) A2A preserves what a handoff needs across the wire: reasoning traces, long-running tool calls, and file artifacts.[adk-a2a](#adk-a2a)
- **Not free.** A network handoff adds everything a local one lacks: a task lifecycle, state across turns, serialization, auth/delegation — and, at the transport layer, long-running tasks over HTTP (polling/streaming/webhooks), idempotency, and retry/timeout semantics.[a2a-life-of-a-task](#a2a-life-of-a-task), [a2a-spec](#a2a-spec) A2A standardizes the *shape* of the handoff; it doesn't make the handoff *cheap*.[anthropic-multi-agent-research](#anthropic-multi-agent-research) *(The lifecycle is longer than "submitted → working → done/failed/canceled" — see [disagreement §7](#7-framework-and-protocol-claims-verified-against-the-docs-with-four-corrections).)*

---

## The honest test, revisited (now as a rule)

The module's decision rule, in one sentence:

> **Start with one agent. Split when — and only when — you can name *which* of the four payoffs (context isolation, independent verification, specialization, parallelism) the split buys, and you accept the handoff cost.**[anthropic-building-effective-agents](#anthropic-building-effective-agents), [own-synthesis](#own-synthesis)

Every additional agent is a boundary you must *maintain* — a contract to specify, a context to serialize, a failure mode to own.[cemri-mast](#cemri-mast) The seven-agent monolith didn't fail because multi-agent is bad; it failed because nobody could name what the seventh agent was *for*.

---

## Worked example: the enterprise assistant

The domain spine, done *restrained*. A support assistant could be seven agents; it needs, at most, two:

- **The coordinator** — the front door. Understands the request, routes, collects, answers.[anthropic-building-effective-agents](#anthropic-building-effective-agents)
- **One specialist sub-agent** — a billing investigator (`task` mode: may ask for the order number, then returns a structured finding).[adk-collaboration](#adk-collaboration)

Why not seven? Because the other five "specialists" don't need disjoint context or a different model — they need *tools* (M8) and *instructions* (M6) on the coordinator. Splitting them would add five context-bleeding boundaries for zero isolation payoff.[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents), [kapoor-ai-agents-matter](#kapoor-ai-agents-matter)

Where a *third* agent earns its place: a **verifier** that checks the billing investigator's finding before the coordinator states it to the user — the debate pattern, justified because *correctness* (a billing claim) matters more than speed.[du-multiagent-debate](#du-multiagent-debate) *(Whether a separate verifier beats cheaper alternatives is genuinely contested[smit-going-mad](#smit-going-mad) — see [disagreement §2](#2-separate-verification-is-not-reliably-better-than-cheaper-alternatives).)* That's the test applied honestly: each extra agent names its payoff.

> **Tradeoff (the ledger entry):**
> - **Isolation vs. integration.** Splitting isolates context (good) and fragments it (bad).[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) The payoff is real only when the isolation *itself* is the goal.
> - **Verification vs. cost.** A verifier agent doubles the cost of the step it checks — worth it exactly where wrongness is expensive (billing, legal, irreversible actions).[du-multiagent-debate](#du-multiagent-debate), [smit-going-mad](#smit-going-mad) Cost is the axis benchmark-first agent design most often omits.[kapoor-ai-agents-matter](#kapoor-ai-agents-matter)
> - **Autonomy of the sub-agent vs. predictability of the system.** The mode knob (`single_turn` / `task` / `chat`) is the dial; turn it up only where the sub-agent genuinely needs to converse.[adk-collaboration](#adk-collaboration)

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design a supervisor topology for a product of your choice (or the enterprise-assistant brief). Then defend it against the honest test.

1. **Start with one agent.** Write down what a single, well-harnessed agent (good instruction + tools) could already do. Be generous — the bar for splitting is high.
2. **Propose splits — each with a named payoff.** For any sub-agent you'd add, write the *specific* payoff it buys (context isolation / independent verification / specialization / parallelism) and its mode (`single_turn` / `task` / `chat`). If you can't name the payoff, delete the agent.
3. **Write the handoff contracts.** For each sub-agent, specify its `input_schema` and `output_schema` — what it receives and what it returns, *structured*, not prose.
4. **Name the top 3 failure modes.** For your topology, write the three most likely breaks (context lost at a handoff, coordination deadlock, a sub-agent failing silently) and the control for each.
5. **Write the ADR.** "Agent decomposition & handoff contracts" — which agents exist, each with its named payoff, and the handoff cost you're accepting.

**Why this exercise matters.** Multi-agent is the most over-adopted pattern in the field[cemri-mast](#cemri-mast), [kapoor-ai-agents-matter](#kapoor-ai-agents-matter), [cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) *(the superlative is the course's, not a measured ranking)*[own-synthesis](#own-synthesis), and its cost is invisible in demos (short, clean handoffs) and catastrophic in production (long, context-bleeding chains).[cemri-mast](#cemri-mast) The discipline here is the discipline of the whole course, applied to topology: *name the reason, specify the boundary, accept the cost.*

---

**In DSH:** multi-agent is the `subagent` package (continuable children, many providers behind one interface) plus `workflow` (which composes the Ralph fresh-agent loop), with an experimental `agentTeams` coordination seam.

## Sources (ADK docs)

- [Collaborative agent teams — coordinator, sub-agents, modes, context isolation](https://adk.dev/workflows/collaboration/index.md)[adk-collaboration](#adk-collaboration)
- [Routing between agents — RoutedAgent, fallback, planning mode, complexity routing](https://adk.dev/agents/routing/index.md)[adk-routing](#adk-routing)
- [Introduction to A2A — local sub-agents vs. remote agents, `A2AServer`, `RemoteA2aAgent`](https://adk.dev/a2a/intro/index.md)[adk-a2a](#adk-a2a)

---

## Where the literature disagrees with this module

The module's argument is a restraint, and the restraint is the part most contested. Two of its load-bearing claims are contradicted by the sources it leans on, one is stated more strongly than the literature supports, and the topology table is one taxonomy among several. Recorded here with the same discipline the module asks of its readers: name the claim, name the source, name the change.

### 1. The module's headline restraint claim is cut by the frontier lab's own number

The module leads with *"one well-harnessed agent … beats seven under-specified agents every time"* and treats the four payoffs as the only reasons to split. The strongest single measurement in the located literature points the other way, and the lab that published it explains the gain as something the module never names.

**What supports the restraint:**

- The failure evidence is real and large: across 7 popular multi-agent frameworks, "our empirical analysis reveals **41% to 86.7% failure rate**," and "their performance gains often remain minimal compared to single-agent frameworks or simple baselines like best-of-N sampling."[cemri-mast](#cemri-mast)
- The costs are measured, not rhetorical: agentic systems "often trade latency and cost for better task performance, and you should consider when this tradeoff makes sense," and the standing recommendation is "finding the simplest solution possible, and only increasing complexity when needed."[anthropic-building-effective-agents](#anthropic-building-effective-agents)
- Benchmark-first design systematically hides that tradeoff: "there is a narrow focus on accuracy without attention to other metrics. As a result, SOTA agents are needlessly complex and costly."[kapoor-ai-agents-matter](#kapoor-ai-agents-matter)

**What contradicts it:**

- **Multi-agent beat single-agent by a wide margin in production.** "We found that a multi-agent system with Claude Opus 4 as the lead agent and Claude Sonnet 4 subagents **outperformed single-agent Claude Opus 4 by 90.2%** on our internal research eval."[anthropic-multi-agent-research](#anthropic-multi-agent-research)
- **And the mechanism was not any of the module's four payoffs.** "Multi-agent systems work mainly because **they help spend enough tokens to solve the problem**. In our analysis, three factors explained 95% of the performance variance … **token usage by itself explains 80% of the variance**."[anthropic-multi-agent-research](#anthropic-multi-agent-research) On that account the fourth payoff (parallelism) is instrumental and the real payoff is *token budget*, a fifth reason the module never lists.
- **The same source prices it:** "agents typically use about **4× more tokens** than chat interactions, and multi-agent systems use about **15× more tokens** than chats."[anthropic-multi-agent-research](#anthropic-multi-agent-research)
- The sampling literature reaches the same place from the other direction: "the performance of large language models (LLMs) scales with **the number of agents instantiated**."[li-more-agents](#li-more-agents)

**Consequence for the module.** Keep the restraint — the two findings are compatible, because MAST measures *systems that were built badly* and Anthropic measures *a system built for a task that fits*. But **stop stating the claim universally.** The defensible form is narrower and more useful: *one agent is the default; a split must name its payoff **or** its budget.* Where the task is breadth-first, information exceeds one window, and the query value pays for a 15× token multiplier, multi-agent is the measured winner — and the honest reason is token spend, not topology.

### 2. Separate verification is not reliably better than cheaper alternatives

The module asserts that "a separate agent that *checks* another's work is worth more than self-checking," and justifies a third agent on it. The claim is the pattern's own thesis, so the pattern's owner supports it — but the head-to-head evaluations do not license "worth more."

**What supports it:**

- The debate pattern's owner reports that "this approach **significantly enhances mathematical and strategic reasoning** across a number of tasks" and "improves the factual validity of generated content, reducing fallacious answers and hallucinations."[du-multiagent-debate](#du-multiagent-debate)
- Trained critics measurably beat the humans doing the same job: on code containing naturally occurring LLM errors, "model-written critiques are preferred over human critiques in 63% of cases, and human evaluation finds that **models catch more bugs than human contractors paid for code review**."[mcaleese-criticgpt](#mcaleese-criticgpt)
- Self-review alone is the weak version: "LLMs **struggle to self-correct their responses without external feedback**, and at times, their performance even degrades after self-correction."[huang-cannot-self-correct](#huang-cannot-self-correct)

**What contradicts it:**

- **Debate does not reliably beat non-agent baselines.** Benchmarking "a range of debating and prompting strategies to explore the trade-offs between cost, time, and accuracy," the authors "find that multi-agent debating systems, in their current form, **do not reliably outperform other proposed prompting strategies, such as self-consistency and ensembling using multiple reasoning paths**." The failure is not that debate is worse but that it is unstable: MAD protocols are "more sensitive to different hyperparameter settings and difficult to optimize."[smit-going-mad](#smit-going-mad)
- **The self-correction literature disagrees with itself**, which matters because the module's contrast is "self-checking vs. separate checker." The pro side reports outputs that are "preferred by humans and automatic metrics … improving by **~20% absolute on average** in task performance" from self-feedback alone,[madaan-self-refine](#madaan-self-refine) while the anti side reports degradation without external feedback.[huang-cannot-self-correct](#huang-cannot-self-correct) The variable that separates them is **whether feedback is external**, not whether the checker is a separate agent.
- **The separate critic has its own failure mode, the same one it is hired to catch:** "Critics can have limitations of their own, including **hallucinated bugs** that could mislead humans into making mistakes they might have otherwise avoided."[mcaleese-criticgpt](#mcaleese-criticgpt)

**Consequence for the module.** Replace "worth more than self-checking" with a testable version: **a verifier earns its place when its measured delta over a cheaper non-agent baseline (self-consistency, best-of-N, a rubric check) is positive on your task.** The mechanism the evidence supports is *external feedback*; structural separation is one way to get it and not the cheapest. And because a critic can hallucinate bugs, the critic needs its own evaluation — M12's territory, not a free win.

### 3. "Every additional agent must earn its place" — true for delegated agents, false for sampled ones

The module's rule is stated over *agents*. The literature contains a large, well-replicated family of results where adding agents requires no justification at all, because nothing is handed off.

- "We find that, simply via a **sampling-and-voting** method, the performance of large language models (LLMs) scales with the number of agents instantiated. Also, this method, termed as Agent Forest, is orthogonal to existing complicated methods to further enhance LLMs, while the degree of enhancement is **correlated to the task difficulty**."[li-more-agents](#li-more-agents)
- MAST frames this as the baseline that undermines the case for elaborate systems: gains are "often minimal compared to single-agent frameworks or **simple baselines like best-of-N sampling**."[cemri-mast](#cemri-mast)
- The production version of the same effect is Anthropic's token-variance finding: more parallel attempts help because they spend more tokens, not because they are specialists.[anthropic-multi-agent-research](#anthropic-multi-agent-research)

**Consequence for the module.** The unit of the claim should be **the handoff, not the agent**. *Sampled* agents (independent attempts, aggregated by vote or judge) have no boundary, no contract, and no serialization loss — they are cheap to add and should not be asked to justify themselves. *Delegated* agents have all three, and the "earn its place" rule is exactly right for them. Read over all agents, the rule is unsupported as stated; read over delegated agents, it holds.[unsupported](#unsupported)

### 4. Context isolation is the payoff *and* the sharpest liability

The module sells context isolation as a clean win: "each sub-agent sees only its own branch … That's a *feature* when context would otherwise drown." A production team that builds coding agents argues the identical property is the reason not to do this at all, and Anthropic's own post concedes the boundary.

**What supports it:**

- Isolation is named as a first-class reason these systems exist: multi-agent systems are "structured to coordinate efforts, enabling task decomposition, performance parallelization, **context isolation**, specialized model ensembling, and diverse reasoning discussions."[cemri-mast](#cemri-mast)
- The dilution half is well measured: performance "is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle,"[liu-lost-in-the-middle](#liu-lost-in-the-middle) and the distractibility result is blunter still — "the model performance is dramatically decreased when irrelevant information is included."[shi-irrelevant-context](#shi-irrelevant-context)
- Parallel sub-agents with their own windows are how the measured wins were obtained — "subagents facilitate compression by operating in parallel with their own context windows."[anthropic-multi-agent-research](#anthropic-multi-agent-research)

**What contradicts it:**

- **Share context, not just messages.** "Share context, and share full agent traces, not just individual messages."[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents)
- **The real failure is conflicting implicit decisions, which isolation *causes*.** "Actions carry implicit decisions, and conflicting decisions carry bad results." Two subagents given the same task produced "a bird and background with completely different visual styles" because "subagent 1 and subagent 2 can not see what the other was doing and so their work ends up being inconsistent with each other," with the decisions "based on conflicting assumptions not prescribed upfront."[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents)
- **The prescription is a default, not a preference:** these two principles "are so critical, and so rarely worth violating, that you should **by default rule out any agent architectures that don't abide by them**," because "running multiple agents in collaboration only results in fragile systems. The decision-making ends up being too dispersed and context isn't able to be shared thoroughly enough between the agents."[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents)
- **Anthropic concedes the fit boundary rather than the principle:** "some domains that **require all agents to share the same context or involve many dependencies between agents are not a good fit** for multi-agent systems today. For instance, most coding tasks involve fewer truly parallelizable tasks than research."[anthropic-multi-agent-research](#anthropic-multi-agent-research)

**Consequence for the module.** The precondition for the isolation payoff is not "different, disjoint context" — it is **independent implicit decisions**. Disjoint context is safe only when the subtasks' unstated choices cannot collide. The module's own worked example passes this test (a billing lookup's assumptions do not constrain the coordinator's prose); a seven-agent coding split does not. Say so, and the "context isolation" payoff stops being available as a blanket justification.

### 5. A typed handoff is necessary, and not sufficient

The module's fix for boundary loss is structure: typed `input_schema`/`output_schema`, because "loose prose is how context dies in transit." The sources agree about prose — and then show that a well-typed handoff still loses the substance, because what matters is *what persists outside the message*.

- **The production mitigation is an artifact store, not a schema.** Under the heading "Subagent output to a filesystem to minimize the 'game of telephone'": "Rather than requiring subagents to communicate everything through the lead agent, implement artifact systems where specialized agents can create outputs that persist independently. Subagents call tools to store their work in external systems, then pass **lightweight references** back to the coordinator. This prevents information loss during multi-stage processing and reduces token overhead from copying large outputs through conversation history."[anthropic-multi-agent-research](#anthropic-multi-agent-research)
- **Copying the full task down is not enough either.** "You might think that a simple solution would be to just copy over the original task as context to the subagents as well. That way, they don't misunderstand their subtask. But remember that in a real production system, the conversation is most likely **multi-turn**, the agent probably had to make some **tool calls** to decide how to break down the task, and any number of details could have consequences on the interpretation of the task."[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents)
- **And the taxonomy has a name for the schema that is never filled:** *information withholding* and *loss of conversation history* are two of the 14 modes, alongside *ignored other agent's input* and *conversation reset*.[cemri-mast](#cemri-mast)

**Consequence for the module.** Keep the schema, add the second half: **the interface is typed, and the substance lives in a durable artifact the next agent can fetch.** "Context doesn't cross the boundary as loose prose" is right but incomplete — context also doesn't cross as a perfect JSON object if the reasoning that produced it stayed behind.

### 6. The topology table is one taxonomy among several

The four shapes are presented as *the* shapes. The survey literature organizes the same space along different axes, and one shape the table omits has the strongest single benchmark result in the located set.

- The survey's framework "characterizes collaboration mechanisms based on key dimensions: **actors** (agents involved), **types** (e.g., cooperation, competition, or coopetition), **structures** (e.g., peer-to-peer, centralized, or distributed), **strategies** (e.g., role-based or model-based), and **coordination protocols**."[tran-collaboration-survey](#tran-collaboration-survey)
- **"Peer" is thinner than the table implies.** Its owner is role-playing between two inception-prompted agents, not a routing mesh: "we propose a novel communicative agent framework named **role-playing** … using inception prompting to guide chat agents toward task completion."[li-camel](#li-camel) Meanwhile the module's own framework documents warn that peer transfer is conditional — `task` sub-agents must be leaves, and manual `transfer_to_agent` hand-backs are what make `chat` mode a peer.[adk-collaboration](#adk-collaboration)
- **The missing shape is layered aggregation.** "We construct a **layered MoA architecture** wherein each layer comprises multiple LLM agents. Each agent takes **all the outputs from agents in the previous layer** as auxiliary information in generating its response" — beating GPT-4 Omni on AlpacaEval 2.0 (65.1% vs 57.5%) with open-source models.[wang-mixture-of-agents](#wang-mixture-of-agents)
- **"Hierarchical" is SOP-driven, not merely nested supervisors.** MetaGPT "encodes **Standardized Operating Procedures (SOPs)** into prompt sequences," using "an assembly line paradigm" so that "agents with human-like domain expertise can **verify intermediate results** and reduce errors."[hong-metagpt](#hong-metagpt)
- **And topology is rarely the isolated variable.** MAST's own conclusion is that "failures identified by MAST often stem from **system design issues**, not just LLM limitations or simple prompt following, and require more than superficial fixes."[cemri-mast](#cemri-mast)

**Consequence for the module.** Present the table as a **map of coordination structures, not an enumeration** — add the layered-aggregation shape, note that the axes (structure / strategy / protocol) are orthogonal, and stop implying that choosing among the four is the design decision. The measured differences are in the handoff contracts and the artifact flow, which is the module's own thesis.

### 7. Framework and protocol claims: verified against the docs, with four corrections

Checked against the live ADK and A2A documentation rather than against the module's prose.

- **Confirmed exactly:** the mode table — `chat` is "Full interaction … Manual (via transfer)," `task` is "For clarification only … Automatic (via `finish_task`)," `single_turn` is "Disallowed … Automatic (with result)" and "Multiple tasks can run in parallel";[adk-collaboration](#adk-collaboration) the auto-injected delegation tools ("causes ADK to automatically generate a delegation tool for each subagent, **named after the subagent itself**");[adk-collaboration](#adk-collaboration) the isolation statement ("Each task or single-turn mode agent operates in its **own isolated session branch** … **cannot see what its peer agents are doing**");[adk-collaboration](#adk-collaboration) failover semantics ("If the selected agent throws an error **before yielding any events**, the router is called again with `errorContext` … If the selected agent throws an error **after yielding events**, the error propagates directly");[adk-routing](#adk-routing) and the A2A surface (`A2AServer`, `RemoteA2aAgent`).[adk-a2a](#adk-a2a)
- **Correction 1 — `chat` is the default.** The module's table lists it last with no marker; the docs label it "`chat` (default)" and "the default, current behavior." The module's advice to turn the dial *up* only where needed is therefore advice to *change* the default, which is worth saying outright.[adk-collaboration](#adk-collaboration)
- **Correction 2 — `mode` is sub-agent-only, and `task` mode is partly disabled.** "The `mode` setting is intended specifically for use with subagents invoked by a coordinator parent agent. **Do not configure a root agent with the mode setting**"; "`Task` mode agents must be **leaf agents** and cannot have subagents"; and "The collaborative mode `task` behavior is **disabled for use in graph-based workflows** in ADK Python v2.0.0." The module presents `task` mode as an unrestricted option.[adk-collaboration](#adk-collaboration)
- **Correction 3 — "deterministic routing" is a claim about *where* the decision is made, not about what makes it.** The router is explicit code, but it may call a model: "the router function can call a lightweight classifier model to categorize input and route to different agents accordingly. Because the router can be **async**, you can make **LLM calls inside it** before selecting an agent." The feature is also marked "Experimental" and "may change in future releases."[adk-routing](#adk-routing)
- **Correction 4 — the A2A lifecycle is longer than three states, and `done` is not one of them.** "It reports progress and asks for input as needed, until it reaches an **interrupted state** (such as `input-required` or `auth-required`) or a **terminal state** (such as `completed`, `canceled`, `rejected`, or `failed`)," with "**Task Immutability**" once terminal.[a2a-life-of-a-task](#a2a-life-of-a-task) The module's "submitted → working → done/failed/canceled" undercounts both categories.
- **One attribution fix.** The module's "A2A preserves … reasoning traces, long-running tool calls, and file artifacts" is ADK's *integration* capability list — "ADK's A2A integration provides three core capabilities" — not a guarantee stated by the A2A specification itself, which defines the data model (Message/Part/Task/Artifact) rather than the preservation of a model's thoughts.[adk-a2a](#adk-a2a), [a2a-spec](#a2a-spec)

---

## Bibliography

*Literature behind the module's claims, plus the framework documentation the module itself cites. **Citations use stable identifier keys, not position numbers.** Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed, or reordered without rewriting a single citation — the BibTeX model, minus a backend to assign numbers. The bibliography is therefore an unordered bullet list, not a ranked one: the order of entries carries no meaning, and no entry's identity changes if you move it. Every entry hyperlinks to the paper itself. Items tagged (industry doc) are vendor documentation, (practitioner) are non-peer-reviewed field reports, and (own synthesis) are the module's inferences rather than sourced claims. `cf.` marks a source that qualifies or contradicts the sentence it follows. `unsupported` is the module's unsupported-claims bucket and `own-synthesis` collects the course's own un-sourced synthesis: anything asserted above that no located source supports is cited there rather than to an invented reference.*

### Framework, protocol, and practitioner documentation

- <a id="adk-collaboration"></a>[adk-collaboration](#adk-collaboration) · [**Build collaborative agent teams** — Google ADK documentation](https://adk.dev/workflows/collaboration/index.md) (industry doc) — owns the coordinator/sub-agent model, the three `mode` values and their comparison table, the auto-injected delegation tools, and the isolated-session-branch statement.
- <a id="adk-routing"></a>[adk-routing](#adk-routing) · [**Route between agents** — Google ADK documentation](https://adk.dev/agents/routing/index.md) (industry doc) — owns `RoutedAgent`: explicit router functions, failover-before-first-event, planning mode, and complexity routing. *cf.* — the router may itself call a classifier model, and the feature is labelled experimental.
- <a id="adk-a2a"></a>[adk-a2a](#adk-a2a) · [**Introduction to A2A** — Google ADK documentation](https://adk.dev/a2a/intro/index.md) (industry doc) — owns the local-sub-agent vs. remote-agent decision rule, `A2AServer`/`RemoteA2aAgent`, and the three capabilities ADK's A2A integration carries across the wire (reasoning, long-running tools, artifacts).
- <a id="a2a-spec"></a>[a2a-spec](#a2a-spec) · [**Agent2Agent (A2A) Protocol Specification** — A2A Project (Linux Foundation)](https://a2a-protocol.org/latest/specification/) (industry doc) — the protocol data model, operations, transport bindings, and security scoping.
- <a id="a2a-life-of-a-task"></a>[a2a-life-of-a-task](#a2a-life-of-a-task) · [**Life of a Task** — A2A Protocol documentation](https://a2a-protocol.org/latest/topics/life-of-a-task/) (industry doc) — owns the task lifecycle: interrupted states (`input-required`, `auth-required`), terminal states (`completed`, `canceled`, `rejected`, `failed`), and task immutability.
- <a id="anthropic-building-effective-agents"></a>[anthropic-building-effective-agents](#anthropic-building-effective-agents) · [**Building effective agents** — Erik Schluntz, Barry Zhang (Anthropic)](https://www.anthropic.com/engineering/building-effective-agents) (industry doc) — owns the "find the simplest solution possible, and only increase complexity when needed" rule, the orchestrator-workers and evaluator-optimizer patterns, and the cost/latency framing of agentic systems.
- <a id="anthropic-multi-agent-research"></a>[anthropic-multi-agent-research](#anthropic-multi-agent-research) · [**How we built our multi-agent research system** — Jeremy Hadfield, Barry Zhang, Kenneth Lien, Florian Scholz, Jeremy Fox, Daniel Ford (Anthropic)](https://www.anthropic.com/engineering/multi-agent-research-system) (industry doc) — owns the 90.2% multi-agent result, the token-variance analysis (80% of variance is token usage), the 4×/15× token multipliers, and the filesystem-artifact pattern against the "game of telephone."
- <a id="cognition-dont-build-multi-agents"></a>[cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) · [**Don't Build Multi-Agents** — Walden Yan (Cognition)](https://cognition.com/blog/dont-build-multi-agents) (practitioner) — owns the two context-engineering principles ("share context, and share full agent traces" / "actions carry implicit decisions") and the explicit anti-multi-agent position.

### Failure modes, cost, and the case for restraint

- <a id="cemri-mast"></a>[cemri-mast](#cemri-mast) · [**Why Do Multi-Agent LLM Systems Fail?** — Mert Cemri, Melissa Z. Pan, Shuyi Yang, Lakshya A. Agrawal, Bhavya Chopra, Rishabh Tiwari, Kurt Keutzer, Aditya Parameswaran, Dan Klein, Kannan Ramchandran, Matei Zaharia, Joseph E. Gonzalez, Ion Stoica](https://arxiv.org/pdf/2503.13657) — *NeurIPS*, 2025. — owns MAST, the 14-mode multi-agent failure taxonomy (including *loss of conversation history*, *information withholding*, *ignored other agent's input*, and *no or incomplete verification*) and the 41%–86.7% measured failure rates.
- <a id="kapoor-ai-agents-matter"></a>[kapoor-ai-agents-matter](#kapoor-ai-agents-matter) · [**AI Agents That Matter** — Sayash Kapoor, Benedikt Stroebl, Zachary S. Siegel, Nitya Nadgir, Arvind Narayanan](https://arxiv.org/pdf/2407.01502) — arXiv:2407.01502, 2024. — owns the cost-controlled evaluation critique: accuracy-only benchmarking makes agents "needlessly complex and costly."
- <a id="li-more-agents"></a>[li-more-agents](#li-more-agents) · [**More Agents Is All You Need** — Junyou Li, Qin Zhang, Yangbin Yu, Qiang Fu, Deheng Ye](https://arxiv.org/pdf/2402.05120) — *TMLR*, 2024. *cf.* — "agents" here means sampled-and-voted instances, not delegated sub-agents; there is no handoff boundary to pay for.

### Coordination topologies

- <a id="tran-collaboration-survey"></a>[tran-collaboration-survey](#tran-collaboration-survey) · [**Multi-Agent Collaboration Mechanisms: A Survey of LLMs** — Khanh-Tung Tran, Dung Dao, Minh-Duong Nguyen, Quoc-Viet Pham, Barry O'Sullivan, Hoang D. Nguyen](https://arxiv.org/pdf/2501.06322) — arXiv:2501.06322, 2025. — owns the actors/types/structures/strategies/protocols characterization of collaboration mechanisms.
- <a id="wu-autogen"></a>[wu-autogen](#wu-autogen) · [**AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation** — Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Beibin Li, Erkang Zhu, Li Jiang, Xiaoyun Zhang, Shaokun Zhang, Jiale Liu, Ahmed Hassan Awadallah, Ryen W White, Doug Burger, Chi Wang](https://arxiv.org/pdf/2308.08155) — arXiv:2308.08155, 2023. — owns the conversable-agent infrastructure behind the supervisor-as-conversation pattern.
- <a id="hong-metagpt"></a>[hong-metagpt](#hong-metagpt) · [**MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework** — Sirui Hong, Mingchen Zhuge, Jiaqi Chen, Xiawu Zheng, Yuheng Cheng, Ceyao Zhang, Jinlin Wang, Zili Wang, Steven Ka Shing Yau, Zijuan Lin, Liyang Zhou, Chenyu Ran, Lingfeng Xiao, Chenglin Wu, Jürgen Schmidhuber](https://arxiv.org/pdf/2308.00352) — *ICLR*, 2024. — owns the SOP-encoded assembly-line decomposition with intermediate verification.
- <a id="li-camel"></a>[li-camel](#li-camel) · [**CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society** — Guohao Li, Hasan Abed Al Kader Hammoud, Hani Itani, Dmitrii Khizbullin, Bernard Ghanem](https://arxiv.org/pdf/2303.17760) — *NeurIPS*, 2023. — owns role-playing with inception prompting, the peer-to-peer pattern's origin.
- <a id="wang-mixture-of-agents"></a>[wang-mixture-of-agents](#wang-mixture-of-agents) · [**Mixture-of-Agents Enhances Large Language Model Capabilities** — Junlin Wang, Jue Wang, Ben Athiwaratkun, Ce Zhang, James Zou](https://arxiv.org/pdf/2406.04692) — arXiv:2406.04692, 2024. — owns the layered-aggregation topology, in which each layer consumes every output of the previous layer.

### Verification, debate, and self-correction

- <a id="du-multiagent-debate"></a>[du-multiagent-debate](#du-multiagent-debate) · [**Improving Factuality and Reasoning in Language Models through Multiagent Debate** — Yilun Du, Shuang Li, Antonio Torralba, Joshua B. Tenenbaum, Igor Mordatch](https://arxiv.org/pdf/2305.14325) — *ICML*, 2024. — owns the multi-agent debate pattern: propose/critique/revise rounds across independent model instances.
- <a id="smit-going-mad"></a>[smit-going-mad](#smit-going-mad) · [**Should We Be Going MAD? A Look at Multi-Agent Debate Strategies for LLMs** — Andries Smit, Paul Duckworth, Nathan Grinsztajn, Thomas D. Barrett, Arnu Pretorius](https://arxiv.org/pdf/2311.17371) — *ICML*, 2024. *cf.* — finds debate protocols do not reliably outperform self-consistency or ensembling, and are harder to optimize.
- <a id="madaan-self-refine"></a>[madaan-self-refine](#madaan-self-refine) · [**Self-Refine: Iterative Refinement with Self-Feedback** — Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank Gupta, Bodhisattwa Prasad Majumder, Katherine Hermann, Sean Welleck, Amir Yazdanbakhsh, Peter Clark](https://arxiv.org/pdf/2303.17651) — *NeurIPS*, 2023. *cf.* — the pro-self-correction half of a dispute; contrast [huang-cannot-self-correct](#huang-cannot-self-correct).
- <a id="huang-cannot-self-correct"></a>[huang-cannot-self-correct](#huang-cannot-self-correct) · [**Large Language Models Cannot Self-Correct Reasoning Yet** — Jie Huang, Xinyun Chen, Swaroop Mishra, Huaixiu Steven Zheng, Adams Wei Yu, Xinying Song, Denny Zhou](https://arxiv.org/pdf/2310.01798) — *ICLR*, 2024. — owns the finding that intrinsic self-correction fails or degrades without *external* feedback, which is what makes a separate checker worth considering.
- <a id="mcaleese-criticgpt"></a>[mcaleese-criticgpt](#mcaleese-criticgpt) · [**LLM Critics Help Catch LLM Bugs** — Nat McAleese, Rai Michael Pokorny, Juan Felipe Ceron Uribe, Evgenia Nitishinskaya, Maja Trebacz, Jan Leike](https://arxiv.org/pdf/2407.00215) — arXiv:2407.00215, 2024. *cf.* — critics beat paid human review on real bugs, and also "hallucinate bugs that could mislead humans."

### What crosses the boundary: context, position, and distraction

- <a id="liu-lost-in-the-middle"></a>[liu-lost-in-the-middle](#liu-lost-in-the-middle) · [**Lost in the Middle: How Language Models Use Long Contexts** — Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang](https://arxiv.org/pdf/2307.03172) — *TACL*, 2023. — owns the position-sensitivity result the module's context-isolation argument rests on.
- <a id="shi-irrelevant-context"></a>[shi-irrelevant-context](#shi-irrelevant-context) · [**Large Language Models Can Be Easily Distracted by Irrelevant Context** — Freda Shi, Xinyun Chen, Kanishka Misra, Nathan Scales, David Dohan, Ed Chi, Nathanael Schärli, Denny Zhou](https://arxiv.org/pdf/2302.00093) — *ICML*, 2023. — owns the finding that irrelevant context measurably degrades accuracy, the dilution half of the isolation argument.

### Unsupported claims and own synthesis

- <a id="unsupported"></a>[unsupported](#unsupported) · **Unsupported.** Claims made in this module that no located source supports. Cited inline as [unsupported](#unsupported) rather than to an invented reference. Currently:
    - **"Every additional agent must earn its place," read over *all* agents.** The sampling-and-voting literature shows accuracy scaling with agent count and requiring no justification beyond the compute, because no handoff exists.[li-more-agents](#li-more-agents) The supported version is narrower: every *delegated* agent — every one that introduces a boundary — must earn its place.
    - **"A verifier agent doubles the cost of the step it checks."** Arithmetic from the module, not a measured figure. The located multipliers are Anthropic's "4× more tokens than chat interactions" and "15× more tokens than chats."[anthropic-multi-agent-research](#anthropic-multi-agent-research)
    - **The opening scene's numbers** ("latency tripled, cost quintupled," "the answers were no better"). An invented illustration, flagged as such in the text; the mechanisms it names are the cited ones.
- <a id="own-synthesis"></a>[own-synthesis](#own-synthesis) · **Own synthesis (not sourced).** Claims this module makes that are the course's framing rather than literature findings, flagged so they are not mistaken for citations:
    - The **four-payoff test** as a decision rule, and **"start with one agent"** as the default posture. Each payoff is separately sourced; the rule that combines them, and the weighting that makes restraint the default, are the course's.
    - **"The hard part is not the agents, it's the boundaries between them."** The literature supports the individual costs of boundaries;[cemri-mast](#cemri-mast), [cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) the ranking is the module's.
    - **"Multi-agent is the most over-adopted pattern in the field."** The direction is supported;[cemri-mast](#cemri-mast), [kapoor-ai-agents-matter](#kapoor-ai-agents-matter), [cognition-dont-build-multi-agents](#cognition-dont-build-multi-agents) the superlative is not a measured ranking.
    - The **DSH mapping** in the "In DSH" line is a first-party description of this repository, not a literature claim.

---

**Next module:** [M12 — Evaluation Harnesses](../12-evaluation/README.md) — how we know the harness works, and how we keep knowing it.
