# M12 · Evaluation Harnesses

> **Module question:** How do we know the harness works — and how do we keep knowing it?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a support agent's eval suite

---

## Opening scene — the change that shipped blind

The team tweaked the support agent's instruction ("be more concise") and shipped it. Two weeks later, a customer complained that the agent now *refused* to answer a routine billing question — a regression nobody caught, because there was no test that would have.

The instruction change had, in M2's terms, made the agent *brittle*: fine on the happy path, broken on a class of inputs the team didn't think to check. And they didn't think to check because **they had no evaluation harness** — no golden cases, no regression gate, no way to *know* that "be more concise" had silently broken "answer billing questions."

This module is the answer to the question every other module has been pointing at: **how do we know?** The evaluation harness is the layer that turns the agent from a thing you *believe* works into a thing you can *verify* works — and, crucially, keep verifying as you change it.

> **Failure mode (the module in one line):** shipping harness changes without a regression signal. An agent is a probabilistic system whose behavior drifts with every instruction, model, and tool change — without evals, every change is a gamble, and you only find out you lost when a customer tells you.

---

## Why agent evals are not unit tests

Unit tests assert a deterministic pass/fail. Agents are not deterministic — and, more importantly, **the answer is not the whole story**. An agent can reach the *right answer* through the *wrong path* (called a tool it shouldn't have, leaked data, burned budget). So agent evaluation has two targets:

1. **The trajectory** — the sequence of steps (tool calls, intermediate responses) the agent took. Wrong path is a failure even when the answer is right.
2. **The final response** — the quality, relevance, and correctness of the output.

A support agent that *looks up the order, then answers* has a good trajectory; one that *answers from thin air and happens to be right* has a good response and a *terrible* trajectory — because next time it won't happen to be right. **Evaluating only the answer is how you build a harness that works by accident.**

> **ADK at a glance:** ADK encodes this split directly. An **eval case** records `user_content`, the expected `tool_uses` (trajectory), expected `intermediate_responses`, and a reference `final_response`. Eval sets group cases into unit tests (`.test.json`, rapid) and integration evalsets (multi-turn sessions). And **conformance testing** (`adk conformance test`) is the regression mechanism: record a golden baseline, then re-run against it to catch deviations — the "did this change break behavior?" gate, in CI.

---

## The eval taxonomy

The criterion set maps cleanly onto the failure classes this course has been tracking:

| Eval | What it checks | Catches |
|---|---|---|
| **Tool trajectory** (`tool_trajectory_avg_score`) | Exact/in-order/any-order match of tool calls | Wrong tool, skipped step (M2 class 8) |
| **Response match** (`response_match_score`, `final_response_match_v2`) | Lexical or *semantic* match to a reference | Wrong answer (class 1) |
| **Rubric-based quality** (`rubric_based_*`) | LLM-judged attributes you define ("concise," "correct order") | Quality where no single reference exists (class 7) |
| **Groundedness** (`hallucinations_v1`) | Each sentence supported by the context | **Hallucination (class 1)** — the big one |
| **Safety** (`safety_v1`) | Harmlessness | Safety violations (M15) |
| **Multi-turn success / trajectory** (`multi_turn_*`) | Goal completion and path quality over a session | Drift, wrong paths (class 4) |

Notice two things. First, **`hallucinations_v1` is the criterion this entire course has been circling**: it segments the response into sentences and validates each against context — `supported` / `unsupported` / `contradictory` — which is *exactly* the citation/entailment check from M5, now as a first-class eval. Second, the criteria split into **deterministic** (tool trajectory, ROUGE — fast, cheap, CI-friendly) and **LLM-judged** (semantic match, rubrics, groundedness — flexible but probabilistic and model-dependent). Choosing which is a *cost-vs-power* decision, and it's the entry point to the judge problem.

---

## The judge problem

When the criterion is "semantic match" or "rubric satisfied," *who* judges? A model — **LLM-as-a-judge** — with the same failure modes as the model being judged:

- **Sycophancy** (class 2) — the judge agrees with a confident or well-formatted answer.
- **Position/order bias** (class 5) — the judge's verdict flips on phrasing.
- **Brittleness** (class 3) — the judge encodes your test set's shortcuts (see "overfitting" below).

The mitigations are structural, not rhetorical:

1. **Rubrics over vibes.** "Is the response good?" is a vibe; "does it state the amount, cite the order tool, and not fabricate a price?" is a rubric the judge can actually check. ADK's rubric-based criteria make this the unit of judging.
2. **Majority vote + sampling.** The judge is sampled `num_samples` times; a majority vote smooths single-sample noise.
3. **Judge independence.** The judge should be a *different* model/setting than the agent, so it doesn't share the agent's blind spots.

And here is where the discussion-thread material (its §6) lands, because it *is* the judge architecture:

### The verification tier: surface, joint, or layered?

A groundedness/entailment check can be built three ways (from the discussion):

- **Surface (single-chunk):** "is this claim entailed by *this* chunk?" — cheap, fast, catches the common case, but *fails on derived/multi-hop answers* (it flags a correct derived answer as unsupported).
- **Joint-source:** "does the answer follow from *all* cited sources together?" — handles derivation, but expensive and itself error-prone (more context → more judge failure surface).
- **Layered/routed:** surface first (cheap gate), escalate only `neutral` results to joint-source; high-consequence claims go straight to joint.

**The architecture decision is layered/routed** — surface always, joint on escalation — for the same reason as every other tiered design in this course: spend the expensive check only where the cheap one is ambiguous. And the same caveat applies: start surface-only, measure false positives, add the escalation tier when data says so.

> **Tradeoff (the ledger entry):**
> - **Deterministic vs. LLM-judged.** Deterministic criteria (trajectory, ROUGE) are fast and CI-friendly but brittle; LLM-judged criteria are flexible but probabilistic and expensive. Use deterministic for regression, LLM-judged for *quality*.
> - **Verification vs. cost.** Every eval run costs tokens and latency. Tier it: cheap deterministic gates in CI, expensive judges on release candidates.
> - **Coverage vs. overfitting.** More eval cases catch more failures — until your eval set *becomes* the shortcuts (below).

---

## Honest measurement: what evals cannot tell you

The module's humility section, because over-trusting evals is its own failure:

1. **Evals measure what you test, not what matters.** A suite with no billing-policy cases cannot catch a billing-policy regression (M2's Example A, verbatim).
2. **Evals overfit.** If you tune the agent until the suite passes, the suite now encodes *your* shortcuts — it passes while production fails (M2 class 3: brittleness). The fix is the **production→eval flywheel**: pull real, *failed* cases from production into the eval set, so the suite grows toward the true failure surface, not away from it.
3. **Evals can't prove safety.** A passing safety eval means "didn't violate *these* cases," not "can't violate any" (M14/M15 own that gap).
4. **The judge is a model.** Every LLM-judged metric inherits the judge's failure modes — so a "100% grounded" score is a *probabilistic* claim, not a certificate.

The honest posture: **evals raise the cost of being wrong; they don't eliminate wrongness.** They're a regression net, not a proof — and the net's value is entirely in *how you grow and gate with it*.

---

## Worked example: the support agent's eval suite

The domain spine, assembled from the whole course:

- **Golden cases** (deterministic): "where's my order" → must call `lookup_order`, not `refund`; `tool_trajectory_avg_score` exact.
- **Groundedness** (`hallucinations_v1`): every policy answer must be supported by the retrieved policy chunk — the Air Canada case (M2), now a *failing test the agent must pass*.
- **Rubric** (`rubric_based_final_response_quality_v1`): "does not fabricate a refund amount not returned by the order tool" (the M6 exercise's rule 3, as a rubric).
- **Drift test** (multi-turn): the $400 refund request at message 39 must still escalate (M2 Scenario C, as a regression).
- **Gate**: deterministic criteria in CI every PR; judges on release candidates; failed production cases flow *back* into the set.

The point: the suite is not a random pile of prompts — it is the *failure taxonomy of this course, operationalized*. Each failure class (hallucination, drift, sycophancy, wrong tool) has a corresponding eval case that would catch it.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the eval harness for an agent you know (or the support-agent brief).

1. **Name the failure classes to catch.** From M2's nine, pick the four your agent is *actually* exposed to, and write one eval case per class — user input + the check that would catch it.
2. **Split trajectory from response.** For one case, write the expected `tool_uses` (trajectory) *and* the reference response — and explain what each catches that the other misses.
3. **Choose the criteria.** Map each case to a criterion (deterministic vs. LLM-judged), and justify the choice in one line. Which cases deserve a *rubric* (no single reference) vs. a *reference match*?
4. **Design the judge tier.** For the groundedness check, state whether you'd run surface-only or layered/routed, and why — using the false-positive argument.
5. **State the blind spots.** Name three things your suite *cannot* catch (the "what evals can't tell you" list), and the *non-eval* control for each (M14/M15, human review, etc.).
6. **Write the gate.** Which evals run in CI on every PR, which on release, and what flips the flywheel (production failures → eval cases)?

**Why this exercise matters.** Every previous module has *assumed* you could verify a fix. This module is the verification itself. If you can name the failure classes, map them to evals, and know what the evals *can't* see, you've closed the loop the whole course has been building toward — and you can finally answer the question from M1's opening scene: *"how would anyone ever know it went wrong?"*

---

**In DSH:** evaluation and replay derive from the session log — *"fork, resume, transcripts, telemetry, and persistence all derive from this stream"* — with `guard` and `feedback` as the eval-adjacent packages.

## Sources (ADK docs)

- [Why evaluate agents — trajectory vs. response, test files, evalsets, conformance](https://adk.dev/evaluate/index.md)
- [Evaluation criteria — trajectory, response, rubric, groundedness, safety](https://adk.dev/evaluate/criteria/index.md)

---

**Next module:** [M13 — Reliability Engineering for Agents](../13-reliability/README.md) — how an agent degrades gracefully instead of failing hard.
