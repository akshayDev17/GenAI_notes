# Discussion 02 — Does injecting dynamic memory into the stable prefix destroy prompt-cache hits?

> **Question:** If a harness injects dynamic per-request state (session state, retrieved agentic memory, or other per-turn-varying content) INTO the stable-prefix region of the prompt, does that destroy prompt-cache hits?
>
> **Short answer: Yes, unconditionally.** All three vendors key the cache on the *byte-for-byte identical prefix*; any injected byte that changes inside the prefix region changes the prefix hash and turns a would-be cache read into a fresh cache write. The fix is always the same structural move: **stable prefix, variable tail.**

---

## §1 · The seven memory kinds: byte-stable vs. dynamic

Taxonomy from the course module [`modules/07-memory-state/README.md`](../../modules/07-memory-state/README.md) (table "The memory taxonomy: seven types, two axes, four scopes"). Classification here answers: *when this kind is placed in the prompt, are its bytes identical across turns?*

| Memory kind | Stable vs. dynamic | Where it must live | One-line justification |
|---|---|---|---|
| **Procedural** | **STABLE** | cacheable prefix (instruction / system prompt) | Module: "**Static, versioned** · The instruction"; it changes only at release, so it is the canonical cacheable prefix. |
| **Parametric** | **STABLE — not in prompt** | nowhere (model weights) | Module: "**Frozen at training time** · The weights"; never injected into the prompt, so it can never invalidate a cache. |
| **Prospective** | **OUT-OF-BAND** (DYNAMIC if naïvely injected) | scheduler/queue, never the prompt | Module: "A scheduler or task queue — **never** the `MemoryService`"; a live "pending tasks" list would change as tasks fire, so if forced into context it is a varying tail. |
| **Working / in-context** | **DYNAMIC** (but the already-sent history is the reuseable prefix) | tail (new user message, tool result, state delta) | Module: "The prompt, rebuilt every turn"; the *new* turn is the varying suffix — the accumulated history is precisely what multi-turn caching reuses. |
| **Semantic** | **DYNAMIC** | tail | Module: "**Long-term, searchable** · An external store"; the retrieved fact is a per-turn `search_memory` result that differs by query/user. |
| **Episodic** | **DYNAMIC** | tail | Module: "What *happened* … Long-term, searchable"; retrieved episodes/reflections differ per session (`load_memory` / `preload_memory`). |
| **External / retrieval** | **DYNAMIC** | tail | Module: "Whatever you … fetched back: docs, records, prior runs"; the fetched content varies per query, so it is per-turn data. |

**The bridging insight (working memory is both):** the already-emitted conversation history is byte-stable and is *the thing caching exploits* ("the growing message history should be cached automatically" — Anthropic, below); the *new* turn's increment (new message, tool result, state) is the varying tail. So "working memory" straddles the line — its prefix is cacheable, its delta is not.

---

## §2 · Where to place dynamic state: the "stable prefix, variable tail" principle (vendor docs)

### Anthropic — explicitly stated
Source: **https://platform.claude.com/docs/en/build-with-claude/prompt-caching** — section **"Structuring your prompt"**:

> "Place static content (tool definitions, system instructions, context, examples) at the beginning of your prompt. Mark the end of the reusable content for caching using the `cache_control` parameter."

Same page, section **"How automatic prefix checking works" → "Key takeaway"**:

> "**Key takeaway:** Place `cache_control` on the last block whose prefix is identical across the requests you want to share a cache. … For a prompt with a varying suffix (timestamps, per-request context, the incoming message), place the breakpoint at the end of the static prefix, not on the varying block."

Same page, section **"Best practices for effective caching"**:

> "Place cached content at the prompt's beginning for best performance." … "Place the breakpoint on the last block that stays identical across requests. For a prompt with a static prefix and a varying suffix (timestamps, per-request context, the incoming message), that is the end of the prefix, not the varying block."

### OpenAI — explicitly stated
Source: **https://developers.openai.com/api/docs/guides/prompt-caching** — section **"How to optimize prompt caching → Preserve conversation history"**:

> "**Keep the prefix stable.** Put stable developer instructions and shared reference material first. If developer instructions or shared material contain timestamps, user-specific content, or other dynamic content, place those at the end rather than the beginning, or move them into later conversation messages."

The same section's code sample is titled **"Keep changing content after the breakpoint"** and shows the exact harness pattern — a breakpoint after stable instructions, then a developer block of *"Dynamic developer instructions, such as user-specific content and timestamps..."*, then the user message.

Section **"Choose a caching mode"**:

> "**Choose breakpoints deliberately.** Place explicit markers at the end of stable content. Use explicit-only mode to avoid unnecessary cache writes for changing suffixes."

### Gemini — partially stated (implicit-caching form)
Source: **https://ai.google.dev/gemini-api/docs/caching** — section **"Implicit caching"**:

> "To increase the chance of an implicit cache hit: Try putting large and common contents at the beginning of your prompt; Try to send requests with similar prefix in a short amount of time."

This states "static content first" but does **not** use the words "dynamic content last." The explicit-caching API (a `CachedContent` resource = the fixed prefix, per-request `contents` = the tail) is documented at https://ai.google.dev/gemini-api/docs/generate-content/caching — that model *structurally* separates stable (cached) from dynamic (request), but the ordering sentence is **NOT STATED** there in the same wording.

### ADK (Gemini wrapper) — mechanism, not the slogan
Source: **https://adk.dev/context/caching/index.md** — it does **not** state "static first, dynamic last" in prose. It provides the `static_instruction` parameter as the stable side of the seam:

> "If your use case requires that you provide instructions that are used throughout a session, consider using the `static_instruction` parameter for an agent, which allows you to amend the system instructions for a generative model."

…and it reveals the cache is keyed on a "cacheable prefix" that must stay unchanged: (section **"Check whether the cache is being used"**, on `CacheMetadata`) "a fingerprint-only state … is the first turn, a prefix that changed since the last turn, or a cache ADK did not create"; and "ADK keeps reusing a cache until it is actually past `expireTime`, has run past `cacheIntervals`, **or its cached prefix changes**."

---

## §3 · What specifically breaks an Anthropic cache, and is it certain?

**Yes — injecting a retrieved memory into the system prompt (the stable prefix) breaks the cache, and the docs make this certain through three independent statements.**

(1) The system prompt *is part of the cached prefix*. Anthropic, section **"How prompt caching works"**, tip **"Prompt caching caches the full prefix"**:

> "Prompt caching references the entire prompt - `tools`, `system`, and `messages` (in that order) up to and including the block designated with `cache_control`."

(2) The **exact-matching requirement**. Anthropic, section **"Cache storage and sharing"**:

> "**Exact matching:** Cache hits require 100% identical prompt segments, including all text and images up to and including the block marked with cache control."

(3) Any byte change before/at the breakpoint changes the cache key. Anthropic, section **"Structuring your prompt" → "How automatic prefix checking works" → "Three core principles"**:

> "Cache writes happen only at your breakpoint. Marking a block with `cache_control` writes exactly one cache entry: a hash of the prefix ending at that block. … Because the hash is cumulative, covering everything up to and including the breakpoint, changing any block at or before the breakpoint produces a different hash on the next request."

And the invalidation hierarchy (section **"What invalidates the cache"**):

> "Modifications to cached content can invalidate some or all of the cache. … the cache follows the hierarchy: `tools` → `system` → `messages`. Changes at each level invalidate that level and all subsequent levels."

The same page's worked counter-example is the exact scenario in question — a per-request timestamp injected into the prefix (section **"Common mistake: Breakpoint on content that changes every request"**):

> "Your prompt has a large static system context (blocks 1 through 5) followed by a per-request block containing a timestamp and the user message (block 6). … **Request 2:** The timestamp differs, so the prefix hash at block 6 differs. … No cache hit. You pay for a fresh cache write on every request and never get a read."

Substitute "retrieved memory" for "timestamp" and the conclusion is identical: **certain, not probabilistic.** OpenAI states the same invariant independently (section **"What is the prompt cache?"**):

> "Cache reuse requires the entire rendered prefix to match. If content or a relevant setting changes before a breakpoint, the prefix after that change cannot match the existing cache entry."

---

## §4 · Getting BOTH dynamic memory retrieval AND cache hits

The answer is not "give up memory" — it is "put the dynamic part *after* the breakpoint (or make the dynamic part load out-of-band)." Every mechanism is documented:

1. **Put memory in the tail, breakpoint at the end of the static prefix.** This is the §2 principle applied directly.
   - Anthropic (section **"When to use multiple breakpoints"**): "You can define up to 4 cache breakpoints if you want to … Cache different sections that change at different frequencies (for example, tools rarely change, but context updates daily)."
   - OpenAI (section **"Gotchas → A shared prefix is not always a cached prefix"**): without a breakpoint after static content, "the first request writes through the dynamic content. Changing that content in the next request does not match the longer cached prefix … To remediate, place an explicit breakpoint after the static content in both requests."

2. **Dynamic tool loading keeps the stable prefix intact** (the "tool-search / defer_loading" mechanism — directly analogous to load-on-demand memory).
   - Anthropic, **https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching**, section **"defer_loading and cache preservation"**:
     > "Deferred tools are not included in the system-prompt prefix. When the model discovers a deferred tool through tool search, the definition is appended inline as a `tool_reference` block in the conversation history. The prefix is untouched, so prompt caching is preserved." … "This means adding tools dynamically through tool search does not break your cache."
   - OpenAI (section **"Manage tools with append-only updates"**):
     > "**Load tools when needed.** Use tool search with `defer_loading: true` … Discovered tools are appended at the end of context, preserving earlier reusable content."

3. **Append a new system message instead of editing the top-level system field** (add dynamic instructions *after* the cached prefix rather than mutating it).
   - Anthropic, section **"What invalidates the cache"** (invalidation-table note, "Mid-conversation system messages"):
     > "you can add a new system instruction partway through a conversation without invalidating the system or message caches. Append a `{"role": "system"}` message to `messages` instead of editing the top-level `system` field, so the cached prefix stays unchanged."

4. **ADK's `static_instruction` parameter** separates stable instructions from the per-turn (dynamic) session/messages — see §2 ADK quote. This is the harness-level encoding of the same seam.

**Summary of the mechanism space:** (a) memory lookups appended in the variable tail after a breakpoint; (b) `defer_loading` / tool-search so the dynamic retrieval result is appended after the prefix rather than spliced into it; (c) append-only system messages rather than in-place prefix edits; (d) multiple breakpoints so "changes daily" content is its own segment. All four preserve the byte-stable prefix and therefore preserve cache hits.

---

## Source inventory

- **Anthropic — Prompt caching:** https://platform.claude.com/docs/en/build-with-claude/prompt-caching (and `…/prompt-caching.md`)
- **Anthropic — Tool use with prompt caching:** https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching
- **OpenAI — Prompt caching:** https://developers.openai.com/api/docs/guides/prompt-caching (redirects from https://platform.openai.com/docs/guides/prompt-caching)
- **Gemini — Context caching (implicit):** https://ai.google.dev/gemini-api/docs/caching
- **Gemini — Context caching (explicit):** https://ai.google.dev/gemini-api/docs/generate-content/caching
- **ADK — Context caching:** https://adk.dev/context/caching/index.md
- **Course module (7-way taxonomy):** `modules/07-memory-state/README.md`
