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

Observability is three instruments, and the division of labor is precise (ADK's own framing)[adk-observability](#adk-observability):

| Pillar | Answers | For an agent, that means |
|---|---|---|
| **Logs** | *What* happened | "the tool returned an error," "the model said X" |
| **Metrics** | *How long / how many* | latency, cost, error rates, escalation rates |
| **Traces** | *Where the time went* — the hierarchy | the waterfall: agent → model call → tool call → sub-call |

**Traces are the one that changes everything for agents**, because an agent's failure is usually *structural* — a wrong *path*, not a wrong *answer*.[dong-agentops](#dong-agentops), [wang-agentops-survey](#wang-agentops-survey) A trace captures the path.

> **ADK at a glance:** traces are **OpenTelemetry** spans, in the standard GenAI semantic conventions — `invoke_agent` (the run), `execute_tool` (each tool), `generate_content` (each model call), with `invoke_workflow` for multi-step flows.[adk-traces](#adk-traces) The spans nest into a "waterfall": the agent run is the root span, the model calls and tool calls are children, and *context propagates* across process boundaries (your tool's microservice spans link back into the agent's trace).[adk-traces](#adk-traces) Emit over OTLP to any backend — and the `adk web` Trace view shows the same run as Event / Request / Response / Graph.[adk-conformance](#adk-conformance)

---

## Reconstructing a run: replay and diff

A trace that *records* the run is necessary; the ability to *re-run* it is where debugging actually happens:

- **Context snapshot** — the trace (or the event stream) records *what the model saw* at each step — the assembled context, the tool args, the results.[alsayyad-agenttrace](#alsayyad-agenttrace) Without this, you know *that* it failed, not *what it was thinking from*.
- **Replay** — re-run the failed step with the *same* recorded context. (ADK's conformance tooling has a "Replay" mode[adk-conformance](#adk-conformance); and M4's context budget + M7's state are the raw material.) Replay turns "it failed once" into "it fails *reproducibly*"[luan-repair-or-resample](#luan-repair-or-resample) — a promise the literature qualifies hard: unguided rerun reproduces a failure only 67.97% of the time, "merely stochastically repair[ing] by leveraging the randomness of LLM sampling." Faithful replay pins the recorded prefix and regenerates only downstream of an intervention anchor.[luan-repair-or-resample](#luan-repair-or-resample)
- **Diff two runs** — run the *changed* harness against the *same* inputs and diff the traces. Which span diverged first? That's your regression.[kang-zero-replay](#kang-zero-replay) This is the observability twin of M12's eval: evals gate *before* shipping, traces diagnose *after*.[adk-conformance](#adk-conformance)

The through-line from the M3 diagram discussion, now concrete: **observability is the passive span at both ends and everywhere between** — the input context at the top, the response at the bottom, and every tool call in the middle, connected into one replayable whole.

---

## The metrics that matter

A platform team alerts on a *small* set of signals. For agents, the load-bearing ones:

| Metric | What it catches |
|---|---|
| **Cost per run** | Budget runaways (M13)[chen-frugalgpt](#chen-frugalgpt) |
| **Latency percentiles** (p50/p95) | Degradation before users scream[dean-tail-at-scale](#dean-tail-at-scale) |
| **Tool error rate** | A flaky or breaking tool (M13's rung)[wang-agentops-survey](#wang-agentops-survey) |
| **Human-edit / override rate** | How often a human had to *fix* the agent's output — the true quality signal[devatine-edit-distance](#devatine-edit-distance) |
| **Escalation rate** | How often it handed off — autonomy miscalibration (M10)[wang-agentops-survey](#wang-agentops-survey) (a term the field names but does not measure — see [literature-gap](#literature-gap)) |

The quiet insight: **human-edit rate is the best single proxy for "is this actually working."**[unsupported](#unsupported) Edit effort is measurable and correlates with real editing time,[devatine-edit-distance](#devatine-edit-distance) but no located source ranks it against other signals or shows it predicts correctness — it scores *effort*, and a careful rewrite and a rubber-stamp both look cheap. A low error rate means nothing if humans are silently rewriting half the outputs; equally, a low edit rate means nothing if nobody is checking. Watch the *edits*, and verify correctness somewhere it can be checked.[shi-citeaudit](#shi-citeaudit)

The gap in this table is **saturation** — the four-golden-signals taxonomy pairs "errors" with it, and calls latency "often a leading indicator" of it.[ewaschuk-monitoring](#ewaschuk-monitoring) An agent system has a saturation signal (context-window fill, token budget consumed, concurrency); the module measures the symptom and not the approach to the limit.

---

## Cost & latency management

Observability's twin is *doing something about* what it sees. The production cost/latency levers (each already met earlier in the course):

- **Caching** (M4) — stable prefixes cut input cost on every repeat turn.
- **Model tiering** (M13's `RoutedLlm`) — cheap model by default, escalate to expensive *only* when the task is hard (the "router by complexity" pattern).[ong-routellm](#ong-routellm) Most requests never touch the expensive model — a learned router cuts cost "by over 2 times in certain cases—without compromising the quality of responses," and a cascade can match the best single model "with up to 98% cost reduction."[ong-routellm](#ong-routellm), [chen-frugalgpt](#chen-frugalgpt)
- **Parallelism** (M11's `single_turn` sub-agents) — independent subtasks run concurrently instead of serially.

These aren't new ideas; M16 is where they become *operational* — measured, budgeted, and alerted on as a *system*, not a set of one-off optimizations.[wang-agentops-survey](#wang-agentops-survey)

---

## Incident response for agentic systems

When an agent does go wrong in production, the response toolkit:

- **Rollback** — revert the instruction/model/tool to the last known-good version. (M6's instruction versioning + model version pinning make this *possible*.)
- **Kill switch** — a feature flag that turns the agent (or a specific tool) off *instantly*, without a redeploy.
- **Model version pinning** — pin the exact model version, so "the model changed under us" can't be a variable mid-incident. This is not a hypothetical: across two releases of the "same" service, GPT-4's accuracy on one task fell from 84% to 51%, with "evidence that GPT-4's ability to follow user instructions has decreased over time."[chen-behavior-changing](#chen-behavior-changing)
- **Replay the incident** — reconstruct the failing run (above) to find the *first* diverging span.[kang-zero-replay](#kang-zero-replay)

The principle: **incident response for agents is version-controlled and replayable, or it's guesswork.**[own-synthesis](#own-synthesis) You can only roll back what you versioned, and you can only diagnose what you traced.

---

## Worked example: the production research agent

The domain spine. A research agent, in production, is instrumented end to end:

- **Trace:** root `invoke_agent` span → `generate_content` (the plan) → N× `execute_tool` (searches) → `generate_content` (the synthesis). Each span records args, results, and token counts.
- **Metrics:** cost/run, p95 latency, search-tool error rate, and — critically — *citation-edit rate* (how often a human corrects a citation).
- **Replay:** a wrong answer is re-run against its recorded context; the diff shows the *third search* returned garbage, and the model trusted it (M5's poisoned-result failure, caught by observability, not by a lucky guess).
- **Response:** roll back the search tool to the previous version, pin the model, and add the bad-search case to M12's eval set.

The point: the research agent doesn't fail *less* because it's observable — it fails *more usefully*. Every failure becomes a replayable, diffable, fixable event instead of a black box.

> **Tradeoff (the ledger entry):**
> - **Trace completeness vs. cost/privacy.** Recording full context (message content, tool args) costs storage and — in M14/M15's terms — *sensitivity* (traces can contain PII). ADK gates this explicitly (`captureMessageContent`, "use with caution in production").[adk-traces](#adk-traces) The cost half is smaller than it looks: sampling is not the only lever, and capturing *all* traces through pattern aggregation has been measured at 2.7% of the storage and 4.2% of the network overhead of naive capture[huang-mint](#huang-mint) — but the fidelity you trade for it is real. Trace *structure* everywhere; trace *content* where it's safe, and record *which* choice you made[own-synthesis](#own-synthesis) — an approximate or redacted trace can replay perfectly while omitting the cause.[khatchadourian-dfah-bench](#khatchadourian-dfah-bench)
> - **Metric volume vs. signal.** Alert on the five metrics that matter, not fifty dashboards. A metric nobody pages on is decoration — and the SRE position is stricter than "decoration": a signal neither dashboarded nor alerting "is a candidate for removal," because alert noise causes engineers to "second-guess, skim, or even ignore incoming alerts."[ewaschuk-monitoring](#ewaschuk-monitoring)
> - **Instrumentation vs. velocity.** Observability is infrastructure with a tax. Pay it *before* the first incident, not during it. The measured tax is not the runtime overhead — an instrumentation-free eBPF approach lands under 3%[zheng-agentsight](#zheng-agentsight) — it is the *design* tax: deciding what to capture, and accepting that the choice constrains what you can later reconstruct.[huang-mint](#huang-mint)

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

- [Observability for agents — logging, metrics, traces](https://adk.dev/observability/index.md) [adk-observability](#adk-observability)
- [Agent activity traces — OpenTelemetry spans, OTLP export, waterfall](https://adk.dev/observability/traces/index.md) [adk-traces](#adk-traces)
- [Evaluate with conformance — Replay mode](https://adk.dev/evaluate/index.md) [adk-conformance](#adk-conformance)

---

## Where the literature disagrees with this module

The claims above are directionally right, and the module's *central* mechanism — an agent failure usually lives in the middle of the run, not at its ends — is the best-supported thing here: the field says the same thing in almost the same words. But one of the module's headline instructions is contradicted by direct measurement, one metric is asserted more strongly than any located source supports, and the taxonomy it presents as settled is one of two competing ones. Recording this is the same discipline the module teaches for traces: keep the evidence, and flag where the source says "maybe."

### 1. "Replay turns 'it failed once' into 'it fails reproducibly'" — this is the claim the literature most directly contradicts

The module's replay bullet is its most actionable instruction, and a 2026 empirical study measures exactly what it promises. The answer is: not reliably.

- **Unguided rerun reproduces the failure fewer than seven times in ten.** Across three mainstream multi-agent frameworks, "existing unguided rerun methods are highly unreliable, exhibiting low failure reproduction and repair rates (only 67.97% and 6.90%, respectively)."[luan-repair-or-resample](#luan-repair-or-resample)
- **The mechanism is the module's own blind spot.** The paper's framing question is whether rerun methods "causally repair MAS failures or merely stochastically repair by leveraging the randomness of LLM sampling" — and its proposed fix is *not* replay alone. SymTrace "records the MAS execution trajectory and establishes intervention anchors," then "reconstructs the execution before the anchor using recorded logs and only regenerates the downstream trajectory."[luan-repair-or-resample](#luan-repair-or-resample) Reproducibility comes from **pinning the prefix and regenerating the suffix**, not from re-running the whole step in the same context.
- **A re-run can agree on the answer and disagree on the work.** Across 570 prospective episodes, "decision agreement is 94.2–95.1%, while agreement on ordered tools, arguments and results is 45.0–51.5%."[khatchadourian-dfah-bench](#khatchadourian-dfah-bench) If the *trajectory* is what your trace diff compares — and it is, since that is where the interesting failure lives — then a "successful" replay is agreeing about the least informative part of the run.
- **And a trace can replay perfectly while omitting what mattered.** "A separate capture diagnostic shows that systematic omissions can preserve perfect replay agreement."[khatchadourian-dfah-bench](#khatchadourian-dfah-bench) Green replay is not evidence of complete capture. This is what the Determinism–Faithfulness harness was built to separate: a tool-using agent "can repeat a final decision while changing their recorded execution."[khatchadourian-dfah](#khatchadourian-dfah)
- The foundation reason is measurable and older: five LLMs "configured to be deterministic" produced "accuracy variations up to 15% across naturally occurring runs with a gap of best possible performance to worst possible performance up to 70%," and "none of the LLMs consistently delivers repeatable accuracy across all tasks, much less identical output strings."[atil-non-determinism](#atil-non-determinism)

**Consequence for the module.** Keep replay, but stop describing it as turning a mystery into a bug. The honest version: **replay is a diagnostic instrument with a measurable reproduction rate, and that rate is the metric you need before you trust a replay's verdict.** Record the trajectory and anchor the intervention point; a "the bug didn't reproduce" outcome is evidence *about your replay harness* first, and about the agent second. The module already says the context snapshot is what makes replay possible — the literature adds that pinning the *prefix* is what makes it faithful.

### 2. The disagreement is not "replay vs. no replay" — it is *replay* vs. *predicting the replay*

The module presents replay as the endpoint of the debugging procedure. The current literature treats exhaustive replay as a *budget*, and spends it deliberately.

- "The standard tool is counterfactual replay (rewind, edit, and re-run the trajectory to measure each event's effect), but its cost grows linearly with the number of candidate events, making exhaustive replay infeasible at scale."[kang-zero-replay](#kang-zero-replay)
- The alternative is to localize the decisive event *without* replaying: compiling the trace into an event knowledge graph and predicting which events a replay oracle would mark as high-effect, raising localization "from 0.73 to 0.93 on held-out families at zero oracle-replay cost."[kang-zero-replay](#kang-zero-replay)
- And the instrumentation question is contested rather than settled. The module's advice — instrument the agent's spans — is the "inside the application" position; AgentSight argues for observing from outside instead: existing tools "observe either an agent's high-level intent (via LLM prompts) or its low-level actions (e.g., system calls), but cannot correlate these two views," and an eBPF "boundary tracing" approach closes that "semantic gap" while being "instrumentation-free … framework-agnostic, resilient to rapid API changes," at "less than 3% performance overhead."[zheng-agentsight](#zheng-agentsight)

**Consequence.** The module's "diff two runs → which span diverged first?" step is the right *question* and, per §1, the expensive way to answer it. The defensible instruction is: **capture first, then localize cheaply before you replay.** "Replay everything until you find it" is the procedure that §1 shows fails to reproduce, at a cost §2 shows grows linearly.

### 3. "Human-edit rate is the best single proxy for 'is this actually working'" — no located source supports the superlative

This is the module's "quiet insight," and it is the claim with the weakest support in the file. What exists:

- Edit effort *is* measurable, and it *is* correlated with real cost: a compression-based edit distance "is highly correlated with actual edit time and effort," and is introduced explicitly to fix the failure of "Levenshtein, BLEU, ROUGE, and TER" to "accurately measure the effort required for post-editing, especially when edits involve substantial modifications, such as block operations."[devatine-edit-distance](#devatine-edit-distance)
- A related quality signal — whether a human accepted the output at all — is a standard deployment metric, so the *class* of metric is real.

What does **not** exist in anything located this run: a study showing human-edit rate beats error rate, latency, or any other signal as a predictor of task success, or one establishing it as a *quality* signal rather than a *friction* signal. Three specific ways it can mislead, none of which the module's framing admits:

1. **It scores effort, not correctness.** A human who rewrites a wrong citation and a human who rewords a correct one produce the same edit distance. The module's own worked example uses a *citation*-edit rate — and citation fabrication is exactly the failure class that survives review: fabricated references "appear plausible but correspond to no real publications," and detectors now exist precisely because "manual verification becomes infeasible."[shi-citeaudit](#shi-citeaudit), [li-citetracer](#li-citetracer)
2. **Low edit rate can mean rubber-stamping, not quality.** Nothing in the edit-rate measure distinguishes a careful reviewer from an inattentive one.
3. **It has no threshold.** The module says "watch the *edits*, not the *errors*" but names no level at which edits page a human — while the one metric philosophy in print is explicit that a signal without an alert is not worth collecting.

**Consequence.** Keep the metric and demote the claim: **human-edit rate is a useful friction signal that is not a correctness signal, and it should be paired with a direct correctness check rather than substituting for one.** "The best single proxy" is the course's framing, not a finding — recorded as such in the unsupported bucket below.[unsupported](#unsupported)

### 4. The three pillars are one taxonomy; the field's other taxonomy is four signals

The module introduces "logs, metrics, traces" as *the* framing and adds a five-metric table. The two do not compose, and the incompatibility is not the module's invention — it is inherited from two different sources.

- The three-pillar grouping is the framework's: "ADK provides built-in observability through logging, metrics, and traces."[adk-observability](#adk-observability)
- But the load-bearing monitoring chapter of Google's SRE book enumerates a **four**-part set instead: "The four golden signals of monitoring are latency, traffic, errors, and saturation. If you can only measure four metrics of your user-facing system, focus on these four."[ewaschuk-monitoring](#ewaschuk-monitoring)
- Under that taxonomy the module's table is *incomplete in a specific way*: cost per run, tool error rate, human-edit rate, and escalation rate have no home in the golden signals, and **saturation** — the signal the SRE book calls out as the leading indicator ("Latency increases are often a leading indicator of saturation") — appears in the module's table nowhere at all.
- The same chapter also contradicts the module's alerting posture more sharply than the module's own "a metric nobody pages on is decoration." The SRE book makes unused signals *removable*: "Signals that are collected, but not exposed in any prebaked dashboard nor used by any alert, are candidates for removal."[ewaschuk-monitoring](#ewaschuk-monitoring)

**Consequence.** Present the pillars as a **span-level** taxonomy (what kind of record you are writing) and the metric table as an **agent-level** one (what you are alerting on), and say that the two are orthogonal — the pillars tell you *how to record*, the signals tell you *what to page on*. Add saturation; it is the one golden signal an agent system genuinely has and the module omits.

### 5. Trace completeness is not primarily a cost/storage tradeoff — it is a fidelity/coverage tradeoff

The module's first tradeoff ("trace structure everywhere; trace content where it's safe") frames the decision as completeness purchased with storage and privacy. The tracing literature frames it as a *design choice with a distortion cost*, and the cheaper option is not simply "less complete."

- Volume is real and the module is right to flag it — but collection and analysis are separate engineering problems, and always have been: Canopy established end-to-end tracing at production scale as a *system* that stores, indexes, and queries traces, not merely a viewer for them.[kaldor-canopy](#kaldor-canopy) The module's tradeoff treats "record it" and "find it later" as the same decision; they are two.
- The sampling fix the module implies is the one the field has moved past. "Previous approaches typically used a '1 or 0' sampling strategy: retaining sampled traces while completely discarding unsampled ones," and an empirical study on production traces found this "actually fails to effectively balance this tradeoff." Mint captures *all* traces while reducing "trace storage (reduced to an average of 2.7%) and network overhead (reduced to an average of 4.2%)."[huang-mint](#huang-mint)
- The residual risk is a new one the module does not name: **approximate traces**. Mint's own "commonality + variability" paradigm necessarily trades exact trace reconstruction for volume, and the paper devotes a discussion section to "Trace Coherence" and "Production Use Cases of Approximate Traces."[huang-mint](#huang-mint)
- Privacy is a first-class constraint rather than a footnote, and the vendor gate the module cites is a real, documented one — ADK's own opt-in is annotated "Enable capturing full message content in traces (use with caution in production)."[adk-traces](#adk-traces)

**Consequence.** "Record the content where it's safe" is underspecified. The sharper rule: **choose capture fidelity deliberately and record which choice you made** — because an approximate trace can reproduce a run perfectly while omitting the cause[khatchadourian-dfah-bench](#khatchadourian-dfah-bench), and because a redaction decision made for privacy is indistinguishable, at diff time, from a capture gap.

### 6. Where the disagreement is with the *worked example*, not the prose

Exempt from citation, but one inference does not survive contact with the sources, and it is the module's punchline:

- The worked example's replay "shows the *third search* returned garbage." Per §1, a single rerun producing that diff is not a localization result: unguided rerun reproduces a failure 67.97% of the time, and tool-path agreement after a repeat decision is 45.0–51.5%.[luan-repair-or-resample](#luan-repair-or-resample), [khatchadourian-dfah-bench](#khatchadourian-dfah-bench)
- The **response** half holds up better than the module claims. "Add the bad-search case to M12's eval set" is exactly the field's conclusion — incident-derived cases are the ones a baseline must carry, and conformance against a recorded baseline is the documented regression gate.[adk-conformance](#adk-conformance) What the literature adds is the other half: an *eval* case tests the agent, not the tool. The bad search was a **tool** failure, so the durable fix is the tool's own contract (M8) plus a trajectory assertion, not a response reference.

---

## Bibliography

*Literature behind the module's claims, with the framework documentation the module itself cites. **Citations use stable identifier keys, not position numbers.** Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed, or reordered without rewriting a single citation — the BibTeX model, minus a backend to assign numbers. The bibliography is therefore an unordered bullet list, not a ranked one: the order of entries carries no meaning, and no entry's identity changes if you move it. Every entry hyperlinks to the source itself — the open PDF where one exists. Items tagged (industry doc) are vendor or project documentation, (preprint) are not yet peer-reviewed, (workshop) are peer-reviewed workshop papers, and (own synthesis) are the module's inferences rather than sourced claims. `cf.` marks a source that qualifies or contradicts the sentence it follows. `unsupported` is the module's unsupported-claims bucket, `literature-gap` holds concepts the field names but does not yet measure under the module's term, and `own-synthesis` collects the course's own un-sourced synthesis: anything asserted above that no located source supports is cited there rather than to an invented reference.*

### Framework documentation (industry docs)

- <a id="adk-observability"></a>[adk-observability](#adk-observability) · [**Observability for agents** — Google ADK documentation](https://adk.dev/observability/index.md) (industry doc) — owns the module's three-pillar framing ("built-in observability through logging, metrics, and traces") and the claim that basic input/output monitoring is insufficient for agents. The four-golden-signals taxonomy it does *not* carry is [ewaschuk-monitoring](#ewaschuk-monitoring).
- <a id="adk-traces"></a>[adk-traces](#adk-traces) · [**Agent activity traces** — Google ADK documentation](https://adk.dev/observability/traces/index.md) (industry doc) — owns every framework-specific trace claim in the module: the `invoke_agent` / `invoke_workflow` / `execute_tool` / `generate_content` span names, the waterfall nesting, OTLP export, cross-process context propagation, and the `captureMessageContent` gate annotated "use with caution in production." The span names are inherited from the OpenTelemetry GenAI semantic conventions it cites.
- <a id="adk-conformance"></a>[adk-conformance](#adk-conformance) · [**Why evaluate agents** — Google ADK documentation](https://adk.dev/evaluate/index.md) (industry doc) — owns replay-as-regression-gate: `adk conformance test`, the golden-baseline workflow, and the **Replay Mode** the module's replay bullet is drawn from ("compares its live LLM requests, responses, and tool calls directly against your previously recorded interactions"). Note what it compares against: *recorded* interactions, not a re-derived context.

### Why the middle of the run is where the failure is

- <a id="dong-agentops"></a>[dong-agentops](#dong-agentops) · [**AgentOps: Enabling Observability of LLM Agents** — Liming Dong, Qinghua Lu, Liming Zhu](https://arxiv.org/pdf/2411.05285) — arXiv:2411.05285, 2024 (preprint). — owns the **AgentOps taxonomy**: the artifacts and lifecycle data that must be traced for an agent to be observable. The earliest systematic statement that the failure lives in the agent's internals rather than at its boundary.
- <a id="wang-agentops-survey"></a>[wang-agentops-survey](#wang-agentops-survey) · [**A Survey on AgentOps: Categorization, Challenges, and Future Directions** — Zexin Wang, Jingjing Li, Quan Zhou, Haotian Si, Yuanhao Liu, Jianhui Li, Gaogang Xie, Fei Sun, Dan Pei, Changhua Pei](https://arxiv.org/pdf/2508.02121) — arXiv:2508.02121, 2025 (preprint). — owns the **four-stage operational framework** — monitoring, anomaly detection, root cause analysis, resolution — and the intra-agent / inter-agent anomaly split. The resolution stage is where the module's escalation-rate metric belongs.
- <a id="alsayyad-agenttrace"></a>[alsayyad-agenttrace](#alsayyad-agenttrace) · [**AgentTrace: A Structured Logging Framework for Agent System Observability** — Adam AlSayyad, Kelvin Yuxiang Huang, Richik Pal](https://arxiv.org/pdf/2602.10133) — *AAAI 2026 Workshop LaMAS*, 2026 (workshop). — owns structured agent logging across three surfaces (operational, cognitive, contextual) as a *security and audit* requirement, not only a debugging one. The module's context snapshot earns a second justification here.

### Replay, reproduction, and root-cause localization

- <a id="luan-repair-or-resample"></a>[luan-repair-or-resample](#luan-repair-or-resample) · [**Repair or Resample? Rethinking Failure Debugging in LLM Multi-Agent Systems** — Zhongwen Luan, Xiaoyu Zhang, Ming Hu, Yue Yang, Jiongchi Yu, Xiaohong Chen](https://arxiv.org/pdf/2608.25920) — arXiv:2608.25920, 2026 (preprint). *cf.* — **the direct measurement contradicting the module's replay promise**: unguided rerun reproduces a failure only 67.97% of the time and repairs 6.90%. Owns SymTrace's anchor-and-regenerate design, which reconstructs the prefix from logs and regenerates only downstream. Also owns the SymFail dataset (536 human-annotated failure trajectories).
- <a id="khatchadourian-dfah-bench"></a>[khatchadourian-dfah-bench](#khatchadourian-dfah-bench) · [**DFAH-Bench: Benchmarking Observable Agent Instability in Financial Decision-Making** — Raffi Khatchadourian](https://arxiv.org/pdf/2607.20491) — arXiv:2607.20491, 2026 (preprint). *cf.* — the corrected study from the same author as [khatchadourian-dfah](#khatchadourian-dfah), and the one whose numbers this module cites. Owns the **decision/path agreement gap** (94.2–95.1% decision agreement against 45.0–51.5% tool-path agreement) and the silent-omission result: "systematic omissions can preserve perfect replay agreement." Separates repeatability, observable execution, evidence alignment, and correctness as four distinct claims.
- <a id="kang-zero-replay"></a>[kang-zero-replay](#kang-zero-replay) · [**Knowledge-Based Zero-Replay Debugging of Multi-Agent LLM Traces** — Dong Ho Kang, Hyeonjeong Cha, Daein Weon](https://arxiv.org/pdf/2606.14805) — arXiv:2606.14805, 2026 (preprint). *cf.* — owns the **cost frontier of replay** ("its cost grows linearly with the number of candidate events, making exhaustive replay infeasible at scale") and the cheaper alternative: predicting counterfactual effect from a trace knowledge graph before paying for replay (Branch Recall@5, 0.73 → 0.93).
- <a id="khatchadourian-dfah"></a>[khatchadourian-dfah](#khatchadourian-dfah) · [**Replayable Financial Agents: A Determinism-Faithfulness Assurance Harness for Tool-Using LLM Agents** — Raffi Khatchadourian](https://arxiv.org/pdf/2601.15322) — arXiv:2601.15322, 2026 (preprint). — owns the **DFAH measurement framework** and, notably, a public correction of its own earlier interpretation. Cited here for the framework's definitions: a tool-using agent "can repeat a final decision while changing their recorded execution."
- <a id="atil-non-determinism"></a>[atil-non-determinism](#atil-non-determinism) · [**Non-Determinism of "Deterministic" LLM Settings** — Berk Atil, Sarp Aykent, Alexa Chittams, Lisheng Fu, Rebecca J. Passonneau, Evan Radcliffe, Guru Rajan Rajagopal, Adam Sloan, Tomasz Tudrej, Ferhan Ture, Zhe Wu, Lixinyu Xu, Breck Baldwin](https://arxiv.org/pdf/2408.04667) — arXiv:2408.04667, 2025 (preprint). *cf.* — the base rate under every replay claim: up to 15% accuracy variation across 10 naturally occurring runs at settings expected to be deterministic, and best-to-worst gaps up to 70%. Owns the TARr@N / TARa@N determinism metrics.
- <a id="khatchadourian-dfah"></a>[khatchadourian-dfah](#khatchadourian-dfah) · [**Replayable Financial Agents: A Determinism-Faithfulness Assurance Harness for Tool-Using LLM Agents** — Raffi Khatchadourian](https://arxiv.org/pdf/2601.15322) — arXiv:2601.15322, 2026 (preprint). — owns the **DFAH measurement framework** and, unusually, a public correction of its own earlier interpretation. Cited here for the framework's central definition: a tool-using agent "can repeat a final decision while changing their recorded execution." Its quantified results are superseded by [khatchadourian-dfah-bench](#khatchadourian-dfah-bench).

### Instrumentation: what to capture, and what it costs

- <a id="zheng-agentsight"></a>[zheng-agentsight](#zheng-agentsight) · [**AgentSight: System-Level Observability for AI Agents Using eBPF** — Yusheng Zheng, Yanpeng Hu, Tong Yu, Andi Quinn](https://arxiv.org/pdf/2508.02736) — *PACMI*, 2025. *cf.* — owns **boundary tracing** and the "semantic gap" diagnosis (tools see either intent or syscalls, never both correlated). The strongest case against the module's assumption that the agent's own spans are the right instrumentation surface; also the source of the "<3% performance overhead" figure for instrumentation-free capture.
- <a id="huang-mint"></a>[huang-mint](#huang-mint) · [**Mint: Cost-Efficient Tracing with All Requests Collection via Commonality and Variability Analysis** — Haiyu Huang, Cheng Chen, Kunyi Chen, Pengfei Chen, Guangba Yu, Zilong He, Yilun Wang, Huxing Zhang, Qi Zhou](https://arxiv.org/pdf/2411.04605) — *ASPLOS*, 2025. *cf.* — owns the finding that "'1 or 0' sampling … actually fails to effectively balance this tradeoff," and the commonality-plus-variability alternative: all traces captured at 2.7% of storage and 4.2% of network overhead. Also the source of the **approximate-trace** caveat the module's tradeoff omits.
- <a id="kaldor-canopy"></a>[kaldor-canopy](#kaldor-canopy) · [**Canopy: An End-to-End Performance Tracing And Analysis System** — Jonathan Kaldor, Jonathan Mace, Michał Bejda, Edison Gao, Joe O'Neill, Kian Win Ong, Bill Schaller, Pingjia Shan, Brendan Viscomi, Vinod Venkataraman, Kaushik Veeraraghavan, Yee Jiun Song](https://dl.acm.org/doi/10.1145/3132747.3132749) — *SOSP*, 2017. — owns end-to-end tracing at production scale as an *analysis system*, not a viewer: the paper that established that trace collection and trace analysis are separate engineering problems.

### Monitoring, alerting, and what to page on

- <a id="ewaschuk-monitoring"></a>[ewaschuk-monitoring](#ewaschuk-monitoring) · [**Monitoring Distributed Systems** — Rob Ewaschuk (ed. Betsy Beyer), in *Site Reliability Engineering*](https://sre.google/sre-book/monitoring-distributed-systems/) (industry doc). — owns the **four golden signals** (latency, traffic, errors, saturation), the symptom-versus-cause rule for paging, the guidance that "latency increases are often a leading indicator of saturation," and the removal rule for unused signals. The competing taxonomy to [adk-observability](#adk-observability), and the source of the alert-fatigue failure mode ("employees second-guess, skim, or even ignore incoming alerts").
- <a id="dean-tail-at-scale"></a>[dean-tail-at-scale](#dean-tail-at-scale) · [**The Tail at Scale** — Jeffrey Dean, Luiz André Barroso](https://dl.acm.org/doi/10.1145/2408776.2408794) — *Communications of the ACM* 56(2), 2013. — owns **why percentiles rather than means**: the paper that established tail latency as the quantity worth monitoring in a composed system, and the techniques for cutting it rather than only measuring it.

### Metrics, cost, and routing

- <a id="chen-frugalgpt"></a>[chen-frugalgpt](#chen-frugalgpt) · [**FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance** — Lingjiao Chen, Matei Zaharia, James Zou](https://arxiv.org/pdf/2305.05176) — arXiv:2305.05176, 2023 (preprint). — owns the **cost of a model call as a first-class operational quantity** and the LLM-cascade pattern behind the module's `RoutedLlm`: matching GPT-4's performance "with up to 98% cost reduction."
- <a id="ong-routellm"></a>[ong-routellm](#ong-routellm) · [**RouteLLM: Learning to Route LLMs with Preference Data** — Isaac Ong, Amjad Almahairi, Vincent Wu, Wei-Lin Chiang, Tianhao Wu, Joseph E. Gonzalez, M Waleed Kadous, Ion Stoica](https://arxiv.org/pdf/2406.18665) — arXiv:2406.18665, 2024 (preprint). — owns the **learned router**: dynamic strong/weak model selection from preference data, reducing cost "by over 2 times in certain cases—without compromising the quality of responses." The measured version of "router by complexity."
- <a id="devatine-edit-distance"></a>[devatine-edit-distance](#devatine-edit-distance) · [**Assessing Human Editing Effort on LLM-Generated Texts via Compression-Based Edit Distance** — Nicolas Devatine, Louis Abraham](https://arxiv.org/pdf/2412.17321) — arXiv:2412.17321, 2024 (preprint). — owns the measurement behind the module's human-edit metric: a Lempel-Ziv-77 compression distance "highly correlated with actual edit time and effort," introduced because Levenshtein/BLEU/ROUGE/TER fail on block-level edits. Note the scope: **effort**, not correctness.
- <a id="shi-citeaudit"></a>[shi-citeaudit](#shi-citeaudit) · [**CiteAudit: You Cited It, But Did You Read It? A Benchmark for Verifying Scientific References in the LLM Era** — Kaiwen Shi, Weixiang Sun, Zheyuan Zhang, Lichao Sun, Nitesh V. Chawla, Yanfang Ye](https://arxiv.org/pdf/2602.23452) — arXiv:2602.23452, 2026 (preprint). *cf.* — owns the failure mode that makes edit-based quality signals insufficient: "fabricated references that appear plausible but correspond to no real publications," for which "manual verification becomes infeasible."
- <a id="li-citetracer"></a>[li-citetracer](#li-citetracer) · [**Source or It Didn't Happen: A Multi-Agent Framework for Citation Hallucination Detection** — Mingzhe Li, Zhiqiang Lin, Shiqing Ma](https://arxiv.org/pdf/2605.08583) — arXiv:2605.08583, 2026 (preprint). — owns the scale estimate for that failure: 957 real-world fabricated citations drawn from ICLR 2026 and desk-rejected submissions, and a field-level taxonomy replacing binary found/not-found checks.

### Drift, pinning, and why "the model changed under us" is a real incident class

- <a id="chen-behavior-changing"></a>[chen-behavior-changing](#chen-behavior-changing) · [**How is ChatGPT's behavior changing over time?** — Lingjiao Chen, Matei Zaharia, James Zou](https://arxiv.org/pdf/2307.09009) — arXiv:2307.09009, 2023 (preprint). — owns the **silent-update drift measurement** the module's model-pinning advice rests on: GPT-4's prime/composite accuracy fell from 84% to 51% between the March and June 2023 versions of the "same" service, with "evidence that GPT-4's ability to follow user instructions has decreased over time."

### Unsupported claims and own synthesis

- <a id="unsupported"></a>[unsupported](#unsupported) · **Unsupported.** Claims made in this module that no located source supports. Cited inline as [unsupported](#unsupported) rather than to an invented reference. Currently: that human-edit rate is *the best single proxy* for whether an agent is working. Edit effort is measured and correlated with effort (see [devatine-edit-distance](#devatine-edit-distance)), but no located source ranks it against other signals, shows it predicts correctness, or gives it a threshold. The claim's superlative — "best single" — is the course's, and §3 of the disagreement section records three ways the metric can mislead.
- <a id="literature-gap"></a>[literature-gap](#literature-gap) · **Named in the literature, not measured under this module's term.** Concepts the field owns under another name where the module's specific metric or mechanism has no instrument: **escalation rate** as a named operational metric (it exists as the *resolution* stage of the AgentOps framework[wang-agentops-survey](#wang-agentops-survey), not as a measured alerting signal); **citation-edit rate** (citation correctness is benchmarked[shi-citeaudit](#shi-citeaudit), [li-citetracer](#li-citetracer), but as detection accuracy, not as a deployment edit metric); and **"first diverging span"** as a defined artifact (localization is measured as Branch Recall@k[kang-zero-replay](#kang-zero-replay), not as span-level divergence detection).
- <a id="own-synthesis"></a>[own-synthesis](#own-synthesis) · **Own synthesis (not sourced).** Claims this module makes that are the course's framing rather than literature findings, flagged so they are not mistaken for citations: the log/metric/trace division of labor as a *table* (the pillars are the framework's framing[adk-observability](#adk-observability); the "answers" column is the course's); the five-metric alert set and its thresholds, including cost per run as the M13 budget-runaway signal; the framing that "observability is the passive span at both ends and everywhere between"; the claim that trace *structure* can be recorded everywhere while content is gated (the sources offer capture-fidelity choices with their own distortion costs[huang-mint](#huang-mint), not a free structure/content split); the principle that "incident response for agents is version-controlled and replayable, or it's guesswork"; and the claim that an agent "fails *more usefully*" when observable. The module's reply/rollback/kill-switch/pin toolkit is standard practice with no single owning paper located; it is presented here as practice, not as a finding.

---

**Next module:** [M17 — End-to-End Harness Design](../17-end-to-end-design/README.md) — how all the layers compose into one coherent, defensible design.
