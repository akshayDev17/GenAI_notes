# M7 · Memory & State

> **Module question:** What does the agent remember, across what scope, and how is it kept correct?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a multi-turn onboarding/sales agent

---

## Opening scene — the agent that remembered the wrong thing

Two incidents, one week apart, same agent.

**First:** a sales agent greeted a returning customer by name, recalled their company size from last quarter, and confidently quoted a price — using the *old* headcount, not the one the customer had updated two weeks ago. The customer corrected it. The agent had *remembered*, and remembered *stale*.

**Second:** the same agent, in a *different* conversation with a *different* user, casually answered "your last order shipped to 12 Main Street" — an address that belonged to the *previous* user. The state had leaked across sessions.

Neither incident was "the model hallucinating." Both were **memory failures** — and both trace to the same root: the harness had no answer to *"what belongs in memory, at what scope, and how is it kept true?"* The agent remembered everything it had seen, for no principled reason, and the boundaries between "this session," "this user," and "everyone" were never drawn.

This module is about drawing them. Memory is not "remember more." Memory is **remember the right thing, at the right scope, and never the wrong user's thing.**

> **Failure mode (the module in one line):** treating memory as a feature to bolt on ("let's make it remember") instead of a *correctness* problem to design. Staleness, contradiction, and leakage are not edge cases — they are the whole subject.

---

## The memory taxonomy: four kinds, four scopes

Before the framework, the map. An agent's "memory" is four different things, and confusing them is the root cause of most memory bugs:

| Kind | What it holds | Lifetime | ADK primitive |
|---|---|---|---|
| **Working / short-term** | The current conversation: what's been said, the in-flight task | One session | `Session` (events) + `State` (scratchpad) |
| **Episodic** | What *happened* across past sessions (events, transcripts) | Long-term, searchable | `MemoryService` |
| **Semantic** | *Facts*: user preferences, entities, "favorite project is X" | Long-term, searchable | `MemoryService` |
| **Procedural** | How to *do* things: rules, skills, escalation policy | Static, versioned | The instruction (M6), not memory |

Two observations that carry the module:

1. **Working memory and long-term memory have different failure modes.** Working memory fails by *overflow* (M4's budget problem — the session grows until it drowns). Long-term memory fails by *staleness, contradiction, and leakage* (below). Design them separately; they are different diseases.
2. **Procedural memory is not memory at all** — it's the instruction. Rules you want to *persist* should live in the instruction (static, versioned, tested), not in a searchable store where they can drift. (This is M6, restated: policy belongs in the constitution, not in a memory archive.)

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

Read that table as the answer to the leakage failure from the opening scene: **the address that leaked across users should never have been session-scoped or left un-prefixed.** Scope is not a storage detail — it is the *boundary* that determines whether one user can see another's data. A `user:`-prefixed key stays with that user; an un-prefixed key stays with that session; an `app:`-prefixed key is intentionally shared. Every state write should be a conscious choice of prefix, not a bare `state['x'] = ...`.

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

The retrieval design question — *preload vs. load-on-demand* — is the memory analog of M4's context budget: preloading spends context every turn on *maybe*-relevant memories; load-on-demand saves budget but only helps if the agent *knows* to ask. Preload when memory is small and always-relevant (a returning user's preferences); load-on-demand when memory is large and mostly-irrelevant (a long support history).

**Three implementations, three tradeoffs** (pick by what "memory" means to you):

| Service | Persistence | Retrieval | Use when |
|---|---|---|---|
| `InMemoryMemoryService` | None (lost on restart) | Keyword | Prototyping |
| `VertexAiMemoryBankService` | Yes (managed) | LLM-extracted + **consolidation**, semantic | You want the agent to *learn* and reconcile memories |
| `VertexAiRagMemoryService` | Yes | Vector search over raw transcripts | You already run RAG, or want raw retrieval |

The standout concept in the table is **consolidation** (Memory Bank's `enable_consolidation`): instead of appending "favorite color is light blue" as a *second* contradictory fact next to "favorite color is blue," the service *merges* them into one coherent memory. That is the direct answer to the *contradiction* failure mode — and it's the long-term analog of M4's compaction: both are *lossy reconciliation of history*, one for the working window, one for the archive.

> **ADK at a glance:** the memory workflow is a loop — *session concludes → `add_session_to_memory` (often via an `after_agent_callback`) → later, a new session asks something about the past → the agent calls `load_memory` → `search_memory` returns `MemoryEntry` objects (content + optional id/author/timestamp/custom_metadata) → the agent answers.* You can also wire a *second* memory service manually (e.g., one for conversations, one for a docs corpus) from a custom tool.

---

## The three failure modes: staleness, contradiction, leakage

This is the module's payload — the taxonomy of how memory *goes wrong*, each with its fix:

| Failure | What it is | Signature | Fix |
|---|---|---|---|
| **Staleness** | A stored fact is no longer true (old headcount, old address, old price) | The agent answers confidently from *last quarter's* data | Timestamps ("as of"), TTL/expiry, re-verify before use on consequential facts |
| **Contradiction** | Two memories disagree (preference changed; old record never removed) | The answer flips depending on *which* memory was retrieved | Consolidation (merge), write-with-overwrite policy, conflict detection → escalate |
| **Leakage** | Data crosses a scope boundary (user A's data visible to user B) | The agent quotes a *different user's* facts | Scope prefixes (`user:` / `app:` / session / `temp:`), never store secrets, retrieval scoped by user/app |

The unifying insight: **memory is a source of truth, and the model treats it as one.** A stale memory is not "old data" — it is *wrongness that presents itself as rightness*, because the model has no reason to doubt its own memory. That's why the fixes are *mechanical* (timestamps, consolidation, scoping) rather than prompt-level ("remember to check if the address is current") — prose cannot keep a store correct; policy can.

---

## What memory should never hold

Because the model can retrieve whatever is in memory — and, once retrieved, may act on it or surface it — memory is an **exfiltration surface** (M14's territory, foreshadowed). Three things must never go in:

1. **Secrets.** API keys, tokens, credentials. Anything in memory is reachable by the model, and a reachable secret is a leaked secret. Secrets belong in a secrets manager, *outside* the model's reach, injected per-call — never in state or memory.
2. **Unverified facts.** A wrong fact stored today is a wrongness the model will *confidently* repeat forever. Only store what was verified at write time; everything else stays in the conversation, not the archive.
3. **PII without policy.** Personal data needs a retention policy, a consent basis, and a scope boundary — *before* it goes in. "Remember this for the user" without "for how long, under what consent, in what scope" is a governance failure waiting to happen (M15).

The rule of thumb: **write to memory only what you would be willing to have the agent state to that user, later, with full confidence — and only under a scope you can defend.**

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

**Long-term memory (write policy):**
- On session end, `add_session_to_memory` (episodic — what happened).
- Explicit *semantic* facts (`user:headcount`) written only when *verified* this turn, always with a timestamp.
- Consolidation on, so "headcount 40" replaces "headcount 35" instead of joining it as a contradiction.

**The failures, prevented:**
- *Staleness:* before quoting headcount, the agent checks `user:last_headcount_updated_at` against a freshness window; if stale, it asks instead of asserting.
- *Contradiction:* consolidation merges the preference changes; no two "headcount" facts coexist.
- *Leakage:* the address is `user:`-scoped — user B's session cannot see user A's address, because the key is scoped to user A.

The point, restated: the schema is not a database diagram — it is a *set of scope and freshness decisions*, and each one maps to a failure it prevents. That is what "memory design" means.

> **Tradeoff (the ledger entry):**
> - **Remember more vs. retrieve correctly.** Every fact you store costs retrieval precision (more memory → more irrelevant recall) and staleness risk. Store the *few* facts that matter, not everything.
> - **Persistence vs. leakage.** Persistence buys continuity; it also buys the possibility of cross-scope leakage. Every persistent key needs a scope prefix and a justification.
> - **Consolidation vs. fidelity.** Consolidation (like compaction) trades exact history for coherence. You accept some loss of detail so the archive stays *consistent* — record that acceptance.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the session + long-term memory schema for a multi-turn agent of your choice (or use the sales-agent brief above). Produce:

1. **The state schema.** List the keys you'd store, each with its **scope prefix** (`session`, `user:`, `app:`, or `temp:`) and a one-line justification. For each `user:` key, add a freshness field (a "last updated" timestamp) or state *why* it doesn't need one.
2. **The long-term memory policy.** What goes into the `MemoryService` (episodic vs. semantic), *when* it's written (session end? every turn?), and *how* it's retrieved (`load_memory` on demand vs. `preload_memory` every turn) — and why, in one sentence.
3. **The three failure modes, concretely.** For staleness, contradiction, and leakage: write the specific scenario in *your* domain, and name the schema decision that prevents it. If a prevention is missing, flag it — that's the point.
4. **The never-store list.** Name three things your agent must *not* put in memory, and where each belongs instead (secrets manager, ephemeral context, etc.).
5. **Write the ADR.** "Memory scope & freshness policy" — the scoping rule, the consolidation choice, and the residual risk you're accepting.

**Why this exercise matters.** Memory is where the harness stops being a stateless function and becomes something that *persists* — and persistence is a correctness and governance commitment, not a checkbox. The schema you just designed is the difference between an agent that remembers *helpfully* and one that remembers *stale, contradictory, and leaking*.

---

**In DSH:** memory is `core/session` (the append-only `SessionEvent` log — the single source of truth), with `storage` for persistence and `scope` for per-agent registration boundaries (the analog of this module's `user:`/`app:` scoping).

## Sources (ADK docs)

- [Session, State & Memory — concepts](https://adk.dev/sessions/index.md)
- [State: the session's scratchpad (prefixes, update paths, `{key}` templating)](https://adk.dev/sessions/state/index.md)
- [Memory: long-term knowledge with MemoryService](https://adk.dev/sessions/memory/index.md)

---

**Next module:** [M8 — Tool Interfaces](../08-tool-interfaces/README.md) — how the model reaches the world safely: contracts, error semantics, and capability boundaries.
