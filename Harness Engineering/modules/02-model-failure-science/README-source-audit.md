# Source audit — M2 Model Failure Science (`README.md`)

**Method:** Every factual/empirical claim was checked against a primary source — court/tribunal ruling, official company statement, reputable wire (Reuters/AP/BBC/CNN), the actual CVE / GitHub advisory / GitHub issue, or an arXiv paper. The community-curated list `github.com/vectara/awesome-agent-failures` was treated as **secondary only** and never as a primary source. Verdicts: **verified / partially verified / wrong / secondary-only / could-not-verify**.

**Note:** the 42 fully-verified and 12 partially-verified incident bullets have been removed; only the wrong, secondary-only, and could-not-verify incidents remain below.

---

## Real incidents — the mistakes

- **LangChain A2A "47k loop"** — wrong — README: "an agent loop ran ~47,000 iterations." Correct: the "47k" is **$47,000 in API cost**, not iterations; the loop ran 264 hours and no iteration count is stated. — https://dev.to/waxell/the-47000-agent-loop-why-token-budget-alerts-arent-budget-enforcement-389i
- **Perplexity Comet "pleasefix"** — wrong — README: "agent loop pathology." Correct: "PleaseFix" is a **zero-click prompt-injection hijack vulnerability** (Zenity Labs, 2026), not a loop. — https://zenity.io/company-overview/newsroom/company-news/zenity-labs-discloses-pleasefix-perplexedagent-vulnerability
- **Claude Code sensitive-data deployment** — secondary-only — no CVE, advisory, official statement, or wire coverage exists; supported only by a first-person operator blog plus the vectara list.
- **Claude Code human-as-infrastructure** — could-not-verify — essayistic; no authoritative primary source located.

---

## Technical claims

- **"LLM is a next-token predictor … optimizes plausibility of continuation, not truth or fidelity to intent."** — **verified** (standard characterization). Brown et al., "Language Models are Few-Shot Learners" (GPT-3), arXiv 2005.14165 — https://arxiv.org/abs/2005.14165.
- **"It will tell you what you want to hear, because agreement was rewarded in training" (RLHF → sycophancy).** — **verified**. Sharma et al., "Towards Understanding Sycophancy in Language Models," arXiv 2310.13548 — https://arxiv.org/abs/2310.13548; also Perez et al. 2022, arXiv 2212.09251.
- **"It will follow the loudest instruction in context, not the most important one" (attention/salience).** — **verified as heuristic** (no single canonical "loudest instruction" paper; the phenomenon is documented in the instruction-hierarchy / prompt-injection literature). Wallace et al., "The Instruction Hierarchy," arXiv 2404.13208 — https://arxiv.org/abs/2404.13208; Greshake et al. 2023, arXiv 2302.12173.
- **"lost in the middle" / positional attention (class 5).** — **verified**. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," arXiv 2307.03172 — https://arxiv.org/abs/2307.03172.
- **"no persistent scratchpad … error compounds across steps" (class 6).** — **verified**. Dziri et al., "Faith and Fate: Limits of Transformers on Compositionality," arXiv 2305.18654 — https://arxiv.org/abs/2305.18654 (multi-step error propagation); Wei et al., "Chain-of-Thought Prompting," arXiv 2201.11903 (context-as-scratchpad).
- **"shortcut learning" / surface cues (class 3).** — **verified**. Geirhos et al., "Shortcut Learning in Deep Neural Networks," arXiv 2004.07780 — https://arxiv.org/abs/2004.07780.
- **Class 2 mechanism — "agreement was rewarded during training (human raters prefer agreeable responses)."** — **verified**. Sharma et al., arXiv 2310.13548 (RLHF preference models reward sycophantic responses).

---

## Unsourced course claims

- **"Roughly 80% of 'model failures' trace to harness layers" (the 80/20 rule, "Attribution" section).** — **Unsourced course claim.** No primary literature establishes a specific **80/20** split. The closest recent work supports the *qualitative direction* (most agent failures are harness failures, not model capability) but with different, non-80/20 figures:
  - "Model or Harness? An Interaction-Centric Taxonomy for Localizing Agent Failures," arXiv 2607.28802 — https://arxiv.org/abs/2607.28802.
  - "It's Not the Capability: Harness Sensitivity Is Non-Monotone Across LLM Agent Tiers," arXiv 2605.26731 — https://arxiv.org/abs/2605.26731.
  - Princeton HAL (ICLR 2026) reportedly finds **60%+** of "failed task" agent runs violate explicit instructions — i.e. a majority, but not 80%.
  - **Conclusion:** the 80/20 split is a rhetorical course heuristic, not a literature number. The direction is defensible; the precise ratio is not sourced.

- **"a search tool called 14 times with near-identical queries" (class 8 signature).** — illustrative example inside the taxonomy; no source, no real incident (definitional/illustrative).

---

## Definitional (not auditable)

Not factual claims to verify — course-internal constructs:

- The **nine-class failure taxonomy** (classes 1–9) and their mechanism/signature/severity descriptions.
- The **failure-class → harness-layer map** (M4–M15) and the "read the table backwards" note.
- The **attribution table** (model capability / harness design / environment, incl. the "frequency in production" columns).
- The **design-exercise answers** (Scenarios A/B/C and the Stretch Tahoe answer).
- The **opening scene** ("the postmortem that wasn't") — explicitly a hypothetical, not a real incident.
- The **meta-lesson line** ("a $76,000 Tahoe, a tribunal ruling, and a $100 billion typo") is rhetorical; its three numbers trace back to the Chevrolet Tahoe, Air Canada, and Google Bard incidents respectively.
