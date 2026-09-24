# Discussion 03 — Do MCP tool definitions live inside the cached prefix, and do tool-schema changes break the cache?

> **Question:** Do MCP servers (new tools added, tool docstrings/schemas changed, servers swapped) impact the "fixed instruction + tool-schema prefix" that a harness caches? Are MCP tool definitions handled separately from the cached prefix, or do tool-schema changes invalidate the cache?
>
> **Short answer:** **Not separate — MCP tools are folded into the `tools` block, which is cached *first*, ahead of `system` and `messages`.** A harness that resolves MCP servers into a flattened `tools` array and then sends that array every turn is putting every tool schema *inside the cacheable prefix*; any change to a name/description/parameter invalidates the *entire* cache (tools + system + messages). Anthropic's only documented escape hatch is `defer_loading` / **tool search**, which keeps dynamic tools *out of the system-prompt prefix* (they load as inline `tool_reference` blocks) — but note it does **not** remove them from the request: you still send every full definition in `tools` on every request. The prompt-caching page itself never mentions MCP; the `mcp_toolset` behavior is documented on the *Tool use with prompt caching* page. ADK documents no tool/MCP interaction with its `ContextCacheConfig` at all.

---

## §1 · The `tools` block is part of the cacheable prefix, and it is cached FIRST

Source: **https://platform.claude.com/docs/en/build-with-claude/prompt-caching** — section **"Structuring your prompt"**:

> "Place static content (tool definitions, system instructions, context, examples) at the beginning of your prompt. Mark the end of the reusable content for caching using the `cache_control` parameter. **Cache prefixes are created in the following order: `tools`, `system`, then `messages`. This order forms a hierarchy where each level builds upon the previous ones.**"

Same page, tip **"Prompt caching caches the full prefix"**:

> "Prompt caching references the entire prompt - `tools`, `system`, and `messages` (in that order) up to and including the block designated with `cache_control`."

Same page, section **"Caching tool definitions"**:

> "Tool definitions can be cached by placing `cache_control` on the last tool in your `tools` array. All tools defined before and including that tool are cached as a single prefix."

So the ordering is unambiguous: tools → system → messages. The tool-schema block is the *head* of the cacheable prefix, not a separate side-channel.

---

## §2 · Does a changed tool schema break the cache? Yes — the whole cache

Source: **https://platform.claude.com/docs/en/build-with-claude/prompt-caching** — section **"What invalidates the cache"** (table):

> "Modifications to cached content can invalidate some or all of the cache. As described in Structuring your prompt, the cache follows the hierarchy: `tools` → `system` → `messages`. Changes at each level invalidate that level and all subsequent levels."

Table row (verbatim): **"Tool definitions | ✘ | ✘ | ✘ | Modifying tool definitions (names, descriptions, parameters) invalidates the entire cache"**

Because `tools` is first, a tool change knocks out all three levels (tools, system, messages) — not just the tools segment. The reason it is certain rather than probabilistic is the cumulative hash (section **"How automatic prefix checking works" → "Three core principles"**):

> "Because the hash is cumulative, covering everything up to and including the breakpoint, changing any block at or before the breakpoint produces a different hash on the next request."

And even *key ordering* inside a tool block counts as a change (section **"Troubleshooting common issues"**):

> "Verify that the keys in your `tool_use` content blocks have stable ordering as some languages (for example, Swift, Go) randomize key order during JSON conversion, breaking caches."

**Conclusion for the harness:** if a harness flattens MCP-resolved schemas into `tools` and re-sends them, then a changed docstring, an added parameter, a newly-registered server, or even a re-serialization that reorders keys all mutate the `tools` block and invalidate the *entire* cache (tools + system + messages). There is no documented "only the tools segment" partial invalidation for a tools-level change.

---

## §3 · The documented escape hatch: tool search / `defer_loading` (with an important caveat)

Anthropic *does* document a way to keep the cached prefix stable while tools are discovered dynamically: **server-side tool search** with `defer_loading`. It does **not** remove the schemas from the request; it removes them from the *context/prefix*.

Source: **https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching** — section **"defer_loading and cache preservation"**:

> "Deferred tools are not included in the system-prompt prefix. When the model discovers a deferred tool through tool search, the definition is appended inline as a `tool_reference` block in the conversation history. The prefix is untouched, so prompt caching is preserved." … "This means adding tools dynamically through tool search does not break your cache."

Source: **https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool** — section **"Deferred tool loading"**:

> "Internally, the API excludes deferred tools from the system-prompt prefix. When Claude discovers a deferred tool through tool search, the API appends a `tool_reference` block inline in the conversation, then expands it into the full tool definition before passing it to Claude. The prefix is untouched, so prompt caching is preserved."

**The caveat that matters for a harness** (same page, same section):

> "`defer_loading` controls what enters the context window, not what you send in the request: **You still send every tool's full definition in the `tools` array on every request, including the deferred ones.** The API needs them server-side to run the search and expand `tool_reference` blocks."

Interpretation for the course: `defer_loading` is Anthropic's *server-side* mechanism — it only helps if the harness *also* marks tools `defer_loading: true` and puts a breakpoint on a non-deferred tool. It changes what is *cached* (only non-deferred tools enter the prefix), but it does **not** change the wire payload (all schemas still transit). A harness doing plain dynamic MCP loading without `defer_loading` still puts every schema into the prefix and still invalidates on change.

Same page, section **"Prompt caching"** (tool-search page):

> "A tool with `defer_loading: true` can't also carry `cache_control`: the API returns a 400. Put the cache breakpoint on a non-deferred tool."

---

## §4 · Does the prompt-caching page mention MCP? No. The tool-use page does.

**NOT STATED on the prompt-caching page.** The body of https://platform.claude.com/docs/en/build-with-claude/prompt-caching contains no mention of MCP. ("MCP" appears only in the navigation sidebar as links to "Remote MCP servers", "MCP connector", "MCP tunnels" — not in the caching content.)

The MCP-toolset caching behavior is documented instead on **https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching** — section **"cache_control on tool definitions"**:

> "For `mcp_toolset`, the `cache_control` breakpoint lands on the last tool in the set. You don't control tool order within an MCP toolset, so place the breakpoint on the `mcp_toolset` entry itself and the API applies it to the final expanded tool."

That is the direct answer to "are MCP tools handled separately?": **no** — the `mcp_toolset` is *expanded* into tool definitions that join the ordinary `tools` prefix, and the breakpoint lands "after the toolset's definition." Its invalidation rule is the same table, section **"What invalidates your cache"**:

> "The cache follows a prefix hierarchy (`tools` → `system` → `messages`), so a change at one level invalidates that level and everything after it: … **Modifying tool definitions → Entire cache (tools, system, messages)**"

The per-tool table (section **"Per-tool interaction table"**) confirms the tool-search path: **"Tool search — Discovered tools load as `tool_reference` blocks, preserving prefix cache."**

MCP + tool search combined (tool-search page, section **"MCP integration"**):

> "If your tools come from MCP servers through the MCP connector, you don't set `defer_loading` on individual tool definitions. Instead, set it once on the `mcp_toolset` entry's `default_config` for the whole server, or per tool in its `configs`."

---

## §5 · ADK side: `ContextCacheConfig` says nothing about tools or MCP

Source: **https://adk.dev/context/caching/index.md** — the whole page describes caching at the `App` level via `ContextCacheConfig` (`min_tokens`, `ttl_seconds`, `cache_intervals`, `create_http_options`) and a `CacheMetadata` diagnostic. It references a "cacheable prefix" but never enumerates whether tools/tool-schemas are part of it. **NOT STATED** whether changing tools invalidates ADK's cache.

Section **"Check whether the cache is being used"** (on the fingerprint-only state):

> "Fingerprint-only: ADK measured the cacheable prefix but no cache is in use. That is the first turn, a prefix that changed since the last turn, or a cache ADK did not create -- most often because the cacheable prefix was below `minTokens`."

Same section:

> "ADK keeps reusing a cache until it is actually past `expireTime`, has run past `cacheIntervals`, or **its cached prefix changes**."

It never says what that prefix contains (tools? system? messages?), and the words "tool", "tool schema", and "MCP" do **not** appear anywhere on the page. The only stability seam documented is `static_instruction` (section **"Next steps"**):

> "If your use case requires that you provide instructions that are used throughout a session, consider using the `static_instruction` parameter for an agent, which allows you to amend the system instructions for a generative model."

### ADK MCP docs: nothing about caching or context-stability

Source: **https://adk.dev/tools-custom/mcp-tools/** (note: the URL given in the brief, `/tools/mcp-tools/`, returns **HTTP 404**; the live page is under `/tools-custom/`). The word "cache" appears **zero** times on the page; there is no discussion of context-stability. The relevant mechanism — dynamic discovery at connect time — is section **"McpToolset class"**:

> "Once connected, `McpToolset` queries the MCP server for its available tools (via the `list_tools` MCP method). It then converts the schemas of these discovered MCP tools into ADK-compatible `BaseTool` instances."

So ADK's MCP toolset *does* resolve tool schemas dynamically (new/edited/swapped servers change the resolved `BaseTool` set), but the docs state **nothing** about how that interacts with `ContextCacheConfig`. Whether a changed MCP tool schema changes ADK's "cacheable prefix" is **NOT STATED**.

---

## Source inventory

- **Anthropic — Prompt caching:** https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- **Anthropic — Tool use with prompt caching:** https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching
- **Anthropic — Tool search tool:** https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool
- **ADK — Context caching:** https://adk.dev/context/caching/index.md
- **ADK — MCP tools:** https://adk.dev/tools-custom/mcp-tools/ (the `/tools/mcp-tools/` path 404s)
- **Prior discussion (memory vs. prefix):** `discussions/02-prompt-caching-vs-memory-injection.md`
