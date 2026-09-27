# Entailment and citation verification

> **Provenance.** Copied from [Discussion 01 — From "the model hallucinated" to derivable vs. interpretive](../../discussions/01-failure-attribution-to-derivation.md): §5 and §6 in full, the diagnosis half of §7, one worked example from §1, and two bridging sentences from §1 and §2. **Nothing here is new**, and none of it is a claim the discussion does not already make — the discussion remains the source of record. This file exists so M5 can own its verification procedure instead of reaching into a cross-module document for it.

## Contents

- [1. The barrier this machinery sits behind](#1-the-barrier-this-machinery-sits-behind)
- [2. The same check, at a second seam](#2-the-same-check-at-a-second-seam)
- [3. The procedure: is the claim supported by its chunk?](#3-the-procedure-is-the-claim-supported-by-its-chunk)
- [4. The engine: one tier or two?](#4-the-engine-one-tier-or-two)
- [5. Where the procedure breaks: derivation](#5-where-the-procedure-breaks-derivation)
- [6. What was not copied, and where it lives](#6-what-was-not-copied-and-where-it-lives)
- [Bibliography](#bibliography)

---

## 1. The barrier this machinery sits behind

- In the fault-barrier picture, M5 owns **one row of four**:

| Barrier's job | Layer | The question it answers |
|---|---|---|
| **Don't make the model guess** | Context/grounding (M4/M5), tool-result verification (M8) | "Why did the model have to fabricate *at all*?" |

- And this is what that row looks like when it is the barrier that failed:

    > **Context:** a research agent asked *"does clause 14 allow termination without cause?"* — with no contract retrieved into context.

    A research agent answered *"does clause 14 allow termination?"* with **no contract retrieved into context**. It had no evidence and no answerability constraint, so it *had* to confabulate. The eval (secondary) and the guardrail (mitigation) are downstream; the **primary** failed barrier is grounding.
- This is M5's **Missing** class, seen from the postmortem side rather than the retrieval side.

---

## 2. The same check, at a second seam

> **The unification:** Design B is the *same check as grounding*, applied at the output seam. "Does this factual claim come from the retrieved contract?" (grounding) and "does this policy assertion come from the approved store?" (guardrail) are both **"does the claim trace to an authoritative source?"**

- The reason this note is copied here rather than into the guardrails module: it is the sentence that says **grounding is a predicate, not a stage.** The verification procedure below is that predicate; the guardrail in M15 is the same predicate run at a later seam, against a different store.

---

## 3. The procedure: is the claim supported by its chunk?

> *"How do you carry out 'the claim is supported by it'?"*

1. Split the answer into **atomic claims** (structured list, not prose).[min-factscore](#min-factscore)
2. Fetch each claim's **cited chunk(s)**.
3. Run an **entailment check**: judge model receives `(claim, chunk)` → `entail | contradict | neutral`; pass only on `entail`.[bowman-snli](#bowman-snli), [thorne-fever](#thorne-fever)
4. `contradict` → block; `neutral` → escalate or regenerate.
5. **Pre-filter** obvious non-matches deterministically (keyword/entity overlap) before invoking the judge.
6. Caveat: the judge itself can err — judge failure modes are M12 territory.[manakul-selfcheckgpt](#manakul-selfcheckgpt)

---

## 4. The engine: one tier or two?

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

## 5. Where the procedure breaks: derivation

> *"Can claim-entailment fail if the question is so complex that complex derivation must be used to arrive at an answer?"*

**Yes — and it's a category mismatch, not a bug.** Entailment verifies *"is this claim in the cited text?"* — it assumes the answer is **extractive**. When the answer needs **multi-hop derivation** (clause A + clause B ⇒ C; arithmetic over retrieved numbers), the final claim is true but **not locally entailed by any single chunk**. A naive entailment checker flags the *correct* answer as unsupported.

**Fixes:** joint-source verification (reason over *all* cited sources) — and, better, **stop deriving in the model** for anything formal.

- The first fix is §4's escalation tier, so it belongs here.
- **The second fix does not.** "Stop deriving in the model" is M8's, and the whole of what follows it in the discussion — Case A vs. Case B, the tool call that replaces the derivation, the decomposition criterion, process supervision — is M8/M10/M12/M15 material. It is deliberately *not* copied into this file; see below.

---

## Bibliography

*Citations use stable identifier keys, not position numbers. Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed or reordered without rewriting a citation. Every entry hyperlinks to the paper's PDF. Scope note: these four entries source the procedure in §3, and are the discussion's four entries copied verbatim so that this file is self-contained.*

- <a id="min-factscore"></a>[min-factscore](#min-factscore) · [**FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation** — Sewon Min, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh, Mohit Iyyer, Luke Zettlemoyer, Hannaneh Hajishirzi](https://arxiv.org/pdf/2305.14251) — *EMNLP*, 2023. — owns the **atomic-fact decomposition** behind step 1: a generation is split into atomic facts and scored by the fraction supported by a chosen knowledge source.
- <a id="bowman-snli"></a>[bowman-snli](#bowman-snli) · [**A Large Annotated Corpus for Learning Natural Language Inference** — Samuel R. Bowman, Gabor Angeli, Christopher Potts, Christopher D. Manning](https://arxiv.org/pdf/1508.05326) — *EMNLP*, 2015. — owns the **`entailment / contradiction / neutral` label set** step 3 borrows, and the sentence-pair task it was built for.
- <a id="thorne-fever"></a>[thorne-fever](#thorne-fever) · [**FEVER: a Large-scale Dataset for Fact Extraction and VERification** — James Thorne, Andreas Vlachos, Christos Christodoulopoulos, Arpit Mittal](https://arxiv.org/pdf/1803.05355) — *NAACL*, 2018. — owns the **claim-against-evidence verification** framing step 3 is an instance of.
- <a id="manakul-selfcheckgpt"></a>[manakul-selfcheckgpt](#manakul-selfcheckgpt) · [**SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models** — Potsawee Manakul, Adian Liusie, Mark J. F. Gales](https://arxiv.org/pdf/2303.08896) — *EMNLP*, 2023. — a **judge that is itself a model with its own failure modes**, which is the caveat in step 6.
