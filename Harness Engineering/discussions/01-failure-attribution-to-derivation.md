# Discussion 01 — From "the model hallucinated" to derivable vs. interpretive

> **What this resolves, in order:** why "the model hallucinated" is never a root cause → which barriers explain a let-through → guardrail design (provenance vs. re-judgment) → caching vs. grounding → how to implement provenance and citation-entailment checks → how to architect the entailment engine → and finally, the boundary between *derivable* (code it) and *interpretive* (decompose, ground, and hand the residue to a human).

The doubts below are kept verbatim — they are the point. A reader will hit the same ones.

---

## §1 · Can evals or guardrails ever explain "let the hallucination reach a user"?

> *"Can the evals or the guardrails harness layer ever explain this 'let the hallucination reach a user' part?"*

**Yes — but each in a different causal sense, and neither is always the right layer.**

When you ask "which layer let the hallucination reach a user," you are not asking who *generated* the error — the model+context did. You are asking **which barrier between the model and the user was missing, thin, or aimed at the wrong seam.** That is fault-barrier reasoning. Each harness layer is a barrier, and a good postmortem names the barrier. There are four distinct causal jobs:

| Barrier's job | Layer | The question it answers |
|---|---|---|
| **Detect before shipping** | Evaluation (M12) | "Why didn't we *know* this failure class existed before release?" |
| **Enforce at runtime** | Guardrails (M14/M15) | "Why didn't anything *stop* it in the request path?" |
| **Don't make the model guess** | Context/grounding (M4/M5), tool-result verification (M8) | "Why did the model have to fabricate *at all*?" |
| **Accept the residual** | Governance / ADR (M15) | "Why did we *choose* to let this residual through?" |

**Five worked examples:**

- **Evals (ex-ante).**
  > **Context:** the support agent told a customer *"you can book a bereavement fare and apply for the refund retroactively"* — a policy that doesn't exist. The question: why wasn't this caught before release?

  The agent told a customer "you can apply for the bereavement refund retroactively." The eval suite had cases for *"where is my order"* and *"change address"* — but **zero cases probing the bereavement clause**. The gate passed because the test surface didn't cover that policy. Evals explain the let-through as: *no test case was responsible for catching a policy fabrication there.* (They do **not** explain why the model fabricated at runtime — that's grounding.)
- **Guardrails (ex-post).**
  > **Context:** the same support agent and the same wrong refund-policy claim — but a guardrail *does* exist. The question: why didn't it stop the claim?

  A guardrail existed but was configured to check **only user input** (a prompt-injection filter), not **agent output** — or it checked the wrong property. A barrier existed, aimed at the wrong seam.
- **Grounding (the primary answer, most often).**
  > **Context:** a research agent asked *"does clause 14 allow termination without cause?"* — with no contract retrieved into context.

  A research agent answered *"does clause 14 allow termination?"* with **no contract retrieved into context**. It had no evidence and no answerability constraint, so it *had* to confabulate. The eval (secondary) and the guardrail (mitigation) are downstream; the **primary** failed barrier is grounding.
- **Risk acceptance (ADR).**
  > **Context:** an internal draft-summarizer whose output a human always reviews before anything leaves the building.

  A draft-summarizer may confabulate because a **human always reviews** before output leaves the building. The let-through is by design, recorded in an ADR. No barrier "failed."
- **Tool-result verification.**
  > **Context:** an agent asked *"what is my order total?"* — and the order system returned an error that the tool wrapper silently converted into a default value.

  An agent reported a wrong order total because the tool wrapper silently converted an error into a default. The "hallucination" was propagation of a bad tool result — the failed seam is M8, not evals or guardrails.

**Precise restatement:** the question is *"which barrier was missing, thin, or aimed at the wrong seam — or was the residual explicitly accepted?"* That phrasing forces the postmortem to name a barrier instead of a model defect.

---

## §2 · Guardrail design: re-judgment vs. provenance

> *"W.r.t. the 'bereavement leave and apply for refund' hallucination example — you mean it was the guardrail's job to also check against policy if a refund exists for bereavement leave?"*

**Two designs exist at that seam:**

- **Design A — semantic re-judgment.** The guardrail itself knows the policy and asks *"does a bereavement refund actually exist?"* This works, but it re-creates the same hallucination risk inside the guardrail itself — you've moved the "which model might be wrong" problem one step downstream, and now you must verify the verifier.
- **Design B — provenance check.** The guardrail does **not** judge whether the policy is *true*. It checks whether the policy the agent asserted is **drawn from the approved source** rather than invented: *"the agent may state policy only by quoting (or citing a resolved excerpt from) the approved policy store; any policy-looking assertion that does not resolve → block or escalate."*

So yes — that seam's job is to stop ungrounded policy assertions. But the robust implementation is **provenance (B)**, not re-derivation (A). The allowlist doesn't need to know bereavement policy; it needs to know that *"apply for the refund retroactively"* matches **no** approved string.

**The unification:** Design B is the *same check as grounding*, applied at the output seam. "Does this factual claim come from the retrieved contract?" (grounding) and "does this policy assertion come from the approved store?" (guardrail) are both **"does the claim trace to an authoritative source?"**

---

## §3 · Caching is not grounding

> *"Could the 'no contract retrieved' be because of caching? Is retrieved context loaded into the prompt? Is the text partitioned into cached vs. non-cached tokens? Or is the case really that none of them were brought into context?"*

The fact to internalize, answering all four at once:

> **Prompt caching changes *how efficiently* the context is sent and priced. It never changes *what content* the model sees.**

| Concept | What it decides | Failure it produces |
|---|---|---|
| **Grounding / retrieval** | Was the evidence placed into context *at all*? | No (or wrong) facts → confabulation |
| **Prompt caching** | Given the context being sent, is a prefix reused to save cost/latency? | No grounding effect; only cost/latency |

Directly:

1. **"Because of caching?"** No — caching is downstream of retrieval. Nothing retrieved ⇒ nothing to cache.
2. **"Retrieved context loaded into the prompt?"** Yes: *retrieve → assemble → send*.
3. **"Partitioned into cached and non-cached tokens?"** Yes, at the transport/pricing level — a stable **prefix** may be a cache hit. But **the model's attention reads the full context either way.** Cached/non-cached is a bill-splitting mechanism, not a content mechanism.
4. **"Or is it that none were brought in?"** Exactly — Example 3 is a **retrieval miss**: the contract was never placed into context. Cached or not is beside the point.

**Honest caveat:** caching *can* cause a different correctness bug — a **stale or wrong-key cache** serving the wrong chunk. That's a cache-*correctness* failure, not the empty-retrieval of Example 3. It's covered properly in M4.

**Checks that prevent "grounding was an issue":** answerability gating (refuse when evidence is absent) · citation resolution · claim-entailment · retrieval observability · grounding evals. The most valuable pair: **force refusal when evidence is absent, and require every assertion to trace to a source.**

---

## §4 · Design B — implementation (lean steps)

1. Maintain a **versioned policy store**: each clause = `id` + verbatim text.
2. **Constrain output**: instruct the agent to state policy *only* by citing clause IDs (prefer structured `claim → clause_id` output).
3. **Extract assertions**: structured field if available; otherwise a cheap classifier over prose.
4. **Resolve to store**: verbatim/exact match first, then embedding-similarity → a score.
5. **Enforce**: below threshold → block or escalate with the offending assertion flagged.
6. **Log** the `(assertion, clause_id, score)` triple for audit/replay.

---

## §5 · "Claim is supported by it" — implementation

> *"How do you carry out 'the claim is supported by it'?"*

1. Split the answer into **atomic claims** (structured list, not prose).[min-factscore](#min-factscore)
2. Fetch each claim's **cited chunk(s)**.
3. Run an **entailment check**: judge model receives `(claim, chunk)` → `entail | contradict | neutral`; pass only on `entail`.[bowman-snli](#bowman-snli), [thorne-fever](#thorne-fever)
4. `contradict` → block; `neutral` → escalate or regenerate.
5. **Pre-filter** obvious non-matches deterministically (keyword/entity overlap) before invoking the judge.
6. Caveat: the judge itself can err — judge failure modes are M12 territory.[manakul-selfcheckgpt](#manakul-selfcheckgpt)

---

## §6 · Entailment engine architecture: one tier or two?

> *"Should my entailment engine be both surface-level and joint-source verification, or only one?"*

**Both, but *routed* — not "both always run."** Surface check is the cheap first gate; joint-source is the escalation tier.

| Architecture | Cost / latency | False positive (flags a correct *derived* answer) | False negative (misses a bad answer) | Complexity |
|---|---|---|---|---|
| Surface-only | Low | **High** | Low extractive / **high derived** | Low |
| Joint-source only | High | Low | Low | Medium |
| Layered / routed | Medium | Low | Low | Medium-high |

- Surface runs **always** — catches the majority case cheaply.
- Joint-source is expensive and has a **larger failure surface** (more context → more room for the judge to err), so it runs only on ambiguity.
- **Routing rule:** `entail` → pass · `contradict` → block · `neutral` → **escalate to joint-source** (not fail). High-consequence claims skip straight to joint-source.

**When one tier suffices:** almost-always-extractive answers → surface-only; almost-always-derived answers → joint-source as the floor. **Start surface-only, measure the false-positive rate, add the escalation tier only when data says so.** The "surface" tier usually carries a deterministic keyword/entity pre-filter beneath the model judge — three tiers total, each escalating only on ambiguity.

- **The cost recurs on every answer, not once.** Each check is paid per answer — a judge call per claim, or per answer — which is what makes the tiering a *coverage* decision as much as an architecture one.

---

## §7 · Derivation: the boundary of verification

> *"Can claim-entailment fail if the question is so complex that complex derivation must be used to arrive at an answer?"*

**Yes — and it's a category mismatch, not a bug.** Entailment verifies *"is this claim in the cited text?"* — it assumes the answer is **extractive**. When the answer needs **multi-hop derivation** (clause A + clause B ⇒ C; arithmetic over retrieved numbers), the final claim is true but **not locally entailed by any single chunk**. A naive entailment checker flags the *correct* answer as unsupported.

**Fixes:** joint-source verification (reason over *all* cited sources) — and, better, **stop deriving in the model** for anything formal.

> *"But what if derivation is logical in nature and requires that level of intellect — such that it can't be deterministically programmed?"*

Two cases, and the conflation is the trap:

- **Case A — formal, rule-structured logic.** If you can write the rule down, you can write it in code — **code *is* formal logic.** "Eligibility = a conjunction of conditions; entitlement math; if X and not Y then Z" is not judgment, it's a compiler target. Most "complex" business logic is secretly Case A.
- **Case B — interpretive, open-textured judgment.** *"Is this event 'material'?" "Does this precedent reasonably apply?"* There is **no rule** — the answer is a semantic judgment. Coding it would be hard-coding one human's opinion.

**"Deterministically code it up" means:** move the derivation out of the model's head into a **function the model calls**, so it's executable and testable rather than sampled. For bereavement eligibility: `check_bereavement_eligibility(customer_id, order_id, request_date) -> {eligible, refund_amount, basis}`. The model's job shrinks to *extracting parameters, calling the tool, reporting the result* — and you verify the *parameters* (a grounding check), not the derivation.

**For Case B, verification of the result is impossible — so you do four things instead:**

1. **Verify the process, not the result** — emit derivation steps; check each step is grounded/entailed.
2. **Split derivable from judgmental** — "eligibility = formal conditions (code) *and* materiality judgment (human)."
3. **Constrain, don't verify** — prove the answer doesn't *violate hard constraints* (no refund > X; no termination absent clause Y), even if you can't prove it *right*.
4. **Contain the blast radius** — human approval on the judgment step, logged for audit.

> *"Seems like Case B becomes a decomposition where the decomposed steps can be deterministically verified?"*

**Right move, one sharp correction.** Decomposition gives you **groundable** steps (each entailed to a source), not **deterministic** ones — because the per-step entailment check is itself a *probabilistic judge*, and, more importantly, decomposition **relocates** the interpretive act to the **weighting/composition step** rather than removing it.

Decompose "materiality": *did the event cause a delay? (codable) → how long? (codable) → does the contract set a threshold? (codable lookup) → apply it (deterministic) → if no threshold, weigh severity × duration × foreseeability (**judgment**).* The judgment didn't vanish — it hid in the weighing.

**The criterion:** decomposition turns Case B into Case A **iff the composition rule and the weights are writable.** If they are, it was Case A all along and decomposition discovered it. If they aren't, you've made the judgment *step-verifiable and inspectable*, but **not deterministic** — and the final leap still belongs to a human.

**So the method is:** *decompose to find the derivable core (code it), isolate the weighting residue (ground its inputs, verify the steps), and route that residue — not the whole judgment — to a human. Determinism where rules exist; inspectability where they don't; never pretend the second is the first.*

(Empirical echo: **process supervision** supervises each reasoning step when the final answer can't be checked — it makes Case B reasoning more trustworthy and inspectable, not provable, because supervising steps is still probabilistic and the final *composition* remains unformalized.)

---

## Feed-forward map

| Section | Folds into |
|---|---|
| §1 fault-barrier reframe + "which barrier" restatement | M1 (edit) · M2 attribution · M12/M14 framing |
| §2 Design A vs. B (provenance guardrails) | M14 Security · M15 Guardrails |
| §3 caching ≠ grounding | M4 Context Engineering I |
| §4–§6 entailment, citation resolution, engine architecture | M5 Retrieval & Grounding · M12 Evaluation |
| §7 derivation, Case A/B, decomposition | M8 Tool Interfaces · M10 Orchestration · M12 · M15 |

---

## Bibliography

*Citations use stable identifier keys, not position numbers. Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed or reordered without rewriting a citation. Every entry hyperlinks to the paper's PDF. Scope note: these entries source the §5 procedure; claims elsewhere in this discussion are not yet sourced.*

- <a id="min-factscore"></a>[min-factscore](#min-factscore) · [**FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation** — Sewon Min, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh, Mohit Iyyer, Luke Zettlemoyer, Hannaneh Hajishirzi](https://arxiv.org/pdf/2305.14251) — *EMNLP*, 2023. — owns the **atomic-fact decomposition** behind step 1: a generation is split into atomic facts and scored by the fraction supported by a chosen knowledge source.
- <a id="bowman-snli"></a>[bowman-snli](#bowman-snli) · [**A Large Annotated Corpus for Learning Natural Language Inference** — Samuel R. Bowman, Gabor Angeli, Christopher Potts, Christopher D. Manning](https://arxiv.org/pdf/1508.05326) — *EMNLP*, 2015. — owns the **`entailment / contradiction / neutral` label set** step 3 borrows, and the sentence-pair task it was built for.
- <a id="thorne-fever"></a>[thorne-fever](#thorne-fever) · [**FEVER: a Large-scale Dataset for Fact Extraction and VERification** — James Thorne, Andreas Vlachos, Christos Christodoulopoulos, Arpit Mittal](https://arxiv.org/pdf/1803.05355) — *NAACL*, 2018. — owns the **claim-against-evidence verification** framing step 3 is an instance of.
- <a id="manakul-selfcheckgpt"></a>[manakul-selfcheckgpt](#manakul-selfcheckgpt) · [**SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models** — Potsawee Manakul, Adian Liusie, Mark J. F. Gales](https://arxiv.org/pdf/2303.08896) — *EMNLP*, 2023. — a **judge that is itself a model with its own failure modes**, which is the caveat in step 6.
