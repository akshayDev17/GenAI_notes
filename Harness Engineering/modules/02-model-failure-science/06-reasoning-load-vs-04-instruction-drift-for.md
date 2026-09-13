# Class 6 or Class 4? The Mistake We Are Already Making

**The disputed question:** can an AI engineer mistake — or plausibly confuse — failure class 6 (reasoning degradation under load) with failure class 4 (instruction drift & compliance decay)?

**Position:** **FOR.** The confusion is not carelessness; it is the *default* read of the evidence a postmortem actually has.

**Verdict:** In production, class 6 and class 4 are the same observation, driven by the same variable, written in the same sentence, and cured by the same three fixes — which is why the wrong diagnosis survives contact with reality.

---

## 1. The observational collapse

- Both present one production symptom: output correct in a short session, wrong in a long one.
  - Class 4's signature is "the same agent obeys a policy in a short session and violates it in a long one" (L59).
  - Class 6's signature is "a two-step task is flawless; a nine-step task fails on step six, and the failure cascades" (L71).
  - Rendered as a trace record, both are `session_length=long → output_wrong`.
- A trace stores inputs, tool calls and outputs; it does not store *why* intermediate state was lost, and both mechanisms are "intermediate state was lost."
- Separating them needs knowledge of what would have happened had you held length constant and shortened the chain, or held the chain and removed the salience competition. The trace contains neither counterfactual.

## 2. The shared confounder

- Context/session length is the independent variable for both.
  - Class 4's mechanism is "attention is diluted across the context" (L58) — a function of length.
  - Class 6's mechanism is "intermediate results live in attention, which is lossy" (L70) — the same attention, the same lossiness, the same length.
- Every field observation implicating one implicates the other. No natural observation takes the form "the session got long and only one of these degraded."
- The confound is structural: **a session gets long by doing many steps.** Length and chain depth are produced by the same behaviour.
- The module concedes overlap between adjacent classes — position bias "compounds with #4" (L66), and one incident in the answer key needs two classes to explain it (L294). A two-class overlap with *different owners* will not survive a ticket.

## 3. The postmortem-language collapse

- Both mechanisms reduce to "the instruction did not reach the action." "It forgot the rule" and "it got lost" are the same sentence in an incident review.
- The module's own generalisation describes both: the model "will follow the loudest instruction in context, not the most important one" (L26) — true of a decayed policy, and equally of a step-six subgoal out-shouting the original goal.
- The module sets a high language standard — "the model was wrong" is never a diagnosis (L30), vague alarm must become a precise work item (L243) — then supplies two classes that both render as the same vague alarm.
- The observed failure is recursively the module's: not "the model was wrong," but "the model degraded under load" — a symptom wearing a class label.

## 4. Cost of disambiguation

- Clean separation needs three experiments, each aimed at one class:
  - **Paraphrase/reorder probes** at fixed context length — isolates salience decay.
  - **Scratchpad ablation**, with and without external scratchpad at fixed length — isolates the lossy-attention mechanism.
  - **Chain-length hold** — same tools, same instruction position, more steps — isolates compounding error.
- Each costs a second production-equivalent run, a synthetic harness capable of driving it, engineering days, and a failure you cannot reproduce on demand.
- The economics decide the outcome: the cheapest defensible postmortem action is to name the class that fits the *narrative*, not the class that fits an experiment nobody ran.
- The module notes these classes are "almost invisible in demos" because demos are short-context and non-adversarial (L236) — so the evidence that would separate them does not exist where teams habitually look.

## 5. Overlapping remediation surface

- Three fixes are offered for both classes, and each works for both:
  - **"Shorten the context"** reduces drift (L58) and reduces the number of lossy intermediate hops (L70).
  - **"Re-ground the instruction mid-session"** is the drift fix (L119); for class 6 it acts as a partial external scratchpad, restoring lost intermediate state.
  - **"Add a step"** — decomposition or verification — is the class-6 fix (L121); it also shortens the instruction-to-check distance, blunting drift.
- The wrong diagnosis therefore still produces a fix that appears to work. **This is the strongest evidence for the FOR position:**
  - A wrong diagnosis that fails visibly is self-correcting; the team learns within a sprint.
  - A wrong diagnosis that *succeeds anyway* removes the only feedback signal that would have corrected it, and entrenches the mislabel in the runbook.

## 6. Evidence from the module's own catalog

- **AutoGPT loops (2023)** — stated symptom: "unbounded loops burned API budgets" (L221).
  - Under 6: the plan never converges because error compounds and the agent cannot tell it is looping.
  - Under 4: the standing termination/budget instruction decayed across a growing context.
  - Both root causes are honestly writable from the stated symptom alone.
- **LangChain A2A 47k loop** — "an agent loop ran ~47,000 iterations" (L222). The symptom *is* length; the cause is invisible. Class 6 and class 4 are equally consistent with a 47,000-iteration trace.
- **McDonald's drive-thru (2024)** — "AI order failures; IBM partnership ended" (L226). An order is a many-step chain (greet, items, modifiers, confirm, total) inside a long noisy session; a mid-chain failure cascades — and that same long session is where the standing script loses salience.
- **Claude Code "human-as-infrastructure"** — "humans became the glue holding the agent together" (L225). Humans re-grounding mid-task is literally the class-4 remediation (L119) *and* the class-6 remediation — supplying the scratchpad the model lacks (L70). The incident name separates nothing.
- **The module's own filing is soft exactly where it matters:** the repeat-tool guard is credited with stopping "the loop pathology this module names as class 6/8" (L318) — two classes for one guard, in the one sentence touching runaway sessions.

## 7. Organizational reasons

- The two sit one module apart by owner: class 4 → instruction layer and memory (M6, M7) (L119); class 6 → orchestration, scratchpads, sub-agents (M10, M11) (L121).
- Same on-call engineer, same incident review, same bucket: *long-session agent misbehaved*.
- The attribution table offers one row for "Harness design" (L101), so taxonomy depth is not enforced at triage — the class is free text on a ticket.
- Both are "high" severity (L60, L72), so neither is dismissed by severity triage, and teams bend the label toward the layer already roadmapped and funded.

## 8. Why this matters at the C-suite level

- **One quarter of engineering, aimed the wrong way.** Real failure class 4, diagnosed as class 6, funds orchestration — planner–verifier loops, scratchpad plumbing, sub-agent decomposition (L121): a two-engineer quarter plus re-architecture.
- The mirror error is cheaper but recurrent: real class 6, funded as instruction work — policy restatement, re-grounding hooks, memory (L119) — trims the symptom without touching the compounding error, and the incident class returns.
- No risk is retired by a wrong label: the module's attribution rule is that roughly 80% of "model failures" trace to harness layers (L104), so a misdiagnosis hardens the wrong layer while exposure stays live.
- A misdiagnosis is an investment error and a residual-risk error at once, and it is invisible because the first fix shipped on time.

## 9. The honest counter-argument

- **Counter:** the module distinguishes the classes cleanly and proves it. Scenario C is a controlled class-4 demonstration — a 40-message session where the 39th message violates the escalation rule, versus a 5-message control with the same request — answered correctly as class 4 with class 5 as mechanism (L263, L294–L300).
- **Why it does not defeat FOR:** that answer key was written by an author who already knew which class to select, against a scenario designed to be separable. It is a demonstration, not a production trace.
- The disambiguation succeeded because someone paid for a controlled experiment — precisely the cost the FOR position claims teams do not pay.
- The class-4 probe also assumes the violation is content-stable under a shorter session; class 6 contaminates that control, because the long session that causes drift is the same one that lengthens the chain.

---

## The decision

- **Believe:** the confusion is the default read, not a rare lapse — the evidence available at postmortem time cannot separate the classes.
- **Fund the disambiguation, not the taxonomy:** two standing probes — a reorder/paraphrase probe and a scratchpad ablation with chain length held — turning an unfalsifiable argument into a regression test.
- **Require both classes named on every long-session incident ticket**, with layer owners for each (M6/M7 against M10/M11), so the fix cannot be chosen before the cause is.
- **Require traces to record chain depth and instruction-distance-to-action as separate fields**, making the shared confounder at least observable.
- **What changes if I am right:** one quarter of engineering stops being spent on the wrong layer, the long-session incident class actually closes instead of shipping a symptom fix, and the next root-cause line becomes a diagnosis rather than a paraphrase.
