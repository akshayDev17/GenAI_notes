# M13 · Reliability Engineering for Agents

> **Module question:** How do we make an agent that degrades gracefully instead of failing hard?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** payments-adjacent automation (fictional)

---

## Opening scene — the agent that died at the first hiccup

The payments agent was mid-task — it had looked up the order, drafted the refund, and was calling the approval service — when that service timed out. The agent, unencumbered by any notion of "try again" or "fall back," reported a cryptic failure and *stopped*. The customer waited, re-asked, and got the same failure. Three retries later (all from the *customer*), the task was abandoned, and a human had to redo the whole thing by hand.

The failure wasn't the timeout. Timeouts happen. The failure was that the agent had **one mode: succeed or die.** There was no ladder between "it worked" and "it crashed" — no retry, no fallback, no graceful handoff, no safe stop.

This module is about building that ladder. Reliability engineering for agents is the classic discipline — retries, timeouts, fallbacks, circuit breakers — moved *up the stack*: not protecting a database from a flaky network, but protecting a *task* from a flaky model, a flaky tool, and a flaky world.[sre-cascading-failures](#sre-cascading-failures), [candea-crash-only](#candea-crash-only), [principles-of-chaos](#principles-of-chaos) That the repertoire *transfers* — that a model failure is the same kind of thing as a network failure and yields to the same controls — is this module's framing rather than a located result.[unsupported](#unsupported)

> **Failure mode (the module in one line):** designing the agent for the happy path and treating every failure as an exception to crash on. The happy path is the rare case; the degradation ladder is the system.[mast-multi-agent-failure](#mast-multi-agent-failure)

---

## The degradation ladder

The core artifact of this module.[own-synthesis](#own-synthesis) When a step fails, the agent climbs a ladder — each rung degrades *less gracefully* but *never* fails hard:

```
retry → fallback → degrade → human handoff → safe fail
```

1. **Retry** — the same call again. Cheap, right for *transient* failures (a timeout, a rate limit). Wrong for *deterministic* failures (the tool says "not found" — retrying won't help).[sre-cascading-failures](#sre-cascading-failures) M8's error semantics told you which is which: `retryable: true` vs. `false`. (ADK's `RetryConfig(max_attempts=3)` does this automatically — and, from the 2.0 notes, it's why you should *let exceptions propagate* out of tools rather than swallowing them in a broad `except`, which disables the framework's own retry.)[adk-2-0](#adk-2-0) *cf.* — `RetryConfig` matches on the exception *class name*, and its default `exceptions=None` retries every exception, so the retryable/deterministic split is configuration, not something the framework infers.[adk-retryconfig](#adk-retryconfig) "Cheap" also assumes the call is safe to repeat, which is a property of the *tool*, not the retry policy.[adk-callback-patterns](#adk-callback-patterns) A retry policy without randomized backoff and a retry budget is itself an outage mechanism.[aws-backoff-jitter](#aws-backoff-jitter)
2. **Fallback** — a different model, or a different path. A cheap model that times out falls back to a different provider (ADK's `RoutedLlm`: the router returns `primary`, and on error is re-called to pick `fallback`).[adk-model-routing](#adk-model-routing) A primary tool that's down falls back to a secondary data source.[adk-plugins](#adk-plugins) *cf.* — the cost literature routes *proactively*, on predicted query difficulty, rather than reactively on error.[routellm](#routellm), [frugalgpt](#frugalgpt), [yue-llm-cascades](#yue-llm-cascades)
3. **Degrade** — do *less*, but finish. Can't get the live price? Answer with the *cached* price and a "as of" caveat. Can't summarize the full contract? Summarize the first three sections and flag the omission.[sre-cascading-failures](#sre-cascading-failures), [zilberstein-anytime](#zilberstein-anytime) *cf.* — a caveat is only as good as the model's ability to know it is degraded: models "often output incorrect answers instead of abstaining when the context is not" sufficient.[joren-sufficient-context](#joren-sufficient-context), [jiang-calibration](#jiang-calibration), [lin-uncertainty-in-words](#lin-uncertainty-in-words)
4. **Human handoff** — stop the machine, hand to a person. The right rung for anything *irreversible* or *ambiguous* (M8's confirmation, M6's escalation).[chow-reject-option](#chow-reject-option), [madras-predict-responsibly](#madras-predict-responsibly), [mozannar-consistent-estimators](#mozannar-consistent-estimators), [horvitz-mixed-initiative](#horvitz-mixed-initiative) ADK supplies both a tool-level approval pause (`require_confirmation`) and a model-free graph pause that "does not require a model, which makes the pause deterministic."[adk-tool-confirmation](#adk-tool-confirmation), [adk-human-input](#adk-human-input) *cf.* — the rung assumes a human who can catch it; the automation literature says the opposite is common.[bainbridge-ironies](#bainbridge-ironies), [parasuraman-riley](#parasuraman-riley)
5. **Safe fail** — stop *safely*: leave state consistent, log the full context (M16), tell the user clearly what happened and what's next. Failing safe is a *designed outcome*, not a crash.[candea-crash-only](#candea-crash-only)

**The design principle:** the rung you land on is a function of *failure type* and *consequence* — not a single global policy. A timeout gets retries; a "not found" gets degradation or safe-fail; an irreversible action gets human handoff *before* it executes, not after.[sre-cascading-failures](#sre-cascading-failures), [chow-reject-option](#chow-reject-option) *(The specific mapping is this module's own.)*[own-synthesis](#own-synthesis)

---

## Budget governance is reliability

Cost and token budgets are usually filed under "ops," but they're *reliability* controls: an unbounded run is a *failure* (the AutoGPT loops, M2's catalog) that burns money and never completes.[mast-multi-agent-failure](#mast-multi-agent-failure), [metr-long-tasks](#metr-long-tasks), [frugalgpt](#frugalgpt) The budgets:

- **Cost cap** — a ceiling on spend per run; hit it → stop.[frugalgpt](#frugalgpt)
- **Token cap** — a ceiling on context/iteration size (M4's per-turn budget, M10's loop budget).[routellm](#routellm)
- **Run limit** — a ceiling on iterations/steps (M10's `max_iterations`).[adk-retryconfig](#adk-retryconfig)

These are the *governor* on the engine. An agent without a cost cap isn't "more capable" — it's a runaway with a credit card.[own-synthesis](#own-synthesis)

---

## Failure recovery: checkpoints and partial completion

Reliability also means *not losing work when a long task fails*:

- **Checkpointing** — persist intermediate state (M7's state) so a mid-task failure can *resume* rather than restart.[elnozahy-rollback-recovery](#elnozahy-rollback-recovery) ADK's runtime supports **resume** (`runtime/resume`) — re-enter a stopped run from where it was.[adk-resume](#adk-resume) *cf.* — the opposing position is crash-only design, which argues recovery code is the least-exercised code and should not be a separate path.[candea-crash-only](#candea-crash-only)
- **Partial completion** — when a multi-step task fails at step 6 of 9, *return* the completed 5 steps with a clear "here's what's done, here's what's left," instead of discarding everything. The user gets value; the failure is scoped, not total.[garcia-molina-sagas](#garcia-molina-sagas), [zilberstein-anytime](#zilberstein-anytime) *cf.* — production RAG studies name **FP7 "Incomplete"** as a failure point: "Incomplete answers are not incorrect but miss some of the information even though that information was in the context and available for extraction."[barnett-seven-failure-points](#barnett-seven-failure-points)

The point of both: **failure should cost the *remaining* work, not the *completed* work.**[own-synthesis](#own-synthesis)

---

## Testing reliability: chaos drills

You can't *assume* the ladder works; you *drill* it. The reliability-testing move is the same as chaos engineering for distributed systems:[principles-of-chaos](#principles-of-chaos)

- **Tool outage drill** — kill the approval service; verify the agent lands on the right rung (fallback or human handoff), not a crash.[toolrobustbench](#toolrobustbench), [fission-grpo](#fission-grpo)
- **Model degradation drill** — point the agent at a slower, dumber model; verify it degrades gracefully.[tau-bench](#tau-bench)
- **Budget-exhaustion drill** — force the run to hit its cap; verify it safe-fails with a clear message and consistent state.[mast-multi-agent-failure](#mast-multi-agent-failure)

Each drill is a *test that the ladder exists and the rungs are in the right order*. If a drill shows the agent crashing instead of climbing, that's a reliability bug — and it's exactly what the opening scene's team never checked for.[sre-cascading-failures](#sre-cascading-failures) *cf.* — the drill must assert the *diagnosis*, not just the absence of a crash: agents "often fall into repetitive invalid re-invocations instead of interpreting the feedback and recovering."[pararecover](#pararecover), [toolemu](#toolemu)

---

## Worked example: the payments-adjacent automation

The domain spine, as a ladder. The agent approves refunds (with M6's $50 boundary). Here's the full ladder for one refund task:

- **Retry:** the order-lookup tool times out → `RetryConfig` retries twice (transient).[adk-retryconfig](#adk-retryconfig)
- **Fallback:** the primary pricing model errors before output → `RoutedLlm` falls back to the secondary model.[adk-model-routing](#adk-model-routing)
- **Degrade:** the live balance API is down → the agent reports the *last known* balance, clearly flagged.[sre-cascading-failures](#sre-cascading-failures)
- **Human handoff:** refund > $50 → `require_confirmation` *before* the refund tool executes (irreversible).[adk-tool-confirmation](#adk-tool-confirmation)
- **Safe fail:** approval service unreachable after all retries → the agent leaves the ticket in "pending," records the full context, and tells the user "I couldn't complete this; it's queued for review."[adk-resume](#adk-resume)

No rung crashes. Every failure lands somewhere *intentional*. That's the whole module: **graceful degradation is a ladder you design, not a property the model has.**[own-synthesis](#own-synthesis) *cf.* — models can be trained to "express calibrated uncertainty about [their] own answers in natural language," so the property is not entirely absent from the model either.[lin-uncertainty-in-words](#lin-uncertainty-in-words)

> **Tradeoff (the ledger entry):**
> - **Resilience vs. latency.** Every retry and fallback costs time. Bound them (max attempts, timeouts) so resilience doesn't become slowness.[sre-cascading-failures](#sre-cascading-failures), [aws-backoff-jitter](#aws-backoff-jitter)
> - **Degradation vs. fidelity.** "Do less but finish" trades correctness for completion — right when a *caveated* answer beats a *crash*.[zilberstein-anytime](#zilberstein-anytime), [barnett-seven-failure-points](#barnett-seven-failure-points)
> - **Autonomy vs. safety at the boundary.** The human-handoff rung is where reliability and governance meet: irreversible actions climb *up* to the human, not *down* to a retry.[chow-reject-option](#chow-reject-option), [madras-predict-responsibly](#madras-predict-responsibly), [bainbridge-ironies](#bainbridge-ironies)

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Write the degradation ladder for a mission-critical agent of your choice (or the payments brief).

1. **Name the failure classes.** List the three most likely failures (tool timeout, model error, upstream outage, budget exhaustion…) and, for each, whether it's *transient* or *deterministic* (M8's retryable-vs-fatal split).[sre-cascading-failures](#sre-cascading-failures)
2. **Write the ladder.** For each failure, specify the rung it lands on — retry → fallback → degrade → human handoff → safe fail — with the *concrete* action at that rung (which model/tool, what the user sees).[own-synthesis](#own-synthesis)
3. **Set the budgets.** State the cost cap, token cap, and run limit — as concrete numbers, and where each triggers a safe-fail.[frugalgpt](#frugalgpt)
4. **Design the checkpoint.** Which intermediate state do you persist so a mid-task failure can *resume* instead of restart? Name the state keys (M7's prefixes).[adk-resume](#adk-resume)
5. **Write one chaos drill.** Pick a failure, write the drill (what you kill, what "pass" looks like), and state which rung you expect the agent to land on.[principles-of-chaos](#principles-of-chaos)
6. **Write the ADR.** "Reliability & degradation policy" — the ladder, the budgets, and the residual risk you're accepting (e.g., "a total approval-service outage queues tasks for review rather than completing them").[own-synthesis](#own-synthesis)

**Why this exercise matters.** Reliability is where the harness earns its keep in production — the difference between an agent that *works until it doesn't* and one that *degrades along a designed path*. The ladder you write here is the thing that turns "the model failed" into "the system handled it."[own-synthesis](#own-synthesis)

---

**In DSH:** reliability lives in `guard` (repeat-tool guard, budgets) + `sandbox` (resource confinement) + `runtime-diagnostics` — the containment and degradation surface.

## Sources (ADK docs)

- [Route between models — RoutedLlm, fallback on error](https://adk.dev/agents/models/routing/index.md)[adk-model-routing](#adk-model-routing)
- [Welcome to ADK 2.0 — RetryConfig, automatic retries](https://adk.dev/2.0/index.md)[adk-2-0](#adk-2-0)
- [RetryConfig — per-node retry policy](https://github.com/google/adk-python/blob/main/docs/guides/workflow/retry_config/index.md)[adk-retryconfig](#adk-retryconfig)
- [Resume stopped agents](https://adk.dev/runtime/resume/index.md)[adk-resume](#adk-resume)
- [Get action confirmation for ADK Tools](https://adk.dev/tools-custom/confirmation/index.md)[adk-tool-confirmation](#adk-tool-confirmation)
- [Human input for agent workflows](https://adk.dev/graphs/human-input/index.md)[adk-human-input](#adk-human-input)
- [Plugins — error-handling callbacks](https://adk.dev/plugins/index.md)[adk-plugins](#adk-plugins)
- [Design Patterns and Best Practices for Callbacks](https://adk.dev/callbacks/design-patterns-and-best-practices/index.md)[adk-callback-patterns](#adk-callback-patterns)

---

## Where the literature disagrees with this module

- The ladder is the right shape, and most of its rungs are backed by decades of work on distributed systems, human factors, and reliability engineering. But several of the module's load-bearing claims are asserted more strongly than the sources allow, and two of them are contradicted by the module's *own* cited framework.
- The sections below record what the module says, what the sources say, and what to change.

### 1. Retry is not a free rung — it is where a large share of reliability incidents are created

- The module calls retry "cheap" and gives it first place on the ladder, with no mention of backoff, jitter, or a retry budget.
- The literature treats unbounded retry as a *cause* of failure, not a remedy for it.
- **Retries can amplify an outage into a cascading failure.** A worked example in the SRE book shows a frontend retrying failed requests until the backend receives 10,200 QPS "200 QPS of which are failing due to overload," and then: "The volume of retries grows: 100 QPS of retries in the first second leads to 200 QPS, then to 300 QPS, and so on." The book's summary is blunt: "the point remains that retries can destabilize a system."[sre-cascading-failures](#sre-cascading-failures)
- **Nested retries multiply.** "avoid amplifying retries by issuing retries at multiple levels: a single request at the highest layer may produce a number of attempts as large as the *product* of the number of attempts at each layer to the lowest layer… then a single user action may create 64 attempts (4^3) on the database."[sre-cascading-failures](#sre-cascading-failures)
- **Crash-only design names the same hazard.** "resubmitting requests to a component that is recovering can overload it and make it fail again."[candea-crash-only](#candea-crash-only)
- **Chaos engineering lists it as a first-class systemic weakness.** The canonical list of weaknesses to hunt includes "retry storms from improperly tuned timeouts."[principles-of-chaos](#principles-of-chaos)
- **Consequence.** Keep retry as rung 1, but stop calling it cheap.
    - The rung needs three things the module never names: randomized exponential backoff, a bounded attempt count, and a retry budget. The SRE book prescribes all three — "Always use randomized exponential backoff when scheduling retries"; "Limit retries per request"; "Consider having a server-wide retry budget."[sre-cascading-failures](#sre-cascading-failures)
    - This is the module's biggest omission, because an agent ladder multiplies rungs: a retrying model calling a retrying tool calling a retrying API is the 4^3 case with the model in the loop.
    - **The module names circuit breakers and then never uses one.** The opening paragraph lists "retries, timeouts, fallbacks, circuit breakers" as the discipline being moved up the stack, but no rung of the ladder trips a breaker. Without one, rungs 1 and 2 can keep offering traffic to a dependency that is already failing; the SRE book's client-side answer is the retry budget, and its server-side answer is to "fail early and cheaply" rather than accept work that will not complete.[sre-cascading-failures](#sre-cascading-failures)

### 2. For a payments agent, "retry the same call" can duplicate an irreversible side effect

- The module's worked example retries a transient timeout with no precondition, and the opening scene is a *refund* — the one operation where a duplicate is worse than a failure.
- The literature makes idempotency a *precondition* of retry, not a detail.
- **The module's own framework documents the duplicate-run hazard.** ADK's resume documentation warns: "the Resume feature ensures that the Tools in an agent are run ***at least once***, and may run more than once when resuming a workflow. If your agent uses Tools where duplicate runs would have a negative impact, such as purchases, you should modify the Tool to check for and prevent duplicate runs."[adk-resume](#adk-resume)
- **ADK's callback guidance repeats it for retries.** "Consider Idempotency: If a callback performs actions with external side effects … design it to be idempotent (safe to run multiple times with the same input) if possible, to handle potential retries in the framework or your application."[adk-callback-patterns](#adk-callback-patterns)
- **Crash-only design states the limit of the whole approach.** After describing a restart/retry architecture, the authors write: "In order for the restart/retry architecture to be highly available and correct, most requests it serves must be idempotent. This requirement might be inappropriate for some applications."[candea-crash-only](#candea-crash-only)
- **Consequence.** Rung 1 needs a guard the module omits: retry only if the operation is idempotent or carries a key that makes it so. A timeout is not evidence that the effect did not happen — it is evidence that you do not know whether it happened.
    - For the payments spine specifically, the retry rung and the safe-fail rung must be chosen by *side-effect status*, not by failure type: an unacknowledged refund is a reconciliation problem, not a retry.

### 3. "RetryConfig does this automatically" is not what the documentation says

- The module asserts that `RetryConfig(max_attempts=3)` "does this automatically" — that is, applies M8's `retryable: true` / `false` distinction.
- The published `RetryConfig` documentation describes a different mechanism.
- **Matching is on exception class name, not on a retryability flag.** "**The match is on the exact class name, not `isinstance`.** Listing `ConnectionError` therefore does not retry a `ConnectionResetError`, and listing `Exception` retries nothing at all."[adk-retryconfig](#adk-retryconfig)
- **The default retries everything.** The `exceptions` field defaults to `None`, which "means retry on all exceptions" — so a deterministic failure is retried unless you explicitly exclude it.[adk-retryconfig](#adk-retryconfig) The default `max_attempts` is also 5, not 3.[adk-retryconfig](#adk-retryconfig)
- **Retried nodes can re-run side-effecting children.** "A child that produced neither [output nor state change] leaves nothing to replay and runs again on every attempt, so give a side-effecting node an output or a state change if repeating it would be harmful."[adk-retryconfig](#adk-retryconfig)
- **The retry budget resets on resume.** "**The attempt counter does not survive an interrupt.** It is **not** persisted. If the workflow is interrupted… and is later resumed, a node that has to run again starts counting from 1 with its full budget of attempts back."[adk-retryconfig](#adk-retryconfig)
- **Consequence.** Rewrite the parenthetical: `RetryConfig` implements *a* retry policy, and the transient/deterministic split is configuration you supply (`exceptions=[...]`), not a framework inference from an error's `retryable` flag.
    - The one claim in that sentence that the docs *do* support verbatim is the exception-swallowing warning: "Allow standard exceptions to propagate out of your tools so the framework can evaluate them against your configured `RetryConfig`… Never catch `BaseException` unless you are explicitly re-raising the exception."[adk-2-0](#adk-2-0)

### 4. Retrying a *model* error is the self-correction question, and the literature is split

- The module's ladder handles model errors by retrying (rung 1) or re-routing (rung 2). It does not distinguish a retry that carries new information from a retry that does not.
- The self-correction literature is genuinely divided on whether a model can fix its own output without external feedback, and the split is the single most relevant result for rung 1.
- **For:** Self-Refine reports that "outputs generated with Self-Refine are preferred by humans and automatic metrics over those generated with the same LLM using conventional one-step generation, improving by ~20% absolute on average in task performance."[madaan-self-refine](#madaan-self-refine) Reflexion reports "a 91% pass@1 accuracy on the HumanEval coding benchmark, surpassing the previous state-of-the-art GPT-4 that achieves 80%."[shinn-reflexion](#shinn-reflexion)
- **Against:** "In the context of reasoning, our research indicates that LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction."[huang-self-correct](#huang-self-correct)
- **Consequence.** Split rung 1 in two. A retry that carries new information — a tool result, a compiler error, a test failure, a retrieved document — is supported; Reflexion's own mechanism is reflection on "task feedback signals." A retry that re-asks the same question with the same context is exactly the "intrinsic self-correction" case the negative result covers.
    - The module's worked example is on the right side of this line by accident: the retry follows a tool timeout, but nothing in the ladder says the distinction matters.

### 5. Checkpoint-and-resume is contested by crash-only design, and it re-runs work

- The module presents resume as an unambiguous improvement: "so a mid-task failure can *resume* rather than restart."
- Two sources resist that framing.
- **Crash-only design argues against a separate recovery path.** "There is only one way to stop such software -- by crashing it -- and only one way to bring it up -- by initiating recovery." The reason is that the recovery path is the one that never gets exercised: "Recovery code deals with exceptional situations, and must run flawlessly. Unfortunately, exceptional situations are difficult to handle, occur seldom, and are not trivial to simulate during development; this often leads to unreliable recovery code. In crash-only systems, however, recovery code is exercised every time the system starts up."[candea-crash-only](#candea-crash-only)
- **Resume re-executes tools.** ADK's own caution, quoted in §2, guarantees at-least-once tool execution on resume.[adk-resume](#adk-resume) Combined with the non-persisted attempt counter,[adk-retryconfig](#adk-retryconfig) a resume can also restore a full retry budget to a node that already exhausted it.
- **Resume is nonetheless the well-studied mainstream.** Rollback-recovery is a mature field with a taxonomy of checkpoint-based and log-based protocols, and the survey's framing is about *restoring system state*, not about never having a recovery path.[elnozahy-rollback-recovery](#elnozahy-rollback-recovery)
- **Consequence.** Keep checkpointing and resume, and record the tradeoff the module currently hides: resume changes *at-most-once* failure into *at-least-once* execution.
    - The ADR in the design exercise should say which steps are replay-safe and what happens when a replayed step is not — this is the same idempotency precondition as §2, reaching a second rung.

### 6. The ladder assumes the agent *notices* the failure — and that is the measured bottleneck

- The tool-outage drill says to "verify the agent lands on the right rung (fallback or human handoff), not a crash." Landing on a rung requires detecting the failure, classifying it, and choosing.
- The agent-reliability literature locates most of the failure in that middle step.
- **Handling tool output is the dominant failure stage.** A stage-wise perturbation benchmark "attributes failures to tool selection, schema grounding, argument binding, tool-output/runtime-feedback handling, and E2E task success" and finds "tool-output/observation perturbation the dominant bottleneck."[toolrobustbench](#toolrobustbench)
- **Models loop rather than recover.** "after a tool-call error, smaller models often fall into repetitive invalid re-invocations instead of interpreting the feedback and recovering."[fission-grpo](#fission-grpo)
- **Even strong models struggle with propagation and replanning.** Benchmarks "reveal that even state-of-the-art models still struggle with multi-turn error propagation, implicit tool-use failures, and precise replanning."[pararecover](#pararecover)
- **Unsafe tool behaviour is common even in the safest agents.** "even the safest LM agent exhibits such failures 23.9% of the time according to our evaluator."[toolemu](#toolemu)
- **Consequence.** Add a rung 0 to the ladder's *test*: the failure must be surfaced to the model in a form it can act on, and the drill's pass criterion must assert the *diagnosis*, not merely the absence of a crash.
    - This is also a design instruction, not only a test: the tool result the model receives on failure is part of the reliability surface.

### 7. "Degrade" and "safe fail" have a reciprocal failure mode the module never names

- The module frames doing less and stopping early as the *safe* rungs, and treats a partial result as a win. It never names over-refusal, excessive abstention, or premature termination.
- The literature measures all three.
- **Models decline to abstain when they should.** Stratifying errors by context sufficiency, "larger models with higher baseline performance (Gemini 1.5 Pro, GPT 4o, Claude 3.5) excel at answering queries when the context is sufficient, but often output incorrect answers instead of abstaining when the context is not."[joren-sufficient-context](#joren-sufficient-context) Confidence is a weak proxy for correctness: question-answering models are poorly calibrated.[jiang-calibration](#jiang-calibration)
- **And they refuse when they should not.** Exaggerated safety is a measured failure mode: XSTest "comprises 250 safe prompts across ten prompt types that well-calibrated models should not refuse to comply with, and 200 unsafe prompts as contrasts."[rottger-xstest](#rottger-xstest) OR-Bench is framed as "the first large-scale over-refusal benchmark."[cui-or-bench](#cui-or-bench)
- **Agents also stop too early.** MAST's taxonomy includes the failure mode **FM-3.1 Premature termination** alongside **FM-1.5 Unaware of stopping conditions** — the two directions of the same control problem.[mast-multi-agent-failure](#mast-multi-agent-failure)
- **"Incomplete" is a named failure point, not a success.** "FP7 Incomplete: Incomplete answers are not incorrect but miss some of the information even though that information was in the context and available for extraction."[barnett-seven-failure-points](#barnett-seven-failure-points)
- **Consequence.** The ladder needs both edges described. A rung that degrades too eagerly and a rung that crashes are different bugs, and the module's framing makes only the second one visible.
    - "Partial completion" should be specified as *flagged* completion: the missing work must be named, or the result is FP7 rather than a win.

### 8. Human handoff presumes a human who can catch it

- The module gives the handoff rung the strongest normative claim in the piece: irreversible actions "climb *up* to the human."
- The human-factors literature says the human at the top of the ladder is often the least able to intervene.
- **Automation degrades the operator it leaves behind.** Bainbridge's abstract: "This paper discusses the ways in which automation of industrial processes may expand rather than eliminate problems with the human operator."[bainbridge-ironies](#bainbridge-ironies)
- **Over-reliance is the documented failure mode.** "Misuse refers to over reliance on automation, which can result in failures of monitoring or decision biases."[parasuraman-riley](#parasuraman-riley)
- **Deference is a learnable, well-studied mechanism.** The reject option originates in "an optimum rejection rule" and "a general relation between the error and reject probabilities";[chow-reject-option](#chow-reject-option) learning to defer has consistent estimators and conditional formulations.[madras-predict-responsibly](#madras-predict-responsibly), [mozannar-consistent-estimators](#mozannar-consistent-estimators) Mixed-initiative design supplies the interaction principles for when to hand over.[horvitz-mixed-initiative](#horvitz-mixed-initiative)
- **The handoff rung is not universally available in the module's own framework.** ADK's tool confirmation has documented limitations: "`DatabaseSessionService` is not supported by this feature" and "`VertexAiSessionService` is not supported by this feature."[adk-tool-confirmation](#adk-tool-confirmation)
- **Consequence.** Keep the rung — the deferral literature supports it — but specify it as a *designed review*, not an automatic safety net.
    - The ADR should record who reviews, on what signal, and whether the deployed session backend can pause at all. A handoff prompt that a tired operator rubber-stamps is a rung that exists on paper only.

---

## Bibliography

- *Literature behind the module's claims, with the framework documentation the module itself cites.*
    - **Citations use stable identifier keys, not position numbers.** Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed, or reordered without rewriting a single citation — the BibTeX model, minus a backend to assign numbers.
    - The bibliography is therefore an unordered bullet list, not a ranked one: the order of entries carries no meaning. Every entry hyperlinks to the paper's PDF.
    - Items tagged (industry doc) are vendor documentation, (preprint) are not yet peer-reviewed, and (own synthesis) are the module's inferences rather than sourced claims.
    - `cf.` marks a source that qualifies or contradicts the sentence it follows.
    - `unsupported` is the module's unsupported-claims bucket and `own-synthesis` collects the course's own un-sourced synthesis.

### Framework documentation (industry docs)

- <a id="adk-model-routing"></a>[adk-model-routing](#adk-model-routing) · [**Route between models** — Google ADK documentation](https://adk.dev/agents/models/routing/index.md) (industry doc) — the source of the `RoutedLlm` fallback rule: "If the selected model fails before producing any output, the routing function is called again with error context so it can select a different model."
- <a id="adk-2-0"></a>[adk-2-0](#adk-2-0) · [**Welcome to ADK 2.0** — Google ADK documentation](https://adk.dev/2.0/index.md) (industry doc) — owns the propagate-don't-swallow rule: "Allow standard exceptions to propagate out of your tools so the framework can evaluate them against your configured `RetryConfig`… Never catch `BaseException` unless you are explicitly re-raising the exception."
- <a id="adk-retryconfig"></a>[adk-retryconfig](#adk-retryconfig) · [**RetryConfig** — google/adk-python repository documentation](https://github.com/google/adk-python/blob/main/docs/guides/workflow/retry_config/index.md) (industry doc) — the per-node retry policy itself: exact-class-name exception matching, `exceptions=None` meaning "retry on all exceptions," a default `max_attempts` of 5, and the note that the attempt counter is not persisted across an interrupt. **There is no `RetryConfig` page on `adk.dev`.** *(Only the repository doc was reachable.)*
- <a id="adk-resume"></a>[adk-resume](#adk-resume) · [**Resume stopped agents** — Google ADK documentation](https://adk.dev/runtime/resume/index.md) (industry doc) — owns resume, and the at-least-once side-effect caution: "the Resume feature ensures that the Tools in an agent are run ***at least once***, and may run more than once when resuming a workflow."
- <a id="adk-tool-confirmation"></a>[adk-tool-confirmation](#adk-tool-confirmation) · [**Get action confirmation for ADK Tools** — Google ADK documentation](https://adk.dev/tools-custom/confirmation/index.md) (industry doc) — owns the pre-execution approval pause (`require_confirmation`, or a confirmation-threshold function) and its session-backend limitations.
- <a id="adk-human-input"></a>[adk-human-input](#adk-human-input) · [**Human input for agent workflows** — Google ADK documentation](https://adk.dev/graphs/human-input/index.md) (industry doc) — owns the model-free HITL pause: "These nodes do not require artificial intelligence (AI) models to run, which can make the input process more predictable and reliable."
- <a id="adk-plugins"></a>[adk-plugins](#adk-plugins) · [**Plugins** — Google ADK documentation](https://adk.dev/plugins/index.md) (industry doc) — owns the framework's built-in fallback hook: from `on_tool_error_callback`, "Return a dict to suppress the exception, provide a fallback result."
- <a id="adk-callback-patterns"></a>[adk-callback-patterns](#adk-callback-patterns) · [**Design Patterns and Best Practices for Callbacks** — Google ADK documentation](https://adk.dev/callbacks/design-patterns-and-best-practices/index.md) (industry doc) — owns the idempotency-under-retry guidance quoted in §2.
- <a id="aws-backoff-jitter"></a>[aws-backoff-jitter](#aws-backoff-jitter) · [**Exponential Backoff And Jitter** — AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) (industry doc) — the practitioner origin of randomized backoff in retry loops; cited by the Google SRE book as the reference for "Always use randomized exponential backoff when scheduling retries."
- <a id="sre-cascading-failures"></a>[sre-cascading-failures](#sre-cascading-failures) · [**Addressing Cascading Failures** — Mike Ulrich, Google SRE book](https://sre.google/sre-book/addressing-cascading-failures/) (industry doc) — owns the retry-amplification arithmetic, the retry-budget and backoff prescriptions, the retriable-vs-nonretriable rule, and the "graceful degradation" definition the module's third rung restates.
- <a id="principles-of-chaos"></a>[principles-of-chaos](#principles-of-chaos) · [**Principles of Chaos Engineering** — chaos-eng.github.io](https://principlesofchaos.org/) (industry doc) — owns the four-step experiment (steady state, hypothesis, real-world variable, try to disprove) and the list of weaknesses to hunt, including "retry storms from improperly tuned timeouts."

### Failure semantics, retries, and recovery

- <a id="candea-crash-only"></a>[candea-crash-only](#candea-crash-only) · [**Crash-Only Software** — George Candea, Armando Fox](https://research.cs.wisc.edu/areas/os/ReadingGroup/os-old/Papers/HotOSIX/Candea-CrashOnlySoftware.pdf) — *HotOS IX*, 2003. — owns `stop=crash` / `start=recover`, the argument against a separate recovery path, the idempotency requirement for restart/retry architectures, and the observation that resubmission to a recovering component can overload it.
- <a id="elnozahy-rollback-recovery"></a>[elnozahy-rollback-recovery](#elnozahy-rollback-recovery) · [**A survey of rollback-recovery protocols in message-passing systems** — E. N. (Mootaz) Elnozahy, Lorenzo Alvisi, Yi-Min Wang, David B. Johnson](https://doi.org/10.1145/568522.568525) — *ACM Computing Surveys* 34(3), 2002. — owns the checkpoint-based / log-based taxonomy behind the module's checkpointing rung.
- <a id="garcia-molina-sagas"></a>[garcia-molina-sagas](#garcia-molina-sagas) · [**Sagas** — Hector Garcia-Molina, Kenneth Salem](https://doi.org/10.1145/38713.38742) — *SIGMOD '87*, 1987. — owns long-lived transactions that complete partially and compensate step by step: the original form of "return the completed steps, not the whole failure."
- <a id="zilberstein-anytime"></a>[zilberstein-anytime](#zilberstein-anytime) · [**Using Anytime Algorithms in Intelligent Systems** — Shlomo Zilberstein](https://ojs.aaai.org/aimagazine/index.php/aimagazine/article/view/1232/1133) — *AI Magazine* 17(3), 1996. — owns "trade deliberation time for quality of results": the formal version of the module's degrade rung and of returning an answer before the deadline.

### Partial results and production failure points

- <a id="barnett-seven-failure-points"></a>[barnett-seven-failure-points](#barnett-seven-failure-points) · [**Seven Failure Points When Engineering a Retrieval Augmented Generation System** — Scott Barnett, Stefanus Kurniawan, Srikanth Thudumu, Zach Brannelly, Mohamed Abdelrazek](https://arxiv.org/pdf/2401.05856) — *CAIN*, 2024. — owns the failure-point catalogue, including **FP3 "Not in Context"** and **FP7 "Incomplete"**, the counterweight to the module's framing of partial completion as a win.

### Human oversight, escalation, and deference

- <a id="chow-reject-option"></a>[chow-reject-option](#chow-reject-option) · [**On Optimum Recognition Error and Reject Tradeoff** — C. K. Chow](https://doi.org/10.1109/TIT.1970.1054406) — *IEEE Transactions on Information Theory* 16(1), 1970. — owns the **reject option**: an optimum rejection rule and the general error/reject tradeoff. The origin of "hand it to a human rather than guess."
- <a id="madras-predict-responsibly"></a>[madras-predict-responsibly](#madras-predict-responsibly) · [**Predict Responsibly: Improving Fairness and Accuracy by Learning to Defer** — David Madras, Toniann Pitassi, Richard Zemel](https://proceedings.neurips.cc/paper_files/paper/2018/hash/09d37c08f7b129e96277388757530c72-Paper.pdf) — *NeurIPS*, 2018. — owns **learning to defer** as a generalization of rejection learning: the classifier's accept/reject decision is conditioned on the downstream decision-maker. *(The proceedings byline prints "Toni Pitassi"; the paper's own text prints "Toniann".)*
- <a id="mozannar-consistent-estimators"></a>[mozannar-consistent-estimators](#mozannar-consistent-estimators) · [**Consistent Estimators for Learning to Defer to an Expert** — Hussein Mozannar, David Sontag](https://proceedings.mlr.press/v119/mozannar20b.html) — *ICML*, 2020. — owns the consistent surrogate loss for learning a classifier-plus-rejector that defers to an expert.
- <a id="horvitz-mixed-initiative"></a>[horvitz-mixed-initiative](#horvitz-mixed-initiative) · [**Principles of Mixed-Initiative User Interfaces** — Eric Horvitz](http://erichorvitz.com/uiact.htm) — *CHI '99*, 1999. — owns the interaction principles for coupling automated action with human direction: the design vocabulary for *when* the handoff prompt should appear.
- <a id="bainbridge-ironies"></a>[bainbridge-ironies](#bainbridge-ironies) · [**Ironies of Automation** — Lisanne Bainbridge](https://ckrybus.com/static/papers/Bainbridge_1983_Automatica.pdf) — *Automatica* 19(6), 1983. *cf.* — the residual human is left monitoring and intervening in exactly the abnormal cases that practice is hardest to keep. *(Semantic Scholar's record for this paper is wrong — it lists the venue as "at - Automatisierungstechnik", 1982; Crossref and OpenAlex both give Automatica 19(6):775–779, 1983.)*
- <a id="parasuraman-riley"></a>[parasuraman-riley](#parasuraman-riley) · [**Humans and Automation: Use, Misuse, Disuse, Abuse** — Raja Parasuraman, Victor Riley](https://doi.org/10.1518/001872097778543886) — *Human Factors* 39(2), 1997. *cf.* — owns the use/misuse/disuse/abuse taxonomy; **misuse** is over-reliance causing "failures of monitoring or decision biases," which is the failure mode a handoff rung can produce.

### Agent failure, cost, and long-horizon reliability

- <a id="mast-multi-agent-failure"></a>[mast-multi-agent-failure](#mast-multi-agent-failure) · [**Why Do Multi-Agent LLM Systems Fail?** — Mert Cemri, Melissa Z. Pan, Shuyi Yang, Lakshya A. Agrawal, Bhavya Chopra, Rishabh Tiwari, Kurt Keutzer, Aditya Parameswaran, Dan Klein, Kannan Ramchandran, Matei Zaharia, Joseph E. Gonzalez, Ion Stoica](https://arxiv.org/pdf/2503.13657) — *NeurIPS* (Datasets & Benchmarks Track), 2025. — owns the MAST taxonomy (14 modes, 3 categories) built from 1,600+ annotated traces, and the 41%–86.7% failure range across seven agent systems. Supplies **FM-1.5 Unaware of stopping conditions**, **FM-1.3 Step repetition**, and **FM-3.1 Premature termination** — the budget-control failure and its mirror image.
- <a id="tau-bench"></a>[tau-bench](#tau-bench) · [**τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains** — Shunyu Yao, Noah Shinn, Pedram Razavi, Karthik Narasimhan](https://arxiv.org/pdf/2406.12045) — *ICLR*, 2025. — owns repeated-trial unreliability for tool agents: "even state-of-the-art function calling agents (gpt-4o) succeed on $<50\%$ of the tasks, and are terribly inconsistent (pass^8 < 25% in retail)."
- <a id="metr-long-tasks"></a>[metr-long-tasks](#metr-long-tasks) · [**Measuring AI Ability to Complete Long Software Tasks** — Thomas Kwa, Ben West, Joel Becker, Amy Deng, Katharyn Garcia, Max Hasin, Sami Jawhar, Megan Kinniment, Nate Rush, Sydney Von Arx, Ryan Bloom, Thomas Broadley, Haoxing Du, Brian Goodrich, Nikola Jurkovic, Luke Harold Miles, Seraphina Nix, Tao Lin, Chris Painter, Neev Parikh, David Rein, Lucas Jun Koba Sato, Hjalmar Wijk, Daniel M. Ziegler, Elizabeth Barnes, Lawrence Chan](https://arxiv.org/pdf/2503.14499) — arXiv:2503.14499, 2025 (preprint; journal reference: *NeurIPS*, 2025). — owns the measured task-length horizon: "current frontier AI models such as Claude 3.7 Sonnet have a 50% time horizon of around 50 minutes," doubling roughly every seven months. The empirical basis for "a long run is where the risk accumulates."
- <a id="frugalgpt"></a>[frugalgpt](#frugalgpt) · [**FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance** — Lingjiao Chen, Matei Zaharia, James Zou](https://arxiv.org/pdf/2305.05176) — arXiv:2305.05176, 2023 (preprint). — owns cascade-based cost control: matching the strongest model's performance "with up to 98% cost reduction." The reason a cost cap is a budget control and not just an ops setting.
- <a id="routellm"></a>[routellm](#routellm) · [**RouteLLM: Learning to Route LLMs with Preference Data** — Isaac Ong, Amjad Almahairi, Vincent Wu, Wei-Lin Chiang, Tianhao Wu, Joseph E. Gonzalez, M. Waleed Kadous, Ion Stoica](https://arxiv.org/pdf/2406.18665) — *ICLR*, 2025. *cf.* — routes between a strong and a weak model *by predicted query difficulty*, cutting cost "by over 2 times in certain cases," rather than by observing a failure. *(The camera-ready title reads "from Preference Data"; the arXiv title reads "with".)*
- <a id="yue-llm-cascades"></a>[yue-llm-cascades](#yue-llm-cascades) · [**Large Language Model Cascades with Mixture of Thoughts Representations for Cost-efficient Reasoning** — Murong Yue, Jie Zhao, Min Zhang, Liang Du, Ziyu Yao](https://arxiv.org/pdf/2310.03094) — *ICLR*, 2024. — owns answer-consistency cascading: reaching a stronger model's performance at a fraction of the cost, the venue-published companion to FrugalGPT.

### Tool-error detection and recovery

- <a id="toolrobustbench"></a>[toolrobustbench](#toolrobustbench) · [**ToolRobustBench: Stage-Wise Perturbation Evaluation and Failure Diagnosis for Tool-Calling Agents** — YiShan Zheng, Yuan Wu, Yi Chang](https://arxiv.org/pdf/2608.23635) — arXiv:2608.23635, 2026 (preprint). — owns the stage-wise decomposition of tool-calling failure and the finding that "tool-output/observation perturbation [is] the dominant bottleneck."
- <a id="fission-grpo"></a>[fission-grpo](#fission-grpo) · [**Robust Tool Use via Fission-GRPO: Learning to Recover from Execution Errors** — Zhiwei Zhang, Fei Zhao, Rui Wang, Zezhong Wang, Bin Liang, Jiakang Wang, Yao Hu, Shaosheng Cao, Kam-Fai Wong](https://arxiv.org/pdf/2601.15625) — *ACL*, 2026. — owns the repetitive-invalid-re-invocation failure mode: "after a tool-call error, smaller models often fall into repetitive invalid re-invocations instead of interpreting the feedback and recovering."
- <a id="pararecover"></a>[pararecover](#pararecover) · [**ParaRecover: A Process-Level Benchmark for Error Localization and Recovery in Parallel Tool-Use Agents** — Bowen Guan, Zhentao Yin, Yanming Shen](https://arxiv.org/pdf/2609.12345) — *EMNLP*, 2026. — owns process-level error-recovery measurement (14 error types, 10,626 instances) and the finding that "even state-of-the-art models still struggle with multi-turn error propagation, implicit tool-use failures, and precise replanning."
- <a id="toolemu"></a>[toolemu](#toolemu) · [**Identifying the Risks of LM Agents with an LM-Emulated Sandbox** — Yangjun Ruan, Honghua Dong, Andrew Wang, Silviu Pitis, Yongchao Zhou, Jimmy Ba, Yann Dubois, Chris J. Maddison, Tatsunori Hashimoto](https://arxiv.org/pdf/2309.15817) — *ICLR*, 2024 (spotlight). — owns the emulated-sandbox risk analysis and the headline that "even the safest LM agent exhibits such failures 23.9% of the time." *(ToolEmu is the framework name; it is not part of the paper's title.)*

### Self-correction: the contested pair

- <a id="huang-self-correct"></a>[huang-self-correct](#huang-self-correct) · [**Large Language Models Cannot Self-Correct Reasoning Yet** — Jie Huang, Xinyun Chen, Swaroop Mishra, Huaixiu Steven Zheng, Adams Wei Yu, Xinying Song, Denny Zhou](https://arxiv.org/pdf/2310.01798) — *ICLR*, 2024. *cf.* — "LLMs struggle to self-correct their responses without external feedback, and at times, their performance even degrades after self-correction."
- <a id="madaan-self-refine"></a>[madaan-self-refine](#madaan-self-refine) · [**Self-Refine: Iterative Refinement with Self-Feedback** — Aman Madaan, Niket Tandon, Prakhar Gupta, Skyler Hallinan, Luyu Gao, Sarah Wiegreffe, Uri Alon, Nouha Dziri, Shrimai Prabhumoye, Yiming Yang, Shashank Gupta, Bodhisattwa Prasad Majumder, Katherine Hermann, Sean Welleck, Amir Yazdanbakhsh, Peter Clark](https://proceedings.neurips.cc/paper_files/paper/2023/hash/91edff07232fb1b55a505a9e9f6c0ff3-Paper-Conference.pdf) — *NeurIPS*, 2023. — the affirmative side: "improving by ~20% absolute on average in task performance."
- <a id="shinn-reflexion"></a>[shinn-reflexion](#shinn-reflexion) · [**Reflexion: Language Agents with Verbal Reinforcement Learning** — Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1b44b878bb782e6954cd888628510e90-Paper-Conference.pdf) — *NeurIPS*, 2023. — owns retry-with-reflection: verbal feedback held in episodic memory, "not by updating weights." *(The NeurIPS proceedings listing prints five authors, omitting Edward Berman.)*

### Abstention, calibration, and over-refusal

- <a id="joren-sufficient-context"></a>[joren-sufficient-context](#joren-sufficient-context) · [**Sufficient Context: A New Lens on Retrieval Augmented Generation Systems** — Hailey Joren, Jianyi Zhang, Chun-Sung Ferng, Da-Cheng Juan, Ankur Taly, Cyrus Rashtchian](https://arxiv.org/pdf/2411.06037) — *ICLR*, 2025. *cf.* — separates "the context is insufficient" from "the model failed to use it," and finds stronger models "often output incorrect answers instead of abstaining when the context is not" sufficient.
- <a id="jiang-calibration"></a>[jiang-calibration](#jiang-calibration) · [**How Can We Know When Language Models Know? On the Calibration of Language Models for Question Answering** — Zhengbao Jiang, Jun Araki, Haibo Ding, Graham Neubig](https://aclanthology.org/2021.tacl-1.57.pdf) — *TACL* 9, 2021. *cf.* — the calibration baseline for the degrade rung's "as of" caveat.
- <a id="lin-uncertainty-in-words"></a>[lin-uncertainty-in-words](#lin-uncertainty-in-words) · [**Teaching Models to Express Their Uncertainty in Words** — Stephanie Lin, Jacob Hilton, Owain Evans](https://arxiv.org/pdf/2205.14334) — arXiv:2205.14334, 2022 (preprint). *cf.* — a model can be shown to "express calibrated uncertainty about its own answers in natural language," which softens the module's claim that graceful degradation is not a property the model has.
- <a id="rottger-xstest"></a>[rottger-xstest](#rottger-xstest) · [**XSTest: A Test Suite for Identifying Exaggerated Safety Behaviours in Large Language Models** — Paul Röttger, Hannah Kirk, Bertie Vidgen, Giuseppe Attanasio, Federico Bianchi, Dirk Hovy](https://aclanthology.org/2024.naacl-long.301.pdf) — *NAACL*, 2024. — owns exaggerated safety as a measured failure mode: 250 safe prompts a calibrated model should not refuse, against 200 unsafe contrasts.
- <a id="cui-or-bench"></a>[cui-or-bench](#cui-or-bench) · [**OR-Bench: An Over-Refusal Benchmark for Large Language Models** — Justin Cui, Wei-Lin Chiang, Ion Stoica, Cho-Jui Hsieh](https://arxiv.org/pdf/2405.20947) — *ICML*, 2025. — owns over-refusal measurement at scale.

### Unsupported claims and own synthesis

- <a id="unsupported"></a>[unsupported](#unsupported) · **Unsupported.** Claims made in this module that no located source supports. Cited inline as [unsupported](#unsupported) rather than to an invented reference. Currently: **the claim that the classic distributed-systems reliability repertoire transfers to model and tool failures** — that a model error and a network error are the same kind of failure and yield to the same controls. The individual techniques are each sourced, but no located source establishes the transfer, and §4 and §6 show model failures differ in kind: self-correction without external feedback is contested, and tool-output handling — not the network — is the measured bottleneck. *(Two claims that merely appeared unsupported turned out to be mis-cited rather than unsourced: "`RetryConfig` does this automatically" is contradicted by the framework's own documentation (see §3), and the five-rung ladder's ordering is this module's construction, filed below.)*
- <a id="own-synthesis"></a>[own-synthesis](#own-synthesis) · **Own synthesis (not sourced).** Claims this module makes that are the course's framing rather than literature findings, flagged so they are not mistaken for citations: the five-rung ladder as a single ordered sequence (each rung has an owner; the *order* does not); the mapping from failure type and consequence to a specific rung; the claim that failure "should cost the remaining work, not the completed work"; the assertion that an agent without a cost cap is a runaway rather than a more capable agent; and the closing claim that graceful degradation is a designed property rather than a model property.

---

**Next module:** [M14 — Security & Injection Defense](../14-security-injection/README.md) — how to stop the environment from weaponizing the model.
