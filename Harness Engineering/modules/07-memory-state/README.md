# M7 · Memory & State

> **Module question:** What does the agent remember, across what scope, and how is it kept correct?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a multi-turn onboarding/sales agent

---

## Opening scene — the agent that remembered the wrong thing

Two incidents, one week apart, same agent.

**First:** a sales agent greeted a returning customer by name, recalled their company size from last quarter, and confidently quoted a price — using the *old* headcount, not the one the customer had updated two weeks ago. The customer corrected it. The agent had *remembered*, and remembered *stale*.

**Second:** the same agent, in a *different* conversation with a *different* user, casually answered "your last order shipped to 12 Main Street" — an address that belonged to the *previous* user. The state had leaked across sessions.

Neither incident was "the model hallucinating." Both were **memory failures**[\[1\]](#ref-1)[\[2\]](#ref-2) — and both trace to the same root: the harness had no answer to *"what belongs in memory, at what scope, and how is it kept true?"* The agent remembered everything it had seen, for no principled reason, and the boundaries between "this session," "this user," and "everyone" were never drawn.

This module is about drawing them. Memory is not "remember more."[\[2\]](#ref-2)[\[3\]](#ref-3) Memory is **remember the right thing, at the right scope, and never the wrong user's thing.**

> **Failure mode (the module in one line):** treating memory as a feature to bolt on ("let's make it remember") instead of a *correctness* problem to design. Staleness, contradiction, leakage, and failed recall are not edge cases — they are the whole subject.[\[2\]](#ref-2)[\[4\]](#ref-4)

---

## The memory taxonomy: seven types, two axes, four scopes

Before the framework, the map. "Memory" is one word for several different things, and confusing them is the root cause of most memory bugs.[\[5\]](#ref-5)[\[6\]](#ref-6) Two axes separate them:

- **What is remembered** — working (this conversation), semantic (facts), episodic (what happened), procedural (how to do things).[\[5\]](#ref-5)[\[7\]](#ref-7)[\[8\]](#ref-8)
- **Where it lives** — in the context window, in an external store you retrieve from, or in the model's weights.[\[9\]](#ref-9)[\[10\]](#ref-10)

Keep the axes apart and "just add a vector DB" stops looking like an answer. Semantic, episodic, and procedural describe *what*; retrieval and parametric describe *where*. A design that names only the first axis has quietly decided the second — usually by accident.

| Type | What it holds | Lifetime | Where it lives | ADK primitive |
|---|---|---|---|---|
| **Working / in-context** | The current conversation — messages, tool results, lookups — re-sent this turn, plus `State`, the scratchpad | One session | The prompt, rebuilt every turn | `Session` (events) + `State` |
| **Semantic**[\[7\]](#ref-7)[\[11\]](#ref-11) | *Facts*: user preferences, entities, "favorite project is X" | Long-term, searchable | An external store | `MemoryService` |
| **Episodic**[\[7\]](#ref-7)[\[8\]](#ref-8) | What *happened* across past sessions (events, transcripts, and any reflections distilled from them) | Long-term, searchable | An external store | `MemoryService` |
| **Procedural** (cf. [\[5\]](#ref-5)[\[8\]](#ref-8)) | How to *do* things: rules, skills, escalation policy | Static, versioned | The instruction | The instruction (M6), not memory |
| **External / retrieval**[\[10\]](#ref-10)[\[12\]](#ref-12) | Whatever you kept outside the window and fetched back: docs, records, prior runs | Long-term | The store itself (vector, SQL, documents, graph) + a retriever | Tools over `MemoryService` / RAG |
| **Parametric**[\[13\]](#ref-13)[\[14\]](#ref-14) | Everything learned in training: language, world knowledge, reasoning | Frozen at training time | The weights | The model itself — unmanaged |
| **Prospective**[\[15\]](#ref-15)[\[16\]](#ref-16) | What must happen *later*: follow-ups, retries, renewals | Until done or cancelled | A scheduler or task queue — **never** the `MemoryService` | Outside ADK (a scheduler you own) |

> where would memory related to "user specified constraints" associated with the [overlook constraints failure class](../02-model-failure-science/README.md#overlooked-constraints) reside?

Three observations that carry the module:

1. **Working memory and long-term memory have different failure modes.** Working memory fails by *overflow* (M4's budget problem — the session grows until it drowns).[\[17\]](#ref-17)[\[18\]](#ref-18) Long-term memory fails by *staleness, contradiction, leakage, and failed recall* (below).[\[2\]](#ref-2)[\[4\]](#ref-4) Design them separately; they are different diseases.
2. **Procedural memory is not memory at all** (cf. [\[5\]](#ref-5)[\[8\]](#ref-8)[\[19\]](#ref-19)) — it's the instruction. Rules you want to *persist* should live in the instruction (static, versioned, tested), not in a searchable store where they can drift. (This is M6, restated: policy belongs in the constitution, not in a memory archive.)
3. **Stored is not the same as active.** Your database can hold an entire conversation, but the model cannot reason over a single byte of it until those bytes are back in the prompt.[\[5\]](#ref-5)[\[9\]](#ref-9) Storage is *potential*; working memory is what the model can actually use right now. This is why "it remembered!" is so often the wrong explanation: the constraint was never remembered, it was simply still being re-sent. Stop re-sending it and the "memory" vanishes.

**Parametric memory is a floor, not a feature.** It is the general-ability layer,[\[13\]](#ref-13) and it is the one store you can neither timestamp, scope, correct,[\[20\]](#ref-20)[\[21\]](#ref-21) nor delete — which is exactly why anything specific, current, or private has to come from one of the other six. Note the shape of the table too: ADK's primitives cover three of the seven. Procedural is the instruction (M6), prospective is a scheduler, and parametric is the model itself — three types with no memory API at all, each of which breaks quietly the moment you treat it as if it had one.

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

Read that table as the answer to the leakage failure from the opening scene: **the address that leaked across users should never have been session-scoped or left un-prefixed.** Scope is not a storage detail — it is the *boundary* that determines whether one user can see another's data.[\[22\]](#ref-22)[\[23\]](#ref-23) A `user:`-prefixed key stays with that user; an un-prefixed key stays with that session; an `app:`-prefixed key is intentionally shared. Every state write should be a conscious choice of prefix, not a bare `state['x'] = ...`.

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

The retrieval design question — *preload vs. load-on-demand* — is the memory analog of M4's context budget: preloading spends context every turn on *maybe*-relevant memories; load-on-demand saves budget but only helps if the agent *knows* to ask.[\[12\]](#ref-12)[\[13\]](#ref-13) Preload when memory is small and always-relevant (a returning user's preferences); load-on-demand when memory is large and mostly-irrelevant (a long support history).

**Three implementations, three tradeoffs** (pick by what "memory" means to you):

| Service | Persistence | Retrieval | Use when |
|---|---|---|---|
| `InMemoryMemoryService` | None (lost on restart) | Keyword | Prototyping |
| `VertexAiMemoryBankService` | Yes (managed) | LLM-extracted + **consolidation**, semantic | You want the agent to *learn* and reconcile memories |
| `VertexAiRagMemoryService` | Yes | Vector search over raw transcripts | You already run RAG, or want raw retrieval |

The standout concept in the table is **consolidation** (Memory Bank's `enable_consolidation`): instead of appending "favorite color is light blue" as a *second* contradictory fact next to "favorite color is blue," the service *merges* them into one coherent memory.[\[10\]](#ref-10)[\[24\]](#ref-24)[\[25\]](#ref-25) That is the direct answer to the *contradiction* failure mode — and it's the long-term analog of M4's compaction: both are *lossy reconciliation of history*, one for the working window, one for the archive.

> **ADK at a glance:** the memory workflow is a loop — *session concludes → `add_session_to_memory` (often via an `after_agent_callback`) → later, a new session asks something about the past → the agent calls `load_memory` → `search_memory` returns `MemoryEntry` objects (content + optional id/author/timestamp/custom_metadata) → the agent answers.* You can also wire a *second* memory service manually (e.g., one for conversations, one for a docs corpus) from a custom tool.

---

## Prospective memory: remembering the future

Every type above remembers the past or the present. A long-running agent needs one more: **what must happen later.**

- Follow up with the customer on Friday.
- Retry the job once the rate limit resets.
- Re-check the deployment after the monitoring data lands.
- Warn the user before their subscription renews.

The problem is structural, not stylistic: **a future task cannot wait inside the conversation.**[\[26\]](#ref-26)[\[27\]](#ref-27) The model is not running while it waits, and the session may be long gone by the time the moment arrives. So a prospective memory cannot be a state key the agent is trusted to check later, and it cannot be a `MemoryService` entry hoping some future `search_memory` call surfaces it. It has to live in a scheduler or a task queue — outside the model — as a durable record that answers five questions:[\[3\]](#ref-3)[\[28\]](#ref-28)

| Field | Question it answers | Failure if missing |
|---|---|---|
| **Action** | What should happen? | The timer fires and nothing knows what to do |
| **Trigger** | When, or on what event? | Fires at the wrong time, or never |
| **Resume state** | What context does the task need to pick back up? | The agent restarts from zero and re-asks the user everything |
| **Done flag** | How do we know it is finished? | It nags forever |
| **Approval** | Who authorizes the action? | A consequential action runs unattended (M15) |

> **Failure mode (the one the other three failure modes don't cover):** a prospective record that never fires (silent drop), fires repeatedly (no done flag), or fires without the state it needs.[\[16\]](#ref-16)[\[29\]](#ref-29) An overdue follow-up is not stale, contradictory, or leaked — it simply *didn't happen*, and nothing in the archive can tell you that.

> **ADK at a glance:** there is no `MemoryService` call here. Prospective memory is the harness's job — a scheduler, a queue, or a durable workflow engine (cron at the small end; a system built for long-delayed, reliable jobs at the other) — and the agent's interface to it is narrow: a tool that *writes* the record, and a callback that *resumes* the session when it fires.

---

## The loop: episodes become procedures

A store of past runs is an archive until something reads it. The step that makes memory *pay* is **reflection**: after a task completes, distill the episode into a short lesson — what worked, what didn't, what to do differently — and store *that* next to the run.[\[30\]](#ref-30)[\[31\]](#ref-31)[\[32\]](#ref-32) The full transcript is for humans and for M16's traces; the lesson is what gets retrieved.

Reflection is also the bridge to procedural memory (M6). A pattern that shows up across episodes — *deployments keep failing because an environment variable was never set* — can be **promoted** into a standing rule in the instruction layer. That is how an agent improves without retraining:[\[31\]](#ref-31)[\[33\]](#ref-33)[\[34\]](#ref-34) episodic memory is the evidence, procedural memory is the verdict.

Promotion is a policy decision, and both extremes are failures:

| Promotion policy | Failure |
|---|---|
| Never promote | The same lesson is re-derived forever; reflection has no consumer and the archive keeps growing |
| Promote from one episode | Turn one unlucky run into a permanent rule and you have taught the agent a bad habit it repeats every time[\[5\]](#ref-5) |

So promotion needs a threshold (how many independent episodes?), a reviewer (the user? an eval — M12?), and — critically — a **retraction path**. Rules promoted into the instruction layer must be as easy to remove as they were to add, or a bad habit becomes permanent policy.

> **Tradeoff (the ledger entry):** **Learning vs. stability.** A system that promotes aggressively adapts fast and drifts; one that never promotes is deterministic and never improves.[\[5\]](#ref-5)[\[33\]](#ref-33)[\[34\]](#ref-34) Set the threshold per rule class, and record who signed off.

---

## The four failure modes: staleness, contradiction, leakage, recall

This is the module's payload — the taxonomy of how memory *goes wrong*, each with its fix:

| Failure | What it is | Signature | Fix |
|---|---|---|---|
| **Staleness** | A stored fact is no longer true (old headcount, old address, old price) | The agent answers confidently from *last quarter's* data | Timestamps ("as of"), TTL/expiry, re-verify before use on consequential facts[\[2\]](#ref-2)[\[4\]](#ref-4)[\[25\]](#ref-25) |
| **Contradiction** | Two memories disagree (preference changed; old record never removed) | The answer flips depending on *which* memory was retrieved | Consolidation (merge), write-with-overwrite policy, conflict detection → escalate[\[24\]](#ref-24)[\[25\]](#ref-25)[\[35\]](#ref-35) |
| **Leakage** | Data crosses a scope boundary (user A's data visible to user B) | The agent quotes a *different user's* facts | Scope prefixes (`user:` / `app:` / session / `temp:`), never store secrets, retrieval scoped by user/app[\[22\]](#ref-22)[\[23\]](#ref-23)[\[36\]](#ref-36) |
| **Recall failure** | The right memory exists but the wrong one comes back — or nothing does | The agent answers from an irrelevant episode, or claims not to know something you stored | Match the retrieval method to the query: vector search for *related*, exact lookup for a *specific fact*, filters for scope/permission, time for *when*, links for *relatedness* — and cap what you store in the first place[\[4\]](#ref-4)[\[30\]](#ref-30)[\[37\]](#ref-37) |

The unifying insight: **memory is a source of truth, and the model treats it as one.**[\[2\]](#ref-2)[\[35\]](#ref-35) A stale memory is not "old data" — it is *wrongness that presents itself as rightness*, because the model has no reason to doubt its own memory (cf. [\[13\]](#ref-13)[\[38\]](#ref-38)). That's why the fixes are *mechanical* (timestamps, consolidation, scoping) rather than prompt-level ("remember to check if the address is current") — prose cannot keep a store correct; policy can.

Recall failure is not mainly a *volume* problem — it is a *distractor* problem. Adding random documents can improve accuracy; what damages it is the retriever's own highest-scoring, semantically related, answer-free documents.[\[39\]](#ref-39) Position matters too: material buried mid-context is recalled worse than material at the edges.[\[40\]](#ref-40) That is the same ledger entry as M4's, moved to the archive: storing more is never free.

---

## What memory should never hold

Because the model can retrieve whatever is in memory — and, once retrieved, may act on it or surface it — memory is an **exfiltration surface**[\[41\]](#ref-41)[\[42\]](#ref-42)[\[43\]](#ref-43) (M14's territory, foreshadowed). Three things must never go in:

1. **Secrets.** API keys, tokens, credentials. Anything in memory is reachable by the model, and a reachable secret is a leaked secret.[\[44\]](#ref-44)[\[45\]](#ref-45) Secrets belong in a secrets manager, *outside* the model's reach, injected per-call — never in state or memory.
2. **Unverified facts.** A wrong fact stored today is a wrongness the model will *confidently* repeat forever. Only store what was verified at write time; everything else stays in the conversation, not the archive.
3. **PII without policy.** Personal data needs a retention policy, a consent basis, and a scope boundary — *before* it goes in.[\[36\]](#ref-36) "Remember this for the user" without "for how long, under what consent, in what scope" is a governance failure waiting to happen (M15).

The rule of thumb: **write to memory only what you would be willing to have the agent state to that user, later, with full confidence — and only under a scope you can defend.**

---

## The write path — and forgetting on purpose

The never-store list is the negative half of the policy. The positive half is a **write path**, and it is a harness component with its own failure modes, not a `state['x'] = ...` afterthought.

Four stages, each of which can be skipped and shouldn't be:

1. **Extraction** — something reads the conversation and decides what is worth saving. In practice that "something" is usually the model itself, which means extraction inherits the model's judgment: it will save a one-off as a preference (*"keep it short today"* → *"always wants short answers"*), and it will save things that were never true. Extraction output is a **candidate**, not a write.[\[2\]](#ref-2)[\[24\]](#ref-24)
2. **Validation** — was this verified *this turn*, by a tool or by the user, or is it the model's paraphrase? Only verified facts get a timestamp and a scope; everything else stays in the conversation, where it costs nothing and expires on its own.[\[2\]](#ref-2)
3. **Update** — a write must be able to *replace*. A store with no overwrite path is how contradiction happens: "headcount 35" and "headcount 40" coexist, and which one wins depends on which one retrieval happened to rank higher.[\[10\]](#ref-10)[\[24\]](#ref-24)
4. **Deletion** — the stage everyone skips. Deletion is what makes the rest real: TTL on facts that decay, a retention window on PII and on episodic transcripts, and an explicit path for a user who withdraws consent (M15).[\[10\]](#ref-10)[\[36\]](#ref-36)[\[46\]](#ref-46) A `MemoryService` interface with `add_*` and `search_memory` and no delete is a store that can only accumulate.

**Forgetting is a design act, not a garbage-collection detail.**[\[2\]](#ref-2)[\[10\]](#ref-10)[\[47\]](#ref-47) A store that only grows gets slower and more expensive to search — and it keeps answering from facts that should have expired two quarters ago. The one-off-vs-lasting test from extraction is the same test as the never-store rule of thumb: write what you would be willing to have the agent state to that user, later, with full confidence — *and* be willing to defend keeping.

> **Tradeoff (the ledger entry):**
> - **Recall precision vs. archive completeness.** Every fact you store competes for the same retrieval slots, and the near-misses are the dangerous ones. Prune on purpose, not never.[\[2\]](#ref-2)[\[39\]](#ref-39)
> - **Retention vs. auditability.** Short TTLs protect users and cost you the ability to explain what the agent knew last month. Choose per data class, not per system.[\[25\]](#ref-25)[\[36\]](#ref-36)
> - **Model-driven extraction vs. deterministic capture.** Letting the model decide what is worth saving scales; it also imports the model's judgment into your source of truth. Deterministic rules are auditable and blind.[\[2\]](#ref-2)[\[24\]](#ref-24)[\[25\]](#ref-25)

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
- *Staleness:* before quoting headcount, the agent checks `user:last_headcount_updated_at` against a freshness window; if stale, it asks instead of asserting.[\[2\]](#ref-2)[\[25\]](#ref-25)
- *Contradiction:* consolidation merges the preference changes; no two "headcount" facts coexist.[\[24\]](#ref-24)
- *Leakage:* the address is `user:`-scoped — user B's session cannot see user A's address, because the key is scoped to user A.[\[22\]](#ref-22)
- *Recall failure:* pricing is an exact lookup by SKU, not a vector search, so "find something similar" cannot substitute a neighbouring product's price.[\[4\]](#ref-4)[\[39\]](#ref-39)
- *Prospective:* the quote follow-up is a scheduler record with a trigger, a done flag, and an approval field — the agent never has to *remember* to check, and the record outlives the session.[\[16\]](#ref-16)[\[28\]](#ref-28)

The point, restated: the schema is not a database diagram — it is a *set of scope, freshness, and retention decisions*, and each one maps to a failure it prevents. That is what "memory design" means.

> **Tradeoff (the ledger entry):**
> - **Remember more vs. retrieve correctly.** Every fact you store competes for the same retrieval slots (more memory → more near-misses) and adds staleness risk. Store the *few* facts that matter, not everything.[\[2\]](#ref-2)[\[39\]](#ref-39)
> - **Persistence vs. leakage.** Persistence buys continuity; it also buys the possibility of cross-scope leakage. Every persistent key needs a scope prefix and a justification.[\[22\]](#ref-22)[\[36\]](#ref-36)
> - **Consolidation vs. fidelity.** Consolidation (like compaction) trades exact history for coherence. You accept some loss of detail so the archive stays *consistent* — record that acceptance.[\[10\]](#ref-10)[\[24\]](#ref-24)
> - **Acting now vs. acting later.** A prospective record buys follow-through across sessions, and it buys unattended action at a time nobody is watching — which is exactly why the record carries an approval field.[\[16\]](#ref-16)[\[28\]](#ref-28)

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

## Sources

**ADK docs**

- [Session, State & Memory — concepts](https://adk.dev/sessions/index.md)
- [State: the session's scratchpad (prefixes, update paths, `{key}` templating)](https://adk.dev/sessions/state/index.md)
- [Memory: long-term knowledge with MemoryService](https://adk.dev/sessions/memory/index.md)

### Bibliography

*Literature behind the conceptual content. Entries are numbered in reading order and cited inline in the text above; each inline number is a link to its own entry below, and `cf.` marks a source that qualifies or contradicts the sentence it follows. Items tagged (practitioner) or (industry doc) are not peer-reviewed.*

1. <a id="ref-1"></a>Cemri, M., Pan, M. Z., Yang, S., Agrawal, L. A., Chopra, B., Tiwari, R., Keutzer, K., Parameswaran, A., Klein, D., Ramchandran, K., Zaharia, M., Gonzalez, J. E., & Stoica, I. (2025). *Why Do Multi-Agent LLM Systems Fail?* arXiv:2503.13657. https://arxiv.org/abs/2503.13657
2. <a id="ref-2"></a>Du, P. (2026). *Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers.* arXiv:2603.07670. https://arxiv.org/abs/2603.07670
3. <a id="ref-3"></a>Ladhwe, S., & Jam, S. K. (2026). *Agent Memory: the 7 types you should know.* Jam with AI. https://jamwithai.substack.com/p/agent-memory-the-7-types-you-should (practitioner)
4. <a id="ref-4"></a>Wu, D., Wang, H., Yu, W., Zhang, Y., Chang, K.-W., & Yu, D. (2025). *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory.* ICLR 2025. https://arxiv.org/abs/2410.10813
5. <a id="ref-5"></a>Sumers, T. R., Yao, S., Narasimhan, K., & Griffiths, T. L. (2024). *Cognitive Architectures for Language Agents.* Transactions on Machine Learning Research (TMLR). https://arxiv.org/abs/2309.02427
6. <a id="ref-6"></a>Zhang, Z., Bo, X., Ma, C., Li, R., Chen, X., Dai, Q., Zhu, J., Dong, Z., & Wen, J.-R. (2024). *A Survey on the Memory Mechanism of Large Language Model-based Agents.* arXiv:2404.13501. https://arxiv.org/abs/2404.13501
7. <a id="ref-7"></a>Tulving, E. (1972). Episodic and semantic memory. In E. Tulving & W. Donaldson (Eds.), *Organization of Memory* (pp. 381–403). Academic Press.
8. <a id="ref-8"></a>Squire, L. R. (2004). Memory systems of the brain: a brief history and current perspective. *Neurobiology of Learning and Memory*, 82(3), 171–177. https://pubmed.ncbi.nlm.nih.gov/15464402/
9. <a id="ref-9"></a>Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). *MemGPT: Towards LLMs as Operating Systems.* arXiv:2310.08560. https://arxiv.org/abs/2310.08560
10. <a id="ref-10"></a>Du, Y., Huang, W., Zheng, D., Wang, Z., Montella, S., Lapata, M., Wong, K.-F., & Pan, J. Z. (2025). *Rethinking Memory in LLM-based Agents: Representations, Operations, and Emerging Topics.* arXiv:2505.00675. https://arxiv.org/abs/2505.00675
11. <a id="ref-11"></a>Tulving, E. (2002). Episodic memory: from mind to brain. *Annual Review of Psychology*, 53, 1–25. https://pubmed.ncbi.nlm.nih.gov/11752477/
12. <a id="ref-12"></a>Asai, A., Wu, Z., Wang, Y., Sil, A., & Hajishirzi, H. (2024). *Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection.* ICLR 2024. https://arxiv.org/abs/2310.11511
13. <a id="ref-13"></a>Mallen, A., Asai, A., Zhong, V., Das, R., Khashabi, D., & Hajishirzi, H. (2023). *When Not to Trust Language Models: Investigating Effectiveness of Parametric and Non-Parametric Memories.* ACL 2023. https://arxiv.org/abs/2212.10511
14. <a id="ref-14"></a>Ovadia, O., Brief, M., Mishaeli, M., & Elisha, O. (2023). *Fine-Tuning or Retrieval? Comparing Knowledge Injection in LLMs.* arXiv:2312.05934. https://arxiv.org/abs/2312.05934
15. <a id="ref-15"></a>Einstein, G. O., & McDaniel, M. A. (1990). Normal aging and prospective memory. *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 16(4), 717–726. https://pubmed.ncbi.nlm.nih.gov/2142956/
16. <a id="ref-16"></a>Liu, G., & Gabriel, S. (2026). *PM-Bench: Evaluating Prospective Memory in LLM Agents.* arXiv:2607.12385 (COLM 2026). https://arxiv.org/abs/2607.12385
17. <a id="ref-17"></a>Modarressi, A., Deilamsalehy, H., Dernoncourt, F., Bui, T., Rossi, R. A., Yoon, S., & Schütze, H. (2025). *NoLiMa: Long-Context Evaluation Beyond Literal Matching.* ICML 2025. https://arxiv.org/abs/2502.05167
18. <a id="ref-18"></a>Hsieh, C.-P., Sun, S., Kriman, S., Acharya, S., Rekesh, D., Jia, F., Zhang, Y., & Ginsburg, B. (2024). *RULER: What's the Real Context Size of Your Long-Context Language Models?* COLM 2024. https://arxiv.org/abs/2404.06654
19. <a id="ref-19"></a>Huang, W.-C., et al. (2026). *A Survey of Agent Memory in the Second Half: Towards Self-Evolving and Long-Horizon Agents.* arXiv:2602.06052. https://arxiv.org/abs/2602.06052
20. <a id="ref-20"></a>Cohen, R., Biran, E., Yoran, O., Globerson, A., & Geva, M. (2024). Evaluating the Ripple Effects of Knowledge Editing in Language Models. *TACL*, 12, 283–298. https://doi.org/10.1162/tacl_a_00644
21. <a id="ref-21"></a>Yao, Y., Wang, P., Tian, B., Cheng, S., Li, Z., Deng, Y., Chen, H., & Zhang, N. (2023). *Editing Large Language Models: Problems, Methods, and Opportunities.* EMNLP 2023. https://arxiv.org/abs/2305.13172
22. <a id="ref-22"></a>Rezazadeh, A., Li, Z., Lou, A., Zhao, Y., Wei, W., & Bao, Y. (2025). *Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control.* arXiv:2505.18279. https://arxiv.org/abs/2505.18279
23. <a id="ref-23"></a>Liu, S. (2026). *Authorization Before Context: A Model-Neutral Audience Boundary Against Cross-Audience Memory Leakage in Agentic Systems.* arXiv:2608.17148. https://arxiv.org/abs/2608.17148
24. <a id="ref-24"></a>Chhikara, P., Khant, D., Aryan, S., Singh, T., & Yadav, D. (2025). *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory.* arXiv:2504.19413. https://arxiv.org/abs/2504.19413
25. <a id="ref-25"></a>Rasmussen, P., Paliychuk, P., Beauvais, T., Ryan, J., & Chalef, D. (2025). *Zep: A Temporal Knowledge Graph Architecture for Agent Memory.* arXiv:2501.13956. https://arxiv.org/abs/2501.13956
26. <a id="ref-26"></a>Einstein, G. O., McDaniel, M. A., Richardson, S. L., Guynn, M. J., & Cunfer, A. R. (1995). Aging and prospective memory: examining the influences of self-initiated retrieval processes. *Journal of Experimental Psychology: Learning, Memory, and Cognition*, 21(4), 996–1007. https://pubmed.ncbi.nlm.nih.gov/7673871/
27. <a id="ref-27"></a>Sellen, A. J., Louie, G., Harris, J. E., & Wilkins, A. J. (1997). The effects of interruptions and resource availability on prospective memory performance. *Memory*, 5(4), 483–507.
28. <a id="ref-28"></a>Temporal Technologies. *Durable Execution* (with the human-in-the-loop and activity-idempotency guides). https://temporal.io/ (industry doc)
29. <a id="ref-29"></a>Zhang, T., et al. (2026). *TriggerBench: Investigating Prospective Memory for Large Language Models.* arXiv:2606.23459. https://arxiv.org/abs/2606.23459
30. <a id="ref-30"></a>Park, J. S., O'Brien, J. C., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023). *Generative Agents: Interactive Simulacra of Human Behavior.* UIST 2023. https://arxiv.org/abs/2304.03442
31. <a id="ref-31"></a>Shinn, N., Cassano, F., Berman, E., Gopinath, A., Narasimhan, K., & Yao, S. (2023). *Reflexion: Language Agents with Verbal Reinforcement Learning.* NeurIPS 2023. https://arxiv.org/abs/2303.11366
32. <a id="ref-32"></a>Tan, Z., et al. (2025). *In Prospect and Retrospect: Reflective Memory Management for Long-term Personalized Dialogue Agents.* ACL 2025. https://arxiv.org/abs/2503.08026
33. <a id="ref-33"></a>Wang, G., Xie, Y., Jiang, Y., Mandlekar, A., Xiao, C., Zhu, Y., Fan, L., & Anandkumar, A. (2024). *Voyager: An Open-Ended Embodied Agent with Large Language Models.* TMLR. https://arxiv.org/abs/2305.16291
34. <a id="ref-34"></a>Zhao, A., Huang, D., Xu, Q., Lin, M., Liu, Y.-J., & Huang, G. (2024). *ExpeL: LLM Agents Are Experiential Learners.* AAAI-24. https://arxiv.org/abs/2308.10144
35. <a id="ref-35"></a>Xu, R., Qi, Z., Guo, Z., Wang, C., Wang, H., Zhang, Y., & Xu, W. (2024). *Knowledge Conflicts for LLMs: A Survey.* EMNLP 2024, 8541–8565. https://arxiv.org/abs/2403.08319
36. <a id="ref-36"></a>Regulation (EU) 2016/679 (General Data Protection Regulation), OJ L 119/1, 4.5.2016 — Art. 5(1)(e) storage limitation, Art. 17 erasure, Art. 25 data protection by design. https://eur-lex.europa.eu/eli/reg/2016/679/oj (legal)
37. <a id="ref-37"></a>Xu, W., Liang, Z., Mei, K., Gao, H., Tan, J., & Zhang, Y. (2025). *A-MEM: Agentic Memory for LLM Agents.* arXiv:2502.12110. https://arxiv.org/abs/2502.12110
38. <a id="ref-38"></a>Xie, J., Zhang, K., Chen, J., Lou, R., & Su, Y. (2024). *Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts.* ICLR 2024. https://arxiv.org/abs/2305.13300
39. <a id="ref-39"></a>Cuconasu, F., Trappolini, G., Siciliano, F., Filice, S., Campagnano, C., Maarek, Y., Tonellotto, N., & Silvestri, F. (2024). *The Power of Noise: Redefining Retrieval for RAG Systems.* SIGIR '24. https://arxiv.org/abs/2401.14887
40. <a id="ref-40"></a>Liu, N. F., Lin, K., Hewitt, J., Paranjape, A., Bevilacqua, M., Petroni, F., & Liang, P. (2024). Lost in the Middle: How Language Models Use Long Contexts. *TACL*, 12, 157–173. https://arxiv.org/abs/2307.03172
41. <a id="ref-41"></a>Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). *Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection.* arXiv:2302.12173. https://arxiv.org/abs/2302.12173
42. <a id="ref-42"></a>OWASP. (2025). *LLM01:2025 Prompt Injection.* OWASP Top 10 for LLM Applications. https://genai.owasp.org/llmrisk/llm01-prompt-injection/ (industry doc)
43. <a id="ref-43"></a>Chen, Z., Xiang, Z., Xiao, C., Song, D., & Li, B. (2024). *AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases.* NeurIPS 2024. https://arxiv.org/abs/2407.12784
44. <a id="ref-44"></a>Carlini, N., Tramer, F., Wallace, E., Jagielski, M., Herbert-Voss, A., Lee, K., Roberts, A., Brown, T., Song, D., Erlingsson, Ú., Oprea, A., & Raffel, C. (2021). *Extracting Training Data from Large Language Models.* USENIX Security 2021. https://arxiv.org/abs/2012.07805
45. <a id="ref-45"></a>Lukas, N., Salem, A., Sim, R., Tople, S., Wutschitz, L., & Zanella-Béguelin, S. (2023). *Analyzing Leakage of Personally Identifiable Information in Language Models.* IEEE S&P 2023. https://arxiv.org/abs/2302.00539
46. <a id="ref-46"></a>Bourtoule, L., Chandrasekaran, V., Choquette-Choo, C. A., Jia, H., Travers, A., Zhang, B., Lie, D., & Papernot, N. (2021). *Machine Unlearning.* IEEE S&P 2021. https://arxiv.org/abs/1912.03817
47. <a id="ref-47"></a>Zhong, W., Guo, L., Gao, Q., Ye, H., & Wang, Y. (2024). *MemoryBank: Enhancing Large Language Models with Long-Term Memory.* AAAI-24, 38(17), 19724–19731. https://doi.org/10.1609/aaai.v38i17.29946

*Statements in this module carrying no citation are the module's own synthesis rather than literature findings. Every conceptual claim is graded — justified, partially justified, or novel — against its sources in [`README-source-audit.md`](./README-source-audit.md).*

---

**Next module:** [M8 — Tool Interfaces](../08-tool-interfaces/README.md) — how the model reaches the world safely: contracts, error semantics, and capability boundaries.
