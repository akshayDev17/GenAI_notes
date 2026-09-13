# Task State vs. Root-Cause — a stress test

**Scenario.** Software/SRE production-incident root-cause agent.
Incident: "checkout is returning 500s since the 14:02 deploy."
The agent must diagnose, then fix / roll back / page on-call.

**Framing.** The framework's `goal` is a *restore*, but the agent's *direction* is the current *hypothesis* — which is revocable by nature. Stress-test the framework against that tension.

---

## 1. Concrete task state

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

### Break

- The five fields have no slot for `direction`/hypothesis — the one field the whole domain turns on.
- Forcing H1 into `decisions` mislabels a conjecture as a commitment; forcing it into `open questions` drops the fact that it is the *current* working direction.
- reasoning: the schema is missing its most load-bearing field, so the diff (§2) and the lock detector (§3) are both blind to it.

## 2. Identification

### Walk

- After each tool turn, a state-update step rewrites task state as a structured object and diffs it field-by-field against the prior version.
- Diff output per field: `{added, removed, changed, unchanged}` across goal / constraints / bindings / decisions / open questions.

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

## 3. Lock-in detection

### Walk

- Trigger: `goal`+`bindings` stop changing while `open questions` still churn → direction has locked.
- Lock is per-field and revocable; provenance supports unlock.

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

## 4. Re-grounding

### Walk

- Inject the compact task-state object near the current action each turn (or when context grows / a failure is suspected), so the model acts on current state instead of re-deriving it from long undifferentiated history.
- This is the framework's fix for instruction drift (class 4, L57) and position bias (class 5, L63).

### Break

- Re-grounding only the *conclusion* (H1) without the *evidence* produces confirmation bias.
  - Handed "current hypothesis: bad deploy" near the action, the model gathers confirming evidence and skips disconfirming checks.
  - reasoning: sycophancy toward the model's own prior (class 2, L45) plus an overlooked "consider alternatives" constraint (class 7, L77).
- The evidence trail must ride along: re-ground `decisions[].conclusion` **and** `decisions[].evidence` (the p50 delta, the breakpoint timestamp, the trace pointer) — conclusion alone is worse than nothing.
- Where re-grounding alone is insufficient:
  - Faithful reproduction of a wrong state: if the state-writer fabricated a metric, re-grounding reproduces the error; grounding is only as good as the state object.
  - Lossy compression: you cannot re-ground the raw 14:02 deploy diff or the full trace into a compact object without dropping the disconfirming detail.
  - It fixes position/drift but not reasoning degradation (class 6, L69) nor tool loops (class 8, L83); the repeat-tool guard (L318) is a separate mechanism the framework does not supply.

## 5. Mirror-probe-trivial

### Walk

- Claim: short-session reconstruction is a mechanical render of the task-state object + the current request, so "shorten the context" is lossless by construction.

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

## Verdict

- Survives as a *control/authorization* ledger; fails as an *investigation* memory.
- The single worst break is the missing `direction` slot: the schema cannot track the one field the domain turns on, so diff and lock are both blind to it.
