# M4 · Context Engineering I: Assembly & Budgets

> **Module question:** What goes into the context window, in what form, and what does it cost?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a context-hungry research agent running a long session

---

## Opening scene — the agent that got dumber as it worked

- The research agent started sharp. "Summarize the merger filings," it said, and produced a tight, sourced brief in forty seconds. 
    - Three hours later, deep into the same session, the same agent was asked a question it had *answered correctly that morning* — and got it wrong, slowly, at five times the cost.
- The team's diagnosis: "the model degraded." It hadn't. The model was identical. 
    - What had changed, steadily, silently, all session long, was the **context window** - the single block of text the model reads every time it thinks. 
    - Every turn had appended a tool result here, a retrieved chunk there, a scratch-pad note, a user clarification. 
    - By hour three the window held ~90,000 tokens, most of them irrelevant to the current question, all of them being paid for and — worse — all of them *competing for the model's attention*.

The agent didn't get dumber. It got **drowned**. And nobody had budgeted the one resource that was doing the drowning.

This module is the first half of the cognitive layer: **assembly and budgets** — what goes into the window, in what form, and what it costs. The *second* half (how the right facts get there, and how we know they're right) is M5.

---

## The context window is a budget, not a canvas

Every model call is a single transaction with two costs, and beginners track only one:

| Cost | What it is | Consequence of ignoring it |
|---|---|---|
| **Token cost** | You pay for every input token, every turn, at your input price | Linear cost blowup as sessions grow |
| **Attention cost** | The model's attention is finite and *positional*; more context dilutes it | Correctness falls, especially for facts in the middle |

- The first is money. 
- The second is *quality* — and it's the one that causes the "the model got dumber" misdiagnosis. 
    - You have seen this failure class already: it is M2's **position bias** ("lost in the middle") and **instruction drift** (policy drowned by later text). 
    - Both are *context-assembly* failures, and both are yours to design away.

**The mental model that carries this whole module:** the context window is **live currency**. 
- You spend it every turn, and you spend it on *attention* as much as on money. 
- A token that is present but irrelevant is not free — it is a *distraction tax* on every other token, plus a cash charge, plus latency (input size scales response time). 

The discipline of context engineering is deciding, deliberately, what earns a place.

> **Failure mode (the module in one line):** treating the context window as a place to *put* things rather than a budget to *spend*. The default agent — append everything, forever — is not "simple," it's a slow, expensive degradation curve with a correctness cliff at the end.

---

## What actually goes into the window

Before you can budget it, you have to name it. Here is the anatomy of a context window, and for each component: who writes it, what it costs, and how it fails.

| Component | Who writes it | What it costs | Its failure mode |
|---|---|---|---|
| **System instructions** | You (the harness) | Fixed, per turn | Drift: drowned or contradicted by later text (M2 class 4) |
| **Tool definitions** | You (the harness) | Fixed, per turn | Steal attention from the task; bloated schemas |
| **Retrieved material** | Retrieval pipeline | Variable, per turn | Wrong/stale/irrelevant → grounding failure (M2 class 1) |
| **Conversation history** | The session (events) | Grows every turn | The biggest budget leak; irrelevant history buries the present |
| **Intermediate results** | Tool outputs, scratchpad | Variable | Verbose tool dumps; dead-end reasoning steps |

Two observations that should reframe how you see the window:

1. **Three of five components are fixed overhead** (instructions, tool definitions, and — in a naive agent — a stable prefix). Fixed overhead is where **caching** pays off (see below). Variable components are where **budgeting** pays off.
2. **The conversation history is the silent killer.** In a long session, most of the window ends up being *old turns* — and old turns are the least relevant thing in the room, yet they sit in the most expensive slot (every one of them re-sent every turn). This is exactly what *compaction* exists for (see below).

---

## Assembly discipline

Budgeting is necessary; *ordering and formatting* are where quality actually comes from. Three disciplines:

### 1. Stable prefix, variable tail

Structure the window so the **beginning never changes** and the **end changes every turn**. The beginning is your stable prefix: standing instructions, tool definitions, and (where sensible) the core policy. The end is the variable tail: this turn's retrieval, this turn's task, the latest few messages.

Why it matters twice over:
- **Caching** (below) only works on a stable prefix — if the whole window shifts every turn, nothing is cacheable.
- **Position bias** is real: the model attends best to the beginning and end. Your *standing policy* should live at the beginning (primacy); your *current task* should live at the end (recency); the middle should be the thing you keep small.

In ADK, `static_instruction` exists precisely for this — a way to amend the system instructions that persist across a session, keeping them in the stable prefix rather than re-sent as part of the mutable body.

### 2. Ordering effects are design inputs, not accidents

M2's position bias means *where* a fact sits changes whether it's used. The practical rule: **the thing that must not be forgotten goes at the end** (the current question, the hard constraint), **the thing that must persist goes at the beginning** (the policy), and **the supporting material goes in a clearly marked middle block** it can be told to cite. If a retrieved fact must be used, don't bury it at token 45,000 of a 90,000-token window — that is where facts go to die.

### 3. Formatting is information

The model is not a human reader; it is a *pattern-matching* reader. Structure that would be noise to a person is signal to it. Prefer:

```
## Retrieved evidence (cite these)
[1] <chunk>
[2] <chunk>

## Task
<the actual question>

## Constraints
- <hard limits>

## Format
<required output shape>
```

over a wall of prose where the task, the evidence, and the constraints are all one paragraph. Deterministic structure makes the model's job of *finding* the right thing cheaper — which is, in effect, more attention budget for the actual reasoning.

> **ADK at a glance:** the framework's `InvocationContext` (the object threaded through every run) is how your code and tools read the current session state; `static_instruction` is the knob for the stable instruction prefix; and the `Runner`/`run_async` loop is where the window gets assembled each turn. We'll go deep on the runtime in M16 — for now the point is architectural: *something* assembles the window every turn, and that something is a decision surface, not a black box.

---

## Prompt caching: what it is, and what it isn't

This is where the discussion-thread caveat from earlier earns its keep, because caching is the most persistently misunderstood idea in context engineering.

> **Caching changes how *efficiently* the context is sent and priced. It never changes *what content* the model sees.**

A prompt cache works like this: when you send a request, the model server caches a **prefix** of the prompt. On the next request, if the prefix is *identical*, the server doesn't re-process it — it reuses the cached computation. Result: lower latency, and the cached tokens are billed at a (much cheaper) cache-read rate.

The crucial fact, worth underlining: **cached and non-cached tokens are both fully in the model's context.** The model reads the same words either way. Caching is a *bill-splitting and latency* mechanism — it is not a content mechanism. It cannot "remove" or "forget" anything, and it cannot be the cause of a grounding failure (if nothing was retrieved, there is nothing to cache).

**The one way caching *does* bite correctness** is a **stale or wrong-key cache**: you cache a "retrieved evidence" block under the wrong key and serve the wrong chunk, or you cache a block past its expiry. That's a cache-*correctness* bug — a different failure from grounding, and one to keep on the radar precisely because caching is usually assumed harmless.

**How to design for cache hits:**
- Put the **stable, large** material first — the system instruction, tool schemas, any big static policy — so it forms a cacheable prefix.
- Keep the **variable** material (per-turn retrieval, the latest messages) *after* it.
- Don't interleave a changing token into the middle of the stable prefix — one changed token breaks the cache from that point on.

At the framework level, ADK exposes this for Gemini models as `ContextCacheConfig` on the `App`: `min_tokens` (don't bother caching tiny requests), `ttl_seconds` (how long the cache lives, default 1800), and `cache_intervals` (max uses before refresh, default 10). With **LiteLLM/Azure backends**, the same principle applies at the *provider* layer — your provider's prompt-caching feature keys off the stable prefix, and LiteLLM passes it through — so the design rule (stable prefix, variable tail) is identical even when the config knob lives elsewhere.

> **Tradeoff (the ledger entry):** caching is a *structure* reward — you get it only if you assemble the window with a stable prefix. That means accepting that some things (the instruction, the tool schemas) must be *fixed and ordered early* rather than free-form. You are trading a little assembly rigidity for a large cost/latency win. It is almost always worth it — but it is a decision you make, not a default you inherit.

---

## Context budgeting: the three dials

Now the spend side. When a session grows, you have three dials, and you turn them in this order:

### Dial 1 — the per-turn budget

Before anything, set a **ceiling**: the maximum number of tokens you will ever send in one call (e.g., "never assemble more than ~20k tokens for this agent"). This is the absolute safety net that stops the unbounded-growth failure. It is not a strategy by itself — it's the tripwire that tells you the other two dials must be turned.

### Dial 2 — eviction (what to drop first)

When you must shed tokens, drop in this order:

1. **Dead intermediate results** — failed tool attempts, abandoned scratchpad steps, superseded drafts.
2. **Verbose tool outputs** — truncate to the fields the task needs; store the full result in an artifact, keep a pointer.
3. **Old retrieved material** — evidence from turns ago, unless the current task still needs it.
4. **Compacted history** — summarize old turns (Dial 3) rather than keeping them verbatim.

And the two things you **never** evict: the **standing instruction** (that's your policy — losing it is how instruction drift happens) and the **current task/question**.

### Dial 3 — summarization-in-the-loop (compaction)

For the conversation history specifically, the right tool is **compaction**: periodically summarize older turns into a short running summary, keep only the recent few turns verbatim, and continue. It's lossy compression of the agent's memory — you trade *fidelity of old turns* for *attention and cost on the current turn*.

This is exactly what ADK's **context compaction** feature automates, via `EventsCompactionConfig` on the `App`, with two strategies:

- **Token-based (primary):** trigger when actual token volume crosses `token_threshold`, and keep the last `event_retention_size` events raw. This is the safety net for unpredictable workloads (a user pastes a 50k-token code block; a file upload floods the window).
- **Sliding-window (turn-based):** trigger every `compaction_interval` turns, with `overlap_size` prior events carried over for continuity. Predictable chats.

And you can supply a custom **`LlmEventSummarizer`** with a dedicated (often cheaper) model so compaction doesn't compete with the main task's model budget.

The honest caveat, because it's the whole point: **compaction is lossy, and its loss is invisible.** A summarized turn has dropped the exact wording, the exact numbers, the exact caveat — and the agent will not tell you it's reasoning from a lossy memory of its own past. Compaction is a *deliberate* acceptance of degraded history in exchange for attention on the present. Like every tradeoff in this course, it belongs in an ADR, not a config comment.

> **Failure mode (compaction):** summarizing away the *load-bearing* detail — the exact contract clause, the exact error message, the exact user requirement — while preserving the chit-chat. A naive summarizer keeps the narrative and drops the specifics; the agent then "remembers" the conversation without remembering any of the facts that mattered. The compaction prompt itself is a harness artifact that needs its own scrutiny.

---

## Beyond budgets: selecting by *content*, not position

The three dials above are all **positional** — they decide how much history to keep and how far back, not *which* turns matter to this question. But a user never says "give me turn 5" — they say *"remember when we discussed the Kunal Kamra Super-Thanks figure?"* or *"document the discussion from 'the problem with unions' through 'how to structure unions.'"* That is a different selector entirely: the assembly layer must resolve a **semantic reference** into the right turns, retrieve that span, and exclude what doesn't belong — *content-based selection*, not budget-based eviction.

This is where the "append everything, forever" default finally gets its full answer. **Session state is the source of truth** (the whole transcript); **the context window is a per-turn projection** of it; and **the assembly layer is the selector.** For the mechanism end to end — reference resolution, topic segmentation, span retrieval, relevance filtering, and the named systems that already do it (MemGPT/Letta, Zep, Mem0) — read the deep dive:

> **[Selective context assembly — the context window as a projection of session state](selective-context-assembly.md)** · the content-based selector, worked case by case, with the active-research frontier flagged honestly.

---

## Worked example: the research agent, budgeted

The domain spine, made concrete. A research agent runs a three-hour session over a corpus. Here's what actually accumulates, and how a designed context budget handles it:

- **Stable prefix (~4k tokens):** system instructions ("cite every claim; if evidence is absent, say so"), tool definitions, output format. *Cacheable — sent once, reused all session.*
- **Per-turn retrieval (~2–4k):** the top chunks for *this* question. *Fresh each turn; evicted after use.*
- **Tool results (variable):** a `fetch_paper` tool returns 8k tokens of full text; the harness keeps the abstract + relevant excerpt (~500 tokens) and stores the full text as an artifact. *Verbose output truncated at the seam.*
- **Conversation history:** compacted every ~6 turns into a running research-progress summary; the last 4 turns kept verbatim. *History costs stay flat instead of growing linearly.*
- **Scratchpad:** the agent's intermediate reasoning, *not* persisted into the window across turns — kept in working memory (M7) or regenerated when needed.

The result: at hour three, the window is ~10–12k tokens — not 90k — the current question sits at the end (recency), the policy sits at the start (primacy), and the three-hours-ago question is answered just as well as it was in minute one. **The agent didn't get dumber, because the window never got fat.**

> **Tradeoff (the ledger entry):** every budget mechanism costs *something*. Truncating tool output can drop a detail the next turn needs. Compacting history loses fidelity. A per-turn budget can force an eviction that was load-bearing. The discipline is not "keep the window small"; it is **"make each eviction and each compaction a named decision, with its cost written down"** — because the failure you're preventing (attention collapse, cost blowup) is invisible until it's catastrophic, while the failure you're causing (a dropped detail) is visible only much later, if ever.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the context budget for a three-hour research session, as in the worked example — but for **your own** agent (or choose a support agent over a 2,000-document knowledge base).

1. **Draw the anatomy.** List the five window components (instructions, tool definitions, retrieved material, history, intermediate results) and, for each: your target token size, and whether it's *stable* or *variable*.
2. **Order it.** Write the assembly order — what goes first, what goes last, what goes in the marked middle block — and justify it in one sentence against position bias.
3. **Set the dials.** State your per-turn budget (Dial 1), your eviction order (Dial 2, with the two things you'll never evict), and your compaction settings (Dial 3: token threshold + retention, or interval + overlap — pick one and justify).
4. **Name the loss you're accepting.** For your compaction choice, write the single most dangerous thing that could be summarized away, and one sentence about how you'd mitigate it (e.g., a "never summarize these fields" rule in the compactor prompt).
5. **Write the ADR.** Record the whole thing as a five-field ADR — "Context budget for the research agent" — with the consequence you're accepting stated explicitly.

**Why this exercise matters.** This is the first module where the deliverable is a *budget with a written rationale* rather than a piece of code. The instinct you're building — *name every component, order it deliberately, budget it, and record what the budget costs* — is the same instinct you'll apply to tools (M8), orchestration (M10), and evals (M12). Context is just the first place you practice it.

---

**In DSH:** prompt assembly is `core/system-prompt` (composable prompt sections + tool schemas), with `context`/`compaction` owning the budget and compaction — governed by the invariant *"model-visible means logged"* (everything the model sees must be reconstructable from the session log).

## Sources (ADK docs)

- [Agent context](https://adk.dev/context/index.md)
- [Context caching with Gemini](https://adk.dev/context/caching/index.md)
- [Compress agent context (compaction)](https://adk.dev/context/compaction/index.md)
- [Session, State & Memory](https://adk.dev/sessions/index.md)

---

**Next module:** [M5 — Context Engineering II: Retrieval & Grounding](../05-context-engineering-2/README.md) — now that we've budgeted the window, how do the *right* facts get into it, and how do we know they're right?
