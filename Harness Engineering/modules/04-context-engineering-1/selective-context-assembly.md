# Selective context assembly — the context window as a projection of session state

> **Companion to M4 (Context Engineering I: Assembly & Budgets).** M4 teaches the *budget*: what the window costs, and the three dials that keep it from growing unbounded. This document teaches the *selection*: given the full record of a conversation, how does the harness decide *which turns* belong in the window for *this* question — and is that even a real mechanism?

---

## Table of contents

- [TL;DR](#tldr)
- [The two objects: session state and the context window](#the-two-objects-session-state-and-the-context-window)
  - [Session state is the record](#session-state-is-the-record)
  - [The context window is a per-turn projection](#the-context-window-is-a-per-turn-projection)
- [Why not put everything in](#why-not-put-everything-in)
- [The three selectors](#the-three-selectors)
  - [Selector 1: positional recency](#selector-1-positional-recency)
  - [Selector 2: summarization and compaction](#selector-2-summarization-and-compaction)
  - [Selector 3: content-based retrieval](#selector-3-content-based-retrieval)
- [The mechanism, end to end](#the-mechanism-end-to-end)
  - [Step 1: reference resolution](#step-1-reference-resolution)
  - [Step 2: retrieval over history](#step-2-retrieval-over-history)
  - [Step 3: span retrieval](#step-3-span-retrieval)
  - [Step 4: relevance and role filtering](#step-4-relevance-and-role-filtering)
  - [Step 5: assembly](#step-5-assembly)
- [Worked case 1: a topical reference](#worked-case-1-a-topical-reference)
  - [What happens](#what-happens)
  - [Where it fails](#where-it-fails)
- [Worked case 2: span retrieval with exclusions](#worked-case-2-span-retrieval-with-exclusions)
  - [Decomposition](#decomposition)
  - [The clarification-exclusion subtlety](#the-clarification-exclusion-subtlety)
- [Is this legitimate: the named architecture](#is-this-legitimate-the-named-architecture)
  - [MemGPT and Letta: virtual context management](#memgpt-and-letta-virtual-context-management)
  - [Zep: temporal knowledge graph and per-turn tagging](#zep-temporal-knowledge-graph-and-per-turn-tagging)
  - [The rest of the field](#the-rest-of-the-field)
- [Is it valid: the active-research frontier](#is-it-valid-the-active-research-frontier)
  - [The recall bottleneck](#the-recall-bottleneck)
  - [Topic segmentation is imperfect](#topic-segmentation-is-imperfect)
  - [Bare references defeat keyword search](#bare-references-defeat-keyword-search)
  - [What the recent papers are still working on](#what-the-recent-papers-are-still-working-on)
- [The honest engineering bottom line](#the-honest-engineering-bottom-line)
  - [Build vs buy](#build-vs-buy)
  - [What you will still be tuning in production](#what-you-will-still-be-tuning-in-production)
- [Sources](#sources)
  - [Core references](#core-references)
  - [Recent preprints and supplementary](#recent-preprints-and-supplementary)

---

## TL;DR

- **Session state holds the full record** — every turn: user messages, agent replies, tool calls, in chronological order.
- **Not all of it goes into the context window.** Deliberately. The window is a *per-turn projection* assembled to answer the current question.
- **The context assembly layer is the selector** — its job is to decide *which* turns, in *what form*, get injected for *this* question.
- **Selection comes in three flavors:**
  - **Positional** — keep the last N turns (recency).
  - **Summarization** — compact old turns into a running summary.
  - **Content-based retrieval** — keep the full history in a store, and pull only the turns *relevant to the current question*.
- **This document is about the third flavor** — the only one that can answer "which turns are about X" rather than "which turns are recent."
- **It is a real, named, productized architecture** — MemGPT/Letta, Zep, Mem0, LangMem all implement it — not a fringe idea.
- **Its hard part** — resolving a *semantic* reference ("remember when we discussed X") into the right turns — is active research. **Recall is the acknowledged bottleneck.**

---

## The two objects: session state and the context window

The whole mechanism rests on one distinction that is easy to skip because the naive agent hides it: **the record and the view are two different objects.**

### Session state is the record

- **What it is:** the complete, append-only transcript of one conversation thread.
  - In ADK: `Session` = the chronological sequence of `Event`s (user messages, agent replies, tool calls); `State` = the scratchpad; a `SessionService` persists and retrieves sessions, appending each new `Event` via `append_event`.
  - In DSH: the `SessionEvent` log in `core/session` — the single source of truth.
- **Key properties:**
  - **Complete** — nothing is dropped; it is the ground truth of "what actually happened."
  - **Ordered** — chronology is preserved; turn 5 comes before turn 6.
  - **Not read by the model** — the model never sees the `Session` object itself. It is *storage*, not *input*.

### The context window is a per-turn projection

- **What it is:** the single block of text the model reads every time it thinks.
- **How it comes to be:** the harness assembles it fresh each turn (ADK: the `Runner` loop; DSH: prompt assembly in `core/system-prompt`).
- **What it contains:** a *selection* — from the session, plus standing instructions, tool definitions, and retrieved material (M4's anatomy table).
- **The governing invariant** (DSH): **"model-visible means logged"** — everything the model sees must be reconstructable from the session log. The window is a *derived view*; the log is the *source of truth*.

> **The one-sentence version:** session state is the truth; the context window is a decision about which sliver of that truth to show, in what form, at what cost.

---

## Why not put everything in

The obvious question: if the session already holds all turns, why not just send all of it every turn? Three reasons, each a failure class from M4:

- **Budget.** You pay for every input token every turn; input size also scales latency. Sending 90k tokens because the session *has* 90k tokens is a cost blowup with no correctness return.
- **Attention.** The model's attention is finite and *positional*. Old turns sit in the middle of the window — the weakest attentional slot (M2's position bias). Irrelevant history doesn't just cost money; it *dilutes* the current question.
- **Correctness.** A stale or contradicted fact that is present competes with the truth. A turn 5 that was superseded by turn 9, but still sits in the window, is wrongness presenting itself as rightness.

> **The failure mode in one line:** treating the window as a *copy* of the session instead of a *projection* of it. The naive default — "append everything, forever" — is precisely this mistake, and M4 names it.

---

## The three selectors

Given "not everything goes in," the assembly layer needs a *policy* for what does. There are exactly three families of policy — and only one of them is about *content*.

### Selector 1: positional recency

- **Policy:** keep the last N turns verbatim; drop everything older.
- **Why it exists:** it is trivial, deterministic, and predictable.
- **Where it fails:**
  - Anything older than N is gone **regardless of relevance**.
  - Fails *case 1*: a reference to a turn-5 figure is dead if N = 4.
  - Fails *case 2*: turns 5–8 are gone if N = 2.

### Selector 2: summarization and compaction

- **Policy:** periodically summarize old turns into a running summary; keep only the recent few verbatim.
- **ADK:** `EventsCompactionConfig` (token threshold + `event_retention_size`, or turn interval + `overlap_size`), with a custom `LlmEventSummarizer`.
- **Where it fails:**
  - **Fidelity loss is invisible.** A summary keeps the narrative and drops the specifics — the exact figure, the exact clause, the exact caveat.
  - Fails *case 1*: "the price you quoted earlier" is unresolvable if the summarizer dropped the number.
  - Fails *case 2*: a summary of turns 5–8 is **not** turns 5–8. You cannot "document the discussion" from a summary; documentation requires the discussion.

### Selector 3: content-based retrieval

- **Policy:** keep the full session in an external store; per turn, retrieve *only the turns relevant to the current question* and inject them.
- **Why it is different:** it answers **"which turns are about X"**, not "which turns are recent." The other two selectors are positional; this one is *semantic*.
- **What it makes possible:**
  - *Case 1* — resolve "the Kunal Kamra figure" to the turn that stated it, and pull that turn.
  - *Case 2* — resolve two topic anchors to a *span* of turns, and pull that span.
- **The catch:** relevance is a *judgment*, so this selector cannot be a deterministic rule unless turns are pre-tagged. It needs the machinery in the next section.

---

## The mechanism, end to end

Content-based selection is not one step. It is a pipeline of five, and each is a named, separable component.

### Step 1: reference resolution

- **The problem:** users speak in *mentions*, not queries. "Remember when we discussed the Kunal Kamra YT-Thanks total?" is not a search string — it is a *reference*.
- **What happens:** a lightweight model (or the assembly layer itself) rewrites the reference into a retrieval query — "Super Thanks total for the Kunal Kamra Naya Bharat video."
- **Why it is a separate step:** the rewrite is *coreference/anaphora resolution plus query expansion*. Without it, retrieval has nothing to match on.
- **The hard sub-case:** a bare anaphor — "that figure," "the thing we said" — carries **no content keywords at all**. Step 1 must inject the content from context; pure embedding search will fail on it.

### Step 2: retrieval over history

- **What happens:** search the stored turns by the rewritten query, and return candidate turns (in *case 1*, turn 5's agent response).
- **What it is, honestly:** the same retrieval machinery as M5's RAG, pointed at **conversation history** instead of a document corpus.
- **The scope note:** "history" must include *tool events* and *intermediate results*, not just chat text — a figure that lives in a tool result is invisible to a retriever that only indexes prose.

### Step 3: span retrieval

- **The problem:** *case 2* needs a *range*, not a single hit.
- **What happens:** resolve two anchors — the start ("the problem with unions") and the end ("theorized way to structure unions") — and take the turns between them.
- **What it requires:** topic boundaries. You cannot take "the turns between A and B" unless you know where A ends and B ends — that is **topic segmentation**, and it is the step that makes span retrieval possible (and fallible).

### Step 4: relevance and role filtering

- **The problem:** inside (or around) the span, some turns do not belong — the clarification turns 9–10 in *case 2*.
- **What happens:** a filter removes them.
- **The subtlety (see the worked case):** clarifications are usually **topically close** to the discussion, so a *topic* filter will not remove them. Exclusion needs a **role/intent classifier** — "is this turn advancing the topic, or asking a clarifying question?" — not a topic classifier.

### Step 5: assembly

- **The problem:** the selected turns must take a *form* before they enter the window.
- **The two forms, and the tradeoff:**
  - **Verbatim transcript** — fidelity, at token cost. Required for "document the discussion."
  - **Structured summary** (topic, decisions, open questions) — cheap, but lossy. Not documentation.
- **This is the same ledger as compaction, applied at selection time** — verbatim = faithful and expensive; summary = cheap and lossy — and it belongs in an ADR.

---

## Worked case 1: a topical reference

> *A 10-turn conversation. Turn 11: the user says "hey, how was that Kunal Kamra YT-Thanks total compared to XYZ?" — referring to a figure the agent stated in its turn-5 response.*

### What happens

- **Step 1** — resolve the reference: rewrite into "total Super Thanks for the Kunal Kamra Naya Bharat video."
- **Step 2** — retrieve: return turn 5 (the agent reply containing the figure).
- **Steps 3–4** — n/a: a single reference, no span, no exclusion.
- **Step 5** — assemble: inject turn 5's figure **verbatim** into the window, alongside the current question, so the model can compare it to XYZ.
- **The naive alternative:** if turn 5 had been compacted into a running summary (or evicted by recency), the figure is gone — and the model either reconstructs it (hallucination) or asks.

### Where it fails

- **The reference is a bare anaphor** ("that figure") → step 1 has nothing to search on; retrieval fails before it starts.
- **Retrieval returns the wrong turn** (a later mention of Kamra, a different video) → the model confidently compares against the wrong figure.
- **The figure lives in a tool result**, not an agent reply → retrieval that indexes only chat text never finds it.

---

## Worked case 2: span retrieval with exclusions

> *Turns 5–8 were a branched discussion ("the problem with unions" → "theorized way to structure unions"). Turns 9–10 were clarifications. The user says: "document the discussion from 'the problem with unions' to 'theorized way to structure unions' — skip the clarification questions."*

### Decomposition

- **Step 1** — two anchors, two queries: "the problem with unions" (start) and "theorized way to structure unions" (end).
- **Step 2** — locate the start turn and the end turn.
- **Step 3** — span retrieval: take the turns between the two anchors.
- **Step 4** — role filtering: exclude 9–10 because they are clarifications, *not* because they are off-topic.
- **Step 5** — assemble a verbatim transcript of 5–8, then hand it to the documentation task.

### The clarification-exclusion subtlety

- **Why a topic filter fails:** clarifications are semantically *close* to the topic — "what did you mean by X?" *is* about X. Topic-based segmentation will keep them in.
- **What you actually need:** a **role/intent signal** — "is this turn advancing the topic, or asking a clarifying question?" — evaluated per turn.
- **How it is done:** a small classifier, or an LLM-as-judge pass, over each turn in the span.
- **The two ways to get it wrong:**
  - Include the clarifications → noise in the documentation.
  - Exclude a substantive turn → **silent omission** — the documentation is missing a real part of the discussion, and no one is told.

---

## Is this legitimate: the named architecture

Yes. This is not a hypothetical mechanism; it is the **dominant long-term-memory architecture** for agents, with a formal name and production implementations.

### MemGPT and Letta: virtual context management

- **The idea:** a fixed *main context* (the window) plus an *external context* (the full history), and a *memory manager* that **pages relevant data in and out each turn**.
- **Why it matters here:** this is literally "not everything goes into the window; an assembly layer pulls the relevant subset" — formalized and peer-reviewed.
- **Provenance:** [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), ICLR 2024. The project is now **Letta**, and it ships in production.

### Zep: temporal knowledge graph and per-turn tagging

- **The idea:** store conversation turns in a temporal knowledge graph; **summarize and tag each turn with topic labels**; retrieve by semantic, temporal, and factual query.
- **Why it matters here:** the per-turn tagging is exactly the machinery *case 2* needs to find topic boundaries and build a span.
- **Provenance:** [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956); product docs at [help.getzep.com](https://help.getzep.com/langgraph-memory).

### The rest of the field

- **Mem0** — extracts and retrieves relevant memories per turn ([Zep vs Mem0 comparison](https://mem0.ai/blog/zep-vs-mem0-which-ai-memory-layer-should-you-choose)).
- **LangMem**, **LangChain's vector-store memory**, **OpenAI's memory feature**, and [Elastic's agent-memory guide](https://www.elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch) — all "persist everything, retrieve the relevant slice per turn."
- **LazyMem** — [*Retrieve Broadly, Construct Selectively*](https://arxiv.org/abs/2607.22690): retrieve a broad candidate set from history, then *construct* the window selectively. Your assembly layer in one title.
- **The surveys** — [A Survey on the Memory Mechanism of LLM-based Agents (ACM TOIS)](https://dl.acm.org/doi/10.1145/3748302) and [Memory for Autonomous LLM Agents](https://ar5iv.labs.arxiv.org/html/2603.07670) — both taxonomize it as **full-window / summarization / retrieval-over-history / hybrid**.

> **Verdict:** the architecture is settled and standard. Content-based retrieval over conversation history is legitimate, mainstream, and productized.

---

## Is it valid: the active-research frontier

"Legitimate" and "solved" are different things. The *architecture* is settled; the *quality* of the semantic-selection edge is not — and that edge is exactly your two cases.

### The recall bottleneck

- **What it is:** retrieval only works as well as (a) the query produced in step 1, and (b) the stored representation of the turns.
- **The evidence:** the surveys and system papers consistently name **recall** — getting the *right* turn back — as the limiting factor, not the generation.

### Topic segmentation is imperfect

- **What it is:** dividing a conversation into topic segments is itself error-prone; boundaries drift, and a turn can belong to two topics at once.
- **The evidence:** dialogue topic segmentation is a standing research problem — see [ACL Anthology 2021.emnlp-main.498](https://aclanthology.org/2021.emnlp-main.498.pdf).

### Bare references defeat keyword search

- **What it is:** "that figure" or "the thing we said" carry no content keywords; retrieval over raw embeddings has nothing to match.
- **The fix:** step 1 must resolve the reference into content *before* retrieval — coreference/anaphora resolution, then query expansion.
- **The evidence:** [SeCom: On Memory Construction and Retrieval for Personalized Conversational Agents](https://iclr.cc/virtual/2025/poster/27790), ICLR 2025, is precisely this problem.

### What the recent papers are still working on

- **TRACE-Memory** — [*Public-Conditioned Retrieval and Utility-Aware Evidence Admission*](https://arxiv.org/html/2608.08446v2) — gates *what gets admitted* to the window by utility, i.e. relevance filtering with a rejection mechanism.
- **LazyMem** — [*Retrieve Broadly, Construct Selectively*](https://arxiv.org/abs/2607.22690) — still refining the retrieve-then-construct split.
- **The through-line:** 2025–2026 preprints are still working on the selection *quality*, not the architecture. That is the honest signal that this edge is active, not settled.

---

## The honest engineering bottom line

### Build vs buy

- **Step 1 (reference → query rewrite):** a small model call; cheap to do yourself, or the default in a memory layer. **Build or buy — it is not exotic.**
- **Steps 2–3 (retrieval and span):** mature; **buy** (Zep, Mem0, LangMem) or build on a vector store.
- **Step 4 (role/intent filtering for exclusions):** usually **custom** — it is domain-specific ("what counts as a clarification here?"). Plan to build.
- **Step 5 (form):** a **policy decision** — verbatim vs. summary — recorded in an ADR.

### What you will still be tuning in production

- **Recall on bare references** ("that figure").
- **Topic-segmentation boundaries** for span cases.
- **The exclusion classifier's precision** — the cost of wrongly *including* a clarification is noise; the cost of wrongly *excluding* a substantive turn is silent omission.
- **The verbatim-vs-summary fidelity decision**, per use case.

> **The one-line takeaway:** session state is the truth; the window is a decision; content-based selection is the third selector — real, mainstream, and productized. But its sharp edge — semantic reference, span retrieval, and exclusion — is a place you *tune*, not a checkbox.

---

## Sources

### Core references

- [MemGPT: Towards LLMs as Operating Systems (ICLR 2024)](https://arxiv.org/abs/2310.08560)
- [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956)
- [Zep documentation — LangGraph memory](https://help.getzep.com/langgraph-memory)
- [A Survey on the Memory Mechanism of LLM-based Agents (ACM TOIS)](https://dl.acm.org/doi/10.1145/3748302)
- [ACL Anthology 2021.emnlp-main.498 — dialogue topic segmentation](https://aclanthology.org/2021.emnlp-main.498.pdf)
- [SeCom: On Memory Construction and Retrieval for Personalized Conversational Agents (ICLR 2025)](https://iclr.cc/virtual/2025/poster/27790)
- [Zep vs Mem0: Which AI Memory Layer Should You Choose?](https://mem0.ai/blog/zep-vs-mem0-which-ai-memory-layer-should-you-choose)
- [Elastic — AI agent memory management](https://www.elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch)

### Recent preprints and supplementary

- [Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers](https://ar5iv.labs.arxiv.org/html/2603.07670)
- [LazyMem: Retrieve Broadly, Construct Selectively for Efficient Long-Term Agent Memory](https://arxiv.org/abs/2607.22690)
- [TRACE-Memory: Public-Conditioned Retrieval and Utility-Aware Evidence Admission](https://arxiv.org/html/2608.08446v2)

> *Note: the three "recent preprints" entries surfaced via web search; their arXiv identifiers imply 2026 publication. Treat them as current front-line material, and re-verify the URL before citing them in a paper.*
