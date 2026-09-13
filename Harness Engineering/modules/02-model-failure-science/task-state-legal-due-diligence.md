# Task-State Framework, Stress-Tested: Legal M&A Due-Diligence Red-Flag Agent

## Domain setup

- Agent: reviews ~500 documents to surface material risks before deal close.
- Consumer: buyer's counsel, deciding walk / renegotiate / proceed.
- Stakes: a missed flag is the signed liability clause the module already names — Scenario A (L262, L270–280).

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

## Verdict

- The framework survives only as a **citation ledger** — an evidence index keyed doc → clause → flag.
- As a task-state scaffold it collapses: `goal`/`open questions` merge, `decisions` holds almost no real decisions, and mirror-probe-trivial is false.
- reasoning: in discovery work the state is the deliverable, so no side-band record can be both compact and lossless.
