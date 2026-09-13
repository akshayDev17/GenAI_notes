# Task State Under Stress — Healthcare Prior-Authorization for Advanced Imaging

> One framework idea (task state + identification + lock-in + re-grounding + mirror-probe-trivial), one industry, stress-tested to failure.

## Scenario

- Domain: prior-authorization agent for advanced imaging (MRI/CT).
- Input: a clinician's office requests pre-authorization for an MRI for patient `P-4821`.
- Output: `approve` / `deny` / `route-to-human`, each grounded in the payer's medical-necessity policy.
- Stakes: a wrong `deny` delays diagnosis; a wrong `approve` exposes the patient and spends the plan; both are class-7 (overlooked constraints) and class-1 (hallucination) hazards (L77–81, L38–43).

## 1. Concrete task state

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

### The crack this scenario plants

- `bindings` mixes two incommensurate kinds: *extractable* (`M54.5`, dates, CPT) and *judged* (`progressive`, `red flag`).
- That incommensurability is the crack every later step falls into.

## 2. Identification

### How the state-update step actually works

- After each turn (clinician message, chart fetch, policy lookup, code extraction), a rewriter emits a fresh task-state object.
- A diff engine compares per-field: which bindings changed, which decision flipped, which open question opened or closed.
- Turn 1 → turn 2 example diff: `bindings` gained `alleged red flag`; `decisions.d3` was added (a new open question opened).

### Where it breaks

- The sharp question: is a diagnosis code *task state* or *context*? `M54.5` is state — a binding the goal names. The clinical context that makes `M54.5` *relevant to §4.9* is context.
- But "progressive lower-extremity weakness" is neither cleanly: it is a *candidate binding* whose admission depends on a clinical judgment (is this a red flag?).
- Identification here requires judgment, not extraction. Extracting `M54.5` is mechanical; deciding the weakness is a red flag *is the task itself*.
- The framework's premise is that the state-update step is a faithful *projection*; in prior-auth the projection is itself a clinical act, so identification inherits the model's failure modes instead of removing them.
- Concretely, classifying free text into binding-vs-noise is where hallucination (class 1) and sycophancy (class 2, if the clinician's confidence steers it) enter — the exact classes the harness was meant to contain (L38–43, L45–49).
- The module's opening scene names the same category error from the other side: the agent had "no mechanism to know which text in its context was policy and which was data" (L13). Identification is supposed to supply that mechanism, and here it must — but the classifier is the same model that confabulates.

## 3. Lock-in detection

### What "lock" means here

- Lock fires when `goal` + `bindings` stop changing across turns while `open questions` keep churning.
- Worked signal: turns 6–10 all carry identical `{P-4821, M54.5, 4wk PT, MRI lumbar}` while `q1`/`q2` keep being re-stated or re-worded → direction locked.

### Why a clinical question may sharpen rather than lock

- A legitimately open clinical question either *resolves* (a new binding lands: an EMG confirms radiculopathy) or stays pending on one decisive datum.
- "Sharpen" = a new binding arrives, so it is *not* lock by the framework's own rule — bindings changed.
- The detector cannot distinguish "churning because the model is lost" from "legitimately waiting on one test result."

### False lock and refusal-to-lock

- False lock: bindings stay stable because extraction is *stale* — the agent reuses the same three facts and never re-reads a new chart note that would change `bindings`. Detector says "locked, proceed"; the direction is settled-but-wrong.
- Refusal-to-lock: the model re-words "progressive weakness" each turn (symptom / finding / red flag / contraindication), so `bindings` churn forever and the detector never fires — the agent re-asks the clinician the same question in a loop (class 6 / 8) (L69–73, L84–87).
- reasoning: lock-in treats *stability of the record* as *stability of the reasoning*. In medicine the record can be stable while the reasoning is wrong, and the reasoning can be unstable while the record is trivially stable.

### The decision forced, and the human

- What lock forces is a *procedure* — emit approve/deny/route — not a *medically necessary* answer.
- Lock is the point where reasoning has *stalled*, not the point where a decision is *safe*.
- The framework cannot force medical necessity out of a stalled record; it can only force the constraint "uncertified open question → route-to-human."
- Human intervention is required whenever a denial or approval rests on a judgment the state cannot certify (the §4.9 red-flag override). That is a class-7 constraint + M15 governance boundary, not a lock-detection output (L77–81, L123–127).

## 4. Re-grounding

### What gets injected, when

- Inject `{goal, constraints, bindings, decisions, open questions}` + the current turn's request immediately before the current action.
- When: every turn; always when context length crosses a threshold or when a failure is suspected (open questions churning, tool retry).
- This is the class-4 / class-5 mitigation the module names: keep the standing rule salient near the current task instead of letting it decay in the middle (L57–61, L63–67).
- But the module's own Scenario C answer ranks this fix "secondary, weaker than the tool fix" (L301) — and that ranking is the whole verdict here.

### What is lost in projecting to the compact state

- `decisions.d2` stores "PT = 4 weeks, insufficient" but drops *why* the 4 weeks count as 4 (the note said "attended 8 of 12 scheduled visits").
- `bindings` stores the alleged red flag but drops *"subjective, patient-reported, no exam finding"* — the qualifier that decides whether §4.9 is met.
- The provenance is a pointer, not the evidence; the nuance that *justified* a decision lives in the free text the object was projected from.

### Where re-grounding alone is insufficient

- Re-grounding re-injects the same lossy object; it cannot restore the dropped nuance, because the nuance was never in the object.
- The real boundary is a human approval gate (M15) on any decision that turns on uncertified clinical judgment — re-grounding is a *salience* fix, not an *evidence* fix.
- The module's own logic says so: the correct fix is to make the action itself impossible without escalation, not to re-state the rule (L295, L299–301). The prior-auth analog is a `deny`/`approve` action that refuses to fire while any binding is `uncertified` — a capability boundary, not a prompt.

## 5. Mirror-probe-trivial

### Does the object reconstruct the task losslessly?

- No. It reconstructs the *checklist layer* losslessly: codes, dates, CPT, and policy-section pointers are mechanical and round-trip.
- It does not reconstruct the *judgment layer*: "is the weakness a red flag under §4.9" is not in the object; it is in the free text the object was projected from, and the projection was a lossy, judgment-laden act.

### What that reveals

- The "shorten the context is lossless" claim holds only where task state is genuinely *separable* from context.
- Prior-auth is separable on its checklist spine and inseparable exactly at its highest-risk point — medical necessity itself.
- reasoning: the framework survives as a routing/checklist scaffold and fails as a decision-maker; it can guarantee that the *procedure* doesn't drift, but not that the *judgment* is right.

## Verdict

- The framework does not survive as a decision engine in this domain.
- It survives as a context-stability and escalation scaffold whose one real contribution is forcing the agent to name, per turn, what is extractable vs what must go to a human.
- The failure is not a bug in any one of the five steps; it is the shared assumption that task state is separable from context and losslessly reconstructable, which medical necessity violates by construction.
