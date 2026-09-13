# Class 6 vs Class 4: separable mechanisms, and the discriminator is one probe away

**Disputed question.** Can an AI engineer plausibly mistake failure class 6 (reasoning degradation under load) for failure class 4 (instruction drift & compliance decay)?

**Position.** Against. An engineer *can* conflate them — but only by skipping a discriminator that is available, cheap, and executable inside a single live session.

**Verdict.** Class 4 and class 6 are distinct mechanisms with distinct losses, distinct trace fingerprints, distinct owners (M6/M7 vs M10/M11), and distinct fixes; confusing them is a diagnostic-discipline failure, not an inherent ambiguity.

---

## The discriminating axis

**The two classes lose different objects: class 4 loses the *salience of a constraint that still exists in full and can be re-presented and obeyed*; class 6 loses the *integrity of an intermediate result that no longer exists in any re-presentable form*.**

- The module states the class 4 mechanism as attention dilution — instructions competing with retrieved text, tool results and user messages for salience (L58).
  - Therefore the constraint itself is intact: it is a standing string, authored outside the session, and an external actor can put it back. The module's own class 4 answer says the model "escalates correctly in short sessions — it *knows* the rule" (L295).
  - That is the whole axis: a rule the model still knows is a rule the harness can re-impose.
- The module states the class 6 mechanism as the absence of a persistent scratchpad, with intermediate results living in lossy attention, so error compounds across steps (L70).
  - The lost object is a *computed value at step N*, and it exists only as attention residue. Nothing external holds a canonical copy because the model never wrote one down.
  - Re-presentation is not merely ineffective here — there is nothing to re-present.
- Corollary that makes the axis operational: **class 4's failure object is reconstructible from outside the session; class 6's is not.** Because of that, the two admit different *classes* of corrective action, which is why the module assigns them to different owners (L119 vs L121).

---

## Observable discriminators — four probes, each with a verdict rule

- **Re-inject the rule mid-session, change nothing else.**
  - Compliance returns → class 4. The rule had lost salience; restoring salience restored behaviour (L58, L119).
  - Compliance stays broken → not class 4. If the agent recites the rule and still fails, the failing object was never the rule.
- **Re-run under an externalized harness — the "shorten the chain" probe, corrected.**
  - *Definition first:* "shorten the chain" means **externalize the handoffs between steps** — a persistent scratchpad, or one step per sub-agent call with the result appended to shared state. It does **not** mean pre-computing intermediates, and it does **not** mean handing the model a solved subproblem: pre-computing removes the task and proves nothing, and the model must still do every step.
  - The depth that matters is **how far a derived value must travel before it is written somewhere outside attention** — not the number of logical steps. Nine steps with every handoff externalized have depth ~1; the same nine steps in one monolithic call have depth 9 (L70).
  - **Verdict:** failure disappears under externalization → class 6; the loss was in attention-held derived values. Failure persists under externalization → not class 6 (or not only class 6); look at 4/5/8.
  - *Honesty note:* externalization grows the context (the state document), so "hold context length constant" is not literally satisfiable — read it as "matched task and inputs". The probe is the same operation as the class-6 remedy, so it establishes the diagnosis by applying the fix in a sandbox, not by a neutral counterfactual. (Worked example: `06-class-6-chain-depth-worked-example.md`.)
- **Hold the chain constant, shorten the context — the mirror probe.**
  - *Definition first:* "shorten the context" does **not** mean deleting turns from the production trace — that is lossy, and you cannot know which turns were "waste" until after the fact. It means **re-author the task in a fresh, minimal session**: same task state, same tools, same request, with the history that is not part of the task left out.
  - The compression key is **the task state**, never "the most recent question". Truncating to the recentmost turn drops the turns where the task was actually defined, and then you have changed the task, not compressed it.
  - **Validity condition:** the task must be *re-instantiable independently of its history*. Scenario C meets it — the task is {order X, refund $400, escalate-if-over-$50}, three messages' worth (L263, L295).
  - **Verdict:** shorter session, same task, failure gone → class 4; the loss was dilution. Failure survives re-authoring at short length → class 6.
  - <details>
    <summary><strong>Both probes are wrenches, not microscopes — and the retort that exposes it</strong></summary>

    - **The retort:** what if the task genuinely needs ten turns of context — the user chases one direction in turns 1–3, abandons it, and only settles later? Those early turns look like waste only in hindsight, and nothing in the session marks *the turn at which the user finally locked in*. So "shorten the context" cannot be done losslessly: every turn is a candidate for the one that mattered.
    - **Why the retort wins:** when the task *is* its own discovery — a debugging thread whose direction locked at turn 4 — there is no compact re-statement that does not either drop the discovery (changing the task) or do the reasoning for the model (pre-computing it). The mirror probe is then inapplicable; fall back to re-injection and the first-error trace reading.
    - **The wrenches:** "shorten the chain" removes class 6's causal variable (attention-held depth); "shorten the context" removes class 4's causal variable (dilution). Neither is a neutral observation — each applies the class's intervention in a sandbox and reads the response.
    - **Both assume a separation the failing harness never maintained:** value-from-attention, and task-from-noise.
    - **The un-runnability is itself the finding.** The harness stores everything undifferentiated — policy, chit-chat, wasted turns, and the moment the direction locked are all just tokens, with no record of *when the task got defined* or *which text is authoritative*. That undifferentiated context is the class 4/5/7 condition.
    - **The fix that closes the loop:** a harness that maintained **task state separately from conversation history** would already know when the direction locked, re-ground to it on demand, and make the mirror probe trivial — because the compact task state would already exist. Its absence is the observation, not an excuse.
    - **Worked across four domains:** `task-state-across-domains.md` — [healthcare](task-state-across-domains.md#healthcare) · [legal](task-state-across-domains.md#legal) · [SRE](task-state-across-domains.md#sre) · [finance](task-state-across-domains.md#finance).

    </details>
- **Ask the agent to state the rule before it acts.**
  - A drifting agent can usually still recite the standing policy verbatim; the recitation disproves the "it lost the rule" story and confirms the salience story (because the module's class 4 mechanism is competition, not deletion, L58).
  - A reasoner whose intermediate state has degraded typically cannot reconcile the stated rule with its own prior steps — it will defend the wrong subtotal as consistent with the rule it just recited. That defence is the class 6 tell, because the wrong value is still being reasoned *from* (L70).
- **Inspect the failure point in the trace.**
  - Class 4 is a **violation at a boundary**: an action taken that a standing rule forbade, and it is the *first* error in the trace — the steps before it are both rule-conformant and value-correct.
  - Class 6 is a **wrong value mid-chain**: the failing step is not the first error; it is correct-looking arithmetic built on an earlier wrong value. The module's own sequence — step six fails, then the failure cascades (L71) — is a definition of a derived error, not an original one.
  - Generalisation: **in class 4 the violating step is the origin of the error; in class 6 the failing step is the descendant of it.**

---

## The trace-graph difference

- Class 4 leaves a **policy-shaped fingerprint**: the offending action is locally reasonable and correct-looking, no rule appears in the reasoning that produced it, and the rest of the chain is sound. The rule was simply not consulted (L58).
- Class 6 leaves an **arithmetic-shaped fingerprint**: step N is wrong and steps N+1..N+k propagate it *consistently* — the suffix is internally coherent under a false premise (L70, L71).
- Why consistency-after-error is nearly unique to class 6: the error is a *value* the later steps were computed *from*, so coherence is the expected consequence of propagation.
  - A class 4 violation is not derived from anything prior, so downstream steps have no shared premise to agree with; their agreement, if any, is coincidence of local plausibility, not inheritance.
  - Test that follows: if you can substitute the true value at step N and the rest of the trace stays valid, the error was a committed value → class 6. If substituting the true value leaves the violating action still executable and still locally reasonable, no value was ever the problem → class 4.

---

## Two owners, two fixes — so the confusion is not free

- The module's map assigns class 4 to the instruction layer and memory — M6, M7 — with orchestration re-grounding only secondary (L119); and class 6 to orchestration — scratchpads, sub-agents — M10, M11, with multi-step evaluation secondary (L121).
- **Named wrong prescription #1 — scratchpads and sub-agents for a salience problem.**
  - Nothing about a scratchpad restores a competing instruction's salience; the policy is still prose in a long context.
  - Spawning sub-agents multiplies the failure surface: each child inherits the same diluted instruction with a fresh context, so the same drift reproduces per child — added latency and token cost, zero fix. The module's class 4 row puts re-grounding at secondary and the instruction layer at primary for exactly this reason (L119).
- **Named wrong prescription #2 — "re-ground the instruction" for a compounding-value failure.**
  - Re-stating a rule the agent already followed correctly at every step fixes nothing: no step violated the rule (L70's loss is the value, not the policy).
  - Worse, it invites the agent to re-derive from the same wrong anchor, re-emitting the propagated error with fresh confidence. The module's class 6 row does not list the instruction layer at all (L121).
- **The class-6 remedy relocates the failure, it does not remove it.** Externalizing intermediate state (scratchpad, sub-agents) shortens the attention-held chain but lengthens the context — the state document grows, and the early state and standing rules sink toward the middle of a long context. The same task that failed as class 6 (depth) can then fail as class 4/5 (length). Orchestration work (M10/M11) therefore must ship alongside re-grounding and context-assembly discipline (M4/M10), not alone as "fixed".
- A third, subtler failure mode of conflating: reaching for the M8 capability boundary as the universal fix. The tool ceiling in the module's class 4 answer (L297) is excellent against drift and cannot repair a wrong subtotal.

---

## What genuinely overlaps, and why overlap is not identity

- **Concede: they co-occur.** A long session is upstream of both — dilution for class 4 (L58), more steps, tools and chain length for class 6 (L69). Both are attention-over-a-growing-context phenomena.
- **Concede: the module itself says so.** Class 5 compounds with class 4 (L66), and the module's exercise opens by warning that "most incidents are combinations" (L254).
- **Concede: the causal substrate is shared.** Lossy attention is named in both rows (L58, L70).
- **Contain it — two faults on one input are not one fault.** The distinguishing question is not *whether attention degraded* but *what the attention had to carry*: a standing invariant that can be re-imposed from outside, or an intermediate value that exists nowhere else.
  - Shared upstream cause does not collapse downstream mechanisms; by that logic every long-session failure would be one class, which would make nine classes into two.
- **The discriminator is a controlled re-run, and it is affordable.** Probes 2 and 3 hold one variable and vary the other; probe 1 needs no re-run at all. The module's own Scenario C *is* this experiment, already run on both arms (L263, L295).
- **Note where the module does allow blending: it blends class 6 with class 8** — the repeat-tool guard stops "the loop pathology this module names as class 6/8" (L318). The module licenses a 6/8 blend and never a 6/4 blend; the module's own text is evidence for separability.

---

## The professional claim

- The module's thesis: "the model was wrong" is never a diagnosis (L30), and the physics of that refusal is precise naming — "sycophancy" and "instruction drift" are the words that convert vague alarm into an engineering work item (L243).
- The opening scene is the precedent: the postmortem wrote "the model hallucinated the discount policy," and the module names that line a **category error** — the model actually followed the most salient instruction in context (L11, L13).
- Writing "the agent drifted off the policy" over a cascading arithmetic failure reproduces that exact vice one class-pair over: a mechanism-shaped word stamped onto a cause nobody interrogated.
  - The module's exercise makes naming specific the deliverable, not a nicety — item 1 is "name the failure class(es) — be specific" (L254). "6 or 4, same thing" fails the exercise before it reaches the incident.
  - Because roughly 80% of "model failures" trace to harness layers (L104), a mis-named class routes the work to the wrong one, and the mis-naming is the only part of the incident that propagates into the budget.

---

## Evidence from the catalog — three clean classifications

- **Scenario C — the escalation that didn't (L263, L294–300) → class 4, clean.**
  - Stated symptom: a policy requiring escalation above $50 is obeyed in a 5-message session and violated at message 39 with a $400 refund.
  - What makes it clean: the module's own answer says the model *knows* the rule and escalates correctly in short sessions (L295) — the failure is salience loss, not state loss, and the module explicitly refuses "the model forgot the policy" as a diagnosis (L300).
- **Air Canada (2024) (L137) → class 4, clean.**
  - Stated symptom: the chatbot mis-stated the bereavement policy; the tribunal held the airline liable, rejecting the "separate legal entity" defence.
  - What makes it clean: a standing authored policy was displaced by the conversational frame at a single compliance boundary. There is no multi-step computational chain whose intermediate value could have degraded — reasoning: the incident shape has one failing step and no propagation.
- **Google Bard demo (2023) (L147) → class 1, clean (a control case).**
  - Stated symptom: claimed JWST took the "first picture" of an exoplanet; ~$100B of Alphabet value erased.
  - What makes it clean: a single fluent false statement with no chain to compound and no standing rule to decay — which is exactly why it is *not* class 4 or 6, and why the two under dispute cannot be the default home for every long-session failure.
- **Claude Code "human-as-infrastructure" (L225) → class 6, clean.**
  - Stated symptom: humans became the glue holding the agent together.
  - What makes it clean: reasoning — the human is supplying the persistent state the module says the model lacks (L70), so the missing object is an intermediate result, not a constraint. Re-injecting any rule would not remove the human.
- **Genuinely mixed, and worth naming as such — AutoGPT loops (2023) (L221).**
  - Stated symptom: unbounded loops burned API budgets; the module files loop pathology as "class 6/8" (L318).
  - Why it is mixed rather than a counterexample: the blend runs 6↔8 (chain degradation plus tool-call repetition), and notably not 6↔4.
- **Chevrolet Tahoe, sold for $1 (L195, L306) → class 8 + class 9, per the module's own analysis.** An authority/injection case, not a drift case; classify it as 4 or 6 and the remediation named at L309–L312 becomes unreachable.

---

## Why this matters at the C-suite level

- The instantiation is an org-chart decision: **class 4 buys instruction-layer and memory headcount (M6, M7) with orchestration re-grounding as a secondary spend (L119); class 6 buys orchestration headcount — scratchpads, sub-agents, multi-step verification evals (M10, M11, secondary M12).** These are different teams.
- Conflating them produces a mis-funded quarter and an unfixed production fault: the funded layer is chosen by the wrong noun, so the fault survives the spend and returns as a second incident.
- Evidence leadership should demand before approving either:
  - A four-cell control: {monolithic, externalized} × {long context, short context}, with the failure reproduced or cleared stated per cell — where "externalized" means scratchpad/sub-agent handoff, never pre-computed intermediates.
  - A re-injection probe result — did compliance return on the same session?
  - A trace appendix showing whether the failing step is the first error or the build-on of an earlier one.
  - Absent those three, the diagnosis is a hypothesis, not a root cause.
- Fund instruction-layer work (M6/M7) only if re-injection or the short-context arm clears the failure. Fund orchestration work (M10/M11) only if the *externalized* arm clears it at matched context length.

---

## The strongest attack on this position, and the rebuttal

- **The best case against me:** in production you get one trace, never a clean experiment. Long context and long chain are inseparable in real sessions, re-running is often impossible (side effects, cost, state), and the module itself names the same lossy attention in both rows (L58, L70) and admits compounding between classes (L66). On one trace alone, "the agent drifted" and "the agent got lost" can look identical, and the cheap probe is not available.
- **Rebuttal — the probe is not a re-run.** Re-injecting the rule mid-session requires no replay: if compliance returns in the same session with the chain untouched, the object lost was salience, and the trace's first-error position independently confirms it.
- **Rebuttal — the trace distinguishes without any experiment.** First error versus derived error is read off a single trace and needs no second run: class 4's violating action is the origin, class 6's failing step is the descendant.
- **Rebuttal — "we cannot always separate them" is not "they are the same mechanism."** The classes differ in what is lost, what restores it, and who fixes it; a shared confounder makes the diagnosis harder, not the mechanism singular.
- **Residual honesty:** where both probes are genuinely unavailable, the correct professional output is *two candidate causes with the discriminating evidence listed as missing* — the module's item 1 already permits combinations (L254). Naming that gap is diagnosis; collapsing the pair into one label is the thing this brief is against.

---

## The decision

- **Believe:** class 4 and class 6 are separable by a discriminator that is cheap, executable in-session, and independent of replay. Treat them as one failure and you have skipped work, not resolved ambiguity.
- **Fund:** whichever layer the four-cell control points at — instruction layer and memory (M6, M7) for drift, orchestration and verification (M10, M11) for load. Not both, on the same evidence.
- **Require:** the re-injection probe, the externalized-vs-monolithic arms, and the first-error-vs-derived-error trace reading before either purchase is approved.
- **What changes if this position is right:** the mis-funded quarter is avoidable, and the next long-session incident is diagnosed in one probe instead of one rewrite — which is the module's own promise that precise language turns alarm into a work item (L243).
- **What changes if this position is wrong:** the discriminator does not separate the two on real traces, the probe returns an ambiguous answer, and the honest report becomes a labelled pair of candidate causes with the missing evidence attached.
