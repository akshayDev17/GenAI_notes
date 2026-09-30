# M7 · Memory & State

> **Module question:** What does the agent remember, across what scope, and how is it kept correct?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a multi-turn onboarding/sales agent

---

## Contents

- [Opening scene — the agent that remembered the wrong thing](#opening-scene--the-agent-that-remembered-the-wrong-thing)
- [The memory taxonomy: seven types, two axes, four scopes](#the-memory-taxonomy-seven-types-two-axes-four-scopes)
- [Working memory: Session & State in ADK](#working-memory-session--state-in-adk)
- [Long-term memory: the MemoryService](#long-term-memory-the-memoryservice)
- [Prospective memory: remembering the future](#prospective-memory-remembering-the-future)
- [The loop: episodes become procedures](#the-loop-episodes-become-procedures)
- [The four failure modes: staleness, contradiction, leakage, recall](#the-four-failure-modes-staleness-contradiction-leakage-recall)
- [What memory should never hold](#what-memory-should-never-hold)
- [The write path — and forgetting on purpose](#the-write-path--and-forgetting-on-purpose)
- [Worked example: the onboarding/sales agent](#worked-example-the-onboardingsales-agent)
- [Design exercise](#design-exercise)
- [Where the literature disagrees](#where-the-literature-disagrees)
- [Sources (ADK docs)](#sources-adk-docs)
- [Bibliography](#bibliography)

---

## Opening scene — the agent that remembered the wrong thing

Two incidents, one week apart, same agent.

**First:** a sales agent greeted a returning customer by name, recalled their company size from last quarter, and confidently quoted a price — using the *old* headcount, not the one the customer had updated two weeks ago. The customer corrected it. The agent had *remembered*, and remembered *stale*.

**Second:** the same agent, in a *different* conversation with a *different* user, casually answered "your last order shipped to 12 Main Street" — an address that belonged to the *previous* user. The state had leaked across sessions.

Neither incident was "the model hallucinating." Both were **memory failures**[cemri-mast](#cemri-mast)[du-memory-agents](#du-memory-agents) — and both trace to the same root: the harness had no answer to *"what belongs in memory, at what scope, and how is it kept true?"* The agent remembered everything it had seen, for no principled reason, and the boundaries between "this session," "this user," and "everyone" were never drawn.

This module is about drawing them. Memory is not "remember more."[du-memory-agents](#du-memory-agents)[jamwithai-seven-types](#jamwithai-seven-types) Memory is **remember the right thing, at the right scope, and never the wrong user's thing.**

> **Failure mode (the module in one line):** treating memory as a feature to bolt on ("let's make it remember") instead of a *correctness* problem to design.[own-synthesis](#own-synthesis) Staleness, contradiction, leakage, and failed recall are not edge cases — they are the whole subject.[du-memory-agents](#du-memory-agents)[wu-longmemeval](#wu-longmemeval)

---

## The memory taxonomy: seven types, two axes, four scopes

Before the framework, the map. "Memory" is one word for several different things, and confusing them is the root cause of most memory bugs.[sumers-coala](#sumers-coala)[zhang-memory-mechanisms](#zhang-memory-mechanisms) Two axes separate them:

- **What is remembered** — working (this conversation), semantic (facts), episodic (what happened), procedural (how to do things).[sumers-coala](#sumers-coala)[tulving-episodic-semantic](#tulving-episodic-semantic)[squire-memory-systems](#squire-memory-systems)
- **Where it lives** — in the context window, in an external store you retrieve from, or in the model's weights.[packer-memgpt](#packer-memgpt)[du-rethinking-memory](#du-rethinking-memory)

Keep the axes apart and "just add a vector DB" stops looking like an answer. Semantic, episodic, and procedural describe *what*; retrieval and parametric describe *where*. A design that names only the first axis has quietly decided the second — usually by accident.[own-synthesis](#own-synthesis)

| Type | What it holds | Lifetime | Where it lives | ADK primitive |
|---|---|---|---|---|
| **Working / in-context** | The current conversation — messages, tool results, lookups — re-sent this turn, plus `State`, the scratchpad | One session | The prompt, rebuilt every turn | `Session` (events) + `State` |
| **Semantic**[tulving-episodic-semantic](#tulving-episodic-semantic)[tulving-episodic-mind-brain](#tulving-episodic-mind-brain) | *Facts*: user preferences, entities, "favorite project is X" | Long-term, searchable | An external store | `MemoryService` |
| **Episodic**[tulving-episodic-semantic](#tulving-episodic-semantic)[squire-memory-systems](#squire-memory-systems) | What *happened* across past sessions (events, transcripts, and any reflections distilled from them) | Long-term, searchable | An external store | `MemoryService` |
| **Procedural** (cf. [sumers-coala](#sumers-coala)[squire-memory-systems](#squire-memory-systems)) | How to *do* things: rules, skills, escalation policy | Static, versioned | The instruction | The instruction (M6), not memory |
| **External / retrieval**[du-rethinking-memory](#du-rethinking-memory)[asai-self-rag](#asai-self-rag) | Whatever you kept outside the window and fetched back: docs, records, prior runs | Long-term | The store itself (vector, SQL, documents, graph) + a retriever | Tools over `MemoryService` / RAG |
| **Parametric**[mallen-when-not-to-trust](#mallen-when-not-to-trust)[ovadia-finetuning-or-retrieval](#ovadia-finetuning-or-retrieval) | Everything learned in training: language, world knowledge, reasoning | Frozen at training time | The weights | The model itself — unmanaged |
| **Prospective**[einstein-prospective-memory](#einstein-prospective-memory)[liu-pm-bench](#liu-pm-bench) | What must happen *later*: follow-ups, retries, renewals | Until done or cancelled | A scheduler or task queue — **never** the `MemoryService` | Outside ADK (a scheduler you own) |

> where would memory related to "user specified constraints" associated with the [overlook constraints failure class](../02-model-failure-science/README.md#overlooked-constraints) reside?

Three observations that carry the module:

1. **Working memory and long-term memory have different failure modes.** Working memory fails by *overflow* (M4's budget problem — the session grows until it drowns).[modarressi-nolima](#modarressi-nolima)[hsieh-ruler](#hsieh-ruler) Long-term memory fails by *staleness, contradiction, leakage, and failed recall* (below).[du-memory-agents](#du-memory-agents)[wu-longmemeval](#wu-longmemeval) Design them separately; they are different diseases.
2. **Procedural memory is not memory at all** (cf. [sumers-coala](#sumers-coala)[squire-memory-systems](#squire-memory-systems)[huang-agent-memory-survey](#huang-agent-memory-survey)) — it's the instruction. Rules you want to *persist* should live in the instruction (static, versioned, tested), not in a searchable store where they can drift.[own-synthesis](#own-synthesis) (This is M6, restated: policy belongs in the constitution, not in a memory archive.)
3. **Stored is not the same as active.** Your database can hold an entire conversation, but the model cannot reason over a single byte of it until those bytes are back in the prompt.[sumers-coala](#sumers-coala)[packer-memgpt](#packer-memgpt) Storage is *potential*; working memory is what the model can actually use right now. This is why "it remembered!" is so often the wrong explanation: the constraint was never remembered, it was simply still being re-sent. Stop re-sending it and the "memory" vanishes.

**Parametric memory is a floor, not a feature.** It is the general-ability layer,[mallen-when-not-to-trust](#mallen-when-not-to-trust) and it is the one store you can neither timestamp, scope, correct,[cohen-ripple-effects](#cohen-ripple-effects)[yao-editing-llms](#yao-editing-llms) nor delete — which is exactly why anything specific, current, or private has to come from one of the other six. Note the shape of the table too: ADK's primitives cover three of the seven. Procedural is the instruction (M6), prospective is a scheduler, and parametric is the model itself — three types with no memory API at all, each of which breaks quietly the moment you treat it as if it had one.[own-synthesis](#own-synthesis)

---

## Working memory: Session & State in ADK

The working memory is the pair ADK calls **`Session`** and **`State`**:

- **`Session`** — one conversation thread: the chronological sequence of `Event`s (user messages, agent replies, tool calls). It *is* the history.
- **`State`** — the scratchpad: a key-value store the agent (and your code) reads and writes during the conversation. It's where "what step are we on," "what did the user just say their budget is," and "shopping cart items" live.

The single most important thing about state is its **scoping prefixes** — because scope is *the* memory design decision, and ADK encodes it in the key name:

| Prefix | Scope | Persists? | Use it for |
|---|---|---|---|
| *(none)* | This session | With a persistent `SessionService` | In-task progress, current-intent flags |
| `user:` | This user, across all their sessions | Yes | Preferences, profile ("user:theme", "user:name") |
| `app:` | This app, across all users | Yes | Global settings ("app:api_endpoint") |
| `temp:` | This invocation only | **No — discarded** | Intermediate values passed between tool calls |

Read that table as the answer to the leakage failure from the opening scene: **the address that leaked across users should never have been session-scoped or left un-prefixed.** Scope is not a storage detail — it is the *boundary* that determines whether one user can see another's data.[rezazadeh-collaborative-memory](#rezazadeh-collaborative-memory)[liu-authorization-before-context](#liu-authorization-before-context) A `user:`-prefixed key stays with that user; an un-prefixed key stays with that session; an `app:`-prefixed key is intentionally shared. Every state write should be a conscious choice of prefix, not a bare `state['x'] = ...`.

> **ADK at a glance:** update state the *right* way — inside a callback or tool, write to the context's `state` (`context.state['key'] = value`); the framework routes it into the event's `state_delta` and the `SessionService` persists it. Do **not** mutate `session.state` on a `SessionService`-retrieved session directly — that bypasses the event history, breaks persistence, and isn't thread-safe. `output_key` saves the agent's final response into state; `EventActions.state_delta` handles multi-key updates; and `{key}` templating injects state into the instruction (`"…focusing on the theme: {topic}"`, with `{topic?}` for optional).

---

## Long-term memory: the MemoryService

Working memory dies with the session. Long-term memory survives it — and that's the **`MemoryService`**, ADK's searchable archive for *episodic* and *semantic* knowledge. The interface has two sides:

- **Ingestion** — get knowledge *in*:
  - `add_session_to_memory(session)` — capture a completed session.
  - `add_events_to_memory(events)` — capture a *delta* (the latest turn) mid-session.
  - `add_memory(MemoryEntry(...))` — write an explicit fact directly.
- **Search** — get knowledge *out*: `search_memory(query)`, typically via a tool.

And two built-in retrieval tools, distinguished by *when* they fire:

- **`load_memory`** — the agent decides, mid-conversation, that it needs the past, and calls the tool.
- **`preload_memory`** — memory is pulled automatically at the start of each turn (a standing "you might need this" injection).

The retrieval design question — *preload vs. load-on-demand* — is the memory analog of M4's context budget: preloading spends context every turn on *maybe*-relevant memories; load-on-demand saves budget but only helps if the agent *knows* to ask.[asai-self-rag](#asai-self-rag)[mallen-when-not-to-trust](#mallen-when-not-to-trust) Preload when memory is small and always-relevant (a returning user's preferences); load-on-demand when memory is large and mostly-irrelevant (a long support history).

**Three implementations, three tradeoffs** (pick by what "memory" means to you):

| Service | Persistence | Retrieval | Use when |
|---|---|---|---|
| `InMemoryMemoryService` | None (lost on restart) | Keyword | Prototyping |
| `VertexAiMemoryBankService` | Yes (managed) | LLM-extracted + **consolidation**, semantic | You want the agent to *learn* and reconcile memories |
| `VertexAiRagMemoryService` | Yes | Vector search over raw transcripts | You already run RAG, or want raw retrieval |

The standout concept in the table is **consolidation** (Memory Bank's `enable_consolidation`): instead of appending "favorite color is light blue" as a *second* contradictory fact next to "favorite color is blue," the service *merges* them into one coherent memory.[du-rethinking-memory](#du-rethinking-memory)[chhikara-mem0](#chhikara-mem0)[rasmussen-zep](#rasmussen-zep) That is the direct answer to the *contradiction* failure mode — and it's the long-term analog of M4's compaction: both are *lossy reconciliation of history*, one for the working window, one for the archive.

> **ADK at a glance:** the memory workflow is a loop — *session concludes → `add_session_to_memory` (often via an `after_agent_callback`) → later, a new session asks something about the past → the agent calls `load_memory` → `search_memory` returns `MemoryEntry` objects (content + optional id/author/timestamp/custom_metadata) → the agent answers.* You can also wire a *second* memory service manually (e.g., one for conversations, one for a docs corpus) from a custom tool.

---

## Prospective memory: remembering the future

Every type above remembers the past or the present. A long-running agent needs one more: **what must happen later.**

- Follow up with the customer on Friday.
- Retry the job once the rate limit resets.
- Re-check the deployment after the monitoring data lands.
- Warn the user before their subscription renews.

The problem is structural, not stylistic: **a future task cannot wait inside the conversation.**[einstein-self-initiated-retrieval](#einstein-self-initiated-retrieval)[sellen-in-situ](#sellen-in-situ) The model is not running while it waits, and the session may be long gone by the time the moment arrives. So a prospective memory cannot be a state key the agent is trusted to check later, and it cannot be a `MemoryService` entry hoping some future `search_memory` call surfaces it. It has to live in a scheduler or a task queue — outside the model — as a durable record that answers five questions:[jamwithai-seven-types](#jamwithai-seven-types)[temporal-durable-execution](#temporal-durable-execution)

| Field | Question it answers | Failure if missing |
|---|---|---|
| **Action** | What should happen? | The timer fires and nothing knows what to do |
| **Trigger** | When, or on what event? | Fires at the wrong time, or never |
| **Resume state** | What context does the task need to pick back up? | The agent restarts from zero and re-asks the user everything |
| **Done flag** | How do we know it is finished? | It nags forever |
| **Approval** | Who authorizes the action? | A consequential action runs unattended (M15) |

> **Failure mode (the one the other three failure modes don't cover):** a prospective record that never fires (silent drop), fires repeatedly (no done flag), or fires without the state it needs.[liu-pm-bench](#liu-pm-bench)[zhang-triggerbench](#zhang-triggerbench) An overdue follow-up is not stale, contradictory, or leaked — it simply *didn't happen*, and nothing in the archive can tell you that.

> **ADK at a glance:** there is no `MemoryService` call here. Prospective memory is the harness's job — a scheduler, a queue, or a durable workflow engine (cron at the small end; a system built for long-delayed, reliable jobs at the other) — and the agent's interface to it is narrow: a tool that *writes* the record, and a callback that *resumes* the session when it fires.

---

## The loop: episodes become procedures

A store of past runs is an archive until something reads it. The step that makes memory *pay* is **reflection**: after a task completes, distill the episode into a short lesson — what worked, what didn't, what to do differently — and store *that* next to the run.[park-generative-agents](#park-generative-agents)[shinn-reflexion](#shinn-reflexion)[tan-reflective-memory](#tan-reflective-memory) The full transcript is for humans and for M16's traces; the lesson is what gets retrieved.

Reflection is also the bridge to procedural memory (M6). A pattern that shows up across episodes — *deployments keep failing because an environment variable was never set* — can be **promoted** into a standing rule in the instruction layer. That is how an agent improves without retraining:[shinn-reflexion](#shinn-reflexion)[wang-voyager](#wang-voyager)[zhao-expel](#zhao-expel) episodic memory is the evidence, procedural memory is the verdict.

Promotion is a policy decision, and both extremes are failures:

| Promotion policy | Failure |
|---|---|
| Never promote | The same lesson is re-derived forever; reflection has no consumer and the archive keeps growing |
| Promote from one episode | Turn one unlucky run into a permanent rule and you have taught the agent a bad habit it repeats every time[sumers-coala](#sumers-coala) |

So promotion needs a threshold (how many independent episodes?), a reviewer (the user? an eval — M12?), and — critically — a **retraction path**. Rules promoted into the instruction layer must be as easy to remove as they were to add, or a bad habit becomes permanent policy.[own-synthesis](#own-synthesis)

> **Tradeoff (the ledger entry):** **Learning vs. stability.** A system that promotes aggressively adapts fast and drifts; one that never promotes is deterministic and never improves.[sumers-coala](#sumers-coala)[wang-voyager](#wang-voyager)[zhao-expel](#zhao-expel) Set the threshold per rule class, and record who signed off.

---

## The four failure modes: staleness, contradiction, leakage, recall

This is the module's payload — the taxonomy of how memory *goes wrong*, each with its fix:[own-synthesis](#own-synthesis)

| Failure | What it is | Signature | Fix |
|---|---|---|---|
| **Staleness** | A stored fact is no longer true (old headcount, old address, old price) | The agent answers confidently from *last quarter's* data | Timestamps ("as of"), TTL/expiry, re-verify before use on consequential facts[du-memory-agents](#du-memory-agents)[wu-longmemeval](#wu-longmemeval)[rasmussen-zep](#rasmussen-zep) |
| **Contradiction** | Two memories disagree (preference changed; old record never removed) | The answer flips depending on *which* memory was retrieved | Consolidation (merge), write-with-overwrite policy, conflict detection → escalate[chhikara-mem0](#chhikara-mem0)[rasmussen-zep](#rasmussen-zep)[xu-knowledge-conflicts](#xu-knowledge-conflicts) |
| **Leakage** | Data crosses a scope boundary (user A's data visible to user B) | The agent quotes a *different user's* facts | Scope prefixes (`user:` / `app:` / session / `temp:`), never store secrets, retrieval scoped by user/app[rezazadeh-collaborative-memory](#rezazadeh-collaborative-memory)[liu-authorization-before-context](#liu-authorization-before-context)[gdpr](#gdpr) |
| **Recall failure** | The right memory exists but the wrong one comes back — or nothing does | The agent answers from an irrelevant episode, or claims not to know something you stored | Match the retrieval method to the query: vector search for *related*, exact lookup for a *specific fact*, filters for scope/permission, time for *when*, links for *relatedness* — and cap what you store in the first place[wu-longmemeval](#wu-longmemeval)[park-generative-agents](#park-generative-agents)[xu-amem](#xu-amem) |

The unifying insight: **memory is a source of truth, and the model treats it as one.**[du-memory-agents](#du-memory-agents)[xu-knowledge-conflicts](#xu-knowledge-conflicts) A stale memory is not "old data" — it is *wrongness that presents itself as rightness*, because the model has no reason to doubt its own memory (cf. [mallen-when-not-to-trust](#mallen-when-not-to-trust)[xie-adaptive-chameleon](#xie-adaptive-chameleon)). That's why the fixes are *mechanical* (timestamps, consolidation, scoping) rather than prompt-level ("remember to check if the address is current") — prose cannot keep a store correct; policy can.[unsupported](#unsupported)

Recall failure is not mainly a *volume* problem — it is a *distractor* problem. Adding random documents can improve accuracy; what damages it is the retriever's own highest-scoring, semantically related, answer-free documents.[cuconasu-power-of-noise](#cuconasu-power-of-noise) Position matters too: material buried mid-context is recalled worse than material at the edges.[liu-lost-in-the-middle](#liu-lost-in-the-middle) That is the same ledger entry as M4's, moved to the archive: storing more is never free.

---

## What memory should never hold

Because the model can retrieve whatever is in memory — and, once retrieved, may act on it or surface it — memory is an **exfiltration surface**[greshake-indirect-injection](#greshake-indirect-injection)[owasp-prompt-injection](#owasp-prompt-injection)[chen-agentpoison](#chen-agentpoison) (M14's territory, foreshadowed). Three things must never go in:

1. **Secrets.** API keys, tokens, credentials. Anything in memory is reachable by the model, and a reachable secret is a leaked secret.[carlini-extracting-training-data](#carlini-extracting-training-data)[lukas-pii-leakage](#lukas-pii-leakage) Secrets belong in a secrets manager, *outside* the model's reach, injected per-call — never in state or memory.
2. **Unverified facts.** A wrong fact stored today is a wrongness the model will *confidently* repeat forever. Only store what was verified at write time; everything else stays in the conversation, not the archive.
3. **PII without policy.** Personal data needs a retention policy, a consent basis, and a scope boundary — *before* it goes in.[gdpr](#gdpr) "Remember this for the user" without "for how long, under what consent, in what scope" is a governance failure waiting to happen (M15).

The rule of thumb: **write to memory only what you would be willing to have the agent state to that user, later, with full confidence — and only under a scope you can defend.**

---

## The write path — and forgetting on purpose

The never-store list is the negative half of the policy. The positive half is a **write path**, and it is a harness component with its own failure modes, not a `state['x'] = ...` afterthought.

Four stages, each of which can be skipped and shouldn't be:

1. **Extraction** — something reads the conversation and decides what is worth saving. In practice that "something" is usually the model itself, which means extraction inherits the model's judgment: it will save a one-off as a preference (*"keep it short today"* → *"always wants short answers"*), and it will save things that were never true. Extraction output is a **candidate**, not a write.[du-memory-agents](#du-memory-agents)[chhikara-mem0](#chhikara-mem0)
2. **Validation** — was this verified *this turn*, by a tool or by the user, or is it the model's paraphrase? Only verified facts get a timestamp and a scope; everything else stays in the conversation, where it costs nothing and expires on its own.[du-memory-agents](#du-memory-agents)
3. **Update** — a write must be able to *replace*. A store with no overwrite path is how contradiction happens: "headcount 35" and "headcount 40" coexist, and which one wins depends on which one retrieval happened to rank higher.[du-rethinking-memory](#du-rethinking-memory)[chhikara-mem0](#chhikara-mem0)
4. **Deletion** — the stage everyone skips. Deletion is what makes the rest real: TTL on facts that decay, a retention window on PII and on episodic transcripts, and an explicit path for a user who withdraws consent (M15).[du-rethinking-memory](#du-rethinking-memory)[gdpr](#gdpr)[bourtoule-machine-unlearning](#bourtoule-machine-unlearning) A `MemoryService` interface with `add_*` and `search_memory` and no delete is a store that can only accumulate.

**Forgetting is a design act, not a garbage-collection detail.**[du-memory-agents](#du-memory-agents)[du-rethinking-memory](#du-rethinking-memory)[zhong-memorybank](#zhong-memorybank) A store that only grows gets slower and more expensive to search — and it keeps answering from facts that should have expired two quarters ago. The one-off-vs-lasting test from extraction is the same test as the never-store rule of thumb: write what you would be willing to have the agent state to that user, later, with full confidence — *and* be willing to defend keeping.

> **Tradeoff (the ledger entry):**
> - **Recall precision vs. archive completeness.** Every fact you store competes for the same retrieval slots, and the near-misses are the dangerous ones. Prune on purpose, not never.[du-memory-agents](#du-memory-agents)[cuconasu-power-of-noise](#cuconasu-power-of-noise)
> - **Retention vs. auditability.** Short TTLs protect users and cost you the ability to explain what the agent knew last month. Choose per data class, not per system.[rasmussen-zep](#rasmussen-zep)[gdpr](#gdpr)
> - **Model-driven extraction vs. deterministic capture.** Letting the model decide what is worth saving scales; it also imports the model's judgment into your source of truth. Deterministic rules are auditable and blind.[du-memory-agents](#du-memory-agents)[chhikara-mem0](#chhikara-mem0)[rasmussen-zep](#rasmussen-zep)

---

## Worked example: the onboarding/sales agent

The domain spine, made concrete. The agent runs multi-turn onboarding and later handles sales. Here's a designed memory schema:

**Working memory (state), by prefix:**
```python
# session-scoped (this conversation only)
"current_step"          # onboarding step: 'needs' -> 'budget' -> 'signup'
"collected_needs"       # list gathered this session

# user-scoped (this customer, across all their sessions)
"user:company_name"
"user:headcount"        # <- the stale fact from the opening scene
"user:preferred_channel"
"user:last_headcount_updated_at"   # <- the timestamp that fixes staleness

# temp (this invocation only)
"temp:raw_crm_response" # discarded after the turn; never leaks forward
```

```python
# NOT state: a prospective record lives in the scheduler, not the scratchpad.
# The agent writes it once and stops thinking about it; the scheduler owns the clock.
followup = {
    "action":   "send_quote_followup",
    "trigger":  "2026-09-26T14:00:00Z",   # or an event: "quote_viewed"
    "resume":   {"quote_id": "q_8812"},   # enough to pick the task back up cold
    "done":     False,                    # so it fires once, not forever
    "approval": "account_owner",          # who signs off before it sends
}
```

**Long-term memory (write policy):**
- On session end, `add_session_to_memory` (episodic — what happened), plus a short *reflection* of what worked and what didn't; the summary is what retrieval will actually surface.
- Explicit *semantic* facts (`user:headcount`) written only when *verified* this turn, always with a timestamp.
- Consolidation on, so "headcount 40" replaces "headcount 35" instead of joining it as a contradiction.
- Retention set per class: PII and transcripts expire on a window; `user:preferred_channel` effectively doesn't.

**Not in memory at all:**
- Pricing rules, the product catalogue, and the reimbursement limit come from a tool call against the system of record — not from the model's weights, and not from the archive. The model knowing *how* pricing works in general is parametric memory; the *actual* price is not.

**The failures, prevented:**
- *Staleness:* before quoting headcount, the agent checks `user:last_headcount_updated_at` against a freshness window; if stale, it asks instead of asserting.[du-memory-agents](#du-memory-agents)[rasmussen-zep](#rasmussen-zep)
- *Contradiction:* consolidation merges the preference changes; no two "headcount" facts coexist.[chhikara-mem0](#chhikara-mem0)
- *Leakage:* the address is `user:`-scoped — user B's session cannot see user A's address, because the key is scoped to user A.[rezazadeh-collaborative-memory](#rezazadeh-collaborative-memory)
- *Recall failure:* pricing is an exact lookup by SKU, not a vector search, so "find something similar" cannot substitute a neighbouring product's price.[wu-longmemeval](#wu-longmemeval)[cuconasu-power-of-noise](#cuconasu-power-of-noise)
- *Prospective:* the quote follow-up is a scheduler record with a trigger, a done flag, and an approval field — the agent never has to *remember* to check, and the record outlives the session.[liu-pm-bench](#liu-pm-bench)[temporal-durable-execution](#temporal-durable-execution)

The point, restated: the schema is not a database diagram — it is a *set of scope, freshness, and retention decisions*, and each one maps to a failure it prevents.[own-synthesis](#own-synthesis) That is what "memory design" means.

> **Tradeoff (the ledger entry):**
> - **Remember more vs. retrieve correctly.** Every fact you store competes for the same retrieval slots (more memory → more near-misses) and adds staleness risk. Store the *few* facts that matter, not everything.[du-memory-agents](#du-memory-agents)[cuconasu-power-of-noise](#cuconasu-power-of-noise)
> - **Persistence vs. leakage.** Persistence buys continuity; it also buys the possibility of cross-scope leakage. Every persistent key needs a scope prefix and a justification.[rezazadeh-collaborative-memory](#rezazadeh-collaborative-memory)[gdpr](#gdpr)
> - **Consolidation vs. fidelity.** Consolidation (like compaction) trades exact history for coherence. You accept some loss of detail so the archive stays *consistent* — record that acceptance.[du-rethinking-memory](#du-rethinking-memory)[chhikara-mem0](#chhikara-mem0)
> - **Acting now vs. acting later.** A prospective record buys follow-through across sessions, and it buys unattended action at a time nobody is watching — which is exactly why the record carries an approval field.[liu-pm-bench](#liu-pm-bench)[temporal-durable-execution](#temporal-durable-execution)

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the session + long-term memory schema for a multi-turn agent of your choice (or use the sales-agent brief above). Produce:

1. **The state schema.** List the keys you'd store, each with its **scope prefix** (`session`, `user:`, `app:`, or `temp:`) and a one-line justification. For each `user:` key, add a freshness field (a "last updated" timestamp) or state *why* it doesn't need one. Then list any **prospective records** (action, trigger, resume state, done flag, approval) and say where each lives, since none of them belong in state.
2. **The long-term memory policy.** What goes into the `MemoryService` (episodic vs. semantic), *when* it's written (session end? every turn?), and *how* it's retrieved (`load_memory` on demand vs. `preload_memory` every turn) — and why, in one sentence. Name the **retrieval method** per query type: what is a vector search, what is an exact lookup, what needs a filter or a time bound.
3. **The four failure modes, concretely.** For staleness, contradiction, leakage, and recall failure: write the specific scenario in *your* domain, and name the schema decision that prevents it. If a prevention is missing, flag it — that's the point.
4. **The never-store list.** Name three things your agent must *not* put in memory, and where each belongs instead (secrets manager, ephemeral context, etc.).
5. **The forgetting policy.** For each class of data you're keeping, state its lifetime (TTL, retention window, or "until the user says otherwise") and what triggers deletion. Then state which episodes get **reflected** into a lesson, and the threshold and approver for **promoting** a lesson into a rule.
6. **Write the ADR.** "Memory scope, freshness & forgetting policy" — the scoping rule, the consolidation choice, the promotion threshold, and the residual risk you're accepting.

**Why this exercise matters.** Memory is where the harness stops being a stateless function and becomes something that *persists* — and persistence is a correctness and governance commitment, not a checkbox. The schema you just designed is the difference between an agent that remembers *helpfully* and one that remembers *stale, contradictory, and leaking* facts, can't find the one that mattered, and forgets to act on it anyway.

---

**In DSH:** memory is `core/session` (the append-only `SessionEvent` log — the single source of truth), with `storage` for persistence and `scope` for per-agent registration boundaries (the analog of this module's `user:`/`app:` scoping). Prospective memory is not a store at all: its analog is the background-job and goal machinery — work that outlives the turn and is resumed by the harness, rather than remembered by the model.

## Where the literature disagrees

Three points where the sources contradict this module, each with the correction it implies.

1. **Procedural memory is not a memory type here — the literature says it is.** The taxonomy table files procedural memory as "the instruction, not memory." Cognitive science does not: [squire-memory-systems](#squire-memory-systems) places skills and habits under nondeclarative *long-term memory*, and [sumers-coala](#sumers-coala) — this module's own cited taxonomy source — defines procedural memory as having two forms, "implicit knowledge stored in the LLM weights, and explicit knowledge written in the agent's code," and synthesises the prompt per call out of *working* memory. [huang-agent-memory-survey](#huang-agent-memory-survey) states the definition plainly: procedural memory is "a form of long-term memory dedicated to how to perform tasks." **The correction:** keep the engineering prescription — versioned policy belongs in the instruction — but drop the categorical claim, and note that the separate *Parametric* row duplicates CoALA's procedural slot rather than complementing it.

2. **"Noise degrades recall" is backwards as stated.** [cuconasu-power-of-noise](#cuconasu-power-of-noise) finds that adding **random** documents *improves* accuracy by up to 35%; what damages it is the retriever's own highest-scoring, semantically related, answer-free documents. [liu-lost-in-the-middle](#liu-lost-in-the-middle) is likewise a *positional* result — the beginning and end of a context are recalled better than the middle — not evidence that long or noisy context is worse. **The correction:** the worked example's fix (an exact lookup by SKU rather than a vector search) is the correct instance of the *distractor* problem and stands; the general dilution claim does not, and has been rewritten onto the distractor finding.

3. **"The model has no reason to doubt its own memory" is one side of a two-sided story.** [xie-adaptive-chameleon](#xie-adaptive-chameleon) finds LLMs "highly receptive to external evidence even when that conflicts with their parametric memory" when the evidence is coherent, balanced by a strong confirmation bias when it only partly agrees; [mallen-when-not-to-trust](#mallen-when-not-to-trust) finds parametric memory competitive on popular facts, which is why retrieval should be conditional. **The correction:** state the range, not the endpoint — the model's failure is that it cannot tell a stale memory from a current one, not that it never doubts one.

A fourth, softer point: the ledger's "recall gets worse as you succeed" asserted a precision-versus-size curve that no located source measures. That sentence has been rewritten; the residual maxim is recorded in [unsupported](#unsupported).

---

## Sources (ADK docs)

- [Session, State & Memory — concepts](https://adk.dev/sessions/index.md)
- [State: the session's scratchpad (prefixes, update paths, `{key}` templating)](https://adk.dev/sessions/state/index.md)
- [Memory: long-term knowledge with MemoryService](https://adk.dev/sessions/memory/index.md)

---

## Bibliography

*Literature behind the module's claims, with the framework documentation the module itself cites. **Citations use stable identifier keys, not position numbers.** Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed, or reordered without rewriting a single citation — the BibTeX model, minus a backend to assign numbers. The bibliography is therefore an unordered bullet list, not a ranked one: the order of entries carries no meaning, and no entry's identity changes if you move it. Every entry hyperlinks to the source itself — the open PDF where one exists; the one print-only item says so rather than faking a link. Items tagged (industry doc) are vendor or project documentation, (preprint) are not yet peer-reviewed, and (own synthesis) are the module's inferences rather than sourced claims. `cf.` marks a source that qualifies or contradicts the sentence it follows. `unsupported` is the module's unsupported-claims bucket and `own-synthesis` collects the course's own un-sourced synthesis: anything asserted above that no located source supports is cited there rather than to an invented reference.*

### Surveys, framings, and failure taxonomies

- <a id="cemri-mast"></a>[cemri-mast](#cemri-mast) · [**Why Do Multi-Agent LLM Systems Fail?** — Mert Cemri, Melissa Z. Pan, Shuyi Yang, Lakshya A. Agrawal, Bhavya Chopra, Rishabh Tiwari, Kurt Keutzer, Aditya Parameswaran, Dan Klein, Kannan Ramchandran, Matei Zaharia, Joseph E. Gonzalez, Ion Stoica](https://arxiv.org/pdf/2503.13657) — *NeurIPS*, 2025 (arXiv:2503.13657). Owns MAST, the taxonomy derived from 200+ traces across seven multi-agent systems (41%–86.7% failure rates), and the finding that failure "is not merely a function of challenges in the underlying model" — the evidence that these are system-design failures rather than model failures.
- <a id="du-memory-agents"></a>[du-memory-agents](#du-memory-agents) · [**Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers** — Pengfei Du](https://arxiv.org/pdf/2603.07670) — arXiv:2603.07670, 2026 (preprint). Treats agent memory as an engineering discipline: the write path, a risk analysis mapping memory failure modes onto downstream consequences, temporal versioning, and per-user access scoping.
- <a id="du-rethinking-memory"></a>[du-rethinking-memory](#du-rethinking-memory) · [**Rethinking Memory in LLM based Agents: Representations, Operations, and Emerging Topics** — Yiming Du, Wenyu Huang, Danna Zheng, Zhaowei Wang, Sebastien Montella, Mirella Lapata, Kam-Fai Wong, Jeff Z. Pan](https://arxiv.org/pdf/2505.00675) — arXiv:2505.00675, 2025 (preprint). Reorganises agent memory into representations, operations, and emerging topics — six core operations (consolidation, updating, indexing, forgetting, retrieval, condensation) and the parametric/contextual split this module's second axis rests on.
- <a id="zhang-memory-mechanisms"></a>[zhang-memory-mechanisms](#zhang-memory-mechanisms) · [**A Survey on the Memory Mechanism of Large Language Model based Agents** — Zeyu Zhang, Xiaohe Bo, Chen Ma, Rui Li, Xu Chen, Quanyu Dai, Jieming Zhu, Zhenhua Dong, Ji-Rong Wen](https://arxiv.org/pdf/2404.13501) — *ACM TOIS*, 2025 (arXiv:2404.13501, 2024). The memory-mechanism survey: memory sources, forms, and operations across LLM agents, plus the evaluation landscape.
- <a id="huang-agent-memory-survey"></a>[huang-agent-memory-survey](#huang-agent-memory-survey) · [**A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents** — Wei-Chieh Huang, Weizhi Zhang, Yueqing Liang, Yuanchen Bei, Yankai Chen, Tao Feng, Xinyu Pan, Zhen Tan, Yu Wang, Tianxin Wei, Shanglin Wu, Ruiyao Xu, Liangwei Yang, Rui Yang, Wooseong Yang, Chin-Yuan Yeh, Hanrong Zhang, Haozhen Zhang, Siqi Zhu, Henry Peng Zou, Wanjia Zhao, Song Wang, Wujiang Xu, Zixuan Ke, Zheng Hui, Dawei Li, Yaozu Wu, Langzhou He, Chen Wang, Xiongxiao Xu, Baixiang Huang, Juntao Tan, Shelby Heinecke, Huan Wang, Caiming Xiong, Ahmed A. Metwally, Jun Yan, Chen-Yu Lee, Hanqing Zeng, Yinglong Xia, Xiaokai Wei, Ali Payani, Yu Wang, Haitong Ma, Wenya Wang, Chenguang Wang, Yu Zhang, Xin Eric Wang, Yongfeng Zhang, Jiaxuan You, Hanghang Tong, Xiao Luo, Xue Liu, Yizhou Sun, Wei Wang, Julian McAuley, James Zou, Jiawei Han, Philip S. Yu, Kai Shu](https://arxiv.org/pdf/2602.06052) — *TMLR*, 2026 (arXiv:2602.06052). *cf.* Maps agent memory onto cognitive mechanisms (sensory, working, episodic, semantic, procedural) and defines procedural memory as "a form of long-term memory dedicated to how to perform tasks" — the definition this module's taxonomy table contradicts.

### Cognitive foundations: the memory systems the taxonomy borrows from

- <a id="sumers-coala"></a>[sumers-coala](#sumers-coala) · [**Cognitive Architectures for Language Agents** — Theodore R. Sumers, Shunyu Yao, Karthik Narasimhan, Thomas L. Griffiths](https://arxiv.org/pdf/2309.02427) — *TMLR*, 2024 (arXiv:2309.02427). *cf.* Owns the cognitive-architecture taxonomy: one short-term working memory plus episodic, semantic, and procedural long-term memories. Defines procedural memory as **two** forms — "implicit knowledge stored in the LLM weights, and explicit knowledge written in the agent's code" — and synthesises the prompt per call out of working memory. This is why the module's separate "parametric" row duplicates CoALA's procedural slot.
- <a id="tulving-episodic-semantic"></a>[tulving-episodic-semantic](#tulving-episodic-semantic) · **Episodic and semantic memory** — Endel Tulving — In Endel Tulving & Wayne Donaldson (eds.), *Organization of Memory* (pp. 381–403), Academic Press, 1972. (print; no open copy located) Owns the episodic/semantic distinction. Cited upstream of every modern agent-memory taxonomy; the chapter predates DOIs, so no open link exists.
- <a id="tulving-episodic-mind-brain"></a>[tulving-episodic-mind-brain](#tulving-episodic-mind-brain) · [**Episodic Memory: From Mind to Brain** — Endel Tulving](https://doi.org/10.1146/annurev.psych.53.100901.135114) — *Annual Review of Psychology*, 53, 1–25, 2002. Tulving's own retrospective on the episodic system he introduced in 1972 — the citable, linkable statement of the same distinction.
- <a id="squire-memory-systems"></a>[squire-memory-systems](#squire-memory-systems) · [**Memory systems of the brain: A brief history and current perspective** — Larry R. Squire](https://doi.org/10.1016/j.nlm.2004.06.005) — *Neurobiology of Learning and Memory*, 82(3), 171–177, 2004. *cf.* Owns the declarative/nondeclarative architecture that files skills and habits under long-term memory — i.e. procedural memory *is* memory, which the module's "not memory at all" claim denies.

### The working window: capacity, context, and what survives it

- <a id="packer-memgpt"></a>[packer-memgpt](#packer-memgpt) · [**MemGPT: Towards LLMs as Operating Systems** — Charles Packer, Sarah Wooders, Kevin Lin, Vivian Fang, Shishir G. Patil, Ion Stoica, Joseph E. Gonzalez](https://arxiv.org/pdf/2310.08560) — arXiv:2310.08560, 2023 (preprint). Owns virtual context management: the window treated as fast memory with data paged between tiers, resting on the premise that the model sees only what is currently resident.
- <a id="modarressi-nolima"></a>[modarressi-nolima](#modarressi-nolima) · [**NoLiMa: Long-Context Evaluation Beyond Literal Matching** — Ali Modarressi, Hanieh Deilamsalehy, Franck Dernoncourt, Trung Bui, Ryan A. Rossi, Seunghyun Yoon, Hinrich Schütze](https://arxiv.org/pdf/2502.05167) — *ICML*, 2025 (arXiv:2502.05167). Owns the finding that long-context collapse is not a literal-matching artefact: at 32K, 11 models fall below 50% of their strong short-length baselines.
- <a id="hsieh-ruler"></a>[hsieh-ruler](#hsieh-ruler) · [**RULER: What's the Real Context Size of Your Long-Context Language Models?** — Cheng-Ping Hsieh, Simeng Sun, Samuel Kriman, Shantanu Acharya, Dima Rekesh, Fei Jia, Yang Zhang, Boris Ginsburg](https://arxiv.org/pdf/2404.06654) — *COLM*, 2024 (arXiv:2404.06654). Owns the measured gap between advertised and usable context: models claiming 32K+ context, of which only half maintain satisfactory performance at 32K.
- <a id="liu-lost-in-the-middle"></a>[liu-lost-in-the-middle](#liu-lost-in-the-middle) · [**Lost in the Middle: How Language Models Use Long Contexts** — Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang](https://arxiv.org/pdf/2307.03172) — *TACL*, 12, 157–173, 2024 (arXiv:2307.03172). *cf.* Owns positional sensitivity: information at the beginning or end of a context is recalled better than information in the middle. Routinely over-read as "long or noisy context is worse" — it is a position result, not a volume result.

### Parametric memory: what the weights hold, and what they cannot be told

- <a id="mallen-when-not-to-trust"></a>[mallen-when-not-to-trust](#mallen-when-not-to-trust) · [**When Not to Trust Language Models: Investigating Effectiveness of Parametric and Non-Parametric Memories** — Alex Mallen, Akari Asai, Victor Zhong, Rajarshi Das, Daniel Khashabi, Hannaneh Hajishirzi](https://arxiv.org/pdf/2212.10511) — *ACL*, 2023 (arXiv:2212.10511). *cf.* Owns the conditional-retrieval result: unassisted LMs stay competitive on high-popularity entities while retrieval dominates elsewhere, so retrieval should not be unconditional. The counterweight to "the model trusts its own memory."
- <a id="ovadia-finetuning-or-retrieval"></a>[ovadia-finetuning-or-retrieval](#ovadia-finetuning-or-retrieval) · [**Fine-Tuning or Retrieval? Comparing Knowledge Injection in LLMs** — Oded Ovadia, Menachem Brief, Moshik Mishaeli, Oren Elisha](https://arxiv.org/pdf/2312.05934) — arXiv:2312.05934, 2023 (preprint). Owns the comparison: RAG outperforms unsupervised fine-tuning for both existing and entirely new knowledge, and LLMs "struggle to learn new factual information through unsupervised fine-tuning."
- <a id="cohen-ripple-effects"></a>[cohen-ripple-effects](#cohen-ripple-effects) · [**Evaluating the Ripple Effects of Knowledge Editing in Language Models** — Roi Cohen, Eden Biran, Ori Yoran, Amir Globerson, Mor Geva](https://doi.org/10.1162/tacl_a_00644) — *TACL*, 12, 283–298, 2024. Owns the ripple effect: editing one fact fails to introduce consistent changes elsewhere in the model, and a simple in-context editing baseline outperforms the editing methods.
- <a id="yao-editing-llms"></a>[yao-editing-llms](#yao-editing-llms) · [**Editing Large Language Models: Problems, Methods, and Opportunities** — Yunzhi Yao, Peng Wang, Bozhong Tian, Siyuan Cheng, Zhoubo Li, Shumin Deng, Huajun Chen, Ningyu Zhang](https://arxiv.org/pdf/2305.13172) — *EMNLP*, 2023 (arXiv:2305.13172). Owns the limits of model editing on portability, locality, and efficiency — the negative results behind "you cannot surgically correct the weights."

### Retrieval and recall quality

- <a id="asai-self-rag"></a>[asai-self-rag](#asai-self-rag) · [**Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection** — Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi](https://arxiv.org/pdf/2310.11511) — *ICLR*, 2024 (arXiv:2310.11511, 2023). Owns learned on-demand retrieval: the critique of retrieving "regardless of whether retrieval is necessary," and self-reflection tokens that gate it.
- <a id="cuconasu-power-of-noise"></a>[cuconasu-power-of-noise](#cuconasu-power-of-noise) · [**The Power of Noise: Redefining Retrieval for RAG Systems** — Florin Cuconasu, Giovanni Trappolini, Federico Siciliano, Simone Filice, Cesare Campagnano, Yoelle Maarek, Nicola Tonellotto, Fabrizio Silvestri](https://arxiv.org/pdf/2401.14887) — *SIGIR*, 2024 (arXiv:2401.14887). *cf.* Owns the counter-intuitive result this module's recall-failure discussion turns on: adding **random** documents improves accuracy by up to 35%, while the retriever's own highest-scoring, semantically related, answer-free documents are what damage it. Distractors, not noise.
- <a id="wu-longmemeval"></a>[wu-longmemeval](#wu-longmemeval) · [**LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory** — Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang, Dong Yu](https://arxiv.org/pdf/2410.10813) — *ICLR*, 2025 (arXiv:2410.10813). Owns the long-term-memory benchmark and its five abilities — including knowledge updates and abstention — and the ~30% accuracy drop across sustained interactions.

### Long-term memory systems: consolidation, staleness, contradiction

- <a id="chhikara-mem0"></a>[chhikara-mem0](#chhikara-mem0) · [**Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory** — Prateek Chhikara, Dev Khant, Saket Aryan, Taranjeet Singh, Deshraj Yadav](https://arxiv.org/pdf/2504.19413) — arXiv:2504.19413, 2025 (preprint). Owns the extraction/update pipeline with explicit ADD, UPDATE, DELETE, and NOOP operations — DELETE defined as "removal of memories contradicted by new information."
- <a id="rasmussen-zep"></a>[rasmussen-zep](#rasmussen-zep) · [**Zep: A Temporal Knowledge Graph Architecture for Agent Memory** — Preston Rasmussen, Pavlo Paliychuk, Travis Beauvais, Jack Ryan, Daniel Chalef](https://arxiv.org/pdf/2501.13956) — arXiv:2501.13956, 2025 (preprint). Owns the bi-temporal memory graph: valid/invalid intervals on the event timeline and created/expired on the transactional one, with LLM-detected contradictions invalidating the affected edges.
- <a id="xu-amem"></a>[xu-amem](#xu-amem) · [**A-MEM: Agentic Memory for LLM Agents** — Wujiang Xu, Zujie Liang, Kai Mei, Hang Gao, Juntao Tan, Yongfeng Zhang](https://arxiv.org/pdf/2502.12110) — *NeurIPS*, 2025 (arXiv:2502.12110). Owns Zettelkasten-style dynamic indexing: memories linked and reorganised rather than appended, with link-following as a retrieval mode.
- <a id="zhong-memorybank"></a>[zhong-memorybank](#zhong-memorybank) · [**MemoryBank: Enhancing Large Language Models with Long-Term Memory** — Wanjun Zhong, Lianghong Guo, Qiqi Gao, He Ye, Yanlin Wang](https://arxiv.org/pdf/2305.10250) — *AAAI*, 38(17), 19724–19731, 2024 (arXiv:2305.10250). Owns the Ebbinghaus-inspired forgetting and reinforcement mechanism — memory strength decaying with elapsed time and relative significance.
- <a id="xu-knowledge-conflicts"></a>[xu-knowledge-conflicts](#xu-knowledge-conflicts) · [**Knowledge Conflicts for LLMs: A Survey** — Rongwu Xu, Zehan Qi, Zhijiang Guo, Cunxiang Wang, Hongru Wang, Yue Zhang, Wei Xu](https://arxiv.org/pdf/2403.08319) — *EMNLP*, 2024, pp. 8541–8565 (arXiv:2403.08319). The survey of knowledge conflict: context–memory, inter-context, and intra-memory conflict as first-class phenomena, with the behaviours and solutions proposed for each.
- <a id="xie-adaptive-chameleon"></a>[xie-adaptive-chameleon](#xie-adaptive-chameleon) · [**Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts** — Jian Xie, Kai Zhang, Jiangjie Chen, Renze Lou, Yu Su](https://arxiv.org/pdf/2305.13300) — *ICLR*, 2024 (Spotlight) (arXiv:2305.13300). *cf.* Owns the two-sided evidence: LLMs are "highly receptive to external evidence even when that conflicts with their parametric memory" when that evidence is coherent, while showing strong confirmation bias when it only partly agrees.

### Reflection and promotion: episodes become procedures

- <a id="park-generative-agents"></a>[park-generative-agents](#park-generative-agents) · [**Generative Agents: Interactive Simulacra of Human Behavior** — Joon Sung Park, Joseph C. O'Brien, Carrie J. Cai, Meredith Ringel Morris, Percy Liang, Michael S. Bernstein](https://arxiv.org/pdf/2304.03442) — *UIST*, 2023 (arXiv:2304.03442). Owns the memory stream with reflection: records synthesised over time into higher-level reflections, retrieved by a combined relevance/recency/importance score.
- <a id="shinn-reflexion"></a>[shinn-reflexion](#shinn-reflexion) · [**Reflexion: Language Agents with Verbal Reinforcement Learning** — Noah Shinn, Federico Cassano, Edward Berman, Ashwin Gopinath, Karthik Narasimhan, Shunyu Yao](https://arxiv.org/pdf/2303.11366) — *NeurIPS*, 2023 (arXiv:2303.11366). Owns verbal reinforcement: self-reflections stored and reused across trials to improve performance with no weight updates. The buffer is bounded and persists across trials of the same task, not as durable cross-task memory.
- <a id="tan-reflective-memory"></a>[tan-reflective-memory](#tan-reflective-memory) · [**In Prospect and Retrospect: Reflective Memory Management for Long-term Personalized Dialogue Agents** — Zhen Tan, Jun Yan, I-Hung Hsu, Rujun Han, Zifeng Wang, Long T. Le, Yiwen Song, Yanfei Chen, Hamid Palangi, George Lee, Anand Iyer, Tianlong Chen, Huan Liu, Chen-Yu Lee, Tomas Pfister](https://arxiv.org/pdf/2503.08026) — *ACL*, 2025 (arXiv:2503.08026). Owns reflective memory management: interactions summarised across utterances, turns, and sessions into a personalised memory bank.
- <a id="wang-voyager"></a>[wang-voyager](#wang-voyager) · [**Voyager: An Open-Ended Embodied Agent with Large Language Models** — Guanzhi Wang, Yuqi Xie, Yunfan Jiang, Ajay Mandlekar, Chaowei Xiao, Yuke Zhu, Linxi Fan, Anima Anandkumar](https://arxiv.org/pdf/2305.16291) — *TMLR*, 2024 (arXiv:2305.16291). Owns the skill library: an ever-growing set of verified, executable, composable skills that "bypass[es] the need for model parameter fine-tuning." Promotion has no demotion counterpart.
- <a id="zhao-expel"></a>[zhao-expel](#zhao-expel) · [**ExpeL: LLM Agents Are Experiential Learners** — Andrew Zhao, Daniel Huang, Quentin Xu, Matthieu Lin, Yong-Jin Liu, Gao Huang](https://arxiv.org/pdf/2308.10144) — *AAAI*, 2024 (arXiv:2308.10144). Owns experiential learning: natural-language insights extracted from gathered trajectories and recalled at inference "without requiring parametric updates."

### Prospective memory: remembering to act later

- <a id="einstein-prospective-memory"></a>[einstein-prospective-memory](#einstein-prospective-memory) · [**Normal aging and prospective memory** — Gilles O. Einstein, Mark A. McDaniel](https://doi.org/10.1037/0278-7393.16.4.717) — *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 16(4), 717–726, 1990. Owns the prospective-memory construct in its modern form: remembering to perform a delayed intention, and the finding that this is a capacity distinct from retrospective memory.
- <a id="einstein-self-initiated-retrieval"></a>[einstein-self-initiated-retrieval](#einstein-self-initiated-retrieval) · [**Aging and prospective memory: Examining the influences of self-initiated retrieval processes** — Gilles O. Einstein, Mark A. McDaniel, Sarah L. Richardson, Melissa J. Guynn, Allison R. Cunfer](https://doi.org/10.1037/0278-7393.21.4.996) — *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 21(4), 996–1007, 1995. Owns the self-initiated retrieval account — why time-based intentions, with no external cue, are harder to realise than event-based ones. The psychology behind "do not keep the intention in the conversation."
- <a id="sellen-in-situ"></a>[sellen-in-situ](#sellen-in-situ) · [**What brings intentions to mind? An in situ study of prospective memory** — Abigail J. Sellen, G. Louie, J. E. Harris, A. J. Wilkins](https://pubmed.ncbi.nlm.nih.gov/9282220/) — *Memory*, 5(4), 483–507, 1997. PMID 9282220. Owns the in-situ evidence that external, event-based cues bring intentions to mind where internally maintained ones fail — the empirical seed of putting prospective records outside the model. Published with initials only; no expanded given names on the record.
- <a id="liu-pm-bench"></a>[liu-pm-bench](#liu-pm-bench) · [**PM-Bench: Evaluating Prospective Memory in LLM Agents** — Genglin Liu, Saadia Gabriel](https://arxiv.org/pdf/2607.12385) — *COLM*, 2026 (arXiv:2607.12385). Owns the first benchmark for prospective memory in LLM agents — prospective memory measured as a capability rather than assumed.
- <a id="zhang-triggerbench"></a>[zhang-triggerbench](#zhang-triggerbench) · [**TriggerBench: Investigating Prospective Memory for Large Language Models** — Tianhua Zhang, Xinjiang Wang, Qianxi Zhang, Qi Chen, Kun Li, Yaoqi Chen, Dingdong Wang, Helen Meng, Yan Lu](https://arxiv.org/pdf/2606.23459) — arXiv:2606.23459, 2026 (preprint). Owns a second prospective-memory benchmark, probing whether and when a model surfaces a stored future intention.

### Scope, leakage, and what must never be stored

- <a id="rezazadeh-collaborative-memory"></a>[rezazadeh-collaborative-memory](#rezazadeh-collaborative-memory) · [**Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control** — Alireza Rezazadeh, Zichao Li, Ange Lou, Yuying Zhao, Wei Wei, Yujia Bao](https://arxiv.org/pdf/2505.18279) — arXiv:2505.18279, 2025 (preprint). Owns multi-user memory with dynamic access control: private and shared tiers, immutable provenance per fragment, and read policies that "project existing memory fragments into filtered transformed views."
- <a id="liu-authorization-before-context"></a>[liu-authorization-before-context](#liu-authorization-before-context) · [**Authorization Before Context: A Model-Neutral Audience Boundary Against Cross-Audience Memory Leakage in Agentic Systems** — Sibo Liu](https://arxiv.org/pdf/2608.17148) — arXiv:2608.17148, 2026 (preprint). Owns the audience boundary at the memory-to-context transition: forbidden facts proven absent *before* the model is called. Single-author non-archival work whose evidence is self-described as preliminary and synthetic.
- <a id="greshake-indirect-injection"></a>[greshake-indirect-injection](#greshake-indirect-injection) · [**Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection** — Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz](https://arxiv.org/pdf/2302.12173) — *AISec @ CCS*, 2023 (arXiv:2302.12173). Owns indirect prompt injection against real LLM-integrated applications, and data-theft side channels via retrieved content.
- <a id="chen-agentpoison"></a>[chen-agentpoison](#chen-agentpoison) · [**AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases** — Zhaorun Chen, Zhen Xiang, Chaowei Xiao, Dawn Song, Bo Li](https://arxiv.org/pdf/2407.12784) — *NeurIPS*, 2024 (arXiv:2407.12784). Owns memory backdooring: under a 0.1% poison rate, over 80% attack success — the memory-specific half of the attack surface.
- <a id="carlini-extracting-training-data"></a>[carlini-extracting-training-data](#carlini-extracting-training-data) · [**Extracting Training Data from Large Language Models** — Nicholas Carlini, Florian Tramer, Eric Wallace, Matthew Jagielski, Ariel Herbert-Voss, Katherine Lee, Adam Roberts, Tom Brown, Dawn Song, Ulfar Erlingsson, Alina Oprea, Colin Raffel](https://arxiv.org/pdf/2012.07805) — *USENIX Security*, 2021 (arXiv:2012.07805, 2020). Owns training-data extraction from language models — the evidence that model-reachable text is extractable text.
- <a id="lukas-pii-leakage"></a>[lukas-pii-leakage](#lukas-pii-leakage) · [**Analyzing Leakage of Personally Identifiable Information in Language Models** — Nils Lukas, Ahmed Salem, Robert Sim, Shruti Tople, Lukas Wutschitz, Santiago Zanella-Béguelin](https://arxiv.org/pdf/2302.00539) — *IEEE S&P*, 2023 (arXiv:2302.00539). Owns the systematic analysis of PII leakage in language models.
- <a id="bourtoule-machine-unlearning"></a>[bourtoule-machine-unlearning](#bourtoule-machine-unlearning) · [**Machine Unlearning** — Lucas Bourtoule, Varun Chandrasekaran, Christopher A. Choquette-Choo, Hengrui Jia, Adelin Travers, Baiwu Zhang, David Lie, Nicolas Papernot](https://arxiv.org/pdf/1912.03817) — *IEEE S&P*, 2021 (arXiv:1912.03817, 2019). Owns machine unlearning: methods for removing a datum's influence after the fact — the only remaining path once a fact has reached the weights.
- <a id="gdpr"></a>[gdpr](#gdpr) · [**Regulation (EU) 2016/679 (General Data Protection Regulation)** — European Parliament and Council of the European Union](https://eur-lex.europa.eu/eli/reg/2016/679/oj) — OJ L 119/1, 4.5.2016. Art. 5(1)(e) storage limitation, Art. 17 erasure, Art. 25 data protection by design. The legal baseline for retention and deletion: Art. 17(2) makes propagating a deletion downstream obligatory — the hard case for derived memory such as summaries, graph edges, and promoted rules.

### Framework, vendor, and practitioner documentation (industry docs)

- <a id="owasp-prompt-injection"></a>[owasp-prompt-injection](#owasp-prompt-injection) · [**LLM01:2025 Prompt Injection** — OWASP](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — *OWASP Top 10 for LLM Applications*, 2025. (industry doc) Documents the markdown-image exfiltration primitive among prompt-injection risks.
- <a id="temporal-durable-execution"></a>[temporal-durable-execution](#temporal-durable-execution) · [**Durable Execution (with the human-in-the-loop and activity-idempotency guides)** — Temporal Technologies](https://temporal.io/) — temporal.io. (industry doc) *cf.* Documents durable execution: triggers, resumption, idempotency, and human approval — the machinery the module's prospective record borrows. Also argues the scheduler-plus-database complexity "isn't necessary … nothing more than a for-loop and a sleep statement," which is why "must live in a scheduler" is this module's framing and not the field's.
- <a id="jamwithai-seven-types"></a>[jamwithai-seven-types](#jamwithai-seven-types) · [**Agent Memory: the 7 types you should know** — Shantanu Ladhwe, Shirin Khosravi Jam](https://jamwithai.substack.com/p/agent-memory-the-7-types-you-should) — *Jam with AI*, 2026. (industry doc) The practitioner post that originated this module's seven-type framing, its "stored vs active" and "what vs where" formulations, and the prospective-record field list. Not peer-reviewed.

### Unsupported claims and own synthesis

- <a id="unsupported"></a>[unsupported](#unsupported) · **Unsupported.** Claims made in this module that no located source supports, cited inline as [unsupported](#unsupported) rather than attached to an invented reference. Currently: (i) the maxim that fixes must be *mechanical* while prose cannot keep a store correct — no located source asserts that dichotomy, and the module offers no measurement; (ii) the claim that a memory store's retrieval precision degrades as it grows — the surveys recommend forgetting and name capacity as an evaluation dimension, but none measures the curve, and the module's text has been rewritten onto the distractor finding ([cuconasu-power-of-noise](#cuconasu-power-of-noise)) that the literature does support.
- <a id="own-synthesis"></a>[own-synthesis](#own-synthesis) · **Own synthesis (not sourced).** Claims this module makes that are the course's framing rather than literature findings, flagged so they are not mistaken for citations: the four-way failure taxonomy (staleness / contradiction / leakage / recall) — each component is sourced individually, but no located source presents this grouping, and the closest published near-miss swaps recall for *provenance collapse*; the two-axis cut (*what* is remembered vs *where* it lives) and the claim that conflating them is why vector-DB-only designs fail; separating **parametric** from **procedural** memory where CoALA files the weights as procedural; the reduction of memory design to "scope, freshness, and retention decisions"; and the promotion-policy apparatus (episode threshold, named reviewer, retraction path).

---

**Next module:** [M8 — Tool Interfaces](../08-tool-interfaces/README.md) — how the model reaches the world safely: contracts, error semantics, and capability boundaries.
