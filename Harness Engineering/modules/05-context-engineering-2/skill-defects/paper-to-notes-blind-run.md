# Skill defects — `paper-to-notes`, blind validation run

> **What this logs.** The first blind validation of the global skill `~/.dsh/skills/paper-to-notes/SKILL.md` (steps, taxonomy, scripts), run against Hsieh et al., *Found in the Middle: Calibrating Positional Attention Bias Improves Long Context Utilization* (arXiv:2406.16008v2), and diffed on substance against the expert-written ground truth `modules/04-context-engineering-1/paper-details/found-in-the-middle.md`. This is a **defect log, not a result sheet** — the run's failures are the payload. No fix has been applied yet; the skill is still in its pre-run state.

## The run

- **Method.** An unprompted subagent was told to invoke `paper-to-notes` and follow it exactly. It received three inputs and no others: the PDF, an explicit output path, and a hard prohibition on reading `paper-details/`. It was told nothing about the paper's content — the point was to test the skill, not the operator's recall.
- **Blind constraint honoured.** `paper-details/` was never read, listed or grepped. Nothing in the repo was written; `extract.py` output was redirected outside the repo.
- **Deliverable.** 364 lines / 7,345 words, plus `calibrate_ref.py` (the executable artifact) and `_extracted.txt`. 159 provenance annotations total (P 87 / B 37 / S 35; bare blocks P 35 / B 29 / S 29).
- **Mechanical audit.** `verify.py` passed structure, citation graph and numbers. One finding was triaged as a false positive — see **D2**.

## Scorecard against the criteria agreed before the run

| Criterion | Result |
|---|---|
| Vaswani classified as *prerequisite machinery* | **FAIL** — filed as prior work, dropped |
| Mechanism background imported | **FAIL** — no scaled dot-product, no multi-head, no causal masking, no "why the last row" |
| Notation inconsistency (query doubled on p. 3, dropped on p. 4) | **MISSED** |
| Other inconsistencies caught | **7** (ground truth catches 1) |
| Numbers retained (83/72, 0.76/0.75, 22-of-24, 6–15 pp) | **PASS** |
| Reproduction imports | **PASS** — richer than the ground truth |

**Net:** the run failed the *mechanism* axis completely and exceeded on the *empirical / reproduction* axis. The failure is systematic, not noise.

---

## D1 — The spine filter drops mechanism prerequisites *(the real defect)*

**What the skill says.** Step 1: *"a term undefined in prose is field vocabulary and you ignore it."*

**What happened.** The run applied that rule literally to the terms the paper's own equations use as black boxes. Its own note states the dismissal explicitly: *"Terms undefined **in prose** … were treated as field vocabulary and not imported (attention heads, decoder layers, self-attention, softmax, greedy decoding, TF-IDF, Spearman's rank correlation, Recall@3)."* It then filed **Vaswani et al. 2017** under *"**Prior work → dropped** … Lineage of the attention mechanism … Field vocabulary; no spine requirement."*

**Why this is worse than an oversight.** The run was not unaware of prerequisite-blindness — it agonised over whether Karpukhin/DPR was a prerequisite (correctly deciding no, because Contriever produced the distractors). It never questioned Vaswani at all. The rule made the wrong answer feel settled and **documented as a decision**, which is harder to catch in review than a gap.

**Measured consequence.** The delivered note contains no scaled dot-product, no multi-head, no causal masking, and no last-row reasoning (`scaled dot` 0, `multi-head` 0, `MultiHead` 0, `QK` 0, `last row` 0). The failure propagates into the artifact: because `attn(·)` was never established as a computable quantity, `calibrate_ref.py` runs on a **synthetic attention tensor** with a *"closed-form stand-in"* for `bias(k)` — so the reproduction never engages the measurement the paper actually performs. The ground truth, having imported Vaswani, can state that the measurement is pinned to the last row of the attention matrix *because the decoder mask is causal* — exactly what a reproducer must know to select the right quantity.

**Proposed fix.** Add a second, overriding test to step 1: **if the paper's equations treat a term as a black box *and* the reproduction must compute it, it is a prerequisite regardless of how familiar the term feels.** Scope the field-vocabulary exemption explicitly: it applies only to terms the note never has to *compute*. Familiarity is not the criterion; computability is.

---

## D2 — `verify.py`'s tag check is not fence-aware

**What happened.** The tag-coverage check skips the ``` fence *delimiters* but not the lines *inside* a fence, so the 19 non-blank stdout lines of the verbatim artifact transcript were scored as untagged body prose.

**Why it matters.** It is a false positive that penalises exactly the thing the skill wants — verbatim evidence. The run handled it correctly: it **refused to rewrite program output to clear a linter**, kept the transcript byte-identical, and documented the triage instead of gaming a green check. A skill whose audit can be cleared by falsifying evidence is worse than one with no audit.

**Fix.** Track fence state (toggle on ```) and skip every line between fences. The current predicate only tests `l.startswith("```")` on the delimiter line itself.

---

## D3 — "Block" is undefined for tagging

**What happened.** The skill says *"tag every block"* without defining a block. The run tagged at **clause level**, producing 159 annotations and noise like `[P/B] [P]` and sentence-final `. [S]` mid-paragraph.

**Why it matters.** Provenance tagging is what makes the P/B/S boundary auditable; tag soup makes it unreadable and undermines the mechanical audit that consumes it.

**Fix.** Define a block as a paragraph, a table row, a list item, or a fenced block, and state that the tag attaches at the **end of the block**, not per clause.

---

## D4 — The ambiguous-use-site rule contradicts itself

**What the skill says.** Step 2 contains both:

- *"Merge as the union of per-use-site imports, deduplicated."*
- *"An ambiguous site is in-spine → import, out-spine → drop."*

These pull in opposite directions. The second sentence invites a coin-flip by spine membership; the first says keep everything each site contributes.

**What happened.** The run hit this on Liu et al. 2023 — simultaneously the *problem source* and the *prerequisite machinery* at the same use-site — deviated from the skill, kept both roles, and reported the deviation. **Its deviation was correct**, which means the second sentence should never have been there.

**Fix.** Delete the second sentence. The union rule already covers the case, and role ambiguity should resolve to *keep both imports*, never to a spine-membership tiebreak.

---

## What the run proved works

- **The judgmental audit earned its place.** The artifact's first version was **rigged** — gold was already the raw-attention argmax, so calibration was asked to fix nothing and "proved" the effect by construction. The fresh critic caught it. The rebuild puts the relevance gap (0.062) below the bias spread (0.225), so **raw attention mis-ranks the mid-sequence gold at 8/20 while calibrated ranks it 1/20**, with the Eq. 5 mass-conservation and Eq. 6 invariants exact. This came from the layer we were least confident about.
- **Fetch-before-import caught a near-miss identifier live.** One fetch landed on `2305.11747` believing it was Karpukhin's DPR; it is HaluEval. The run discarded it, re-fetched the correct `2004.04906`, and no wrong-source import survived. This is the `lit-survey` failure mode reproducing in the wild, caught by discipline rather than luck.
- **The run found real ambiguities instead of smoothing them.** Eq. 5's normalizer `C` has unspecified scope and it changes the arithmetic; `x_dum`'s content is never stated; the instruction template is a figure in both the PDF and the upstream source. Each is documented as unresolved rather than invented.

## Open questions raised by the run, not yet acted on

- The critic corrected a **numeric** judgement: `0.6832 − 0.2052 = 0.478` at K = 20 *is* a clean single-row delta for the paper's "up to 48 Recall@3 points", so the run's original hedge ("cross-setting framing") was wrong. Worth noting as a check the skill has no step for.
- One skill-level capability is deliberately deferred: **figure reading** (a gated VLM pass for figures whose captions fail the round-trip test). The run was caption-only and worked around it by noting that the p. 3 template is unextractable.
- Whether the D1 fix actually cures the failure is **unverified** — it needs a second blind run. Reading a better rule is not evidence that the rule fires.
