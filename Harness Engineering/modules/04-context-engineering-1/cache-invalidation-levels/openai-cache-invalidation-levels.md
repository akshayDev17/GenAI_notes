# Discussion 04 — Does OpenAI document cache-invalidation levels (tools → system → messages) and mid-conversation system/tool changes like Anthropic?

> **Question (Part A):** Anthropic documents a per-level invalidation hierarchy — cache assembled `tools → system → messages`, "changes at each level invalidate that level and all subsequent levels." Does OpenAI document an equivalent notion of *which* change invalidates *which* part of the cache? (tool changes vs. developer/system changes vs. message changes; and is it a "tools" level vs. "developer/system" level vs. "messages" level, or one flat prefix?)
>
> **Question (Part B):** Anthropic lets you (a) append a `{"role":"system"}` message mid-conversation instead of editing the top-level `system` field, and (b) use `tool_addition`/`tool_removal` blocks that reference tools by name so the `tools` array never changes — both to preserve the cached prefix. Does OpenAI provide equivalents? Does the OpenAI Agents SDK expose any of this?
>
> **Short answer:** **OpenAI has NO per-level invalidation matrix.** Its cache is a **single flat prefix** with "breakpoints"; the only invalidation rule is "the entire rendered prefix must match" + a flat table of *settings that affect the cached prefix*. There is no `tools → system → messages` ordering and no "changing tools invalidates tools+system+messages" matrix. For Part B: OpenAI's functional analogue of (a) is the **`developer` role with append-only messages** (not literally "system", and not the exact Anthropic sentence), and of (b) is the **`additional_tools` input item** — but it is *add-only* (there is no `tool_removal` block; removal is done by omitting a tool from `tool_search_output`, which OpenAI says **will** break the cache). The open-source Agents SDK exposes tool search (`ToolSearchTool`/`defer_loading`) but documents **nothing** about per-level invalidation or a cache-preserving mid-conversation tool add/remove.

---

## §1 · Part A — What invalidates OpenAI's cache: a flat "match the prefix" rule, not a level matrix

Source: **https://developers.openai.com/api/docs/guides/prompt-caching** — section **"What is the prompt cache?"**:

> "OpenAI caches the model's full rendered context including OpenAI-provided instructions, [developer messages](https://developers.openai.com/api/docs/guides/prompt-engineering#message-roles-and-instruction-following), [tool definitions](https://developers.openai.com/api/docs/guides/function-calling), and [conversation history](https://developers.openai.com/api/docs/guides/conversation-state)…"

> "Cache reuse requires the entire rendered prefix to match. If content or a relevant setting changes before a breakpoint, the prefix after that change cannot match the existing cache entry."

Section **"Which settings affect the cached prefix?"**:

> "Changing a request does not necessarily discard an existing cache entry. What matters is whether a subsequent request has the same prefix and can find an eligible matching breakpoint."

The closest thing OpenAI has to "which change invalidates what" is a flat table of *settings* (not message roles). Verbatim rows:

| Setting | Impact (verbatim) |
|---|---|
| `model` | "A different model can use different weights and caching behavior." |
| `tools` | "Changes tool names, descriptions, schemas, ordering, or tool-specific instructions." |
| `parallel_tool_calls` | "Can change instructions about calling multiple tools in one turn." |
| `text.format` (Structured Outputs) | "Adds output-format instructions and the requested schema." |
| `reasoning.effort` | "Can change model-side reasoning instructions. On supported models, use a [configuration update] to change effort while preserving the earlier prefix." |
| `text.verbosity` | "Can change instructions about response detail." |
| `context_management` (Compaction) | "Replaces earlier conversation content with a compacted context that can prevent reuse from the first changed token onward." |

**Conclusion:** OpenAI *does* document what invalidates a cache, but as **flat rules + a settings table**, not as Anthropic's "changes at each level invalidate that level and all subsequent levels." A `tools` change is described as invalidating because it changes the prefix — there is no statement that it also ripples through a "system" and "messages" level, because those levels don't exist as separate entities in OpenAI's model.

---

## §2 · Part A — One flat prefix, not a tools/developer/messages hierarchy

Source: **https://developers.openai.com/api/docs/guides/prompt-caching** — section **"How caching works"**:

> "A **cache breakpoint** marks the end of a prompt prefix that OpenAI can save to the cache and reuse in later requests."

Section **"What is the prompt cache?"**:

> "Prompt caching preserves that state for a reusable **prefix**: the unchanged tokens at the beginning of a prompt." … "The prompt cache stores key-value (KV) tensors, not the tokens themselves."

The only "levels" OpenAI enumerates are *which messages get an automatic breakpoint*, not invalidation levels. Section **"How caching works → GPT-5.6 and later"** (implicit mode):

> "Eligible messages are: user messages, the last tool response in a consecutive group of tool responses, the last developer message in the initial consecutive group of developer messages."

There **is** a rendering-order hint that *loosely* parallels Anthropic's `tools → system → messages`, but it is framed as breakpoint placement, not invalidation. Section **"How to optimize prompt caching → Choose a caching mode"**:

> "Illustration: In explicit-only mode, tools and schemas precede a stable developer-message prefix and breakpoint 1."

And section **"Cache location"** confirms tools sit in the hashed head of the prefix:

> "A hash of the initial tokens after the hidden OpenAI content, including tool definitions when present."

**Conclusion:** **No `tools` / `developer` / `messages` levels, and no per-level invalidation matrix.** It is a single flat rendered prefix delimited by breakpoints. The exact Anthropic sentence "changes at each level invalidate that level and all subsequent levels" has **no OpenAI equivalent** — **NOT STATED**.

---

## §3 · Part A — The tool-search quotes the brief asked to confirm

Source: **https://developers.openai.com/api/docs/guides/tools-tool-search**

Intro (no heading):

> "Tool search allows the model to dynamically search for and load tools into the model's context as needed. … For optimal cost and latency, tool search is designed to **preserve the model's cache**. When new tools are discovered by the model, they are injected at the end of the context window."

Section **"Advanced usage → Tool search and caching"**:

> "All tools are loaded at the end of the model's context window. This holds true for both hosted tool search and client-executed tool search. This allows the model's cache to be preserved from one request to another, lowering overall costs and boosting speed."

Section **"Advanced usage → Understand what gets loaded"**:

> "`tool_search_output.tools` contains the list of tools that were dynamically loaded by the model. … Tools that were not listed as part of this array will not be available to the model. If you want to disable a loaded tool, you can remove it from the `tool_search_output` item where you define the loaded tool set, but note that **changing the loaded tool set will break the model's cache from that point forward**."

All three quotes confirmed verbatim. Note the last one is the *opposite* of Anthropic's `tool_removal`: OpenAI's own way to remove a loaded tool is documented as **breaking** the cache, whereas Anthropic's `tool_removal` block exists specifically to *preserve* it.

---

## §4 · Part B — "Append a developer message instead of editing": functional equivalent, not the exact sentence

OpenAI's role is **`developer`** (Responses API), not `system`. The exact Anthropic sentence "append a `{"role":"system"}` message instead of editing the top-level `system` field" is **NOT STATED** for OpenAI. The functional equivalent *is* present:

Source: **https://developers.openai.com/api/docs/guides/prompt-caching** — section **"How to optimize prompt caching → Preserve conversation history"**:

> "**Keep the prefix stable.** Put stable developer instructions and shared reference material first. If developer instructions or shared material contain timestamps, user-specific content, or other dynamic content, place those at the end rather than the beginning, or move them into later conversation messages."

> "**Preserve conversation history.** Append new messages rather than rewriting earlier turns. Summarization, [compaction], or context truncation can change the prefix and reset cache reuse."

The same section's JSON sample, titled **"Keep changing content after the breakpoint"**, is the concrete "append a second developer message" pattern — a stable developer message carrying `prompt_cache_breakpoint`, then a **second** developer message:

```json
"input": [
  { "role": "developer", "content": [ { "type": "input_text", "text": "Stable instructions and shared reference material...", "prompt_cache_breakpoint": { "mode": "explicit" } } ] },
  { "role": "developer", "content": "Dynamic developer instructions, such as user-specific content and timestamps..." },
  { "role": "user", "content": "The user's current question..." }
]
```

Also relevant — section **"Gotchas → Not all developer messages are automatic implicit mode cache lookup boundaries"** (developer messages after the initial block are *not* auto breakpoints, which is exactly why the second developer message can carry changing content):

> "In implicit mode, developer messages after the initial consecutive block of developer messages are not automatic cache lookup boundaries."

**Conclusion:** OpenAI's equivalent exists as *"append new messages rather than rewriting earlier turns"* + a worked multi-`developer`-message example, but the role is `developer` and there is no verbatim "append a developer message instead of editing the top-level field" instruction. The `prompt-caching` guide uses "developer messages," never the word "system message" for this technique.

---

## §5 · Part B — Mid-conversation tool changes: `additional_tools` is add-only; no `tool_removal`

Source: **https://developers.openai.com/api/docs/guides/tools-tool-search** — section **"Advanced usage → Add tools at a specific point in the input"**:

> "For advanced workflows, you can use an `additional_tools` input item to make tools available at a specific point in the conversation. This is useful when your application loads tools outside the normal tool search flow or needs to preserve the ordering of tools added during a previous response."

> "Set `role` to `developer` and include the tools to add in the item's `tools` array:"

> "Tools in an `additional_tools` item become available only after that item appears in the input. When you manually round-trip conversation items, preserve the item's position so the model sees the same tools at the same point in the conversation."

The prompt-caching guide also points at it (section **"Manage tools with append-only updates"**):

> "**Preserve tool-loading history.** Use a developer-role [`additional_tools` input item] to add tools during a thread according to your application's logic."

**Is it the tool-change equivalent of Anthropic's `tool_addition`/`tool_removal`?** **Partially.** `additional_tools` is the *addition* equivalent. There is **no `tool_removal` block** — Anthropic's removal block has **no OpenAI analogue**. OpenAI's only documented removal path (omit from `tool_search_output`) is documented to *break* the cache (§3), the opposite of Anthropic's intent. Two further constraints worth recording:

- Section **"How caching works → GPT-5.6 and later"** (prompt-caching.md): "`additional_tools` input items do not currently accept `prompt_cache_breakpoint`."
- The `additional_tools` mechanism is a **Responses API input item**, not a first-class SDK concept — the open-source SDK docs do not mention it (see §6).

---

## §6 · Part B — What the OpenAI Agents SDK exposes (and what it doesn't)

**Distinguish two different things:** the **open-source Agents SDK** (`openai-agents-python`, `openai-agents-js`) vs. the **server-side "Agents API"** (`platform.openai.com`, `client.beta.agents.*`). The tool-search guide's **"Agents API"** section is the *server-side* product, not the open-source SDK. Cited below accordingly.

### 6.1 Open-source Python SDK — tool search / `defer_loading`: YES

Source: **https://openai.github.io/openai-agents-python/tools/** — section **"Hosted tool search"**:

> "Tool search lets OpenAI Responses models defer large tool surfaces until runtime, so the model loads only the subset it needs for the current turn."

> "Add exactly one `ToolSearchTool()` when you configure deferred-loading surfaces on an agent." … "Searchable surfaces include `@function_tool(defer_loading=True)`, `tool_namespace(name=..., description=..., tools=[...])`, and `HostedMCPTool(tool_config={..., "defer_loading": True})`."

Client-executed tool search is **not** auto-handled by the Python Runner:

> "`ToolSearchTool(execution="client")` is for manual Responses orchestration. If the model emits a client-executed `tool_search_call`, the standard `Runner` raises instead of executing it for you."

### 6.2 Open-source Python SDK — conditional tool enabling (NOT a cache-preserving add/remove)

Source: **https://openai.github.io/openai-agents-python/tools/** — section **"Agents as tools → Conditional tool enabling"**:

> "You can conditionally enable or disable agent tools at runtime using the `is_enabled` parameter." … "Disabled tools are completely hidden from the LLM at runtime."

This is a **per-run visibility filter** (enable/disable the `tools` array before the request), and the docs do **not** tie it to cache preservation. It is **not** the mid-conversation `tool_addition`/`tool_removal` equivalent.

### 6.3 Open-source Python SDK — context page: no cache / invalidation language

Source: **https://openai.github.io/openai-agents-python/context/** — section **"Agent/LLM context"**:

> "When an LLM is called, the **only** data it can see is from the conversation history." … "You can add it to the Agent `instructions`. This is also known as a 'system prompt' or 'developer message'."

The words **cache**, **invalidation**, **breakpoint**, and **`additional_tools`** do not appear on this page. (Note it *does* confirm `instructions` == "system prompt"/"developer message", matching §4.)

### 6.4 Open-source JS SDK — tool search: YES (and it does support client execution)

Source: **https://openai.github.io/openai-agents-js/guides/tools** — section **"Deferred tool loading with tool search"**:

> "Tool search lets the model load only the tool definitions it needs at runtime instead of sending every schema up front."

Hosted-tools table (same page):

> "`toolSearchTool(options?)` … Pair it with deferred function tools or hosted MCP tools that set `deferLoading: true`. Supports hosted execution by default or client execution with `execution: 'client'` plus `execute`."

Also present: `toolNamespace({ name, description, tools })`, and **"Conditional tool availability"** via `isEnabled` (the JS mirror of Python's `is_enabled`).

**Python vs. JS difference:** the **JS** SDK's `toolSearchTool({ execution: 'client', execute })` supports client-executed tool search through the standard `run()` loop (for the built-in `{ paths: string[] }` shape), whereas the **Python** standard `Runner` raises on client-executed `tool_search_call`. (JS quote: "If you set `toolSearchTool({ execution: 'client', execute })`, the standard `run()` loop only supports the built-in `{ paths: string[] }` client query shape; custom client-side schemas require your own Responses loop.")

### 6.5 SDK gaps (marked NOT STATED)

- **Per-level invalidation (`tools → system → messages`):** **NOT STATED** in either SDK's docs. Neither `tools` page, `context` page, nor `sessions` page mentions any invalidation hierarchy or cache-breakpoint semantics.
- **Mid-conversation tool add/remove (`tool_addition`/`tool_removal` equivalent):** **NOT STATED** in either SDK. The SDKs expose *tool search* (`defer_loading` + `ToolSearchTool`) and *per-run* `is_enabled`/`isEnabled` filtering, but no name-referencing mid-conversation add/remove block, and no `additional_tools` input item in the documented SDK surface.
- **`defer_loading` as a cache-preserving device:** the SDK tool-search sections frame `defer_loading` purely as "reduce tool-schema tokens," and do **not** state the "loaded at the end of the context window → cache preserved" rationale that the platform tool-search guide states. (The platform guide's caching rationale is §3 above; the SDK does not repeat it.)

### 6.6 Server-side "Agents API" (for contrast, NOT the open-source SDK)

Source: **https://developers.openai.com/api/docs/guides/tools-tool-search** — section **"Agents API"**:

> "The [Agents API] loads function definitions eagerly by default. To defer selected functions, include `{ "type": "tool_search" }` in `agent.tools` and set `defer_loading: true` on each function you want the agent to discover on demand."

Section **"Agents API → Choose a function loading strategy"** (the one explicit cache-invalidation sentence in the whole tool-search guide):

> "Eager loading … Tradeoff: Unused definitions occupy context. **Changing a definition can invalidate a cached prefix.**"

---

## Source inventory

- **OpenAI — Prompt caching:** https://developers.openai.com/api/docs/guides/prompt-caching (and `…/prompt-caching.md`)
- **OpenAI — Tool search:** https://developers.openai.com/api/docs/guides/tools-tool-search (and `…/tools-tool-search.md`)
- **OpenAI Agents SDK (Python) — Tools:** https://openai.github.io/openai-agents-python/tools/ (source: `openai/openai-agents-python` `docs/tools.md`)
- **OpenAI Agents SDK (Python) — Context management:** https://openai.github.io/openai-agents-python/context/ (source: `docs/context.md`)
- **OpenAI Agents SDK (JS/TS) — Tools:** https://openai.github.io/openai-agents-js/guides/tools (source: `docs/src/content/docs/guides/tools.mdx`)
- **OpenAI Agents SDK (JS/TS) — Sessions:** https://openai.github.io/openai-agents-js/guides/sessions (source: `docs/src/content/docs/guides/sessions.mdx`)
- **Prior discussion (Anthropic invalidation matrix):** `discussions/03-mcp-tools-vs-cached-prefix.md`
- **Prior discussion (memory vs. prefix):** `discussions/02-prompt-caching-vs-memory-injection.md`
