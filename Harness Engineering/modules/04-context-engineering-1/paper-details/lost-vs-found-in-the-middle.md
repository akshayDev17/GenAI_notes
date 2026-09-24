# Resolving the apparent contradiction — *Lost in the Middle* vs. *Found in the Middle*

**Question answered here:** are Liu et al. (2023) and Hsieh et al. (2024) in genuine contradiction, or do they describe different things?

**Verdict up front:** *Not a contradiction — two different levels of description of the same observation.* Liu measures **behavior** (task accuracy vs. position) and reports a U-shaped curve. Hsieh measures a candidate **mechanism** (attention weights vs. position), *reproduces* Liu's behavioral U, then proposes and tests an **intervention** (attention calibration). Hsieh does not deny Liu's result; it presupposes it ("lost-in-the-middle") and re-explains it ("found-in-the-middle"). The genuine open question is whether either the behavioral U or the attention-weight U is **robust** — and the follow-up literature says: only conditionally.

Sibling notes: [`lost-in-the-middle.md`](./lost-in-the-middle.md) (behavioral claim, metric detail) · [`found-in-the-middle.md`](./found-in-the-middle.md) (attention mechanism, calibration math, and its internal notation inconsistency).

---

## Verification status

| Source | Title / venue / ID | Verified against |
|---|---|---|
| **Liu et al. 2023** | *Lost in the Middle: How Language Models Use Long Contexts*, TACL 2023, arXiv:2307.03172 | arXiv API + ar5iv full text (authors: Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang) |
| **Hsieh et al. 2024** | *Found in the Middle: Calibrating Positional Attention Bias Improves Long Context Utilization*, Findings of ACL 2024, arXiv:2406.16008 | arXiv API + ar5iv full text (11 authors, Cheng-Yu Hsieh et al.) |
| **Veseli et al. 2025** | *Positional Biases Shift as Inputs Approach Context Window Limits*, COLM 2025, arXiv:2508.07479 | arXiv API (abstract) |
| **Rahimi et al. 2025** | *Not Lost After All: How Cross-Encoder Attribution Challenges Position Bias Assumptions in LLM Summarization*, Findings of EMNLP 2025, ACL Anthology 2025.findings-emnlp.846, DOI 10.18653/v1/2025.findings-emnlp.846 | ACL Anthology record (abstract). **No arXiv ID located/verified** — cite by Anthology ID/DOI. |
| **Salvatore et al. 2025** | *Lost in the Middle: An Emergent Property from Information Retrieval Demands in LLMs*, arXiv:2510.10276 | arXiv API (abstract) |
| **Zehle & Aßenmacher 2026** | *Can Calibration of Positional Encodings Enhance Long Context Utilization?* (Caliope), Findings of EACL 2026, ACL Anthology 2026.findings-eacl.120 | ACL Anthology record (abstract) |
| **Jain & Wallace 2019** | *Attention is not Explanation*, NAACL 2019, arXiv:1902.10186 | arXiv API (abstract) |
| **Wiegreffe & Pinter 2019** | *Attention is not not Explanation*, EMNLP 2019, arXiv:1908.04626 | arXiv API (abstract) |

All quotations below are transcribed from these records; I flag the two places where I am extrapolating rather than quoting.

---

## 1. Behavior (Liu) vs. mechanism (Hsieh) — the exact metrics

### Liu = **accuracy**, and only accuracy

Liu's evaluation metric for the language model is **exact-answer substring presence**, stated twice:

- Multi-doc QA (§2.1): *"we use **accuracy** as our primary evaluation metric, judging whether any of the correct answers (as taken from the NaturalQuestions annotations) appear in the predicted output."*
- Key-value retrieval (§3.1): *"We again measure **accuracy** by evaluating whether the correct value appears in the predicted output."*

Liu does **not** report a recall metric for the model. ⚠️ *Correction to the prompt's framing ("Liu = accuracy/Recall"):* the only "recall" in Liu is **retriever recall** in §5's open-domain QA case study — that is the *Contriever* retrieval system's recall, not a metric scored on the LLM. **Liu's model metric is accuracy alone.** (The prompt's "Recall" likely came from Hsieh's Recall@3, cross-wired onto Liu.)

- Two tasks: (a) **multi-document QA** on NaturalQuestions — `k ∈ {10, 20, 30}` documents, exactly one gold, the rest Contriever distractors; (b) **synthetic key-value retrieval** — a serialized JSON of `k` UUID key-value pairs (up to 300), return the value for a given key.
- The claim is purely **behavioral**: *"language model performance is highest when relevant information occurs at the very beginning (**primacy bias**) or end of its input context (**recency bias**), and performance significantly degrades when models must access and use information in the middle of their input context."* Liu explicitly does **not** claim to explain *why* — §4 is titled *"Why Are Language Models Not Robust…"* but its results are correlations (architecture, query-aware contextualization, instruction fine-tuning), not an attention mechanism.

### Hsieh = **attention weights + Recall@3 + downstream accuracy** (three different instruments)

Hsieh layers three measurements, and conflating them is the root of the "contradiction":

1. **Attention weights** (the *mechanism* claim). §2.1: *"Attn(x_prompt,k) = Σ_{i=1}^{N_k} attn(x_{k,i}^doc) / N_k*, where `attn(x_{k,i}^doc)` is the attention weight value allocated to token `x_{k,i}^doc` when predicting the next `|x_prompt|+1` token… averaged across all its tokens, all decoder layers, and heads." Plotting this against position yields the U: *"Documents at the beginning and end receive greater attention, regardless of order."*
2. **Recall@3** (the *"can it locate the relevant doc"* claim). Intro: calibrated attention *"outperforms popular existing approaches for ranking the relevance of retrieved documents (**up to 48 Recall@3 points**)"*; Table 3 reports Recall@3 over `K ∈ {10, 20}`.
3. **Downstream RAG accuracy** (the *"does the answer improve"* claim). Intro/§4.2: *"improvements over standard model generation by **up to 15 percentage point** on NaturalQuestion dataset."*

So the two papers are not measuring the same thing. **Liu: does the model get the answer right, as a function of where the answer sits? Hsieh: where does the model allocate attention, and does re-weighting that allocation fix the answer?** The former is a performance curve; the latter is a proposed causal story *plus* an intervention. A mechanism and the behavior it purports to explain cannot contradict each other directly — only the mechanism can be *wrong* as an explanation.

---

## 2. Does Hsieh reproduce Liu, then fix it? — Yes, and it says so in its own words

Hsieh is explicit that it (a) inherits Liu's framing, (b) adheres to Liu's setup, and (c) reproduces the phenomenon before intervening.

- **Naming the phenomenon as Liu's** (Intro): *"recent experiments highlight a striking deficiency: LLMs struggle to locate relevant documents when they are placed in the middle of their input prompts (**[Liu et al. 2023]**; [Li et al. 2023a]). **They call this the lost-in-the-middle phenomenon.**"*
- **Adopting Liu's setup** (§2, "Setup"): *"We adhere to the original experimental setup outlined in **[Liu et al. 2023]**, utilizing an open-domain question answering task ([Kwiatkowski et al. 2019]) for our exploratory study."*
- **Reproducing the behavioral U** (§2): *"Here, we **reproduce** lost-in-the-middle phenomenon with a Vicuna-7b-v1.5-16k (Vicuna) model."*
- **Bridging its attention U to Liu's performance U** (Intro): *"we find that models often demonstrate a U-shaped attention distributions… **This correlates well with the U-shaped RAG performance observed in prior literature ([Liu et al. 2023]).**"*
- **The "fix" as a re-interpretation, not a denial** (Intro): *"This finding **challenges the recent belief that LLMs struggle to capture relevant context embedded in the middle of inputs**, suggesting they may indeed be capable of doing so, but are only hindered by the overwhelming positional bias."*

Two precision caveats before you over-read "reproduce":

1. **Hsieh reproduces the *setup*, not Liu's exact models.** Liu ran MPT-30B-Instruct, LongChat-13B (16K), GPT-3.5-Turbo, Claude-1.3. Hsieh runs Vicuna-7b-v1.5-16k and Tulu-2-7B. So "reproduce" = same task template (multi-doc QA, one gold doc, distractors), different checkpoints.
2. **Hsieh reproduces only the multi-doc QA task.** Liu's second task (synthetic key-value retrieval) is not re-run by Hsieh. The calibration story is demonstrated on NaturalQuestions + SynthWiki multi-doc QA only.

Also note Hsieh's own hedge on the mechanism: §2.1 cites the U-shaped *attention* while admitting *"the weights has been shown to correlate with models' generations, **although not necessarily causal** (Dong et al., 2021; Zhang et al., 2023)."* Hsieh is candid that attention weights are a proxy, not a proven cause — see §3 below for why that matters.

---

## 3. Work that reconciles, distinguishes, or destabilizes the U-shape

Four follow-ups bear directly on the question, and they cut in *different* directions.

### 3a. The U-shape is *relative*, not absolute — and it dissolves near the window limit (Veseli et al. 2025, COLM)

> *"the LiM effect is strongest when inputs occupy up to **50% of a model's context window**. Beyond that, the primacy bias weakens, while recency bias remains relatively stable. **This effectively eliminates the LiM effect**; instead, we observe a **distance-based bias**, where model performance is better when relevant information is closer to the end of the input."*

Implication: Liu's U was measured on short absolute contexts (tens of documents ≈ a small fraction of a long-context window). "Lost in the middle" is **not** a fixed property of position in the middle — it is a property of **moderate window fill**. At high fill, recency dominates and the "middle penalty" goes away. This is a *scope* limit on Liu, not a contradiction.

### 3b. The measurement method changes the picture — cross-encoder attribution finds different bias patterns (Rahimi et al. 2025, Findings of EMNLP)

> *"To measure position bias, prior studies **rely heavily on n-gram matching techniques, which fail to capture semantic relationships in abstractive summaries**… Experiments with five LLMs across six summarization datasets reveal **significantly different position bias patterns** than those reported by traditional metrics… LLMs **use content from all positions more effectively than previously assumed, challenging common claims about 'lost-in-the-middle' behaviour**."*

Implication: how you *measure* "which source the output used" (n-gram overlap vs. cross-encoder semantic alignment) changes whether you see the U. This is a **measurement-validity** challenge to the *behavioral* claim — and a direct cousin of the "attention is not explanation" literature (see 3d). Caveat to state plainly: this is **summarization**, not retrieval QA, so it challenges the *generality* of LiM to a second task family more than it refutes Liu's specific QA finding.

### 3c. The U-shape is a trained adaptation, not information loss (Salvatore et al. 2025)

> *"this behavior is **not simply a flaw indicative of information loss but an adaptation to different information retrieval demands during pre-training**… the **primacy effect is induced by the uniform long-term memory demand** and is additionally influenced by the model's autoregressive properties and the formation of **attention sinks**… the **recency effect directly aligns with short-term memory demand**."*

Implication: this *reconciles* Liu and Hsieh from a third altitude. It agrees with Liu (the U is real) and with Hsieh (positional/attention-based, not relevance-based), while reframing it as a **learned and partly rational** bias rather than a defect — which predicts exactly the task-dependence and model-dependence the field keeps finding.

### 3d. The mechanism half rests on "attention = explanation," which is contested (Jain & Wallace 2019; Wiegreffe & Pinter 2019)

Hsieh's causal claim ("positional attention bias → lost in the middle") leans on reading **attention weights** as what the model "uses." That reading is precisely what the attention-as-explanation debate contests:

- Jain & Wallace: *"learned attention weights are **frequently uncorrelated with gradient-based measures of feature importance**, and one can identify very different attention distributions that nonetheless yield equivalent predictions."*
- Wiegreffe & Pinter: the rebuttal — attention can be explanation *under the right tests* — but the burden is on the claim, not free.

Implication: Hsieh's **intervention worked** (Recall@3 up, accuracy up), which is stronger evidence than the attention visualization alone. But the *specific* story "the U is caused by a positional attention bias that overwhelms the model's latent ability to attend to the middle" is a **mechanistic hypothesis with correlational support**, not a settled causal proof. Hsieh's own "not necessarily causal" hedge concedes this.

### 3e. Calibration-style fixes replicate — LiM persists, and positional-encoding calibration helps (Zehle & Aßenmacher 2026)

> *"Our empirical study **confirms the persistence of these biases in modern large language models**… we introduce **Caliope**, a training-free framework for calibrating Positional Encodings at inference time… substantial improvements on needle-in-a-haystack and cross-chunk reasoning benchmarks."*

Implication: independent, later work still finds LiM in modern models and still gets gains from position-*calibration* (analogous in spirit to Hsieh's attention calibration). This supports Hsieh's direction without endorsing every detail of its mechanism.

> ⚠️ *Extrapolation, not quote:* the summary judgment that these five papers "cut in different directions" (3a/3b destabilize; 3c reconciles; 3e supports) is my synthesis over their abstracts, not a sentence any of them states. I did not fetch the full PDFs of 3a–3e, only their abstracts/anthology records; the quotes above are from those records.

---

## 4. What to believe (one paragraph)

Liu and Hsieh are **not** in contradiction — they are two rungs on the same ladder. Liu established the *behavioral* fact: on multi-document QA and key-value retrieval, **accuracy vs. position is U-shaped** — highest at the start (primacy) and end (recency), worst in the middle. Hsieh *reproduced* that behavioral U (same setup, different models), then moved to the *mechanism*: the model **does** allocate real attention to relevant middle content, but a **positional attention bias** (U-shaped attention weights favoring the ends, "regardless of relevance") overwhelms it, and **cancelling that bias** (attention calibration) restores middle-utilization — measured by Recall@3 (up to +48) and downstream accuracy (up to +15 pp). So "found in the middle" presupposes "lost in the middle" at the behavioral level and re-explains it; the only genuine tension is whether the *mechanism* (attention weights) is a trustworthy causal account. The follow-up literature says the behavioral U itself is **conditional, not universal**: it is strongest on retrieval/QA-style tasks with a single gold item among ranked distractors, at **moderate window fill (≲50%)** (Veseli — beyond that primacy collapses and a distance-from-end bias takes over), it can **shift or vanish under semantic (cross-encoder) attribution** on summarization (Rahimi), it may be a **trained adaptation rather than a defect** (Salvatore), and the attention-weights-as-cause reading is **methodologically contested** (Jain & Wallace). 

**Practical rule for a harness engineer:** treat position as a **risk multiplier, not a physical law** — and it is an *asymmetric* one, because a middle placement fails silently while end placement costs almost nothing. Put the **must-persist policy at the beginning** (primacy), the **must-act-on-now query/constraint at the end** (recency), and keep the **middle as a clearly-marked lookup block** for retrieved evidence/tool results that the model may cite but never *needs* to remember; re-order so anything load-bearing sits near an end, and re-inject critical facts near the point of use. But **do not over-engineer against a fixed "middle is dead" rule**: the penalty is largest only at moderate fill and on certain task types, so measure it on *your* model/task/fill level (a quick position-sweep with a few dozen queries) before paying for re-rankers or calibration, and default to the ends not because the middle provably fails but because the cost of being wrong there is cheap to avoid.

---

## Quick reference — the four sub-answers

1. **Behavior vs. mechanism:** Yes. Liu = **accuracy** (substring match) only — *not* "accuracy/Recall" (the recall in Liu is the retriever's, §5). Hsieh = **attention weights** (mechanism) + **Recall@3** (locating) + **downstream accuracy** (task).
2. **Does Hsieh reproduce then fix Liu?** Yes — verbatim: *"We adhere to the original experimental setup outlined in [Liu et al. 2023]"*, *"Here, we reproduce lost-in-the-middle phenomenon"*, *"This finding challenges the recent belief… suggesting they may indeed be capable of doing so, but are only hindered by the overwhelming positional bias."* Caveats: same setup, **different models** (Vicuna/Tulu, not MPT/GPT/Claude), and **only the multi-doc QA task** (not key-value retrieval).
3. **Reconciling/robustness work:** Veseli et al. (arXiv:2508.07479, COLM 2025) — U-shape dissolves above ~50% fill; Rahimi et al. (Findings EMNLP 2025, Anthology 2025.findings-emnlp.846) — cross-encoder attribution shifts the picture; Salvatore et al. (arXiv:2510.10276) — emergent training adaptation; Jain & Wallace (arXiv:1902.10186) / Wiegreffe & Pinter (arXiv:1908.04626) — attention-is-not-explanation caveat; Zehle & Aßenmacher (Findings EACL 2026, Caliope) — LiM persists, calibration helps.
4. **Synthesis:** see §4.
