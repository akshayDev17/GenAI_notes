# Discussion 05 — Does Google ADK / Gemini document cache-invalidation levels (tools → system → messages) and mid-conversation system/tool changes like Anthropic?

> **Question (Part A):** Anthropic documents a per-level invalidation hierarchy — cache assembled `tools → system → messages`, "changes at each level invalidate that level and all subsequent levels." Does Google ADK / Gemini document an equivalent notion of *which* change invalidates *which* part of the cache?
>
> **Question (Part B):** Anthropic lets you (a) append a `{"role":"system"}` message mid-conversation instead of editing the top-level `system` field, and (b) use `tool_addition`/`tool_removal` blocks that reference tools by name so the `tools` array never changes — both to preserve the cached prefix. Does ADK / Gemini provide equivalents?
>
> **Short answer:** **Neither ADK nor Gemini documents a per-level `tools → system → messages` invalidation matrix.** Gemini's model is a **flat "fixed prefix + per-request tail"**: implicit caching is keyed on "similar prefix" matching, and explicit caching is an *immutable* `CachedContent` prefix (which can contain `systemInstruction`, `contents`, `tools`, `toolConfig`) plus a separate per-request `contents`. ADK inherits that and only ever speaks of a single "**cached prefix**" — "ADK keeps reusing a cache until … its cached prefix changes." For Part B: ADK's `static_instruction` **is** the documented cache-preserving mid-session-instruction mechanism (it pins the system instruction and pushes the per-turn `instruction` into *user content*), but Gemini/ADK have **no** `tool_addition`/`tool_removal` name-referencing equivalent for mid-conversation tool changes — **NOT STATED**.

---

## §1 · Part A1 — ADK documents NO invalidation matrix; only "cached prefix changes"

Source: **https://adk.dev/context/caching/index.md** — section **"Check whether the cache is being used"**:

> "`expireSoon` means the cache expires within about two minutes, or has already expired. It is a signal for your own code, not something ADK acts on: ADK keeps reusing a cache until it is actually past `expireTime`, has run past `cacheIntervals`, or its cached prefix changes."

The same section's Kotlin sample annotates the fingerprint-only state (i.e., the state where no cache is being reused):

> "Not cached yet; fingerprinted … That is the first turn, a prefix that changed since the last turn, or a cache ADK did not create — most often because the cacheable prefix was below minTokens."

**Conclusion:** The only invalidation rule ADK states is a **single flat "cached prefix changed"** condition. There is **no** `tools`-level vs `system-instruction`-level vs `messages`-level matrix, and no "changes at each level invalidate that level and all subsequent levels" statement. A per-level invalidation matrix is **NOT STATED** in the ADK caching doc.

---

## §2 · Part A2 — Gemini caching docs: flat "similar prefix" + immutable CachedContent, no per-level matrix

### 2.1 Implicit caching — "similar prefix" (flat)

Source: **https://ai.google.dev/gemini-api/docs/caching** — section **"Implicit caching"**:

> "Implicit caching is enabled by default for all Gemini 2.5 and newer models. … We automatically pass on cost savings if your request hits caches."

> "To increase the chance of an implicit cache hit:
> - Try putting large and common contents at the beginning of your prompt
> - Try to send requests with similar prefix in a short amount of time"

### 2.2 Explicit caching — a fixed prefix you pre-create, referenced per request

Source: **https://ai.google.dev/gemini-api/docs/generate-content/caching** — section **"Explicit caching"**:

> "Using the Gemini API explicit caching feature, you can pass some content to the model once, cache the input tokens, and then refer to the cached tokens for subsequent requests."

The section **"Generate content using a cache"** shows the structure: the *cache* holds `system_instruction` + `contents=[video_file]`, while the *request* sends a separate `contents` plus `cached_content=cache.name`:

```python
cache = client.caches.create(
    model=model,
    config=types.CreateCachedContentConfig(
        system_instruction=('You are an expert video analyzer, …'),
        contents=[video_file],
        ttl="300s",
    )
)
response = client.models.generate_content(
    model=model,
    contents=('Introduce different characters …'),
    config=types.GenerateContentConfig(cached_content=cache.name)
)
```

Also note the two-product split (main caching doc, note box under the title **"Context caching"**):

> "The **Interactions API** only supports implicit caching. Explicit caching (manually creating and managing cache objects) is not supported in the Interactions API. To use explicit caching, switch to the generateContent API."

**Conclusion:** Both Gemini caching docs describe caching as **prefix matching** (implicit) or **one immutable `CachedContent` prefix + a per-request tail** (explicit). **No section documents a per-level invalidation matrix** (`tools` vs `system instruction` vs `messages`). That matrix is **NOT STATED**.

---

## §3 · Part A3 — Does Gemini/ADK distinguish a "tools" level from "system instruction" from "messages"?

**Gemini: structurally YES as fields, but only as one immutable prefix — no invalidation levels.**

Source: **https://ai.google.dev/api/caching** — **`Method: cachedContents.create` → Request body → Fields**:

> "`contents[]` … Optional. Input only. Immutable. The content to cache."

> "`systemInstruction` … Optional. Input only. Immutable. Developer set system instruction. Currently text only."

> "`tools[]` … Optional. Input only. Immutable. A list of `Tools` the model may use to generate the next response"

> "`toolConfig` … Optional. Input only. Immutable. Tool config. This config is shared for all tools."

> "`model` … Required. Immutable. The name of the `Model` to use for cached content"

So Gemini's `CachedContent` **does** name separate `systemInstruction`, `contents`, `tools`, and `toolConfig` fields — but every one is tagged **"Immutable"**. They are the *components of a single fixed prefix*, not independently-invalidatable "levels." There is no field-level invalidation: you change anything and you create a new cache object.

**ADK: names "instructions, tools and contents" as what an explicit cache covers, but documents no levels.**

Source: **https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py** — `static_instruction` field docstring, **"Context Caching:"** bullet:

> "**Explicit Cache**: Cache explicitly created by user for instructions, tools and contents"

And the ADK caching doc itself only ever refers to a single "**cached prefix**" (§1) — it never decomposes the prefix into tools/system/messages levels.

**Conclusion:** Neither side documents Anthropic's "each level invalidates itself and all subsequent levels" semantics. Gemini gives you a *named* split (systemInstruction / contents / tools) but as an all-or-nothing immutable prefix; ADK only has the flat "cached prefix." The per-level invalidation semantics are **NOT STATED**.

---

## §4 · Part B1 — ADK `static_instruction`: the documented cache-preserving "stable system / dynamic per-turn" split

**Yes, ADK has this — it is `static_instruction`, and it is explicitly framed as a caching optimization.**

### 4.1 The doc pointer

Source: **https://adk.dev/context/caching/index.md** — section **"Next steps"**:

> "If your use case requires that you provide instructions that are used throughout a session, consider using the `static_instruction` parameter for an agent, which allows you to amend the system instructions for a generative model."

### 4.2 The dynamic side exists too: `instruction` is a template/function

Source: **https://adk.dev/agents/llm-agents/** — section **"Guide the agent with instructions"**:

> "The `instruction` parameter is arguably the most critical for shaping an `LlmAgent`'s behavior. It's a string (or a function returning a string) that tells the agent:"

> "**Use dynamic state variables:**
> - The instruction is a string template, you can use the `{var}` syntax to insert dynamic values into the instruction."

### 4.3 The mechanism, verbatim (ADK Python source docstrings)

Source: **https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py** — `static_instruction` field docstring:

> "Static instruction content sent literally as system instruction at the beginning."

> "This field is for content that never changes and doesn't contain placeholders. It's sent directly to the model without any processing or variable substitution."

> "This field is primarily for context caching optimization. Static instructions are sent as system instruction at the beginning of the request, allowing for improved performance when the static portion remains unchanged."

> "**Impact on instruction field:**
> - When static_instruction is None: instruction → system_instruction
> - When static_instruction is set: instruction → user content (after static content)"

`instruction` field docstring (same file):

> "Dynamic instructions for the LLM model, guiding the agent's behavior."

> "**Behavior depends on static_instruction:**
> - If static_instruction is None: instruction goes to system_instruction
> - If static_instruction is set: instruction goes to user content in the request"

> "This allows for context caching optimization where static content (static_instruction) comes first in the prompt, followed by dynamic content (instruction)."

And the request-builder confirms it at the call level:

Source: **https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/flows/llm_flows/prompt/_instructions.py** — `_build_instructions`:

> "elif agent.instruction and agent.static_instruction:
>     # Static instruction exists, so add dynamic instruction to content"

**Conclusion:** ADK's analogue of Anthropic's (a) is **not** "append a `role:system` message" — it is the inverse and arguably cleaner: keep the immutable system instruction in `static_instruction` (→ `systemInstruction`) and push the per-turn, state-interpolated `instruction` into **user content**. The docstring states the purpose directly ("primarily for context caching optimization … allowing for improved performance when the static portion remains unchanged"). Note the boundary the docs *do* draw: "Setting static_instruction alone does NOT enable caching automatically. For explicit caching control, configure context_cache_config at App level." The docs stop short of a sentence that literally says "changing `instruction` never invalidates the cache," but the placement (static first, dynamic in user content) is the documented cache-preserving pattern.

---

## §5 · Part B2 — Mid-conversation TOOL changes: NOT STATED for both ADK and Gemini

**ADK: tools are a static per-agent list; no mid-session add/remove-to-preserve-cache.**

Source: **https://adk.dev/agents/llm-agents/** — section **"Equip the agent with tools"**:

> "**`tools` (Optional):** Provide a list of tools the agent can use."

The ADK tool pages (e.g. **https://adk.dev/tools-custom/function-tools/** — "Function tools") cover *defining* tools, not changing them between turns. **No ADK doc describes adding/removing tools mid-session while preserving cache** → **NOT STATED**.

**Gemini: tools are part of the immutable cached prefix; no `tool_addition`/`tool_removal`.**

The function-calling guide (**https://ai.google.dev/gemini-api/docs/generate-content/function-calling**, section **"Function calling with the Gemini API"**) shows tools declared once via `GenerateContentConfig(tools=[…])` and round-tripped as `function_call`/`function_response` parts — it describes **no** name-referencing add/remove block and no cache-preservation claim for changing the tool set mid-conversation. And in the caching API, `tools[]` is "**Immutable**" (§3), i.e. the tool set is baked into the `CachedContent` prefix; changing tools means a new cache object.

**Conclusion:** Anthropic's `tool_addition`/`tool_removal` blocks (referencing tools by name so the `tools` array never changes) have **no ADK or Gemini equivalent** — **NOT STATED** in any of the caching, function-calling, or ADK tools docs.

---

## §6 · Part B3 — Gemini's explicit cache IS the "stable prefix / variable tail" pattern, but only for a FIXED prefix

**Yes, structurally it is the analogue** — `CachedContent` = stable prefix, per-request `contents` = variable tail:

Source: **https://ai.google.dev/gemini-api/docs/generate-content/caching** — section **"Explicit caching"** + **"Generate content using a cache"**:

> "Using the Gemini API explicit caching feature, you can pass some content to the model once, cache the input tokens, and then refer to the cached tokens for subsequent requests."

The code (§2.2) separates the cached `system_instruction` + `contents=[video_file]` (prefix) from the request's `contents=(question)` + `cached_content=cache.name` (tail). The API reference locks this down — every prefix field is "**Immutable**" (§3).

**But it does NOT cover mid-conversation instruction/tool changes:** because `systemInstruction`, `contents`, `tools`, and `toolConfig` are all "Immutable," the "variable tail" is only the per-request `contents` passed to `generate_content`. There is no documented way to vary the system instruction or the tool set inside the cached region while keeping the cache — the cache is a *fixed* prefix by construction. **Mid-conversation instruction/tool mutation with cache preservation is NOT STATED** (and contradicted by "Immutable").

---

## Source inventory

- **ADK — Context caching:** https://adk.dev/context/caching/index.md
- **ADK — Simple agents (LlmAgent):** https://adk.dev/agents/llm-agents/ (source `…/agents/llm-agents/index.md`)
- **ADK — Custom tools (Function tools):** https://adk.dev/tools-custom/function-tools/
- **ADK Python source — `LlmAgent` (static_instruction / instruction docstrings):** https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/agents/llm_agent.py
- **ADK Python source — instructions builder:** https://raw.githubusercontent.com/google/adk-python/main/src/google/adk/flows/llm_flows/prompt/_instructions.py
- **Gemini — Context caching (main):** https://ai.google.dev/gemini-api/docs/caching
- **Gemini — Context caching (generateContent/explicit):** https://ai.google.dev/gemini-api/docs/generate-content/caching
- **Gemini — Function calling:** https://ai.google.dev/gemini-api/docs/generate-content/function-calling
- **Gemini — Caching API reference (`CachedContent`):** https://ai.google.dev/api/caching
- **Prior discussion (OpenAI invalidation levels, for format/parallel):** `discussions/04-openai-cache-invalidation-levels.md`
- **Prior discussion (Anthropic invalidation matrix):** `discussions/03-mcp-tools-vs-cached-prefix.md`
