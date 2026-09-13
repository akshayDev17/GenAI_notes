# Task-state framework, stress-tested: portfolio rebalancing / trade-instruction agent

> Scenario: a client instructs "reduce my tech exposure to 20%." The agent drafts sell/buy orders within regulatory and client risk constraints, with a human approval gate before any order executes.

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

## 2. Identification

How it works:

- After each turn, a state-update step re-reads the conversation + tool results, rewrites the object, and diffs each field against the prior version.
- Diff granularity is per-field: goal, bindings, decisions, open questions.

Where it breaks:

- The task-state vs standing-policy split is a *prior* design decision, not something the diff can discover. The diff compares two objects; it cannot tell you the objects assigned "no-wash" to the wrong bucket.
- Who decides the split: a human (compliance/advisor) pre-authorizes the taxonomy; the broker's OMS enforces standing policy as capability boundaries, not as diffable text. The framework offers no slot for this delegation.
- A stable-but-wrong binding diffs clean. The identification step transcribes "20%" → "25%" (class 1, L38-43) or mis-parses a paraphrase (class 3, L51-55); the object is wrong *consistently*, so the diff reports no drift. Identification detects change *between turns*, never error *against source text*.
- Re-phrasing reads as churn. The client re-states "20%" as "one-fifth"; bindings churn, the diff flags unsettled direction that does not exist.

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

## 4. Re-grounding

What gets injected, when:

- The current task-state object, placed adjacent to the current action (the draft-order step), so binding facts sit near the action rather than at token 3,000 — the class-4 / class-5 (L63-67) mitigation.

Where it breaks:

- Re-grounding a *superseded* instruction amplifies staleness. Client says "20%," then "make it 25%." If the object still reads 20%, injection makes the withdrawn figure maximally salient at the exact moment it matters. The object is only as current as identification, and identification can misclassify supersession as re-phrasing.
- Re-grounding is silent about *authority*. A correct, current object next to the action still does not authorize execution. It improves fidelity to the plan, not permission to act.
- Where re-grounding alone is insufficient: any action that changes a binding's reversibility class (draft → executed → settled) must pass a human gate. That gate is a capability boundary in the OMS (class 8, L83-87) and a governance concern (class 9, L89-93), not a context trick. reasoning: conflating "clear context" with "authorized action" is the Tahoe failure shape — the model does the thing because the plan was clear, and authority was never checked (L307-315).

## 5. Mirror-probe-trivial

Does the object reconstruct the task losslessly? No, on two dimensions:

- Intent is lost. "reduce tech exposure to 20%" is a compression of the client's fuller instruction (concern about AI concentration, fund tuition next year, keep it tax-efficient). The object re-derives the letters, not the intent — class 9 misspecification is built in (L89-93).
- Reversibility class is lost. Settled trades are irrevocable facts about the world; drafted orders are revocable proposals. The schema has one `bindings` field with no irreversibility flag. reasoning: reconstructing a settled trade as a draft permits a phantom re-sell (double-sell) of the same position; reconstructing a draft as settled fabricates a position that was never bought.

What mirror-probe-trivial would need to be true here:

- `bindings` must carry `status ∈ {draft, approved, executed, settled}` and `reversibility ∈ {revocable, irrevocable}`, and the reconstruction must preserve both. The framework as specified does not, so the reconstruction is lossy exactly where finance cares.

## Verdict

- Survives as *context hygiene*: the object and re-grounding genuinely tame instruction drift (class 4) and position bias (class 5), which are real in this domain.
- Fails as a *governance boundary*: lock-in detection models plan stability, but the dangerous boundary in finance is irreversibility + authority, which the framework neither represents nor enforces.
- The 80/20 attribution (L98, L107) cuts both ways here: the framework's failures are harness-design failures, which means they are fixable — but only by adding an authority/irreversibility layer the framework does not have. That layer is the human approval gate, and the framework cannot manufacture it from task state.
