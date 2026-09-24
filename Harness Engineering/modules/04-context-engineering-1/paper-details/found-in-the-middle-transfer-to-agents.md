# Does *Found-in-the-Middle* transfer to agent instruction / tool selection?

**Question investigated:** Can the Found-in-the-Middle (FitM) technique be applied to an agentic system by treating each *instruction section* (or tool docstring / sub-agent description) as a "document" ranked by calibrated attention?

**Verdict (short):** No, not as a faithful transfer. The FitM intervention fails to transfer on **two independent grounds**, both with peer-reviewed/preprint support: (1) for tool selection the model *already attends* to the correct tool and still picks wrong — the bottleneck is the decision readout, not attention (Chen 2026); and (2) the calibration's core assumption — that the "dummy"/null pass is relevance-agnostic — *breaks exactly in instruction-heavy prompts* (Karypis et al. 2026). And it is unusable through a closed API regardless.

---

## Q1 — Has any published work applied attention-based document ranking / calibration to agent instruction or tool-selection contexts (not RAG-over-passages)?

**Directly: yes, and the two closest papers both argue the FitM transfer does not hold in the agent setting.**

- **Chen, Shiyang. "Looking Is Not Picking: An Attention-Segment Account of Tool-Selection Failures in LLM Agents." arXiv:2606.16364 (2026, cs.AI).** *(single author; verified from the arXiv abstract page.)*
  This is the closest thing to "calibrated attention over tool docstrings." It treats tool definitions as *labeled tool-definition segments* and reads per-segment attention. Its findings are the opposite of the FitM/lost-in-the-middle story:
  - By per-candidate attention argmax, the model attends *most* to the correct tool **80% of the time** (chance ≈ 21%); the gold tool is the *under-attended* segment on only **10%** of failures. "It looks at the right tool and still picks wrong."
  - It therefore "directly refutes the intuitive 'crowded-harness / lost-in-the-middle' explanation": the failure is at the **decision readout**, not the harness.
  - Reordering or duplicating the gold tool recovers ≤23% of failures, while readout-side interventions (additive attention-logit bias; residual-stream steering vector) recover 59–91%.
  - It does ship a *training-free, gold-free selector* using per-segment attention (+11.9 pts BFCL function-name selection, +14.9 pts on Seal-Tools) — so attention *is* usable as a weak selector — but the paper's headline is that attention does **not** diagnose the failure, and the causal attention-bias result holds only on "10 mask-honoring models (3–32B)" while the selector is evaluated only on single-turn models and "does not yet transfer to a multi-turn loop."

- **Karypis, P., Faghihi, H. R., Chen, P., Zhu, R., Sachdeva, N., Zhu, Y., McAuley, J. "How Calibration Content Shapes Attention-Based Reranking." arXiv:2609.17764 (2026, cs.CL/cs.IR).** *(verified from abstract page.)*
  This is about the *generalized* FitM mechanism (subtract a null-query calibration pass) as used in attention-based reranking. Its result directly bears on the "instruction sections as documents" idea:
  - "calibration assumes that the null pass removes irrelevant signal… We show that modern prompt content, e.g. **constraints, instructions, personas, and demonstrations** can violate this assumption when it enters the scoring readout, making the null pass **relevance-aware rather than null**."
  - "calibration is especially **harmful** when applied to prompts containing longer, more detailed instructions as the null-pass step removes relevant signal."
  - Proposes "interpolated null calibration" to fix this on instruction-heavy tasks.

**For RAG-over-passages** the FitM mechanism itself is the original result (Hsieh et al. 2024) and its lineage is the null-query subtraction of Peysakhovich & Lerer, *Attention Sorting Combats Recency Bias in Long Context Language Models* (2023; cited as bib [38] in FitM — not separately re-fetched this session). No paper I found applies the FitM *intervention* (weight rescaling) to agent instruction/tool selection; the two above apply the *measurement* (attention ranking) and reach negative conclusions about it.

---

## Q2 — What is the analog of "the query"? Is the relevance ranking turn-independent?

**The query is, in the paper, the user question `x^q`, and `rel(x_doc)` is explicitly query-dependent.** Verified from the paper text:
- §2 setup serializes `x_prompt = [x^q, x_1^doc, …, x_k^doc, x^q]` — the query brackets the documents (footnote 1 repeats it "so that the model can better attend to relevant contexts").
- Eq. (4) derives `rel(x_doc) = Attn(x_doc,k) − Attn(x_dum,k) + rel(x_dum)`, i.e. calibrated attention is an estimate of relevance *for the current query at the current generation step*. The intervention Eq. (5) then rescales token attention by `α_k = softmax(rel(x_k), t)` computed *per query*.

**Consequence for agents — the ranking is necessarily turn-dependent, and there is no stable turn-independent ranking of instruction sections via attention:**

- Attention weights are computed at a specific generation step conditioned on the *current* prompt. A tool docstring that is irrelevant this turn can be the single most relevant next turn. So "rank instruction sections by calibrated attention" yields a *per-turn* ranking that changes with the current task — the same property retrieval-over-tools systems already exploit (see Q3).
- For **static instruction sections** (orchestration policy, output format, "how to decide which sub-agent"), there is no query at all in the retrieval sense: these are *fixed directives*, not candidates to rank against a query. Mapping them onto FitM "documents" is a category error — FitM's documents are interchangeable distractors + one gold answer-source the model must *locate*; agent instruction sections are heterogeneous, mostly-all-relevant directives. This is exactly where Karypis et al. (2026) show the null-pass assumption breaks: instructions contaminate the calibration pass.

**Any paper that addresses it?** Karypis et al. (2026) addresses precisely the "instruction content corrupts calibration" failure. Chen (2026) addresses the "ranking is conditioned on the current task, and even correct ranking doesn't fix selection" point. Neither provides a *stable, turn-independent* relevance ranking — the stable ranking is computed by an external embedding retriever (BM25/embeddings), not by model attention.

---

## Q3 — Positional bias in function-calling/tool selection; tool docstrings "lost in the middle"; retrieval-over-tools motivation.

**Positional bias in tool selection — the direct academic answer is that the "lost in the middle" explanation is *refuted* for tools:**
- Chen 2026 (above): the gold tool is under-attended in only 10% of failures; the model attends correctly and mis-picks at readout. So "tool docstrings placed mid-prompt are lost" is **not** what the attention evidence shows. Reordering/duplication recovers ≤23%.

**Retrieval-over-tools / tool search — this is real, widely deployed, and motivated by *token budget + selection confusion*, not (primarily) by the FitM positional-attention mechanism:**
- **Anthropic, "Introducing advanced tool use on the Claude Developer Platform" (Nov 24, 2025), https://www.anthropic.com/engineering/advanced-tool-use** *(full text verified).* The **Tool Search Tool** loads tools on demand (`defer_loading: true`) instead of stuffing every definition into context. Stated motivations: token overhead (5 servers ≈ 55K tokens; "we've seen tool definitions consume 134K tokens"), and "the most common failures are wrong tool selection and incorrect parameters, especially when tools have similar names." Reported: Opus 4 **49%→74%**, Opus 4.5 **79.5%→88.1%** on MCP evals with large tool libraries. Doc: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- **Sakizli, Furkan. "Tool-Schema Compression Enables Agentic RAG Under Constrained Context Budgets." arXiv:2605.26165 (2026).** *(verified.)* Tool schemas consume the same context window as RAG; at 8K, JSON schemas overflow → near-zero EM, compressed schemas restore +20.5pp. "At 32K — where both formats fit — … delta ≤ 1pp, confirming the effect is **purely budget-driven**." (This is the same "two mechanisms" point the module README already makes.)
- **Sadani, A. & Kumar, D. "Tool Attention Is All You Need: Dynamic Tool Gating and Lazy Schema Loading for Eliminating the MCP/Tools Tax…" arXiv:2604.21816 (2026).** *(verified.)* Names the "MCP/Tools Tax" (~10k–60k tokens/turn). **Caveat:** its results are on a *simulated* 120-tool benchmark; end-to-end figures are "projections derived from measured token counts… not measured on live LLM agents." Treat as a design sketch, not evidence.
- **Ge et al., "MCP Servers for Pyserini and RankLLM: Enabling Agentic Retrieval-Augmented Generation," SIGIR 2026 (uWaterloo PDF): http://cs.uwaterloo.ca/~jimmylin/publications/Ge_etal_SIGIR2026_MCP.pdf** — MCP servers as a retrieval layer for agentic RAG; evidence that "retrieval over tools" is now a first-class systems area. *(Title/venue read from the PDF filename + search snippet; not full-text verified.)*
- Also surfaced (search snippets only, **not** full-text verified this session): "TSCG: Deterministic Tool-Schema Compilation for Agentic LLM Deployments" (arXiv:2605.04107); "AutoTool: Dynamic Tool Selection and Integration for Agentic Reasoning" (arXiv:2512.13278, "embedding-anchored tool selection"); "Tool-Call Dependency Structure is Linearly Decodable in LLM Agent Residual Streams" (arXiv:2605.25310). Practitioner, non-peer-reviewed: OpenDataScience, "Evaluating Agent Tool Selection — Testing if First Really is the Worst."

**Bottom line on Q3:** retrieval-over-tools is motivated by (a) context/token budget and (b) selection-accuracy degradation with many similar tools — *not* by the FitM positional-attention-bias mechanism, and the one paper that tests the positional story for tools (Chen 2026) rejects it.

---

## Q4 — Is FitM usable via a closed (frontier) API? What lever remains?

**Not usable at all.**
- The FitM intervention requires (i) *reading* self-attention weights and (ii) *editing/rescaling* token-level attention (Eq. 5). Closed APIs (OpenAI, Anthropic, Google via LiteLLM) expose neither logprobs/attention weights nor any hook to modify attention. The measurement step (calibrated attention ranking, Eq. 4) equally requires reading attention, so even *ranking* instruction sections by calibrated attention is impossible on a frontier API.
- The only lever that remains for a closed-API user is **prompt-side assembly**: ordering/placement of sections, and retrieval/subsets of tools.
- **Does the paper support even that lever?** Only weakly, and partly against itself:
  - The U-shape *does* support the crude "put the important thing at the beginning or end" heuristic (FitM Fig. 4; Liu et al. 2023 "Lost in the Middle", arXiv:2307.03172, TACL 2024).
  - But FitM's own Introduction states re-ranking/re-ordering "does not fundamentally improve LLMs' ability to utilize and capture relevant information" — reordering is presented as the *inadequate baseline* that the weight-level intervention exists to surpass. So FitM does **not** endorse reordering as a sufficient fix.
  - For tools specifically, Chen (2026) shows reordering/duplication of the gold tool recovers only ≤23% of failures — the reordering lever is weak where it matters most.
  - The prompt-only lever with actual empirical support is a *different* paper: Zhang, Meng & Collier, "Attention Instruction: Amplifying Attention in the Middle via Prompting," arXiv:2406.17095 (2024) — index-based "attention instructions" shift attention to a named segment without weight access. That is the closest closed-API-compatible analog, and it is not FitM.

---

## The three-way split

**(a) Directly supported by the paper (Hsieh et al. 2024, arXiv:2406.16008):**
- Decoder-only LLMs show a U-shaped *positional* attention bias (beginning/end > middle), invariant to document order (Fig. 4 + shuffle control).
- Attention decomposes additively as `Attn(x_doc,k) = rel(x_doc) + bias(k) + ε`; subtracting a fixed dummy document at the same position cancels `bias(k)` and recovers `rel(x_doc)` (Eqs. 1–4).
- Rescaling token attention so document attention ∝ softmax(relevance) (Eq. 5) improves locating relevant info and RAG accuracy on *open-weight* models (Vicuna-7B-16k, Tulu-2-7B) on multi-doc QA.
- `rel(x_doc)` is **query-dependent** (defined against the current question `x^q`).

**(b) Reasonable extrapolation:**
- The U-shape likely also biases where a model *looks* among tool docstrings / instruction sections in a long prompt — i.e., position matters in agent prompts too.
- The "beginning = standing policy, end = current task, middle = supporting material" ordering heuristic is a defensible *mitigation* (this is already the module's guidance).
- Calibrated-attention-as-a-selector is *measurable* on open-weight models (Chen 2026 ships one), so an open-weight agent could in principle rank instruction sections per turn by calibrated attention.

**(c) Unsupported / speculative — do not assert:**
- That FitM's weight-rescaling *improves* agent tool/sub-agent selection. No evidence; Chen (2026) argues the failure is at readout, not attention; Karypis et al. (2026) argue the calibration assumption breaks on instruction-heavy prompts.
- That "tool docstrings mid-prompt are lost" is *the* cause of tool-selection failure — contradicted by Chen (2026).
- That there is a stable, turn-independent attention-based relevance ranking of instruction sections — contradicted by the query-dependence of `rel(x_doc)`.
- That any of this works on a closed frontier API — impossible by construction (no attention access).
- The "MCP/Tools Tax" numeric claims of Sadani & Kumar (2026) are simulation/projection, not measured on live agents.

---

## Sources & verification status

| Source | ID | Verified |
|---|---|---|
| Hsieh et al., *Found in the Middle*, Findings of ACL 2024 | arXiv:2406.16008 | abstract + full HTML text |
| Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*, TACL 2024 | arXiv:2307.03172 | search + TACL DOI link (not re-fetched) |
| Chen, *Looking Is Not Picking: An Attention-Segment Account of Tool-Selection Failures in LLM Agents*, 2026 | arXiv:2606.16364 | abstract page |
| Karypis et al., *How Calibration Content Shapes Attention-Based Reranking*, 2026 | arXiv:2609.17764 | abstract page |
| Sadani & Kumar, *Tool Attention Is All You Need…*, 2026 | arXiv:2604.21816 | abstract page |
| Sakizli, *Tool-Schema Compression Enables Agentic RAG…*, 2026 | arXiv:2605.26165 | abstract page |
| Zhang, Meng & Collier, *Attention Instruction…*, 2024 | arXiv:2406.17095 | abstract page |
| Anthropic, *Introducing advanced tool use…*, Nov 2025 | URL | full text |
| Anthropic, *Tool Search Tool* docs | URL | referenced in blog |
| Ge et al., MCP servers for agentic RAG, SIGIR 2026 | uWaterloo PDF | snippet only |
| Peysakhovich & Lerer, *Attention Sorting…*, 2023 | (cited in FitM) | not re-fetched |
| TSCG (2605.04107), AutoTool (2512.13278), Tool-Call Dependency (2605.25310) | — | search snippet only |
