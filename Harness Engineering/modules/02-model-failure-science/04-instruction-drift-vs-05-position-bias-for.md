# Instruction Drift vs. Position Bias — the two labels are one failure

**Disputed question:** Can an AI engineer mistake, or plausibly confuse, failure class 4 (instruction drift & compliance decay) with failure class 5 (position & ordering bias)?

**Position:** FOR — the confusion is real, common, and defensible from the module's own material.

**Verdict:** In any real postmortem the two classes are indistinguishable, the severity gradient routes ambiguous cases to the expensive one by default, and the remedies overlap — so the mislabel is not carelessness, it is the field's default outcome.

---

## 1. One mechanism, stated at two altitudes

- Class 4's mechanism is "attention is diluted across the context; instructions compete with retrieved text, tool results, and user messages for salience" (L59).
- Class 5's mechanism is "positional attention patterns from training; the model is not a uniform reader of its context" (L65).
- "Not a uniform reader" *is* "diluted attention" — one is the observation (attention varies across the context), the other is the variable it varies with (position).
- The module's own class-4 example makes the positional reading explicit: it names token indices — "policy at token 3,000 is simply less salient than the customer message at token 3,001" (L59).
- Because that sentence is a claim about *adjacent positions*, it is simultaneously a salience claim and a positional-adjacency claim; the module cannot state class 4 without borrowing class 5's vocabulary.
- Both are attention-allocation failures over a growing context; the difference is the axis you name, not the failure you observe.
- Consequence: a label that depends on which axis the author happens to name is not a separable class, it is a separable *description*.

### The signatures are the same geometry

- Class 4's signature: "the same agent obeys a policy in a short session and violates it in a long one" (L60).
- Class 5's signature: "move the same fact from the middle to the end of the context, and correctness flips" (L66).
- A long session *is* a context with the policy far from the current turn; a short session *is* a context with it close.
- Distance and dilution therefore co-vary perfectly in every production session — **because** there is no way to lengthen a context that does not also push early text away from the last turn.
- No production observation can separate the two, because the two variables are the same variable.

## 2. The module's own linkage settles the causal question

- The class 5 severity line states outright that position bias "compounds with #4" (L67) — the module's own text refuses the firewall between them.
- The written answer for Scenario C — a class-4 incident — classifies it as "**class 4 — instruction drift / compliance decay**, with **class 5 — position bias** as the mechanism" (L295).
- Its prescribed remedy for that class-4 incident is a positional one: "keep the standing rule in the stable prefix / re-ground it near the current task each turn" (L299).
- If moving the rule to a position the model attends to fixes the incident, then position was doing the causal work.
- Separation would require the class-4 remedy (instruction layer, memory) to succeed where the positional remedy fails — the module never claims that, and its own answer key chooses the other order.
- Implication for separability: the two classes are one phenomenon with a primary owner chosen by which remedy the author happened to reach for first.

## 3. The observational collapse

- A trace records the prompt, the tool calls, and the output — it does not record *why* one span of text lost to another.
- Both classes render in a postmortem as one sentence: "the model used X instead of, or ignored, Y."
- Neither the class-4 nor the class-5 signature is contradicted by that sentence, and no instrument in the catalog measures attention over the context.
- The mechanisms collapse to a single true statement: **attention was not allocated to the right text**.
- "Diluted by competitors" and "unattended because it sat in the middle" are two explanations of the identical token-level outcome, with zero distinguishing evidence in the artifact.
- The map rows differ — class 4: instruction layer (M6) and memory (M7) primary, orchestration re-grounding (M10) secondary (L120); class 5: context assembly (M4), no secondary (L121) — but a *map* difference is not an *observation* difference.

## 4. The severity gradient biases triage by construction

- Class 4 is **high** severity (L61); class 5 is **medium** (L67).
- An engineer facing an ambiguous long-context failure has two honest readings and one default: file the higher-severity class, because under-filing a high-severity class is the error that gets audited and over-filing a medium one is not.
- So the *cheap* class (M4 reordering, "cheaply fixable", L67) gets absorbed by the *expensive* one (M6/M7 instruction-layer and memory work) **by default**, without anyone deciding to absorb it.
- This is a mechanism of confusion, not a symptom of carelessness — the incentive gradient pulls the same direction in every review.
- Once the ticket says "instruction drift," the M4 owner is not in the room, and the class-5 question is never asked.

## 5. Disambiguation costs more than the incident

- The swap test — move the fact, re-run — needs a second run and a controllable artifact, not a postmortem.
- You cannot retroactively reorder a real production session: the ordering that caused the failure is the ordering the trace recorded, and there is no counterfactual in the log.
- Consequential sessions have side effects that forbid replay — a refund was issued, a binding message was sent, a transaction committed.
- Replaying a session to reorder it changes the session: a re-run is a different context with different retrieved text, so even a successful A/B does not isolate position.
- The module concedes the classes are "almost invisible in demos — demos are short-context, single-domain, non-adversarial" (L237) — the exact regime in which neither class manifests, so the only affordable experiment is unrepresentative.
- Conclusion: the field has a disambiguation procedure it cannot afford to run, which is precisely how a legible distinction becomes an operational confusion.

## 6. Overlapping remediation entrenches the mislabel

- Reordering or re-placing context improves both classes: the M4 remedy serves class 5 directly and class 4 as its secondary fix (L299).
- Even class 4's secondary owner is a *positional* remedy — orchestration re-grounding (L120) puts the policy back near the current task.
- So the wrong label still ships a working fix, which is why nobody catches the error.
- A fix that works for the wrong reason is the strongest evidence for this position: it removes the feedback signal that would have corrected the label.
- The incident closes, the org's causal model is now wrong, and the same failure returns in a longer context where M4 was never funded.

## 7. The catalog files under either class

- **Air Canada (L138)** — "chatbot mis-stated bereavement policy." Read as class 4: a standing bereavement policy was not complied with. Read as class 5: the correct policy sat in one position and the user's framing in another. The stated symptom excludes neither.
- **NYC MyCity (L202)** — "official bot gave businesses illegal advice." Read as class 4: governing legal guidance decayed against the user's question. Read as class 5: the guidance was not where the answer was generated. Same symptom, either file.
- **McDonald's drive-thru (L227)** — "AI order failures; IBM partnership ended." Read as class 4: ordering policy diluted across a long, noisy transcript. Read as class 5: a late customer correction outranked an earlier spec. No length or position measurement is recorded for either reading.
- **Amazon Q retail outages (L229)** — "hallucinated retail outages." Class 4 with drift, class 5 with displacement — the module states no context-length or ordering evidence to choose.
- **ServiceNow AI agent misconfiguration (L230)** — "misconfigured agent caused failures." A config *misplaced* in the context is class 5; a config *unheeded* is class 4; the stated symptom names neither.
- In all five, the module's catalog records what happened, never where in the context it happened — so the class assignment rests on the analyst's chosen axis, not on evidence.

## 8. Organizational absorption

- Because the module's own Scenario C answer places class 4's remedy in the context-assembly layer (L299), both classes land on the same engineer, the same review, and the same ticket bucket: "long-context agent misbehaved."
- The M6/M7 owner and the M4 owner are different rows on a slide, but the same standup when a refund goes out.
- Practical result: the distinction survives only in the taxonomy, not in the work queue.
- This is the ordinary end state of two classes that share a remedy and share a symptom — the cheaper label is simply never contested.

## 9. What leadership is buying

- If the confusion holds, the dominant error is funding instruction-layer and memory work (M6, M7) when the fix was deterministic context ordering.
- Cost: one to two engineer-quarters of prompt-and-memory redesign, against days-to-weeks for an M4 assembly change.
- Worse, memory work can *increase* residual risk: retrieving more text into the middle of the context increases dilution and pushes key facts into the band the model reads worst.
- Residual risk if mislabeled: the failure recurs in longer sessions, unmeasured, because no M4 ordering test was ever added.
- The reverse error is cheaper but also real: funding ordering when the policy genuinely needed a capability boundary — Scenario C's actual primary fix is a tool-level ceiling, not a prompt or a placement (L298).

## 10. The strongest counter-argument, honestly

- Counter: the classes *are* separable in a controlled eval — a swap test at fixed context length isolates position, a fixed-length decay test isolates dilution — and the map's distinct owners (M6/M7 vs. M4) preserve a real engineering split.
- That is true in a lab with a replayable artifact and a budget for two runs; it is not available at the moment a postmortem is written.
- The distinction is recoverable in an evaluation harness and unrecoverable in triage, and triage is where the label is assigned.
- The module itself half-concedes the point by writing "compounds with #4" (L67) rather than asserting independence.
- A distinction that can only be recovered under conditions the field cannot produce is, operationally, a confusion — which is exactly the proposition under dispute.

## The decision

- **Believe:** classes 4 and 5 are one attention-allocation failure described at two altitudes, and the module's own answer key treats them as such.
- **Fund:** one context-assembly ownership (M4) for positional and long-context placement failures, with a standing reorder-and-re-run test — deterministic, cheap, and the fix for either label.
- **Require:** every long-context incident ticket to record context length, the position of the violated rule, and the position of the winning text, so the ambiguous case stops defaulting to the high-severity class.
- **Do not** fund instruction-layer and memory work as the *first* response to a long-context compliance failure; fund it only after a position-controlled test has ruled ordering out.
- **If I am right:** the next long-context incident is triaged in hours instead of a quarter, and the symptom "the model ignored the rule" stops being a diagnosis in either direction.
