# Task State Across Domains

## Table of Contents

- [Healthcare](#healthcare)
  - [Scenario](#healthcare-scenario)
  - [1. Concrete task state](#healthcare-1-concrete-task-state)
    - [The five fields, with worked values](#healthcare-the-five-fields-with-worked-values)
    - [The crack this scenario plants](#healthcare-the-crack-this-scenario-plants)
  - [2. Identification](#healthcare-2-identification)
    - [How the state-update step actually works](#healthcare-how-the-state-update-step-actually-works)
    - [Where it breaks](#healthcare-where-it-breaks)
  - [3. Lock-in detection](#healthcare-3-lock-in-detection)
    - [What "lock" means here](#healthcare-what-lock-means-here)
    - [Why a clinical question may sharpen rather than lock](#healthcare-why-a-clinical-question-may-sharpen-rather-than-lock)
    - [False lock and refusal-to-lock](#healthcare-false-lock-and-refusal-to-lock)
    - [The decision forced, and the human](#healthcare-the-decision-forced-and-the-human)
  - [4. Re-grounding](#healthcare-4-re-grounding)
    - [What gets injected, when](#healthcare-what-gets-injected-when)
    - [What is lost in projecting to the compact state](#healthcare-what-is-lost-in-projecting-to-the-compact-state)
    - [Where re-grounding alone is insufficient](#healthcare-where-re-grounding-alone-is-insufficient)
  - [5. Mirror-probe-trivial](#healthcare-5-mirror-probe-trivial)
    - [Does the object reconstruct the task losslessly?](#healthcare-does-the-object-reconstruct-the-task-losslessly)
    - [What that reveals](#healthcare-what-that-reveals)
  - [Verdict](#healthcare-verdict)
- [Legal](#legal)
  - [Domain setup](#legal-domain-setup)
  - [Step 1 — Concrete task state (and why `goal` is a lie here)](#legal-step-1-concrete-task-state-and-why-goal-is-a-lie-here)
  - [Step 2 — Identification: what the diff does, and where it breaks](#legal-step-2-identification-what-the-diff-does-and-where-it-breaks)
  - [Step 3 — Lock-in: where locking is catastrophic](#legal-step-3-lock-in-where-locking-is-catastrophic)
  - [Step 4 — Re-grounding: what's injected, what's lost](#legal-step-4-re-grounding-whats-injected-whats-lost)
  - [Step 5 — Mirror-probe-trivial: the reconstruction that re-does the discovery](#legal-step-5-mirror-probe-trivial-the-reconstruction-that-re-does-the-discovery)
  - [Verdict](#legal-verdict)
- [SRE](#sre)
  - [1. Concrete task state](#sre-1-concrete-task-state)
    - [Walk](#sre-walk)
    - [Break](#sre-break)
  - [2. Identification](#sre-2-identification)
    - [Walk](#sre-walk-2)
    - [Break](#sre-break-2)
  - [3. Lock-in detection](#sre-3-lock-in-detection)
    - [Walk](#sre-walk-3)
    - [Break — the crux](#sre-break-the-crux)
  - [4. Re-grounding](#sre-4-re-grounding)
    - [Walk](#sre-walk-4)
    - [Break](#sre-break-3)
  - [5. Mirror-probe-trivial](#sre-5-mirror-probe-trivial)
    - [Walk](#sre-walk-5)
    - [Break](#sre-break-4)
  - [Verdict](#sre-verdict)
- [Finance](#finance)
  - [1. Concrete task state](#finance-1-concrete-task-state)
  - [2. Identification](#finance-2-identification)
  - [3. Lock-in detection](#finance-3-lock-in-detection)
  - [4. Re-grounding](#finance-4-re-grounding)
  - [5. Mirror-probe-trivial](#finance-5-mirror-probe-trivial)
  - [Verdict](#finance-verdict)

<a id="healthcare"></a>
## Healthcare

# Task State Under Stress — Healthcare Prior-Authorization for Advanced Imaging

> One framework idea (task state + identification + lock-in + re-grounding + mirror-probe-trivial), one industry, stress-tested to failure.

<a id="healthcare-scenario"></a>
## Scenario

- Domain: prior-authorization agent for advanced imaging (MRI/CT).
- Input: a clinician's office requests pre-authorization for an MRI for patient `P-4821`.
- Output: `approve` / `deny` / `route-to-human`, each grounded in the payer's medical-necessity policy.
- Stakes: a wrong `deny` delays diagnosis; a wrong `approve` exposes the patient and spends the plan; both are class-7 (overlooked constraints) and class-1 (hallucination) hazards (L77–81, L38–43).

<a id="healthcare-1-concrete-task-state"></a>
## 1. Concrete task state

<a id="healthcare-the-five-fields-with-worked-values"></a>
### The five fields, with worked values

- `goal`: "Determine medical necessity for MRI lumbar spine (CPT `72148`, without contrast) for `P-4821` under policy §4; emit approve / deny / route-to-human."
- `constraints`:
  - "No decision until every policy-required clinical element is present and cited."
  - "A denial must name the exact failed criterion (§4.x), never a paraphrase."
  - "Any criterion whose satisfaction requires clinical judgment → route-to-human."
  - "Never fabricate a diagnosis code or an exam finding (class 1)."
- `bindings`:
  - patient: `P-4821`, 64M
  - requested study: `MRI lumbar spine w/o contrast` / CPT `72148`
  - ordering clinician: `Dr. R`
  - primary diagnosis code: `M54.5` (low back pain) — extractable, machine-checkable
  - documented conservative therapy: `4 weeks PT` (policy §4.2 requires `6`)
  - alleged red flag: `progressive lower-extremity weakness` — free-text, uncoded
- `decisions`:
  - `d1`: "§4.2 conservative-therapy requirement applies" — provenance: `policy §4.2` + `chart note 2024-01-12`
  - `d2`: "PT documented = 4 weeks, below the 6-week threshold" — provenance: `PT notes 2024-01-03..02-01`
  - `d3`: "open — whether 'progressive weakness' invokes the §4.9 red-flag waiver" — provenance: `clinician phone note (unstructured)`
- `open questions`:
  - `q1`: "Does the documented weakness meet §4.9's 'progressive neurological deficit' bar?"
  - `q2`: "Is CT lumbar an acceptable, policy-sanctioned substitute?"

<a id="healthcare-the-crack-this-scenario-plants"></a>
### The crack this scenario plants

- `bindings` mixes two incommensurate kinds: *extractable* (`M54.5`, dates, CPT) and *judged* (`progressive`, `red flag`).
- That incommensurability is the crack every later step falls into.

<a id="healthcare-2-identification"></a>
## 2. Identification

<a id="healthcare-how-the-state-update-step-actually-works"></a>
### How the state-update step actually works

- After each turn (clinician message, chart fetch, policy lookup, code extraction), a rewriter emits a fresh task-state object.
- A diff engine compares per-field: which bindings changed, which decision flipped, which open question opened or closed.
- Turn 1 → turn 2 example diff: `bindings` gained `alleged red flag`; `decisions.d3` was added (a new open question opened).

<a id="healthcare-where-it-breaks"></a>
### Where it breaks

- The sharp question: is a diagnosis code *task state* or *context*? `M54.5` is state — a binding the goal names. The clinical context that makes `M54.5` *relevant to §4.9* is context.
- But "progressive lower-extremity weakness" is neither cleanly: it is a *candidate binding* whose admission depends on a clinical judgment (is this a red flag?).
- Identification here requires judgment, not extraction. Extracting `M54.5` is mechanical; deciding the weakness is a red flag *is the task itself*.
- The framework's premise is that the state-update step is a faithful *projection*; in prior-auth the projection is itself a clinical act, so identification inherits the model's failure modes instead of removing them.
- Concretely, classifying free text into binding-vs-noise is where hallucination (class 1) and sycophancy (class 2, if the clinician's confidence steers it) enter — the exact classes the harness was meant to contain (L38–43, L45–49).
- The module's opening scene names the same category error from the other side: the agent had "no mechanism to know which text in its context was policy and which was data" (L13). Identification is supposed to supply that mechanism, and here it must — but the classifier is the same model that confabulates.

<a id="healthcare-3-lock-in-detection"></a>
## 3. Lock-in detection

<a id="healthcare-what-lock-means-here"></a>
### What "lock" means here

- Lock fires when `goal` + `bindings` stop changing across turns while `open questions` keep churning.
- Worked signal: turns 6–10 all carry identical `{P-4821, M54.5, 4wk PT, MRI lumbar}` while `q1`/`q2` keep being re-stated or re-worded → direction locked.

<a id="healthcare-why-a-clinical-question-may-sharpen-rather-than-lock"></a>
### Why a clinical question may sharpen rather than lock

- A legitimately open clinical question either *resolves* (a new binding lands: an EMG confirms radiculopathy) or stays pending on one decisive datum.
- "Sharpen" = a new binding arrives, so it is *not* lock by the framework's own rule — bindings changed.
- The detector cannot distinguish "churning because the model is lost" from "legitimately waiting on one test result."

<a id="healthcare-false-lock-and-refusal-to-lock"></a>
### False lock and refusal-to-lock

- False lock: bindings stay stable because extraction is *stale* — the agent reuses the same three facts and never re-reads a new chart note that would change `bindings`. Detector says "locked, proceed"; the direction is settled-but-wrong.
- Refusal-to-lock: the model re-words "progressive weakness" each turn (symptom / finding / red flag / contraindication), so `bindings` churn forever and the detector never fires — the agent re-asks the clinician the same question in a loop (class 6 / 8) (L69–73, L84–87).
- reasoning: lock-in treats *stability of the record* as *stability of the reasoning*. In medicine the record can be stable while the reasoning is wrong, and the reasoning can be unstable while the record is trivially stable.

<a id="healthcare-the-decision-forced-and-the-human"></a>
### The decision forced, and the human

- What lock forces is a *procedure* — emit approve/deny/route — not a *medically necessary* answer.
- Lock is the point where reasoning has *stalled*, not the point where a decision is *safe*.
- The framework cannot force medical necessity out of a stalled record; it can only force the constraint "uncertified open question → route-to-human."
- Human intervention is required whenever a denial or approval rests on a judgment the state cannot certify (the §4.9 red-flag override). That is a class-7 constraint + M15 governance boundary, not a lock-detection output (L77–81, L123–127).

<a id="healthcare-4-re-grounding"></a>
## 4. Re-grounding

<a id="healthcare-what-gets-injected-when"></a>
### What gets injected, when

- Inject `{goal, constraints, bindings, decisions, open questions}` + the current turn's request immediately before the current action.
- When: every turn; always when context length crosses a threshold or when a failure is suspected (open questions churning, tool retry).
- This is the class-4 / class-5 mitigation the module names: keep the standing rule salient near the current task instead of letting it decay in the middle (L57–61, L63–67).
- But the module's own Scenario C answer ranks this fix "secondary, weaker than the tool fix" (L301) — and that ranking is the whole verdict here.

<a id="healthcare-what-is-lost-in-projecting-to-the-compact-state"></a>
### What is lost in projecting to the compact state

- `decisions.d2` stores "PT = 4 weeks, insufficient" but drops *why* the 4 weeks count as 4 (the note said "attended 8 of 12 scheduled visits").
- `bindings` stores the alleged red flag but drops *"subjective, patient-reported, no exam finding"* — the qualifier that decides whether §4.9 is met.
- The provenance is a pointer, not the evidence; the nuance that *justified* a decision lives in the free text the object was projected from.

<a id="healthcare-where-re-grounding-alone-is-insufficient"></a>
### Where re-grounding alone is insufficient

- Re-grounding re-injects the same lossy object; it cannot restore the dropped nuance, because the nuance was never in the object.
- The real boundary is a human approval gate (M15) on any decision that turns on uncertified clinical judgment — re-grounding is a *salience* fix, not an *evidence* fix.
- The module's own logic says so: the correct fix is to make the action itself impossible without escalation, not to re-state the rule (L295, L299–301). The prior-auth analog is a `deny`/`approve` action that refuses to fire while any binding is `uncertified` — a capability boundary, not a prompt.

<a id="healthcare-5-mirror-probe-trivial"></a>
## 5. Mirror-probe-trivial

<a id="healthcare-does-the-object-reconstruct-the-task-losslessly"></a>
### Does the object reconstruct the task losslessly?

- No. It reconstructs the *checklist layer* losslessly: codes, dates, CPT, and policy-section pointers are mechanical and round-trip.
- It does not reconstruct the *judgment layer*: "is the weakness a red flag under §4.9" is not in the object; it is in the free text the object was projected from, and the projection was a lossy, judgment-laden act.

<a id="healthcare-what-that-reveals"></a>
### What that reveals

- The "shorten the context is lossless" claim holds only where task state is genuinely *separable* from context.
- Prior-auth is separable on its checklist spine and inseparable exactly at its highest-risk point — medical necessity itself.
- reasoning: the framework survives as a routing/checklist scaffold and fails as a decision-maker; it can guarantee that the *procedure* doesn't drift, but not that the *judgment* is right.

<a id="healthcare-verdict"></a>
## Verdict

- The framework does not survive as a decision engine in this domain.
- It survives as a context-stability and escalation scaffold whose one real contribution is forcing the agent to name, per turn, what is extractable vs what must go to a human.
- The failure is not a bug in any one of the five steps; it is the shared assumption that task state is separable from context and losslessly reconstructable, which medical necessity violates by construction.


<a id="legal"></a>
## Legal

# Task-State Framework, Stress-Tested: Legal M&A Due-Diligence Red-Flag Agent

<a id="legal-domain-setup"></a>
## Domain setup

- Agent: reviews ~500 documents to surface material risks before deal close.
- Consumer: buyer's counsel, deciding walk / renegotiate / proceed.
- Stakes: a missed flag is the signed liability clause the module already names — Scenario A (L262, L270–280).

<a id="legal-step-1-concrete-task-state-and-why-goal-is-a-lie-here"></a>
## Step 1 — Concrete task state (and why `goal` is a lie here)

Fields with worked values:

- `goal`: "Surface all material risks to Buyer in acquiring TargetCo's widget division."
  - reasoning: vacuous — a placeholder that says nothing until reading begins.
- `constraints`: materiality threshold ($250k or deal-thesis-relevant); every flag cites doc + clause; nothing asserted without provenance; hard stop at close date.
- `bindings`: TargetCo; widget division; purchase agreement; earn-out provision; material customer contracts; counterparties.
- `decisions`: `scope = {corporate authority, IP ownership, litigation, customer concentration}` — provenance: counsel's initial scope letter.
- `open questions`: "Does TargetCo own the patent it licenses to its largest customer?" — provenance: licence agreement §4.2.

Break:

- The framework assumes `goal` is given and stable; here the goal **is** the output.
- The real diligence question — "is the earn-out collateral actually TargetCo's to sell?" — crystallizes only around doc ~200.
- So `goal` and `open questions` collapse into one field: the goal *is* an open question.
- A worked example must either write a vacuous goal (class 9: literal-but-wrong, L89–93) or smuggle the answer in as the goal.
- reasoning: the separation the whole framework leans on does not exist in this domain.

Also:

- A risk flag is neither `decision` nor `binding`: it is a *finding* with a confidence, not a commitment.
- The agent's genuine decisions are few (prioritization, threshold calls) and are not the load-bearing content; the binding decisions — walk / renegotiate / proceed — sit with counsel, outside the agent.
- `bindings` implies facts; "the licensed patent" is itself a hypothesis that ownership is defective.

<a id="legal-step-2-identification-what-the-diff-does-and-where-it-breaks"></a>
## Step 2 — Identification: what the diff does, and where it breaks

How it works:

- Each turn, a state-update step rewrites the five fields and diffs against the prior object.
- Diff signals: new bindings, changed goal, new decisions, churning open questions.

The sharp question:

- Is a risk flag a `decision` in task state, or is it context?
- If **context**: it is excluded from the compact state; re-grounding never carries it; the citation trail drops out.
- If **task state**: the state re-encodes the documents to hold the flags, and "compact" dies.
- reasoning: either way the framework loses the one thing that matters.

The emerging hypothesis:

- The hypothesis is part of the *reasoning* — the chain clause → materiality.
- The framework explicitly keeps reasoning out of task state ("how it got there" vs "what it is doing").
- So the actual work product — the risk hypothesis — lives in the layer the framework treats as disposable.
- reasoning: identification here can only diff scaffolding, never substance.

<a id="legal-step-3-lock-in-where-locking-is-catastrophic"></a>
## Step 3 — Lock-in: where locking is catastrophic

What lock means:

- `goal` + `bindings` stable across turns while `open questions` churn ⇒ direction locked.
- Per-field, revocable, provenance supports unlock.

Why locking the wrong scope is catastrophic:

- A red flag outside the locked bindings is exactly what kills a deal — the missed liability clause (L77–81, L270–280).
- Lock on "target's IP is clean" while questions churn = premature closure, not completion.
- Sycophancy worsens it: the agent locks onto the conclusion the buyer hopes for (L45–50).

Why the domain resists lock:

- Every new document can reopen a closed binding; doc 437 can invalidate doc 12's conclusion.
- Diligence scope is revisable **by definition** — revision is the value, not a defect.
- So the mechanical lock signal is a false-positive-for-correctness: it fires when the agent *stopped looking*.

The decision forced:

- Is lock a mechanical signal (`goal`+`bindings` stable) or a governance gate?
- It must be the latter: scope confirmation carries legal consequence, and the agent cannot bind its own scope.
- reasoning: lock-in detection here flags the failure, not the success.

Human intervention:

- Counsel must confirm scope at each lock event; the agent cannot declare diligence scope closed.
- Lock is a handoff to counsel, not a state transition the agent owns.

<a id="legal-step-4-re-grounding-whats-injected-whats-lost"></a>
## Step 4 — Re-grounding: what's injected, what's lost

What gets injected:

- Current task state near the current action, when context grows or a failure is suspected.

What's lost:

- The **citation trail** — which document, which clause.
- "62% revenue from one customer" without "purchase agreement exhibit 3, revenue schedule, clause 4.2" is a hallucination waiting to happen (L38–43).
- The flag survives projection; the load-bearing evidence does not.

Where re-grounding alone is insufficient:

- It re-injects conclusions, not the evidence the conclusions rest on.
- The model then re-derives or confabulates the citation (class 1), and the flag floats unverifiable.
- It also does not fix position bias — injecting state near the action just moves emphasis; the middle of 500 docs is still the middle (L63–67).
- reasoning: re-grounding preserves the summary and discards the proof.

<a id="legal-step-5-mirror-probe-trivial-the-reconstruction-that-re-does-the-discovery"></a>
## Step 5 — Mirror-probe-trivial: the reconstruction that re-does the discovery

The claim:

- Short-session reconstruction = mechanical render of the task-state object + the current request.
- So "shorten the context" is lossless by construction.

Why it fails here:

- The "task state" that matters is the set of risk hypotheses with citations — the deliverable.
- Reconstruction either contains the hypotheses (then it *is* the diligence report, not a scaffold) or contains only the scaffolding (then the discovery is lost and must be re-read).
- reasoning: no compression is lossless, because the state and the product are the same thing.

What this reveals:

- Task state is a scaffold for domains where the goal is given and the work is execution.
- It is not a scaffold for domains where the goal *is* the work product.
- The framework's limit: it conflates "what the agent is doing" with "what the agent is producing," and here they coincide.

<a id="legal-verdict"></a>
## Verdict

- The framework survives only as a **citation ledger** — an evidence index keyed doc → clause → flag.
- As a task-state scaffold it collapses: `goal`/`open questions` merge, `decisions` holds almost no real decisions, and mirror-probe-trivial is false.
- reasoning: in discovery work the state is the deliverable, so no side-band record can be both compact and lossless.


<a id="sre"></a>
## SRE

# Task State vs. Root-Cause — a stress test

**Scenario.** Software/SRE production-incident root-cause agent.
Incident: "checkout is returning 500s since the 14:02 deploy."
The agent must diagnose, then fix / roll back / page on-call.

**Framing.** The framework's `goal` is a *restore*, but the agent's *direction* is the current *hypothesis* — which is revocable by nature. Stress-test the framework against that tension.

---

<a id="sre-1-concrete-task-state"></a>
## 1. Concrete task state

<a id="sre-walk"></a>
### Walk

- `goal` = restore, not explain: `"checkout returns non-500"` — constant for the whole incident.
- `direction` = current hypothesis `H1: "deploy d-14:02 introduced the regression"` — revocable, and *not* the goal.
- Worked value per field:
  - `goal` — restore checkout availability.
  - `constraints` — read-only by default; no rollback without a verified rollback plan; page on-call at 20 min without a confirmed cause.
  - `bindings` — service=checkout, env=prod-us-east-1, deploy={id=d-14:02, sha=abc123, prev=def456}, symptom="POST /checkout → 500", window=14:02Z.
  - `direction` — `H1 = bad deploy` (**no schema slot**; see break).
  - `decisions` — [{conclusion:"H1 is lead", evidence:[error-rate breakpoint ≈ 14:02, prev-sha flat], provenance:[metric:p50_error_rate, tool:deploy_diff]}, {conclusion:"rollback to def456 is candidate", status:"not-executed", provenance:[policy:rollback-gate]}].
  - `open questions` — [coincident DB failover at 14:01? 500 on all routes or POST only? config change, not code?].

<a id="sre-break"></a>
### Break

- The five fields have no slot for `direction`/hypothesis — the one field the whole domain turns on.
- Forcing H1 into `decisions` mislabels a conjecture as a commitment; forcing it into `open questions` drops the fact that it is the *current* working direction.
- reasoning: the schema is missing its most load-bearing field, so the diff (§2) and the lock detector (§3) are both blind to it.

<a id="sre-2-identification"></a>
## 2. Identification

<a id="sre-walk-2"></a>
### Walk

- After each tool turn, a state-update step rewrites task state as a structured object and diffs it field-by-field against the prior version.
- Diff output per field: `{added, removed, changed, unchanged}` across goal / constraints / bindings / decisions / open questions.

<a id="sre-break-2"></a>
### Break

- The update step is itself an LLM call, so it inherits all nine failure classes.
  - A state-writer that hallucinates "rollback executed" poisons every downstream read (class 1, L38).
  - String diffs on `decisions`/`open questions` are shallow: "candidate rollback" vs "rollback candidate" registers as a change (class 3, L51).
- Cost: an extra model call per turn on the incident hot path. reasoning: during an outage, latency is MTTR, and this tax is paid at the worst moment.
- The sharp question — is `H1 = bad deploy` task state or context?
  - Neither cleanly: it is a live conjecture with evidence attached, which the schema has no slot for (§1 break).
  - Consequence: the diff cannot distinguish "hypothesis flipped" from "hypothesis refined."
- If the hypothesis flips turn-over-turn, is that a lock event or just investigation?
  - Under the framework's own trigger (goal+bindings stable, open questions churning) it is *not* lock — it is exactly the healthy revision this domain wants.
  - But the detector never sees the flip, because the hypothesis is not a tracked field. The one signal that matters is invisible.

<a id="sre-3-lock-in-detection"></a>
## 3. Lock-in detection

<a id="sre-walk-3"></a>
### Walk

- Trigger: `goal`+`bindings` stop changing while `open questions` still churn → direction has locked.
- Lock is per-field and revocable; provenance supports unlock.

<a id="sre-break-the-crux"></a>
### Break — the crux

- This domain explicitly does NOT want lock-in; it wants tracked revision.
  - Lock here = committed to H1 = confirmation bias = you miss the coincident DB failover.
  - reasoning: the framework's "lock" is only the *correct* state when evidence supports it, and the detector cannot tell supported lock from unsupported lock.
- The detector fires almost immediately and never unlocks.
  - `goal` is constant by construction; `bindings` are set at t=0 and rarely change; `open questions` churn for the entire investigation.
  - So "locked" is reported on turn 2 and stays reported — lock becomes a constant, not an event → a useless signal.
- The decision forced:
  - (a) redefine lock for this domain as "hypothesis unchanged across N turns *despite* disconfirming evidence" — the *inverse* of the framework's definition; or
  - (b) admit the framework measures goal/bindings stability, which is trivially true here, so it measures nothing about direction.
- Does a human on-call arbitrate the flip?
  - The flip H1→H2 (belief revision) needs no human: it is cheap, reversible reasoning, and a human gate on every flip only adds outage latency.
  - What needs human (or pre-authorized policy) arbitration is the *action the hypothesis licenses*: rollback is a `decision` with blast radius, and that decision — not the flip — is the gate. reasoning.

<a id="sre-4-re-grounding"></a>
## 4. Re-grounding

<a id="sre-walk-4"></a>
### Walk

- Inject the compact task-state object near the current action each turn (or when context grows / a failure is suspected), so the model acts on current state instead of re-deriving it from long undifferentiated history.
- This is the framework's fix for instruction drift (class 4, L57) and position bias (class 5, L63).

<a id="sre-break-3"></a>
### Break

- Re-grounding only the *conclusion* (H1) without the *evidence* produces confirmation bias.
  - Handed "current hypothesis: bad deploy" near the action, the model gathers confirming evidence and skips disconfirming checks.
  - reasoning: sycophancy toward the model's own prior (class 2, L45) plus an overlooked "consider alternatives" constraint (class 7, L77).
- The evidence trail must ride along: re-ground `decisions[].conclusion` **and** `decisions[].evidence` (the p50 delta, the breakpoint timestamp, the trace pointer) — conclusion alone is worse than nothing.
- Where re-grounding alone is insufficient:
  - Faithful reproduction of a wrong state: if the state-writer fabricated a metric, re-grounding reproduces the error; grounding is only as good as the state object.
  - Lossy compression: you cannot re-ground the raw 14:02 deploy diff or the full trace into a compact object without dropping the disconfirming detail.
  - It fixes position/drift but not reasoning degradation (class 6, L69) nor tool loops (class 8, L83); the repeat-tool guard (L318) is a separate mechanism the framework does not supply.

<a id="sre-5-mirror-probe-trivial"></a>
## 5. Mirror-probe-trivial

<a id="sre-walk-5"></a>
### Walk

- Claim: short-session reconstruction is a mechanical render of the task-state object + the current request, so "shorten the context" is lossless by construction.

<a id="sre-break-4"></a>
### Break

- The investigation *is* the task, so reconstruction ≈ rerunning the investigation.
  - The work product of a root-cause agent is the evidence trail (metrics, traces, hypotheses tested, hypotheses falsified) — not the goal/bindings.
  - `decisions` with provenance is the framework's only slot for evidence; if provenance stays lossless, the object is no longer compact.
- The tension: compact (mirror-lossless) vs. lossless (must carry evidence) — this domain cannot have both.
  - Drop the evidence to stay compact → reconstruction re-fetches every dashboard, re-pulls every log → mirror-probe-expensive.
  - Keep the evidence → the "compact state" is the full incident transcript → mirror-probe-trivial is vacuously true.
- What it reveals:
  - The framework models task state as *control state* ("what am I doing / allowed to do"), but this domain's state is *data state* ("what have I learned").
  - It survives for the control fields (goal, constraints, the rollback boundary) and breaks on the epistemic content (the investigation).

---

<a id="sre-verdict"></a>
## Verdict

- Survives as a *control/authorization* ledger; fails as an *investigation* memory.
- The single worst break is the missing `direction` slot: the schema cannot track the one field the domain turns on, so diff and lock are both blind to it.


<a id="finance"></a>
## Finance

# Task-state framework, stress-tested: portfolio rebalancing / trade-instruction agent

> Scenario: a client instructs "reduce my tech exposure to 20%." The agent drafts sell/buy orders within regulatory and client risk constraints, with a human approval gate before any order executes.

<a id="finance-1-concrete-task-state"></a>
## 1. Concrete task state

Worked value per field:

```jsonc
{
  "goal": "Draft sell orders to reduce client tech-sector equity from ~32% to 20% of AUM, and buy orders to redeploy proceeds, for approval only.",
  "constraints": [
    {"src": "client instruction", "text": "reduce my tech exposure to 20%", "status": "current"},
    {"src": "IPS §4.2", "text": "no short sales; max 5% single-position; drift bands ±3%"},
    {"src": "Reg BI / FINRA 2111", "text": "suitability & best interest, documented"},
    {"src": "IRS wash-sale", "text": "no repurchase of substantially identical security within 30d in any related account"}
  ],
  "bindings": {
    "client_id": "ACME-1042",
    "account_type": "taxable",
    "target_tech_weight": 0.20,
    "current_tech_weight": 0.32,
    "positions": {"AAPL": 0.062, "MSFT": 0.051, "NVDA": 0.044, "QQQ": 0.071}
  },
  "decisions": [
    {"id": "d1", "text": "sell NVDA 400sh, LIFO lot", "provenance": "tax-lot optimizer v3 → client tax profile", "status": "draft"},
    {"id": "d2", "text": "redeploy proceeds → VTI", "provenance": "IPS §4.2 reallocation policy", "status": "draft"}
  ],
  "open_questions": [
    "does 'tech exposure' include QQQ (~50% tech overlap)?",
    "20% measured gross or net of cash?",
    "any NVDA purchase in last 30d (wash-sale) in a related account?"
  ]
}
```

The blur, named plainly:

- `goal`, `constraints`, and `bindings` all derive from the *same* authoritative texts.
- "20%" is simultaneously a binding (target value), a constraint (ceiling), and the goal (objective). The schema forces one slot; the reality is all three.
- The no-wash rule and risk limits are standing policy (apply to every client, every trade); the 20% figure is this instruction's task state. But the IPS *is* standing policy that this instruction invokes as a binding — the boundary is not in the text, it is a classification someone must assign. This is the class-4 blur (L57-61) re-appearing as a schema problem.

<a id="finance-2-identification"></a>
## 2. Identification

How it works:

- After each turn, a state-update step re-reads the conversation + tool results, rewrites the object, and diffs each field against the prior version.
- Diff granularity is per-field: goal, bindings, decisions, open questions.

Where it breaks:

- The task-state vs standing-policy split is a *prior* design decision, not something the diff can discover. The diff compares two objects; it cannot tell you the objects assigned "no-wash" to the wrong bucket.
- Who decides the split: a human (compliance/advisor) pre-authorizes the taxonomy; the broker's OMS enforces standing policy as capability boundaries, not as diffable text. The framework offers no slot for this delegation.
- A stable-but-wrong binding diffs clean. The identification step transcribes "20%" → "25%" (class 1, L38-43) or mis-parses a paraphrase (class 3, L51-55); the object is wrong *consistently*, so the diff reports no drift. Identification detects change *between turns*, never error *against source text*.
- Re-phrasing reads as churn. The client re-states "20%" as "one-fifth"; bindings churn, the diff flags unsettled direction that does not exist.

<a id="finance-3-lock-in-detection"></a>
## 3. Lock-in detection

The conflation is the failure:

- Framework "lock" = goal+bindings stable while open questions still churn = a *planning* signal ("we settled the plan").
- Finance "lock" = a binding becomes *irreversible* — executed order, settled trade (T+1), elected tax lot. That is a *legal* signal, and the framework has no field for it.

Premature lock:

- Open questions drain to empty because the agent silently resolved one wrongly — e.g., decided QQQ is "not tech" rather than asking (class 7 overlooked constraint, L77-81; class 2 sycophancy, L45-49). The diff reads "stable," reports lock, and the direction freezes on a bad binding. That is a compliance event: orders drafted on an unconfirmed interpretation.

False unlock / failure to lock:

- Open questions keep churning after the client already answered ("gross or net" re-asked every turn). The detector refuses to lock; the agent stalls or re-drafts the same orders.

Forced decision:

- Whether a drafted order may cross into the execution system. The framework cannot decide this — it has no notion of *irreversibility* or *authority*.

Human intervention: required, and not optional:

- The approval gate is the real lock. The framework's detector can flag "direction stable, execution imminent," but order release is a human authorization recorded as a decision with provenance (approver, timestamp, authority). reasoning: without this, the framework's "lock" is a planning heuristic wearing a governance costume.

<a id="finance-4-re-grounding"></a>
## 4. Re-grounding

What gets injected, when:

- The current task-state object, placed adjacent to the current action (the draft-order step), so binding facts sit near the action rather than at token 3,000 — the class-4 / class-5 (L63-67) mitigation.

Where it breaks:

- Re-grounding a *superseded* instruction amplifies staleness. Client says "20%," then "make it 25%." If the object still reads 20%, injection makes the withdrawn figure maximally salient at the exact moment it matters. The object is only as current as identification, and identification can misclassify supersession as re-phrasing.
- Re-grounding is silent about *authority*. A correct, current object next to the action still does not authorize execution. It improves fidelity to the plan, not permission to act.
- Where re-grounding alone is insufficient: any action that changes a binding's reversibility class (draft → executed → settled) must pass a human gate. That gate is a capability boundary in the OMS (class 8, L83-87) and a governance concern (class 9, L89-93), not a context trick. reasoning: conflating "clear context" with "authorized action" is the Tahoe failure shape — the model does the thing because the plan was clear, and authority was never checked (L307-315).

<a id="finance-5-mirror-probe-trivial"></a>
## 5. Mirror-probe-trivial

Does the object reconstruct the task losslessly? No, on two dimensions:

- Intent is lost. "reduce tech exposure to 20%" is a compression of the client's fuller instruction (concern about AI concentration, fund tuition next year, keep it tax-efficient). The object re-derives the letters, not the intent — class 9 misspecification is built in (L89-93).
- Reversibility class is lost. Settled trades are irrevocable facts about the world; drafted orders are revocable proposals. The schema has one `bindings` field with no irreversibility flag. reasoning: reconstructing a settled trade as a draft permits a phantom re-sell (double-sell) of the same position; reconstructing a draft as settled fabricates a position that was never bought.

What mirror-probe-trivial would need to be true here:

- `bindings` must carry `status ∈ {draft, approved, executed, settled}` and `reversibility ∈ {revocable, irrevocable}`, and the reconstruction must preserve both. The framework as specified does not, so the reconstruction is lossy exactly where finance cares.

<a id="finance-verdict"></a>
## Verdict

- Survives as *context hygiene*: the object and re-grounding genuinely tame instruction drift (class 4) and position bias (class 5), which are real in this domain.
- Fails as a *governance boundary*: lock-in detection models plan stability, but the dangerous boundary in finance is irreversibility + authority, which the framework neither represents nor enforces.
- The 80/20 attribution (L98, L107) cuts both ways here: the framework's failures are harness-design failures, which means they are fixable — but only by adding an authority/irreversibility layer the framework does not have. That layer is the human approval gate, and the framework cannot manufacture it from task state.
