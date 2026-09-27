# Entailment engine — ideation

> **The loop this engine sits in:** Retrieve → [answerability gate] → Generate → Verify → plan

## Component 1 — the pairer

- **Name:** *the pairer* (short for claim–evidence pairer).
- **Does:** emits `(claim, cited chunk)` tuples — claim splitting and citation resolution in one step.
- **Input:** the drafted answer, plus the citations it carries.
- **Output:** a set of `(claim, chunk)` pairs, one per atomic claim.
- **Failure axis:** omission — a **recall** problem.
    - A claim is never split out, so nothing downstream can check it.
    - A citation never resolves, so the claim arrives with no evidence to judge against.
- **Substitutable by:** a structured-output constraint (`claim → clause_id`), a classifier over prose, or FActScore-style decomposition.
- **Owns the atomicity decision** — and therefore bounds what everything downstream can ever catch.

## Component 2 — the resolver

- **Name:** *the resolver*.
- **Does:** confirms, for each pair the pairer emitted, that the cited chunk **exists** and **is the chunk it claims to be**.
- **Input:** the candidate pairs from the pairer.
- **Output:** the same pairs, each marked *resolved* or *unresolved*, with a reason — `not found in corpus`, `span mismatch`, `ambiguous reference`.
- **Owns one question and refuses the other.**
    - *"Does this chunk exist, and is it the one being cited?"* — the resolver's question. This is **authenticity**.
    - *"Does this chunk back the claim?"* — **not** the resolver's question. That is the judge's. This is **support**.
- **Hybrid by nature — part deterministic, part agentic.**
    - *Deterministic* when the citation is a chunk id or a verbatim span: existence is an index lookup, identity is a string match.
    - *Agentic* when the citation is a natural-language reference ("the refund policy says…"): resolving it to the right document, page and chunk is itself a retrieval step.
    - §4 already has this shape: verbatim/exact match first, embedding-similarity fallback.
- **Failure axis:** unlike the pairer and the judge, it carries **both** faults.
    - *False negative:* a real chunk it fails to resolve → a genuine claim is rejected as a phantom.
    - *False positive:* a fabricated reference it resolves to a real-looking chunk → the fabrication passes into the judge.
    - So the resolver **narrows** the phantom-citation window; it does not close it.
    - The strong version closes it: API-managed citations, where the pointer's validity is guaranteed by construction — with M5's caveat intact, that a valid pointer guarantees the chunk is *real*, never that it *supports* the claim.
- **Position in the chain — before the judge, deliberately.**
    - A judge call spent on an unresolvable pair is waste at best.
    - At worst it **launders a fabrication into a semantic label**: "neutral" reads as a judgement about content, when the real fault was provenance.
- **Substitutable by:** an exact index lookup, a span matcher, an embedding resolver, or a provider-managed citation layer.
- **Owns the existence gate** — and therefore determines which pairs the judge is ever allowed to see.

## Component 3 — the entailment judge

- **Name:** *the entailment judge*.
    - Kept deliberately: this is already M5's vocabulary (*"The entailment judge is not a faithful 'supports' oracle"*, disagreement item 4), so it is not a new coinage.
- **Does:** categorises one pair into `entail` / `contradict` / `neutral`.
- **Input:** a single `(claim, chunk)` pair.
- **Output:** one of three labels; the gate accepts only `entail`.
- **Failure axis:** miscalibration — a **precision** problem.
    - A wrong verdict on a pair it was correctly handed.
    - Failure modes are M12 territory: judge bias, position/order bias, self-preference, verbosity.
- **Substitutable by:** a model judge, a small dedicated NLI model, or a deterministic matcher.

## Course of action — a mixed-verdict response

> A prose answer rests on **10 claims**, each paired with the chunk or chunks that support it, drawn from a corpus of proprietary PDFs — a claim may be backed by more than one chunk. The verdicts come back: **3 entail** (their chunks mutually consistent), **3 contradict**, **2 neutral**, **1 with no chunk at all**, and **1 whose cited chunk cannot be found anywhere in the authoritative source**.

| Signature | Fault owner | Recoverable by looping? | Course of action |
|---|---|---|---|
| 3 × `entail` | none | n/a | Retain. |
| 3 × `contradict` | generation — or evidence | Yes, mostly | Regenerate from the **same** evidence. If the claim's own chunks conflict with *each other*, that is a different fault → escalate. |
| 2 × `neutral` | ambiguous | Yes | Disambiguate with the sufficiency check: evidence missing → **re-retrieve with a changed query**; evidence present → claim over-reaches → **re-scope the claim**. |
| 1 × no chunk | generation | Yes | The model asserted something it could not cite. Remove the claim or obtain evidence — the **draft** must change. |
| 1 × phantom chunk | **pipeline integrity** | **No** | Hard block + provenance alarm. Looping re-runs the same broken path and the phantom recurs. |

- **The verdict is not a fraction.** The response is one artifact, so its fate is set by the worst claim *class*, not by the majority — a threshold like "9 of 10 verified → ship" is wrong.
- **Naming the resolver is what makes the `entail` row safe to retain.** Authenticity is the resolver's output; with it in the chain, the three `entail` pairs are pairs whose chunks were established as *real*. Without it, "retain" would rest on citations whose existence was never checked — and the phantom would be the only sign that anything had been checked at all.

## Why these are different components

- **Different failure axes** — omission (recall) vs. miscalibration (precision). Different metrics, different fixes, different owners.
- **Independently substitutable** — each has several viable implementations at different cost and latency profiles.
- **One-way dependency: the pairer sets the judge's ceiling.**
    - Atomicity is decided in the pairer.
    - No judge can catch an over-generalised claim it was never handed as a separate unit.
    - M5's trace 4 (Insufficient → an over-generalised claim that every control passes) is exactly this failure.
- **Conflating them destroys the diagnosis.**
    - With one component doing both, a miss is unclassifiable: "never proposed" (recall) and "proposed and mis-judged" (precision) look identical.
    - Splitting them is what makes the failure attributable to a stage.
