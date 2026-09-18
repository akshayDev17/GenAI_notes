# The mirror probe's two counters — what the primary sources say

> **The probe under challenge** (the mirror probe, `06-reasoning-load-vs-04-instruction-drift-against.md` L35–40): hold the chain constant, shorten the context — re-author the task in a fresh, minimal session (same task state, same tools, same request), leaving out history that is not part of the task. \
> **Verdict:** failure gone at short length → class 4 (salience loss); failure survives re-authoring at short length → class 6 (degraded derived value). \
> **Validity condition:** the task must be re-instantiable independently of its history.

## Counter 1 — the probe can underdetermine

> **Counter, as raised:** what if it really *was* a new session — i.e. context-less — and we still encountered some problem where we are unsure if it is 04 or 06?

**The probe's verdict-rules read a *mechanism* off of *behavior* (trace, recitation, one re-run). The primary literature establishes independent reasons that reading can underdetermine — the residual failure stays genuinely ambiguous between class 4 and class 6.**

- **The trace is not a faithful record of the mechanism.**
  - CoT/step explanations "systematically misrepresent the true reason for a model's prediction" — biasing inputs flips the answer while the model rationalizes the wrong answer, dropping accuracy up to 36% on 13 BIG-Bench Hard tasks; the explanation is "plausible yet misleading" ([2305.04388](https://arxiv.org/abs/2305.04388)).
  - Faithfulness is task- and scale-dependent: "as models become larger and more capable, they produce less faithful reasoning on most tasks" — least reliable exactly where the brief needs it (large production models) ([2307.13702](https://arxiv.org/abs/2307.13702)).

- **The first error in the trace is not the deciding step.**
  - In LLM-agent failures "the step that executes the harmful action is usually not the step that decided on it"; a state-of-the-art LLM-judge reaches only ~14% step-level attribution accuracy on the Who&When benchmark ([2606.08275](https://arxiv.org/abs/2606.08275)).
  - This directly undercuts the brief's trace rule — "in class 4 the violating step is the origin of the error" (L56) and "the trace distinguishes without any experiment" (L144). A class-4-looking boundary violation can be the *execution* of a decision made earlier under a degraded value (class 6), or vice versa; trace position cannot settle it.

- **A single counterfactual re-run is confounded by stochasticity — not a clean experiment.**
  - Causal Agent Replay exists because re-execution under the same policy is confounded: it models the run as a structural causal model, applies a do-operation, and uses "a point-of-commitment rule [that] resolves a confound specific to stochastic run-forward," reporting every effect with confidence intervals ([2606.08275](https://arxiv.org/abs/2606.08275)). CausalFlow computes step-level Causal Responsibility Scores by intervention and argues "causal attribution is necessary for reliable improvement" ([2605.25338](https://arxiv.org/abs/2605.25338)).
  - Meaning: the mirror probe (L35–40) is a one-arm intervention read once, with no confidence interval and no commitment-point control. When the re-run outcome is itself noisy, "failure gone / survives" (L40) can be sampling noise, not mechanism — the exact underdetermined case the counter names.

- **Behavior underdetermines mechanism as a matter of theory.**
  - Interpretability exists because low-level behavior does not identify the causal mechanism: causal abstraction formalizes faithful simplification as intervention-based (mechanism replacement), not observation-based ([2301.04709](https://arxiv.org/abs/2301.04709)).
  - There is "very little consensus on what interpretability is and how it should be measured" — attribution is underdetermined at the level of method ([1702.08608](https://arxiv.org/abs/1702.08608)).
  - Class 4 and class 6 share a substrate (lossy attention, L88): separating them means distinguishing two mechanisms over one shared confounder — precisely where single-observation attribution underdetermines.

- **The binary verdict rule can manufacture a clean split that isn't there.**
  - Emergent-ability work shows apparent qualitative shifts "appear due to the researcher's choice of metric rather than due to fundamental changes"; nonlinear/discontinuous metrics produce apparent binary effects that "evaporate with different metrics" ([2304.15004](https://arxiv.org/abs/2304.15004)).
  - The mirror probe's verdict is a nonlinear metric ({gone→4, survives→6}, L40). A residual failure that is partly diluted salience *and* partly degraded value gets forced to one label by the rule, not resolved by it.

**Counter 1 verdict:** *sustained as a limit.* The literature does not collapse class 4 into class 6 — it makes *one decisive re-run* non-decisive. The brief's own L142 and L146 already name the no-clean-experiment problem and the two-candidates fallback; the primary sources relocate that fallback from "rare" to "structural," and specifically invalidate L144 and L56 as general claims. The literature's remedy is convergent probes plus intervention-with-confidence-intervals — compatible with the three-probe battery (L25), not with the "one probe away" title (L1).

---

## Counter 2 — tasks that require the long context

> **Counter, as raised:** what if the investigatory activity required a significant long context to be carried out in the first place — something like solving tough partial differential equations, or creating an AI Judge who would first have to get the context of the Indian Constitution, the very many laws in IPC or BNS, then how judgments are to be given, etc., before even beginning to kick off the deep research activity of exploring a particular case?

**The mirror probe requires "the task must be re-instantiable independently of its history" (L39). For a real class of tasks the context *is* the prerequisite, so the validity condition fails by construction. The literature establishes both (a) degradation with length and position, and (b) that the answer is externalization — retrieval + scratchpad + map-reduce + step verification — not shortening.**

### (a) Reasoning degrades with length and position — not a flat capacity ceiling

- **Position ("lost in the middle"):** performance "is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models" ([2307.03172](https://arxiv.org/abs/2307.03172)).
- **Effective length < claimed length:** across 17 long-context LMs "almost all models exhibit large performance drops as the context length increases"; despite all claiming ≥32K, "only half of them can maintain satisfactory performance at the length of 32K," measured on tasks beyond vanilla needle-in-haystack (multi-needle, multi-hop, aggregation) ([2404.06654](https://arxiv.org/abs/2404.06654)).
- **Beyond 100K:** "existing long context LLMs still require significant advancements to effectively process 100K+ context," and the tasks "are designed to require well understanding of long dependencies… making simply retrieving a limited number of passages from contexts not sufficient" — retrieval alone cannot substitute for reasoning over held long context ([2402.13718](https://arxiv.org/abs/2402.13718)).
- **General long-context benchmarks:** the best commercial model (GPT-3.5-Turbo-16k) "still struggles on longer contexts" ([2308.14508](https://arxiv.org/abs/2308.14508)); open-source models trail GPT-4/Claude on extended-context reasoning, and n-gram metrics fail to correlate with human judgment on long outputs ([2307.11088](https://arxiv.org/abs/2307.11088)); long-dependency modeling is constrained by position encodings ([2309.16039](https://arxiv.org/abs/2309.16039)).
- **Legal domain (the AI-judge case):** long-context legal evaluation is itself underdeveloped — "most existing evaluations rely on simplified synthetic tasks that fail to represent the complexity of real-world document understanding," and models show "context-dependent reasoning failures" and shallow heuristics on overruling relationships ([2510.20941](https://arxiv.org/abs/2510.20941)). The canonical legal benchmark defines the reasoning types (162 tasks / 6 types, expert-authored) but is not a long-document corpus-loading test ([2308.11462](https://arxiv.org/abs/2308.11462)).

### (b) The architectural answer is externalize, not shorten

- **The corpus → retrieval (RAG), not in-context.** RAG pairs parametric memory with a non-parametric vector index and set SOTA on open-domain QA by retrieving rather than holding all knowledge ([2005.11401](https://arxiv.org/abs/2005.11401)).
- **But the head-to-head is not "RAG wins":** "when resourced sufficiently, LC consistently outperforms RAG in terms of average performance. However, RAG's significantly lower cost remains a distinct advantage" → the practical answer is a hybrid that routes between them (Self-Route) ([2407.16833](https://arxiv.org/abs/2407.16833)). LongBench concurs: retrieval/compression "brings improvement for model with weak ability on long contexts, but the performance still lags behind models that have strong long context understanding capability" ([2308.14508](https://arxiv.org/abs/2308.14508)).
- **Retrieval itself must be long-context-aware:** grouping documents into ~4K-token units with a "long retriever + long reader" reduces retrieval burden and matches fully-trained SOTA on NQ/HotpotQA — "externalize" does not mean short, lossy chunks ([2406.15319](https://arxiv.org/abs/2406.15319)).
- **The derived state → step-level externalization/verification.** Chain-of-thought generates intermediate steps inside one context ([2201.11903](https://arxiv.org/abs/2201.11903)); process supervision (feedback on each intermediate step, not just the outcome) significantly outperforms outcome supervision on MATH ([2305.20050](https://arxiv.org/abs/2305.20050)). This is the literature's answer to the brief's class-6 mechanism (no persistent scratchpad, L70): write and verify each step — don't shorten the task.

**Counter 2 verdict:** *sustained.* For corpus-as-prerequisite tasks (PDEs; an AI judge that must load a constitution + statutes + precedent structure), the validity condition (L39) is unsatisfiable, and "shorten the context" would drop required content — the same lossy move the brief forbids at L37. The literature prescribes the brief's class-6 remedy (externalize) while conceding its cost (L79): externalize the corpus to retrieval and the derived state to a scratchpad, then mitigate the resulting length with re-grounding. The counter adds a *second* named inapplicability case, not a refutation.

---

## What this does to the mirror probe

- **Counter 1 is sustained — it changes two strong claims, not the taxonomy.**
  - Soften L144 ("the trace distinguishes without any experiment"): the trace is unfaithful ([2307.13702](https://arxiv.org/abs/2307.13702)) and the executing step is usually not the deciding step ([2606.08275](https://arxiv.org/abs/2606.08275)).
  - Demote L56 ("the violating step is the origin") from rule to *heuristic*, per the same source.
  - The verdict (L40) needs the CI/intervention discipline the causal-attribution literature demands ([2606.08275](https://arxiv.org/abs/2606.08275), [2605.25338](https://arxiv.org/abs/2605.25338)) — or it must fall back to L146's "two candidates + missing evidence," which the primary sources show is the *expected* case, not the residual case.
  - Title L1 ("one probe away") overstates; the three-probe battery (L25) is the load-bearing part, and the literature endorses convergence over a single decisive re-run.

- **Counter 2 is sustained — it extends, not contradicts, the brief.**
  - The brief names one inapplicability case ("task is its own discovery," L44–45). The literature adds a second: **"context is the prerequisite"** (corpus-loading tasks), where L39 fails by construction and where retrieval alone is insufficient ([2402.13718](https://arxiv.org/abs/2402.13718)).
  - Wording to add near L39/L45: *the mirror probe is inapplicable when the context is the task's prerequisite (statutes, precedent, corpus) or when the task is its own discovery — in both cases fall back to re-injection + externalized-step verification, not a forced 4/6 verdict.*
  - L79 already concedes externalization lengthens context and can re-trigger 4/5; the RAG-vs-LC result (accuracy favors LC, cost favors RAG, hybrid routes) is the operational shape of that concession ([2407.16833](https://arxiv.org/abs/2407.16833)).

- **Net:** neither counter collapses class 4 into class 6. Counter 1 makes the mirror probe a *convergent* probe, not a decisive one; Counter 2 scopes it to *re-instantiable* tasks and routes the rest to externalization. Both are wording/scope repairs, not refutations of the mechanism distinction.

---

## Sources

1. Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," TACL 2023 — https://arxiv.org/abs/2307.03172
2. Bai et al., "LongBench: A Bilingual, Multitask Benchmark for Long Context Understanding," ACL 2024 — https://arxiv.org/abs/2308.14508
3. Hsieh et al., "RULER: What's the Real Context Size of Your Long-Context Language Models?," COLM 2024 — https://arxiv.org/abs/2404.06654
4. Zhang et al., "∞Bench: Extending Long Context Evaluation Beyond 100K Tokens," arXiv — https://arxiv.org/abs/2402.13718
5. An et al., "L-Eval: Instituting Standardized Evaluation for Long Context Language Models," arXiv — https://arxiv.org/abs/2307.11088
6. Xiong et al., "Effective Long-Context Scaling of Foundation Models," arXiv — https://arxiv.org/abs/2309.16039
7. Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models," NeurIPS 2022 — https://arxiv.org/abs/2201.11903
8. Lanham et al., "Measuring Faithfulness in Chain-of-Thought Reasoning," arXiv — https://arxiv.org/abs/2307.13702
9. Turpin et al., "Language Models Don't Always Say What They Think," NeurIPS 2023 — https://arxiv.org/abs/2305.04388
10. Lightman et al., "Let's Verify Step by Step," arXiv — https://arxiv.org/abs/2305.20050
11. Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks," NeurIPS 2020 — https://arxiv.org/abs/2005.11401
12. Guha et al., "LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in LLMs," arXiv — https://arxiv.org/abs/2308.11462
13. Li et al., "Retrieval Augmented Generation or Long-Context LLMs? A Comprehensive Study and Hybrid Approach," EMNLP 2024 — https://arxiv.org/abs/2407.16833
14. Jiang et al., "LongRAG: Enhancing Retrieval-Augmented Generation with Long-context LLMs," arXiv — https://arxiv.org/abs/2406.15319
15. Zhang et al., "Do LLMs Truly Understand When a Precedent Is Overruled?," JURIX 2025 — https://arxiv.org/abs/2510.20941
16. Shah, "Causal Agent Replay: Counterfactual Attribution for LLM-Agent Failures," arXiv — https://arxiv.org/abs/2606.08275
17. Bonagiri et al., "CausalFlow: Causal Attribution and Counterfactual Repair for LLM Agent Failures," arXiv — https://arxiv.org/abs/2605.25338
18. Geiger et al., "Causal Abstraction: A Theoretical Foundation for Mechanistic Interpretability," arXiv — https://arxiv.org/abs/2301.04709
19. Doshi-Velez & Kim, "Towards A Rigorous Science of Interpretable Machine Learning," arXiv — https://arxiv.org/abs/1702.08608
20. Schaeffer et al., "Are Emergent Abilities of Large Language Models a Mirage?," NeurIPS 2023 — https://arxiv.org/abs/2304.15004
