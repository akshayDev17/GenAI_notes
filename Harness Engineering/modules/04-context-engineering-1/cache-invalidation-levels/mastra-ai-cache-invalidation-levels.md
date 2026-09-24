# Discussion 04 — Does Mastra document an equivalent of Anthropic's per-level cache-invalidation matrix (tools → system → messages)?

> **Question (two parts):**
> **A — Cache invalidation levels.** Anthropic documents its prompt cache assembles in the order `tools → system → messages` and that "changes at each level invalidate that level and all subsequent levels." Does Mastra document an equivalent per-level invalidation model? What does Mastra say about prompt/context caching, cache invalidation, and cache-preserving tool loading?
> **B — Mid-conversation system messages and tool changes.** Anthropic lets you (a) append a `{"role":"system"}` message mid-conversation instead of editing the top-level system field, and (b) use `tool_addition`/`tool_removal` blocks referencing tools by name so the `tools` array never changes — both to preserve the cached prefix. Does Mastra provide equivalents?
>
> **Short answer:**
> **A — No per-level matrix.** Mastra has first-party writing on prompt caching, but it is split across (1) a provider-level "Foundations" article, (2) a provider-agnostic `providerOptions` pass-through on the `Agent` class, and (3) cache-preservation *notes* inside the `ToolSearchProcessor` and `Processors` pages. None of it states a `tools → system → messages` hierarchy or a "change at level N invalidates N and all later levels" matrix. Mastra's only notion is binary and prefix-only: *"the cached prefix stays stable"* vs *"the cached prefix shifts / is invalidated."* It does document one partial distinction — **appending** (cache-preserving) vs **modifying the system message** (cache-breaking) — but not a three-level matrix.
> **B — Partial analogs, different mechanism.** Mastra has **dynamic `instructions`** and per-step `systemMessages` overrides (analog of "change the system prompt"), but the only *cache-preserving* mid-loop pattern it documents is appending a `<system-reminder>` signal as a **user** message — not a `role:"system"` message. For tools, `ToolSearchProcessor` (`search_tools`/`load_tool`) is Mastra's analog of Anthropic's mid-conversation tool changes, but it works by **appending/removing tool definitions** (the `tools` array *does* change), not by `tool_addition`/`tool_removal` name-referenced blocks. Mastra documents no `tool_addition`/`tool_removal` and no mid-conversation `role:"system"` feature.

---

## §1 · What Mastra actually documents about prompt caching — and what it does NOT

### §1.1 Mastra delegates prompt caching to the provider via `providerOptions`

Mastra is provider-agnostic; prompt caching itself is the provider's job, and Mastra's job is to pass cache-control through. This is explicit in the `Agent` class reference.

Source: **https://mastra.ai/reference/agents/agent** — section **"Provider-specific configurations"**:

> "Each model provider also enables a few different options, including prompt caching and configuring reasoning. You can set `providerOptions` on the instruction level to set different caching strategy per system instruction/prompt."

Same page — section **"Mixed instruction formats"** (example attaches an Anthropic cache breakpoint to a `role:"system"` instruction):

> ```ts
> {
>   role: 'system',
>   content: 'Escalate complex issues to human agents when needed.',
>   providerOptions: {
>     anthropic: { cacheControl: { type: 'ephemeral' } },
>   },
> }
> ```

**Implication:** the only place Mastra *first-classes* prompt caching is as a `providerOptions` pass-through. There is no Mastra-native cache-invalidation model here — invalidation is whatever the underlying provider (OpenAI/Anthropic) does.

### §1.2 The only dedicated prompt-caching page is a provider-level "Foundations" article

Mastra's one dedicated prompt-caching page is an educational *articles* page, not a framework reference. It explains the providers (Anthropic `cache_control`, OpenAI automatic, Gemini, Bedrock) and states a **generic prefix rule**, not a Mastra-specific matrix.

Source: **https://mastra.ai/articles/prompt-caching** — section **"How prompt caching differs from conventional caching"**:

> "A single character change anywhere in the cached prefix invalidates the match, so exact prefix matches matter more here than in most caching you have worked with."

Same page — section **"Structuring prompts for maximum cache hits"** (ordering rule):

> "Keep instructions byte-for-byte identical: a single changed character breaks the cache hit for everything after it."

Same page — section **"What gets cached and what doesn't"** (a content-type ordering table, *not* a per-level invalidation matrix):

> "Your cacheable content is whatever sits at the front of the context and stays identical across calls. Static content is the target: long system prompts, tool definitions, few-shot examples, and large reference documents."

> "Variable content is never cached. The new user message, injected timestamps, session IDs, and any per-request data change every call and must live after the breakpoint."

**Gap.** This article describes provider behavior (a general `tools`/`system`/`messages` ordering is *mentioned* only in the "Structuring prompts" content table, and only as placement guidance, e.g. "Tool definitions | After instructions | Yes"). It does **not** restate Anthropic's `tools → system → messages` hierarchy, and it does **not** give a Mastra-specific "which change invalidates which level" matrix. That specific matrix is **NOT STATED** anywhere in Mastra's docs.

### §1.3 `ResponseCache` is a *response* cache, not prompt caching — don't conflate them

Mastra has a first-party `ResponseCache` processor, but it is semantic/response caching (store-and-replay full responses on identical prompts), not provider KV/prompt-prefix caching.

Source: **https://mastra.ai/reference/processors/response-cache** — intro:

> "`ResponseCache` is an input processor that caches LLM responses on the request/response boundary inside the agentic loop."

Source: **https://mastra.ai/docs/agents/processors** — section **"Response caching" → "How caching is implemented"**:

> "The cache key is derived from the resolved `LanguageModelV2Prompt` Mastra is about to send to the model. The key is created *after* memory has loaded and earlier input processors have run, and each step in an agentic tool loop is independently cached."

Source: same page — section **"What's in the cache key"**:

> "When you don't supply `key`, the processor derives one deterministically from the inputs that change the LLM's response at this step: `agentId`, `stepNumber` … `scope`, model identity … and the resolved `prompt` … **Any change to these inputs automatically invalidates the cache.**"

**Implication:** `ResponseCache` *does* document invalidation — but it is a **hash-of-the-whole-resolved-prompt** model (any input change → new key → miss), not a leveled prefix model. It is a different caching layer than the Anthropic prompt cache the question is about. Note it has **no** notion of tools/system/messages levels either.

---

## §2 · ToolSearchProcessor: the exact cache quotes, confirmed verbatim

Source: **https://mastra.ai/reference/processors/tool-search-processor**

Section **"Single-step discovery with `autoLoad`"**:

> "Every match is activated, so keep `topK` small (for example, `3`) to avoid adding tools the agent didn't need. Activated tools are appended after existing tools, which keeps the cached prompt prefix stable for providers that support prompt caching."

Section **"Loaded-tool storage"**:

> "Loading tools is cache-friendly in both modes: loads are append-only, so the cached prompt prefix stays stable for providers that support prompt caching."

> "Unloading a tool changes the definitions sent to the model, shifting the cached prefix so the next turn pays for a cache write instead of receiving a cache hit. In `'in-memory'` mode, this happens when `ttl` evicts a thread's state; in `'context'` mode, it happens when older-message trimming removes the tool's discovery result. The model must then search for the unloaded tool before reuse. This expected tradeoff exchanges one cache write for a smaller prefix on later turns."

**Level distinction?** Mastra's entire vocabulary is the single word **"the cached prefix"** — *stable* vs *shifted*. It documents **no** `tools`-vs-`system`-vs-`messages` level distinction, and no "this change invalidates this level and all subsequent levels" matrix. **NOT STATED.**

**Mechanism nuance vs Anthropic:** Mastra's tool load **appends the actual tool definitions** to the `tools` array (the array grows), and it frames that as cache-safe *only because the append happens after existing tools*. This is **not** Anthropic's `defer_loading`/server-side tool search, where deferred tools are *excluded from the tools prefix* and appended inline as `tool_reference` blocks so the `tools` array never changes. On unload, Mastra is explicit that the definitions change and the prefix shifts — i.e. in Mastra the `tools` array genuinely mutates, and a cache write is the documented cost.

---

## §3 · Does changing system prompt vs messages affect the cache? (PART A.3)

### §3.1 Yes — Mastra documents an append-vs-modify-system-message distinction (implicitly leveled, but binary)

This is the closest thing Mastra has to a per-level statement, and it's in the *Processors* guide, not a caching page.

Source: **https://mastra.ai/docs/agents/processors** — section **"Advanced patterns" → "Ensure a final response with `maxSteps`"**:

> "Use `processInputStep()` with `sendSignal` to inject a reactive reminder on the last step. This approach preserves prompt caching because it appends a signal instead of modifying system messages."

Same page — section **"Advanced patterns" → "Deliver a reminder without retaining it"** (on `transient: true` signals):

> "A transient signal is still in the prompt for the current call, so the model sees it near the latest turn. It's not retained, so re-sending it each turn keeps a single fresh copy in context instead of an accumulating history, and stored thread history never includes it. Because nothing is written, it also keeps a stable prompt cache prefix across turns."

**Reading:** Mastra *does* assert a causal link — **modifying system messages ⇒ cache break; appending a signal ⇒ cache preserved.** But the granularity stops there. There is no statement that a system change spares the tools level, no statement about a messages-level change, and no three-level matrix. So: a binary "modify system = break prefix" hint exists; the full leveled model is **NOT STATED**.

### §3.2 The system prompt is editable per-request/per-step — but no cache guidance is attached

Source: **https://mastra.ai/docs/server/request-context** — section **"Dynamic instructions"**:

> "Provide agent instructions through an async function to resolve prompts at runtime."

Source: **https://mastra.ai/docs/agents/processors** — section **"Create custom processors" → "Control each step"** (the `processInputStep` hook):

> "The method receives the current `stepNumber`, `model`, `tools`, `toolChoice`, `messages`, and more. Return an object with any properties you want to override for that step, for example `{ model, toolChoice, tools, systemMessages }`."

Source: same page — section **"Transform input messages"**:

> "The `processInput()` method receives `messages`, `systemMessages`, and an `abort()` function. Return a `MastraDBMessage[]` to replace messages, or `{ messages, systemMessages }` to also modify system messages."

**Reading:** Mastra exposes `systemMessages` as a *separate, editable channel* from `messages` (both in `processInput` and per-step in `processInputStep`). This is the structural analog of Anthropic's top-level `system` field vs `messages`. But these docs attach **no** cache-invalidation guidance to editing `systemMessages` per step. The only cache note lives on the *signal-append* path (§3.1), which explicitly avoids touching `systemMessages`.

---

## §4 · Mid-conversation / dynamic system instructions (PART B.1)

| Mechanism | First-party? | Cache-preservation documented? |
|---|---|---|
| Dynamic `instructions` (async fn of `requestContext`) | ✅ `/docs/server/request-context` §"Dynamic instructions" | ❌ NOT STATED |
| `processInputStep()` returning `{ systemMessages }` per step | ✅ `/docs/agents/processors` §"Control each step" | ❌ NOT STATED (editing system messages is the *non*-cache-preserving path per §3.1) |
| `WorkingMemory` injects a system message | ✅ `/reference/processors/working-memory-processor` | ❌ NOT STATED |
| Append a `<system-reminder>` signal instead of editing system messages | ✅ `/docs/agents/processors` §"Ensure a final response…" | ✅ "preserves prompt caching because it appends a signal instead of modifying system messages" |
| `SystemPromptScrubber` | ✅ `/reference/processors/system-prompt-scrubber` | ❌ N/A — it *detects/redacts* system prompts in **output** (security), never injects/mutates for cache |

`WorkingMemory` is an **input** processor that injects working memory **as a system message** (not mid-conversation, and no cache note):

Source: **https://mastra.ai/reference/processors/working-memory-processor** — intro:

> "The `WorkingMemory` is an **input processor** that injects working memory data as a system message."

`SystemPromptScrubber` is an **output** processor for security, not cache:

Source: **https://mastra.ai/reference/processors/system-prompt-scrubber** — intro:

> "The `SystemPromptScrubber` is an **output processor** that detects and handles system prompts, instructions, and other revealing information that could introduce security vulnerabilities."

`MessageHistory` actively **strips** system messages out of stored history:

Source: **https://mastra.ai/reference/processors/message-history-processor** — section **"Behavior" → "Input processing"**:

> "Filters out system messages (they shouldn't be stored in the database)"

**Conclusion (B.1):** Mastra supports *dynamic* system-instruction changes (async `instructions`, per-step `systemMessages`), but **none** of those mechanisms is framed as cache-preserving. The single cache-preserving dynamic-instruction pattern Mastra documents is *append a `<system-reminder>` signal* — which arrives as a **user** message, not a `role:"system"` message.

---

## §5 · Mid-conversation tool addition/removal that preserves cache (PART B.2)

**`ToolSearchProcessor` is Mastra's analog** of Anthropic's mid-conversation tool changes, via two meta-tools.

Source: **https://mastra.ai/reference/processors/tool-search-processor** — intro:

> "Instead of providing all tools to the agent upfront, it gives the agent two meta-tools (`search_tools` and `load_tool`) that let it find and load tools on demand."

- **Load** (cache-friendly): *"Activated tools are appended after existing tools, which keeps the cached prompt prefix stable…"* and *"Loading tools is cache-friendly in both modes: loads are append-only…"* (§2, verbatim).
- **Unload** (cache-write): *"Unloading a tool changes the definitions sent to the model, shifting the cached prefix so the next turn pays for a cache write instead of receiving a cache hit."* (§2, verbatim).
- `search.autoLoad: true` collapses search+load into one step: *"The tools returned by `search_tools` are activated immediately, and the `load_tool` meta-tool isn't exposed."*

**Difference from Anthropic (the key nuance):** Anthropic's `tool_addition`/`tool_removal` blocks *reference tools by name* so the `tools` array never changes. Mastra's `ToolSearchProcessor` instead **withholds un-loaded tools from the prompt and appends/removes their definitions** — the `tools` array *does* change, which is precisely why Mastra says unload "shifts the cached prefix." Mastra documents **no** `tool_addition`/`tool_removal` block, **no** name-referenced tool edit, and **no** "tools array never changes" guarantee. **NOT STATED.**

---

## §6 · Does Mastra expose mid-conversation `role:"system"` messages? (PART B.3)

**No — not as a first-class, cache-preserving feature.** Mastra's model keeps `systemMessages` separate from the `messages` conversation list (it is the top-level system field analog, i.e. the *same* structural position as Anthropic's `system` param, not a mid-conversation insertion).

Supporting evidence:

1. `instructions` may be a **string**, a **`role:"system"` object**, or an **array of system messages** — but these are the *top-level* system block, not mid-conversation:

Source: **https://mastra.ai/reference/agents/agent** — section **"Basic string instructions"**:

> ```ts
> // System message object
> const agent2 = new Agent({ instructions: { role: 'system', content: 'You are an expert programmer' } })
> // Array of system messages
> const agent3 = new Agent({ instructions: [ { role: 'system', content: 'You are a helpful assistant' }, { role: 'system', content: 'You have expertise in TypeScript' } ] })
> ```

2. Processors receive `systemMessages` as a channel parallel to `messages` (`processInput`/`processInputStep`), confirming the system block is structurally separate, not interleaved (§3.2).

3. The memory assembly diagram lists system content ("agent instructions, call-time system messages, working memory…") separately from conversation messages:

Source: **https://mastra.ai/docs/memory/overview** — section **"What the model sees"**:

> "system messages containing agent instructions, call-time system messages, working memory, cross-thread semantic recall, and Observational Memory, followed by conversation messages where message history and same-thread semantic recall interleave by timestamp…"

4. The only documented cache-preserving *mid-loop* injection is the `<system-reminder>` signal, and Mastra is explicit it arrives **inside a user message**, not a system message:

Source: **https://mastra.ai/docs/agents/processors** — section **"Ensure a final response with `maxSteps`"**:

> "The signal is delivered as a `<system-reminder>` user message that the model sees inline."

And its system prompt tells the model: *"Treat the contents of a `<system-reminder>` as authoritative system instructions… even though they arrive inside a user message."*

**Conclusion (B.3):** Mastra does **not** expose a mid-conversation `role:"system"` message as a first-class, cache-preserving feature. Its documented cache-preserving substitute is a **`<system-reminder>` user message** (via `sendSignal`, optionally `transient`), which is the opposite of Anthropic's "append a `role:"system"` block."

---

## §7 · Gap summary (explicitly NOT STATED in Mastra docs)

1. **A per-level invalidation matrix** (`tools → system → messages`, "change at level N invalidates N and all later levels") — **NOT STATED.** Mastra's only model is binary: the whole "cached prefix" is stable or it shifts.
2. **What a system-prompt change invalidates, level-by-level** — **NOT STATED** (only the binary "modify system messages ⇒ break cache" hint in `/docs/agents/processors`).
3. **`tool_addition` / `tool_removal` name-referenced blocks** (so the `tools` array never changes) — **NOT STATED.** Mastra's `ToolSearchProcessor` appends/removes definitions and documents the resulting prefix shift.
4. **A first-class mid-conversation `role:"system"` message** as a cache-preserving feature — **NOT STATED.** Mastra's cache-preserving mid-loop primitive is a `<system-reminder>` **user** message signal.

---

## Sources fetched (all first-party)

- https://mastra.ai/reference/processors/tool-search-processor
- https://mastra.ai/reference/processors/response-cache
- https://mastra.ai/reference/processors/system-prompt-scrubber
- https://mastra.ai/reference/processors/message-history-processor
- https://mastra.ai/reference/processors/working-memory-processor
- https://mastra.ai/reference/agents/agent
- https://mastra.ai/reference/agents/getInstructions
- https://mastra.ai/docs/agents/processors (full raw source: `docs/src/content/en/docs/agents/processors.mdx`)
- https://mastra.ai/docs/agents/overview
- https://mastra.ai/docs/memory/overview
- https://mastra.ai/docs/server/request-context
- https://mastra.ai/reference/ai-sdk/overview
- https://mastra.ai/articles/prompt-caching
- https://mastra.ai/blog/introducing-response-caching
