# M4 · Context Engineering I: Assembly & Budgets

> **Module question:** What goes into the context window, in what form, and what does it cost?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a context-hungry research agent running a long session

---

## Contents

- [Opening scene — the agent that got dumber as it worked](#opening-scene--the-agent-that-got-dumber-as-it-worked)
- [The context window is a budget, not a canvas](#the-context-window-is-a-budget-not-a-canvas)
    - [Why format is its own budget line](#why-format-is-its-own-budget-line)
      - [Is code output a format?](#is-code-output-a-format)
- [What actually goes into the window](#what-actually-goes-into-the-window)
- [Assembly discipline](#assembly-discipline)
  - [1. Position is a design input — and a stability requirement](#1-position-is-a-design-input--and-a-stability-requirement)
  - [2. Formatting is information](#2-formatting-is-information)
- [Prompt caching — the practical playbook](#prompt-caching--the-practical-playbook)
  - [The science behind prompt caching (collapse-by-default)](#the-science-behind-prompt-caching-collapse-by-default)
- [Context budgeting: the three dials](#context-budgeting-the-three-dials)
  - [Dial 1 — the per-turn budget](#dial-1--the-per-turn-budget)
  - [Dial 2 — eviction (what to drop first)](#dial-2--eviction-what-to-drop-first)
  - [Dial 3 — summarization-in-the-loop (compaction)](#dial-3--summarization-in-the-loop-compaction)
- [Beyond budgets: selecting by *content*, not position](#beyond-budgets-selecting-by-content-not-position)
- [Worked example: the research agent, budgeted](#worked-example-the-research-agent-budgeted)
- [Design exercise](#design-exercise)
- [Where the literature disagrees with this module](#where-the-literature-disagrees-with-this-module)
  - [1. The "lost in the middle" effect is genuinely contested](#1-the-lost-in-the-middle-effect-is-genuinely-contested)
  - [2. The module's *premise* has its strongest support from a source it does not cite](#2-the-modules-premise-has-its-strongest-support-from-a-source-it-does-not-cite)
  - [3. "Formatting is information" is the weakest *design* claim in the module](#3-formatting-is-information-is-the-weakest-design-claim-in-the-module)
  - [4. Tool-schema bloat has *two* mechanisms, and the module names only the wrong one](#4-tool-schema-bloat-has-two-mechanisms-and-the-module-names-only-the-wrong-one)
  - [5. System instructions do not reliably outrank later text — and compaction is *documented* to lose them](#5-system-instructions-do-not-reliably-outrank-later-text--and-compaction-is-documented-to-lose-them)
  - [6. "A naive summarizer keeps the narrative and drops the specifics" — this one is empirically backwards](#6-a-naive-summarizer-keeps-the-narrative-and-drops-the-specifics--this-one-is-empirically-backwards)
  - [7. Compression is not uniformly lossy — *what* is compressed is what matters](#7-compression-is-not-uniformly-lossy--what-is-compressed-is-what-matters)
  - [8. "The agent will not tell you it's reasoning from a lossy memory" — restate as a harness gap](#8-the-agent-will-not-tell-you-its-reasoning-from-a-lossy-memory--restate-as-a-harness-gap)
  - [9. The module's cost claim rests on complexity arguments, not measured NLP latency](#9-the-modules-cost-claim-rests-on-complexity-arguments-not-measured-nlp-latency)
  - [10. Keep the window small — the counter-position the module never names](#10-keep-the-window-small--the-counter-position-the-module-never-names)
  - [11. Framework claims: verified against the docs, with three corrections](#11-framework-claims-verified-against-the-docs-with-three-corrections)
- [Sources (ADK docs)](#sources-adk-docs)
- [Bibliography](#bibliography)
  - [Framework documentation (industry docs)](#framework-documentation-industry-docs)
  - [Assembly discipline: ordering, instructions, formatting](#assembly-discipline-ordering-instructions-formatting)
  - [Formatting and selection](#formatting-and-selection)
  - [Measuring the cost: attention, position, and latency](#measuring-the-cost-attention-position-and-latency)
  - [Tool-definition budget and tool-selection scaling](#tool-definition-budget-and-tool-selection-scaling)
  - [Prompt caching](#prompt-caching)
  - [Context compression and compaction](#context-compression-and-compaction)
  - [Harness behaviour: what compaction actually preserves](#harness-behaviour-what-compaction-actually-preserves)
  - [Session memory and selective assembly](#session-memory-and-selective-assembly)
  - [Unsupported claims and own synthesis](#unsupported-claims-and-own-synthesis)

---

## Opening scene — the agent that got dumber as it worked

- The research agent started sharp. "Summarize the merger filings," it said, and produced a tight, sourced brief in forty seconds. 
    - Three hours later, deep into the same session, the same agent was asked a question it had *answered correctly that morning* — and got it wrong, slowly, at five times the cost.
- The team's diagnosis: "the model degraded." It hadn't. The model was identical. 
    - What had changed, steadily, silently, all session long, was the **context window** - the single block of text the model reads every time it thinks. 
    - Every turn had appended a tool result here, a retrieved chunk there, a scratch-pad note, a user clarification. 
    - By hour three the window held ~90,000 tokens, most of them irrelevant to the current question, all of them being paid for and — worse — all of them *competing for the model's attention*.

The agent didn't get dumber. It got **drowned**. And nobody had budgeted the one resource that was doing the drowning.

*The scene above is a composite illustration, not a reported case study — the token counts and durations are invented to show the shape of the failure. The claims this module makes about the mechanisms behind it are sourced below.*

This module is the first half of the cognitive layer: **assembly and budgets** — what goes into the window, in what form, and what it costs. The *second* half (how the right facts get there, and how we know they're right) is M5.

---

## The context window is a budget, not a canvas

Every model call carries **three** costs, and beginners track only one:

| Cost | What it is | Consequence of ignoring it |
|---|---|---|
| **Token cost** | You pay for every input token, every turn, at your input price | Linear cost blowup as sessions grow[fu-long-context-deployment](#fu-long-context-deployment) |
| **Attention cost** | The model's attention is finite and *positional*; more context dilutes it | Correctness falls, especially for facts in the middle[liu-lost-in-the-middle](#liu-lost-in-the-middle) |
| **Format cost** | Asking for a *shape* (JSON, XML, LaTeX, Markdown) taxes the capability you asked for — *on top of* the token (since formatting instructions will be represented as tokens) and attention cost (since formatting instructions will compete with other tokens to occupy context window) those instructions already incur | Accuracy drops on the same task, with the same content[lee-format-tax](#lee-format-tax) |

- The first is money. 
- The second is *quality* — and it's the one that causes the "the model got dumber" misdiagnosis. 
    - You have seen this failure class already: it is M2's **position bias** ("lost in the middle")[liu-lost-in-the-middle](#liu-lost-in-the-middle) and **instruction drift** (policy drowned by later text).[wallace-instruction-hierarchy](#wallace-instruction-hierarchy), [geng-control-illusion](#geng-control-illusion) 
    - Both are *context-assembly* failures, and both are yours to design away.
- The third is the one nobody budgets for, because it looks like a rendering detail.

#### Why format is its own budget line

Format cost is scoped narrowly: it is the cost of **constraining the model's output shape**, and nothing else. (Formatting on the *input* side — examples, templates, delimiters — is a different sensitivity with a different mechanism, treated under attention cost.)

The measured quantity is a difference of two performances on the same task:

    Format tax = Perf(freeform) − Perf(format-constrained)

Positive means requiring a shape degraded the work.

The measurement uses two setups that need names, because the result turns on the difference between them:

- **1-Turn (GET·):** one generation; the model produces its answer *and* the required format in the same pass. The prompt carries the format spec (G), examples (E), and the task (T).
- **2-Turn (··T· → GET·):** two generations. First the model answers freeform (no format instruction at all); then a second pass reformats that answer under the *same* format instructions.

Same format instructions in both — only *when* the format is applied changes, and that is what isolates the tax. On the LaTeX writing task, one open-weight model paid **15.7 quality points** in 1-Turn and **7.0** in 2-Turn.[lee-format-tax](#lee-format-tax)

So the fix is real but partial: 2-Turn recovers **8.7 of the 15.7** — just over half — and it is not uniform (one model's tax *grew* in 2-Turn). It also buys the recovery with an extra call and roughly doubled token consumption.[lee-format-tax](#lee-format-tax) Decoupling reasoning from formatting is a mitigation, not a cure, and it costs the same currency this module is about.

**Practical rule, stated once:** keep format requests late and narrow rather than pinning a heavy output schema into the standing instruction, where it is re-applied — and re-charged — every turn.

**Caveats.** Most recent closed-weight models show little to no tax, so it is a gap open-weight models have yet to close rather than a permanent property of structured generation.[lee-format-tax](#lee-format-tax) The evidence rests on one systematic study; treat the magnitude as provisional and A/B it on your own model.[unsupported](#unsupported)

##### Is code output a format?

The definition above turns on a phrase worth pulling out: format "specifies presentation, not content — a **pure transduction** (a rewriting that preserves all content, changing only its form) that should leave task performance unchanged."[lee-format-tax](#lee-format-tax) That is a testable criterion, not a slogan:

- **Something is a format when the content is determined independently of it** — when you could re-render the same content another way without loss.
- The answer to a math problem is fixed before you choose JSON. Re-render to XML, content unchanged. **Format.**
- The text of an essay is fixed before you choose Markdown. **Format.**
- *"Compute the median"* in Python versus Rust is **not** the same program re-rendered — algorithms, data structures, memory and error handling, and what's idiomatic all change. **Not format: task specification.**
- So most code requests are not format, and this budget line does not apply to them.
- A real sub-class *does* satisfy pure transduction, and the tax should apply to it: *"write the provided algorithm in Go"* (algorithm fixed elsewhere), transpilation and codemods, and schema-constrained artifacts such as a JSON Schema, a `.proto`, or a config file.
- **So the answer is not yes-or-no.** Code is format-ambiguous; the discriminator is whether the language choice is transparent to the solution.

<details>
<summary><strong>Why this matters beyond pedantry</strong></summary>

- The freeform baseline in the measurement is not "no structure" — it is *no additional format instruction beyond the task itself*.[lee-format-tax](#lee-format-tax)
- The structure a task already implies is treated as content; the tax is on the extra shape you layer on top.
- Code requests usually fall on the content side of that line, which is why "just ask for Python" is not the same kind of decision as "reply in JSON."

</details>

<details>
<summary><strong>Why the code case stays open</strong></summary>

- **The yardstick changes.** JSON and LaTeX can be scored against gold text; code is scored by execution. So `Perf(freeform) − Perf(format)` is not computable as written — the freeform arm has no executable output, and a freeform-versus-code comparison would need a common scoring basis that does not exist here.[unsupported](#unsupported)
- **The decoder decomposition barely applies.** Structured-output APIs do constrain JSON, but almost nothing grammar-constrains Python, so whatever tax exists in code is nearly all prompt-side.[unsupported](#unsupported)

</details>

\

**The mental model that carries this whole module:** the context window is **live currency**. 
- You spend it every turn, and you spend it on *attention* as much as on money — and on *format* as much as either. 
- A token that is present but irrelevant is not free — it is a *distraction tax* on every other token,[shi-irrelevant-context](#shi-irrelevant-context), [unsupported](#unsupported) plus a cash charge, plus latency (input size scales response time).[fu-long-context-deployment](#fu-long-context-deployment) 

The discipline of context engineering is deciding, deliberately, what earns a place — and in what form.

> **Failure mode (the module in one line):** treating the context window as a place to *put* things rather than a budget to *spend*. The default agent — append everything, forever — is not "simple," it's a slow, expensive degradation curve with a correctness cliff at the end.[liu-lost-in-the-middle](#liu-lost-in-the-middle)

---

## What actually goes into the window

Before you can budget it, you have to name it. Here is the anatomy of a context window, and for each component: who writes it, what it costs, and how it fails.

| Component | Who writes it | What it costs | Its failure mode |
|---|---|---|---|
| **System instructions** | You (the harness) | Fixed, per turn | Drift: drowned or contradicted by later text (M2 class 4)[wallace-instruction-hierarchy](#wallace-instruction-hierarchy), [geng-control-illusion](#geng-control-illusion) |
| **Tool definitions** | You (the harness) | Fixed, per turn | Steal attention from the task; bloated schemas[gan-rag-mcp](#gan-rag-mcp), [paramanayakam-less-is-more](#paramanayakam-less-is-more) |
| **Retrieved material** | Retrieval pipeline | Variable, per turn | Wrong/stale/irrelevant → grounding failure (M2 class 1)[hsieh-ruler](#hsieh-ruler) |
| **Conversation history** | The session (events) | Grows every turn | The biggest budget leak; irrelevant history buries the present[hsieh-ruler](#hsieh-ruler) |
| **Intermediate results** | Tool outputs, scratchpad | Variable | Verbose tool dumps; dead-end reasoning steps[gan-rag-mcp](#gan-rag-mcp) |

Two observations that should reframe how you see the window:

1. **Three of five components are fixed overhead** (instructions, tool definitions, and — in a naive agent — a stable prefix).[unsupported](#unsupported) Fixed overhead is where **caching** pays off (see below).[ding-mcp-performance](#ding-mcp-performance), [gan-rag-mcp](#gan-rag-mcp) Variable components are where **budgeting** pays off.
2. **The conversation history is the silent killer.** In a long session, most of the window ends up being *old turns* — and old turns are the least relevant thing in the room, yet they sit in the most expensive slot (every one of them re-sent every turn).[ding-mcp-performance](#ding-mcp-performance) This is exactly what *compaction* exists for (see below).[adk-context-compaction](#adk-context-compaction)

---

## Assembly discipline

Budgeting is necessary; *ordering and formatting* are where quality actually comes from. Three disciplines:

### 1. Position is a design input — and a stability requirement

- **Position and stability are two separate reasons to care about placement** — easy to conflate:
    - **Where it sits** changes whether the content is *used*.
    - **Whether the prefix changes** determines whether it is *cacheable at all*.
- **Placement rule** — same slots every turn:
    - **Beginning → the standing policy** (primacy). Instructions that must persist across turns belong at the start.[liu-lost-in-the-middle](#liu-lost-in-the-middle), [hsieh-found-in-the-middle](#hsieh-found-in-the-middle)
    - **End → the current task and latest few messages** (recency). That is what the model looks at as it produces the next token.[liu-lost-in-the-middle](#liu-lost-in-the-middle)
    - **Middle → supporting material only** (retrieved context, tool results, not-yet-compacted history). Use and attention both dip here, so it holds only what the model may *look back at* — never what it must *act on* or *remember*.[liu-lost-in-the-middle](#liu-lost-in-the-middle), [hsieh-found-in-the-middle](#hsieh-found-in-the-middle) *(full attention walkthrough → [found-in-the-middle.md](paper-details/found-in-the-middle.md))*
        - Keep it small: it is the slot compaction exists to drain.
- **Ordering within a pair** — order matters independently of position:
    - **Context precedes the question that reads it.** Worth up to **+31%**; the reverse order costs over **14 percentage points**.[shaier-context-before-question](#shaier-context-before-question), [ok-prompt-order](#ok-prompt-order)
- **Stability requirement** — the part position alone does *not* give you:
    - Caching keys off an **unchanging** prefix, not an *important* one.[adk-context-caching](#adk-context-caching)
    - Policy-first is not enough — policy-first-and-**never-changing** is what makes the prefix cacheable.
    - In ADK, `static_instruction` is the knob for this: instructions that persist across a session, held in the stable prefix rather than re-sent as part of the mutable body.[adk-context-caching](#adk-context-caching), [unsupported](#unsupported)
- **Memorability test** — position raises the odds, it does not guarantee use:
    - If a fact is load-bearing, re-inject it near the point of use rather than trusting end-placement alone.
    - The position penalty is **fill-dependent**, not a fixed law.[veseli-positional-biases](#veseli-positional-biases)

### 2. Formatting is information

The model is not a human reader; it is a *pattern-matching* reader. Structure that would be noise to a person is signal to it.[unsupported](#unsupported) Prefer:

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

over a wall of prose where the task, the evidence, and the constraints are all one paragraph. Deterministic structure makes the model's job of *finding* the right thing cheaper[lee-format-tax](#lee-format-tax) — which is, in effect, more attention budget for the actual reasoning.

> **ADK at a glance:** the framework's `InvocationContext` (the object threaded through every run) is how your code and tools read the current session state;[adk-context](#adk-context) `static_instruction` is the knob for the stable instruction prefix;[adk-context-caching](#adk-context-caching) and the `Runner`/`run_async` loop is where the window gets assembled each turn.[adk-context](#adk-context), [unsupported](#unsupported) We'll go deep on the runtime in M16 — for now the point is architectural: *something* assembles the window every turn, and that something is a decision surface, not a black box.

---

## Prompt caching — the practical playbook

- **What it is, in one line.** Caching reuses the already-computed prefix of your prompt, so the repeated part is billed at a cheap read rate and returns faster — and nothing is dropped from what the model sees.[anthropic-prompt-caching](#anthropic-prompt-caching)
    - The server caches a **prefix**; if the next request's prefix is byte-identical, that prefix's computation is reused.
    - Result: lower latency, and cached tokens are billed at a much cheaper cache-read rate.
- **When it pays off — you need a repeatable, byte-identical prefix.**
    - **Conversational agents** — the system prompt, tool schemas, and prior turns are re-sent every turn.[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **Large document processing** — a fixed corpus held in context across queries, without paying full latency each time.
    - **Tool-heavy prompts** — a large tool-schema prefix identical across calls.
    - Not limited to multi-turn: any *repeated static block* (system prompt, uploaded doc, tool set) benefits, even across unrelated single-turn requests.
- **How to design for cache hits** — same rule as [stable prefix, variable tail](#1-position-is-a-design-input--and-a-stability-requirement):[adk-context-caching](#adk-context-caching), [anthropic-prompt-caching](#anthropic-prompt-caching)
    - Put the **stable, large** material first — system instruction, tool schemas, big static policy — so it forms the cacheable prefix.[anthropic-prompt-caching](#anthropic-prompt-caching)
    - Keep the **variable** material (per-turn retrieval, latest messages) *after* it.
    - **Don't interleave a changing token into the middle of the stable prefix.** One changed byte breaks the cache from that point on — the key is a cumulative hash, and hits need 100% byte-identical segments.[anthropic-prompt-caching](#anthropic-prompt-caching)
        - **That is the memory rule, concretely.** The docs name the cache-killers as a *varying suffix*: *"timestamps, per-request context, the incoming message."*[anthropic-prompt-caching](#anthropic-prompt-caching) Dynamic memory/state *is* per-request context.
        - **Stable — safe in the prefix:** the **procedural** instruction ("static, versioned"). ([M7 · Memory & State](../07-memory-state/README.md))
        - **Dynamic — belongs in the tail:** **working** (this turn's message/tool result), **semantic** (`search_memory` hits), **episodic** (`load_memory` hits), **external/retrieval** (fetched docs) — every one differs per turn. ([M7 · Memory & State](../07-memory-state/README.md))
        - **Neither breaks a cache:** **parametric** memory never enters the prompt (it's the weights); **prospective** memory lives in a scheduler, not the prompt. ([M7 · Memory & State](../07-memory-state/README.md))
        - **Both memory *and* cache hits is possible** — retrieve into the tail after the breakpoint, or load out-of-band (tool search / `defer_loading`, appended `system` messages) so the prefix stays untouched.[anthropic-tool-caching](#anthropic-tool-caching), [anthropic-prompt-caching](#anthropic-prompt-caching)
    - [**TTL Support by Anthropic**](https://platform.claude.com/docs/en/build-with-claude/prompt-caching#ttl-support): *By default, automatic caching uses a 5-minute TTL. You can specify a 1-hour TTL at 2x the base input token price.*
    - **Invalidation** — what a change actually kills, per framework.[anthropic-prompt-caching](#anthropic-prompt-caching), [openai-prompt-caching](#openai-prompt-caching), [mastra-prompt-caching](#mastra-prompt-caching), [adk-context-caching](#adk-context-caching)
        - **Anthropic — the only per-level model.** The cache is assembled `tools` → `system` → `messages`, and *"changes at each level invalidate that level and all subsequent levels."*[anthropic-prompt-caching](#anthropic-prompt-caching)
            - A `messages` change invalidates **only the messages cache** — tools ✓ and system ✓ survive.
            - A `system` change invalidates system **and** messages; tools ✓ survives.
            - A `tools` change invalidates **the entire cache** (✘ ✘ ✘).
            - The full matrix also covers web-search/citations/speed toggles (system-level), `tool_choice` and images (messages-only), and thinking/effort (messages always; tools/system model-dependent).[anthropic-prompt-caching](#anthropic-prompt-caching)
        - **OpenAI — no levels; your breakpoints *are* the levels.** Render order is fixed (hidden internal instructions → `tools` → developer messages → messages), but nothing invalidates "a level": *"Cache reuse requires the entire rendered prefix to match,"* and the lookup walks breakpoints longest → shortest.[openai-prompt-caching](#openai-prompt-caching)
            - A change at or before breakpoint *k* kills prefix *k* **and every longer prefix built on it**; prefixes ending earlier still hit. Editing the stable developer block kills both tiers; editing a branch suffix kills only the longer one.[openai-prompt-caching](#openai-prompt-caching)
            - **The `tools` tier is unreachable.** Breakpoints attach only to *content blocks inside input messages*; `tools` render before all messages, and `additional_tools` items reject breakpoints — so every message breakpoint necessarily swallows the tool schemas.[openai-prompt-caching](#openai-prompt-caching)
            - <details><summary><strong>Example A — OpenAI's default: one fused prefix (implicit breakpoint)</strong></summary>

                ```typescript
                import OpenAI from "openai";

                const MODEL = "gpt-5.6";
                const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

                /** Byte-identical on every call — that is what makes the prefix reusable. */
                const tools = [
                  {
                    type: "function" as const,
                    name: "get_weather",
                    description: "Get the current weather for a city.",
                    parameters: {
                      type: "object",
                      properties: { city: { type: "string" } },
                      required: ["city"],
                      additionalProperties: false,
                    },
                  },
                  {
                    type: "function" as const,
                    name: "search_docs",
                    description: "Search the internal document corpus.",
                    parameters: {
                      type: "object",
                      properties: { q: { type: "string" } },
                      required: ["q"],
                      additionalProperties: false,
                    },
                  },
                ];

                const SYSTEM =
                  "You are a research assistant. Cite every claim; if evidence is absent, say so.";

                type Msg =
                  | { role: "developer"; content: string }
                  | { role: "user"; content: string }
                  | { role: "assistant"; content: string };

                const thread: Msg[] = [{ role: "developer", content: SYSTEM }];

                async function turn(label: string, question: string, toolDefs = tools) {
                  thread.push({ role: "user", content: question });
                  const res = await client.responses.create({
                    model: MODEL,
                    // IMPLICIT (the default): ONE breakpoint at the end of the latest
                    // eligible message, walked forward as the thread grows.
                    prompt_cache_options: { mode: "implicit", ttl: "30m" },
                    tools: toolDefs, // tools render BEFORE every message -> in that one prefix
                    input: thread,
                  });
                  thread.push({ role: "assistant", content: res.output_text }); // append, never rewrite
                  const d = res.usage.input_tokens_details;
                  console.log(
                    `${label}: input=${res.usage.input_tokens} cached=${d.cached_tokens} write=${d.cache_write_tokens}`,
                  );
                }

                await turn("1 cold write", "Summarise the merger filing.");
                await turn("2 append turn", "What are the termination clauses?");
                await turn("3 append turn", "Which governing law applies?");
                // One character in ONE tool description changes -> the fused entry is discarded.
                await turn("4 tool description edited", "Which governing law applies?", [
                  { ...tools[0], description: "Get the current weather for a city. [edited]" },
                  tools[1],
                ]);
                ```

                One breakpoint, at the end of the latest eligible message. The single entry written covers **hidden instructions + both tool schemas + the developer message + the turns so far** — there is no `tools` entry and no `system` entry to invalidate separately.

                Offline simulation output (no API key; token counts illustrative — run `npx tsx example-a.ts` against the real API for real numbers):

                ```text
                1 cold write: input=141 cached=0 write=141
                2 append turn: input=152 cached=141 write=152
                3 append turn: input=162 cached=152 write=162
                4 tool description edited: input=175 cached=0 write=175
                ```

                Step 4 is the proof of fusion: editing **one tool description** takes `cached` from 152 to **0**. There was never a separate tool tier to preserve.

                </details>
            - <details><summary><strong>Example B — explicit breakpoints: the closest OpenAI gets to Anthropic's ordering</strong></summary>

                ```typescript
                import OpenAI from "openai";

                const MODEL = "gpt-5.6";
                const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

                const tools = [
                  {
                    type: "function" as const,
                    name: "get_weather",
                    description: "Get the current weather for a city.",
                    parameters: {
                      type: "object",
                      properties: { city: { type: "string" } },
                      required: ["city"],
                      additionalProperties: false,
                    },
                  },
                ];

                const STABLE_POLICY =
                  "STABLE POLICY — you are a research assistant; cite every claim; if evidence is absent, say so.";
                const TENANT_RUBRIC = "SEMI-STABLE — the calling tenant's house rubric.";

                type InputText = {
                  type: "input_text";
                  text: string;
                  prompt_cache_breakpoint?: { mode: "explicit" };
                };

                /** A developer block carrying an explicit breakpoint == one cached tier. */
                function tier(text: string) {
                  const content: InputText[] = [
                    { type: "input_text", text, prompt_cache_breakpoint: { mode: "explicit" } },
                  ];
                  return { role: "developer" as const, content };
                }

                async function ask(
                  label: string,
                  question: string,
                  opts: { policy?: string; rubric?: string; toolDefs?: typeof tools } = {},
                ) {
                  const res = await client.responses.create({
                    model: MODEL,
                    // EXPLICIT: ONLY the breakpoints you mark are written; mark
                    // nothing and the request is not cached at all.
                    prompt_cache_options: { mode: "explicit", ttl: "30m" },
                    tools: opts.toolDefs ?? tools,
                    input: [
                      tier(opts.policy ?? STABLE_POLICY), // tier 1: hidden + ALL tools + policy
                      tier(opts.rubric ?? TENANT_RUBRIC), // tier 2: tier 1 + the tenant rubric
                      { role: "user" as const, content: question }, // no breakpoint -> never cached
                    ],
                  });
                  const d = res.usage.input_tokens_details;
                  console.log(
                    `${label}: input=${res.usage.input_tokens} cached=${d.cached_tokens} write=${d.cache_write_tokens}`,
                  );
                }

                const Q = "Summarise the merger filing.";

                await ask("1 cold write", Q);
                // Same prefix, DIFFERENT question: both tiers are read, only the tail is fresh.
                await ask("2 same prefix, new question", "What are the termination clauses?");
                // Edit ONLY tier 2 -> tier 1 survives.
                await ask("3 tier 2 (rubric) edited", Q, { rubric: TENANT_RUBRIC + " [v2]" });
                // Edit tier 1 -> both tiers die.
                await ask("4 tier 1 (policy) edited", Q, { policy: STABLE_POLICY + " [v2]" });
                // Edit a TOOL description -> also kills tier 1, because tools are welded into it.
                await ask("5 one tool description edited", Q, {
                  toolDefs: [
                    { ...tools[0], description: "Get the current weather for a city. [edited]" },
                  ],
                });
                ```

                Tier 1 = hidden instructions + **all tool schemas** + the stable developer block. Tier 2 = tier 1 + the semi-stable developer block. Anthropic gives `tools` and `system` as *two separate tiers* here; OpenAI **fuses** them, and there is no way to split them — a breakpoint on a later, user-role message block is what would extend the prefix into the conversation. Up to four writes per request.[openai-prompt-caching](#openai-prompt-caching)

                Offline simulation output (no API key; token counts illustrative — run `npx tsx example-b.ts` for real numbers):

                ```text
                1 cold write: input=106 cached=0 write=186
                2 same prefix, new question: input=107 cached=99 write=0
                3 tier 2 (rubric) edited: input=107 cached=87 write=100
                4 tier 1 (policy) edited: input=107 cached=0 write=188
                5 one tool description edited: input=108 cached=0 write=190
                ```

                Steps 3 → 4 are the nesting: editing tier 2 drops `cached` from 99 to **87** (tier 1 survives); editing tier 1 drops it to **0**. Step 5 shows a tool edit behaving exactly like a tier-1 edit — the schemas are welded in.

                </details>
        - **Mastra — binary, no levels.** Prompt caching is a provider pass-through (`providerOptions`); the only documented rule is append-vs-modify — *"preserves prompt caching because it appends a signal instead of modifying system messages."* `ToolSearchProcessor` loads are append-only (prefix stays stable); unloading shifts the prefix into a cache write.[mastra-prompt-caching](#mastra-prompt-caching), [mastra-tool-search](#mastra-tool-search)
            - <details><summary><strong>Anthropic-ordered example — <code>providerOptions</code> at tool and instruction level</strong></summary>

                ```typescript
                import { Agent } from '@mastra/core/agent'
                import { createTool } from '@mastra/core/tools'
                import { z } from 'zod'

                const EPHEMERAL = { anthropic: { cacheControl: { type: 'ephemeral' } } }

                const getWeather = createTool({
                  id: 'getWeather',
                  description: 'Get the current weather for a city.',
                  inputSchema: z.object({ city: z.string() }),
                  execute: async ({ context }) => ({ city: context.city, tempC: 21 }),
                })

                const searchDocs = createTool({
                  id: 'searchDocs',
                  description: 'Search the internal document corpus.',
                  inputSchema: z.object({ q: z.string() }),
                  execute: async ({ context }) => ({ q: context.q, hits: [] }),
                  providerOptions: EPHEMERAL,         // tier 1 — breakpoint on the LAST tool
                })

                export const agent = new Agent({
                  id: 'cached-agent',
                  name: 'Cached Agent',
                  model: 'anthropic/claude-sonnet-4-5',
                  tools: { getWeather, searchDocs },  // tools render first
                  instructions: [
                    { role: 'system', content: 'You are a research assistant.' },
                    {
                      role: 'system',
                      content: '<large static policy / rubric block>',
                      providerOptions: EPHEMERAL,     // tier 2 — breakpoint on the LAST system block
                    },
                  ],
                })
                ```

                Yields `[tools]` and `[tools + system]` — Anthropic's first two nested prefixes, produced by *placement* rather than by a level rule. The **messages** tier has no documented Mastra seam: no message-level `providerOptions` with `cacheControl`.[mastra-prompt-caching](#mastra-prompt-caching)

                </details>
        - **Google ADK / Gemini — nothing but "the prefix changed".** No order and no levels: *"ADK keeps reusing a cache until it is actually past `expireTime`, has run past `cacheIntervals`, or its cached prefix changes"*; Gemini's only advice is *"put large and common contents at the beginning of your prompt"* and *"similar prefix."*[adk-context-caching](#adk-context-caching), [gemini-context-caching](#gemini-context-caching)
    - **Mid-conversation changes** — append-don't-edit, and who else can do it.[anthropic-mid-conversation](#anthropic-mid-conversation)
        - **Anthropic** — append a `{"role": "system"}` message instead of editing the top-level `system` field (prefix untouched, operator priority retained); `tool_addition`/`tool_removal` reference tools by name so the `tools` array never changes; **turn-scoped** `clear_at: "next_user_message"` reminders cost nothing after their turn.[anthropic-mid-conversation](#anthropic-mid-conversation)
        - **OpenAI** — `developer` role + *"append new messages rather than rewriting earlier turns"* (guidance, not a primitive); `additional_tools` **adds** mid-thread but there is **no removal** — dropping a tool *"will break the model's cache from that point forward."*[openai-prompt-caching](#openai-prompt-caching), [openai-tool-search](#openai-tool-search)
        - **Mastra** — no mid-conversation `role: "system"`; its cache-safe mid-loop move is a `<system-reminder>` *user* message, and `ToolSearchProcessor` load/unload mutates the real `tools` array (no name-referenced add/remove).[mastra-prompt-caching](#mastra-prompt-caching)
        - **Google ADK / Gemini** — `static_instruction` pins the static instruction and pushes the per-turn `instruction` into *user* content (inverted seam, same intent); **no** mid-conversation tool changes.[adk-context-caching](#adk-context-caching), [gemini-context-caching](#gemini-context-caching)
    - **MCP servers share the tool-schema prefix — and are its most fragile level.**[anthropic-tool-caching](#anthropic-tool-caching)
        - MCP toolsets resolve into the `tools` block — cached *first*, before system and messages.[anthropic-prompt-caching](#anthropic-prompt-caching) The breakpoint lands on the `mcp_toolset` entry, not on individual tools.[anthropic-tool-caching](#anthropic-tool-caching)
        - **A new server, renamed tool, or changed docstring/parameter invalidates the whole cache** — "entire cache (tools, system, messages)."[anthropic-tool-caching](#anthropic-tool-caching)
        - **Fix: keep the always-loaded set stable, discover the rest dynamically.** `defer_loading`/tool search appends discovered tools *after* the prefix — *"the prefix is untouched, so prompt caching is preserved."*[anthropic-tool-caching](#anthropic-tool-caching)
        - **But `defer_loading` saves the *window*, not the wire.** Full schemas still transit every request — it only keeps deferred tools out of the cached prefix.[anthropic-tool-search](#anthropic-tool-search) A deferred tool can't also carry `cache_control` (API 400), so the breakpoint goes on a non-deferred tool.[anthropic-tool-search](#anthropic-tool-search)
            - **OpenAI:** same idea, own flag — `defer_loading: true` on a function/MCP server plus `{"type": "tool_search"}` in `tools`; discovered tools are injected "at the end of the context window," which "allows the model's cache to be preserved from one request to another."[openai-tool-search](#openai-tool-search) In the Agents API, MCP tools are deferred automatically; "changing the loaded tool set will break the model's cache from that point forward."[openai-tool-search](#openai-tool-search)
            - **Mastra (provider-agnostic):** no `defer_loading` — its `ToolSearchProcessor` hands the agent `search_tools`/`load_tool` meta-tools instead; "activated tools are appended after existing tools, which keeps the cached prompt prefix stable," and loads are append-only, so they stay cache-friendly.[mastra-tool-search](#mastra-tool-search) Unloading a tool shifts the prefix, so the next turn "pays for a cache write instead of receiving a cache hit."[mastra-tool-search](#mastra-tool-search)
        - **Even JSON key order counts:** Swift/Go randomize map-key order during serialization, which alone changes the block bytes and breaks the cache.[anthropic-prompt-caching](#anthropic-prompt-caching)
        - **ADK is silent** on tools/MCP in caching — it keys only on a "cacheable prefix" that must not change.[adk-context-caching](#adk-context-caching)
    - **How to write the system instruction for it:** keep it byte-stable across turns — no timestamps, no per-request context injected into it — and put all per-turn variation in the tail, not the head.[anthropic-prompt-caching](#anthropic-prompt-caching)
- **ADK knobs** — `ContextCacheConfig` on the `App`:[adk-context-caching](#adk-context-caching)
    - `ttl_seconds` — cache lifetime, **default 1800**.
    - `cache_intervals` — max uses before refresh, **default 10**.
    - `min_tokens` — skip caching tiny requests; note the **default is `0`**, so this is a setting you choose.[adk-context-caching](#adk-context-caching), [unsupported](#unsupported)
    - With **LiteLLM/Azure backends** the same principle applies at the *provider* layer — your provider's prompt-caching keys off the stable prefix, and LiteLLM passes it through.[ding-mcp-performance](#ding-mcp-performance)
- **Cache pre-warming** — buy the first turn's latency back.[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **Mechanism:** send `max_tokens: 0` — the API reads the prompt, writes the cache at the breakpoint, returns no output.[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **Why it isn't redundant though the first send is "full-priced":** the pre-warm call is what absorbs the **cache write** (1.25× base); the first *real* request then finds the entry already written and pays only the **cache read** (0.1× base) and skips the re-prefill.[anthropic-prompt-caching](#anthropic-prompt-caching)
        - The stated payoff is **latency**, not cost alone: *"eliminates the cache-miss latency penalty on the first user interaction, reducing time-to-first-token (TTFT)."*[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **Requirements:** breakpoint on the *shared* prefix (not the placeholder), the same thinking/effort config as real traffic, re-warm inside the TTL (5 min, or the 1-hour cache).[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **When not worth it:** the docs never state it — they scope pre-warming to *latency-sensitive* apps. The first real turn performs the same cache write anyway; pre-warming only moves that write earlier so the first turn reads instead.[unsupported](#unsupported)
    - **In ADK:** no pre-warm knob — `ContextCacheConfig` has only `min_tokens`, `ttl_seconds`, `cache_intervals`, `create_http_options`; the first turn is a plain cache miss.[adk-context-caching](#adk-context-caching)
- **Tradeoff (the ledger entry).**
    - Caching is a *structure* reward: you get it only by assembling the window with a **stable prefix**.[adk-context-caching](#adk-context-caching)
    - That means accepting the instruction and tool schemas must be **fixed and ordered early** rather than free-form.
    - You trade a little assembly rigidity for a large cost/latency win — a decision you make, not a default you inherit.

---

### The science behind prompt caching (collapse-by-default)

<details>
<summary><strong>Why a reused prefix is safe, what is conserved, and when it can still bite</strong></summary>

- **Why a prefix is safe to reuse — the causal-attention argument.**
    - *"The KV cache of a prefix is not affected by the succeeding text."*[yao-cacheblend](#yao-cacheblend) The model reads the full prefix; only the recomputation is skipped.
    - On the output side, Anthropic states it outright: *"The response you receive is identical to what you would get if prompt caching were not used."*[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **The counter-case** — this safety fails for **non-prefix** reuse: ignoring cross-attention with preceding text "can lead to a wrong response."[yao-cacheblend](#yao-cacheblend)
- **What is being conserved** — why the cheaper rate exists at all.
    - On a cache hit the model does **not re-run the forward pass** over the cached prefix; only the new suffix is computed, and the cached part is read back.[yao-cacheblend](#yao-cacheblend)
    - What's saved is **compute** (the prefill/pre-processing of the prefix) and its **GPU time** — that saving is what the provider passes back as a lower price.
    - No token is omitted from the model's context; the discount is for *not recomputing*, not for *not reading*.
- **When caching can still matter.**
    - **Numerical divergence.** Recomputing vs. reusing cached KV can differ, because reduction order differs between prefill and decode. Vendors conflict: OpenAI says "identical requests are not guaranteed to produce identical outputs"; Anthropic says the response "is identical to what you would get if prompt caching were not used."[anthropic-prompt-caching](#anthropic-prompt-caching)
    - **Measurable, quantization-amplified divergence.** Fixed model, params, seed, order, batch size one: cache changed the trajectory on **36.2%** of episodes at 16-bit and **75.0%** at 4-bit, vs. a cache-off control that was "bit-identical… 0 of 800 episodes." Aggregate accuracy did not move.[patodiya-cache-divergence](#patodiya-cache-divergence)
    - **Other caching mechanisms *do* drop content.**
        - KV-cache *eviction* discards entries — H₂O drops ~80% with "significant performance degradation."[zhang-h2o](#zhang-h2o)
        - *Semantic* caching can return a wrong stored answer (matches on meaning, not exact text).
        - These are not prefix caching — but they are why the bare word "caching" can't mean "harmless."
    - **Stale / wrong-key cache.** Serving the wrong chunk, or a block past expiry, is a cache-*correctness* bug — distinct from grounding.
        - Vendor keys are coarse enough that a mismatch usually degrades to a **cache miss**, not a stale hit — the safer failure.
        - Anthropic reports hits "only when the beginning of your prompt is byte-for-byte identical," and labels prefix mismatches "Your bug."[anthropic-prompt-caching](#anthropic-prompt-caching)
        - Real wrong-key hazard exists for non-text modalities: the key can cover the text but not the image.

</details>

---

## Context budgeting: the three dials

Now the spend side. When a session grows, you have three dials, and you turn them in this order:

### Dial 1 — the per-turn budget

Before anything, set a **ceiling**: the maximum number of tokens you will ever send in one call (e.g., "never assemble more than ~20k tokens for this agent"). This is the absolute safety net that stops the unbounded-growth failure.[fu-long-context-deployment](#fu-long-context-deployment) It is not a strategy by itself — it's the tripwire that tells you the other two dials must be turned.

### Dial 2 — eviction (what to drop first)

When you must shed tokens, drop in this order:

1. **Dead intermediate results** — failed tool attempts, abandoned scratchpad steps, superseded drafts.
2. **Verbose tool outputs** — truncate to the fields the task needs; store the full result in an artifact, keep a pointer.[ding-mcp-performance](#ding-mcp-performance)
3. **Old retrieved material** — evidence from turns ago, unless the current task still needs it.
4. **Compacted history** — summarize old turns (Dial 3) rather than keeping them verbatim.[adk-context-compaction](#adk-context-compaction)

And the two things you **never** evict: the **standing instruction** (that's your policy — losing it is how instruction drift happens)[wallace-instruction-hierarchy](#wallace-instruction-hierarchy), [geng-control-illusion](#geng-control-illusion) and the **current task/question**.[shaier-context-before-question](#shaier-context-before-question)

**Sizing note — how many tool definitions belong in the prefix at all.** This is a budget decision, not a fixed cost: tool selection degrades as the candidate set grows, so the practical fix is to show the model a retrieved *shortlist* rather than every schema you own.[repantis-how-many-tools](#repantis-how-many-tools), [gan-rag-mcp](#gan-rag-mcp) The scaling limits are concrete — JSON schemas begin to overflow constrained windows by roughly 500 tools, while compressed schemas keep working past 800.[sakizli-tool-schema-compression](#sakizli-tool-schema-compression) "How many tools should this agent see?" is a question with a number attached; M8 is where you answer it.

> **Note the level.** The eviction policies you will meet in the systems literature — H₂O's heavy-hitter oracle,[zhang-h2o](#zhang-h2o) StreamingLLM's attention sinks[xiao-streamingllm](#xiao-streamingllm) — operate on the **KV cache inside the inference server**. They change which tokens the model *attends to*, not which tokens you *send*. The dial above is the harness-level version: it changes the request. Don't conflate them.[own-synthesis](#own-synthesis)

### Dial 3 — summarization-in-the-loop (compaction)

For the conversation history specifically, the right tool is **compaction**: periodically summarize older turns into a short running summary, keep only the recent few turns verbatim, and continue.[adk-context-compaction](#adk-context-compaction), [packer-memgpt](#packer-memgpt) It's lossy compression of the agent's memory — you trade *fidelity of old turns* for *attention and cost on the current turn*.

This is exactly what ADK's **context compaction** feature automates, via `EventsCompactionConfig` on the `App`, with two strategies:[adk-context-compaction](#adk-context-compaction)

- **Token-based (primary):** trigger when actual token volume crosses `token_threshold`, and keep the last `event_retention_size` events raw. This is the safety net for unpredictable workloads (a user pastes a 50k-token code block; a file upload floods the window).
- **Sliding-window (turn-based):** trigger every `compaction_interval` turns, with `overlap_size` prior events carried over for continuity. Predictable chats.

And you can supply a custom **`LlmEventSummarizer`** with a dedicated (often cheaper) model so compaction doesn't compete with the main task's model budget.[adk-context-compaction](#adk-context-compaction)

The honest caveat, because it's the whole point: **compaction is lossy, and its loss is invisible.[unsupported](#unsupported)** A summarized turn has dropped the exact wording, the exact numbers, the exact caveat — and the agent will not tell you it's reasoning from a lossy memory of its own past.[unsupported](#unsupported) Compaction is a *deliberate* acceptance of degraded history in exchange for attention on the present. Like every tradeoff in this course, it belongs in an ADR, not a config comment. And note the counter-evidence before you conclude that compression must hurt: targeted compression can *raise* accuracy while cutting tokens,[jiang-longllmlingua](#jiang-longllmlingua) and learned context compression can substitute for raw demonstrations.[chevalier-autocompressors](#chevalier-autocompressors) The loss is a property of *what* you compress, not of compressing.[fei-semantic-compression](#fei-semantic-compression) And it is not merely an implementation defect: compaction has been shown equivalent to one-way communication complexity, so a minimum loss is a property of the problem, not of your summarizer.[patodiya-cache-divergence](#patodiya-cache-divergence)

> **Failure mode (compaction):** summarizing away the *load-bearing* detail — the exact contract clause, the exact error message, the exact user requirement — while preserving the chit-chat.[unsupported](#unsupported) A naive summarizer keeps the narrative and drops the specifics; the agent then "remembers" the conversation without remembering any of the facts that mattered. The compaction prompt itself is a harness artifact that needs its own scrutiny.

---

## Beyond budgets: selecting by *content*, not position

The three dials above are all **positional** — they decide how much history to keep and how far back, not *which* turns matter to this question. But a user never says "give me turn 5" — they say *"remember when we discussed the Kunal Kamra Super-Thanks figure?"* or *"document the discussion from 'the problem with unions' through 'how to structure unions.'"* That is a different selector entirely: the assembly layer must resolve a **semantic reference** into the right turns, retrieve that span, and exclude what doesn't belong — *content-based selection*, not budget-based eviction.

This is where the "append everything, forever" default finally gets its full answer. **Session state is the source of truth** (the whole transcript); **the context window is a per-turn projection** of it;[adk-context](#adk-context) and **the assembly layer is the selector.** For the mechanism end to end — reference resolution, topic segmentation, span retrieval, relevance filtering, and the named systems that already do it (MemGPT/Letta,[packer-memgpt](#packer-memgpt) Zep,[rasmussen-zep](#rasmussen-zep) Mem0[chhikara-mem0](#chhikara-mem0)) — read the deep dive:

> **[Selective context assembly — the context window as a projection of session state](selective-context-assembly.md)** · the content-based selector, worked case by case, with the active-research frontier flagged honestly.

---

## Worked example: the research agent, budgeted

The domain spine, made concrete. A research agent runs a three-hour session over a corpus. Here's what actually accumulates, and how a designed context budget handles it:

- **Stable prefix (~4k tokens):** system instructions ("cite every claim; if evidence is absent, say so"), tool definitions, output format. *Cacheable — sent once, reused all session.*[adk-context-caching](#adk-context-caching), [anthropic-prompt-caching](#anthropic-prompt-caching)
- **Per-turn retrieval (~2–4k):** the top chunks for *this* question. *Fresh each turn; evicted after use.*
- **Tool results (variable):** a `fetch_paper` tool returns 8k tokens of full text; the harness keeps the abstract + relevant excerpt (~500 tokens) and stores the full text as an artifact. *Verbose output truncated at the seam.*[gan-rag-mcp](#gan-rag-mcp), [ding-mcp-performance](#ding-mcp-performance)
- **Conversation history:** compacted every ~6 turns into a running research-progress summary; the last 4 turns kept verbatim. *History costs stay flat instead of growing linearly.*[adk-context-compaction](#adk-context-compaction)
- **Scratchpad:** the agent's intermediate reasoning, *not* persisted into the window across turns — kept in working memory (M7) or regenerated when needed.

The result: at hour three, the window is ~10–12k tokens — not 90k — the current question sits at the end (recency), the policy sits at the start (primacy), and the three-hours-ago question is answered just as well as it was in minute one.[shaier-context-before-question](#shaier-context-before-question), [hsieh-ruler](#hsieh-ruler) **The agent didn't get dumber, because the window never got fat.**[hsieh-ruler](#hsieh-ruler)

> **Tradeoff (the ledger entry):** every budget mechanism costs *something*. Truncating tool output can drop a detail the next turn needs.[unsupported](#unsupported) Compacting history loses fidelity.[adk-context-compaction](#adk-context-compaction), [liu-lost-in-the-middle](#liu-lost-in-the-middle) A per-turn budget can force an eviction that was load-bearing. The discipline is not "keep the window small"; it is **"make each eviction and each compaction a named decision, with its cost written down"** — because the failure you're preventing (attention collapse, cost blowup) is invisible until it's catastrophic,[anthropic-prompting-best-practices](#anthropic-prompting-best-practices) while the failure you're causing (a dropped detail) is visible only much later, if ever.[unsupported](#unsupported)

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Design the context budget for a three-hour research session, as in the worked example — but for **your own** agent (or choose a support agent over a 2,000-document knowledge base).

1. **Draw the anatomy.** List the five window components (instructions, tool definitions, retrieved material, history, intermediate results) and, for each: your target token size, and whether it's *stable* or *variable*.
2. **Order it.** Write the assembly order — what goes first, what goes last, what goes in the marked middle block — and justify it in one sentence against position bias.[shaier-context-before-question](#shaier-context-before-question), [ok-prompt-order](#ok-prompt-order), [liu-lost-in-the-middle](#liu-lost-in-the-middle)
3. **Format it, then test it.** Write the markup for your marked middle block, and name the model you will A/B it on — because delimiter and markup choices move accuracy in *both* directions.[he-prompt-formatting](#he-prompt-formatting), [zhao-calibrate-before-use](#zhao-calibrate-before-use)
4. **Set the dials.** State your per-turn budget (Dial 1), your eviction order (Dial 2, with the two things you'll never evict),[own-synthesis](#own-synthesis) and your compaction settings (Dial 3: token threshold + retention, or interval + overlap — pick one and justify).[adk-context-compaction](#adk-context-compaction)
5. **Name the loss you're accepting.** For your compaction choice, write the single most dangerous thing that could be summarized away, and one sentence about how you'd mitigate it. Be specific about the field type: the measured failure mode is temporal and quantitative detail, so a rule of the form "preserve dates, times, and quantities verbatim" is better targeted than a vague "keep the important bits."[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent)
6. **Write the ADR.** Record the whole thing as a five-field ADR — "Context budget for the research agent" — with the consequence you're accepting stated explicitly.

**Why this exercise matters.** This is the first module where the deliverable is a *budget with a written rationale* rather than a piece of code. The instinct you're building — *name every component, order it deliberately, budget it, and record what the budget costs* — is the same instinct you'll apply to tools (M8), orchestration (M10), and evals (M12). Context is just the first place you practice it.

---

**In DSH:** prompt assembly is `core/system-prompt` (composable prompt sections + tool schemas), with `context`/`compaction` owning the budget and compaction, and bundled MCP tool definitions inflating token usage by default[ding-mcp-performance](#ding-mcp-performance) — governed by the invariant *"model-visible means logged"* (everything the model sees must be reconstructable from the session log).

---

## Where the literature disagrees with this module

The claims above are not uniformly settled. Several are contested in print, a few are asserted here more strongly than the sources support, and one is empirically backwards. The sharpest disagreement is about the *central* claim of the module. Recording these is the same discipline this module teaches for budgets — apply it to the module itself.

### 1. The "lost in the middle" effect is genuinely contested

This is not a minor quibble: the module's core mechanism ("facts in the middle go to die") is the one claim on which the literature most visibly splits. Present it as contested, not settled.

**What supports it:**

- The original result is real but carefully hedged: performance "can degrade" and is "often highest" when relevant information occurs "at the beginning or end," on two synthetic retrieval tasks.[liu-lost-in-the-middle](#liu-lost-in-the-middle)
- A follow-up attributes the pattern to attention rather than relevance — models "exhibit a U-shaped attention bias where the tokens at the beginning and at the end of its input receive higher attention, **regardless of their relevance**." That clause is what makes the causation positional.[hsieh-found-in-the-middle](#hsieh-found-in-the-middle)
    - *How Hsieh actually measured attention and derived the calibration → [found-in-the-middle.md](paper-details/found-in-the-middle.md).*
- Independent of position, effective context falls well short of advertised context: across 17 long-context models all claiming ≥32K, "only half of them can maintain satisfactory performance at the length of 32K."[hsieh-ruler](#hsieh-ruler)
- The effect is strongest only up to ~50% of a model's context window; beyond that, primacy weakens while recency holds, and "this effectively eliminates the LiM effect," leaving a distance-from-end bias instead.[veseli-positional-biases](#veseli-positional-biases)

**What contradicts it:**

- **The measurement may be an artifact.** In summarization, prior position-bias studies "rely heavily on n-gram matching techniques, which fail to capture semantic relationships in abstractive summaries." Using cross-encoder semantic alignment across five LLMs and six datasets yields "significantly different position bias patterns," and the authors conclude LLMs "use content from all positions more effectively than previously assumed, challenging common claims about 'lost-in-the-middle' behaviour."[rahimi-not-lost-after-all](#rahimi-not-lost-after-all)
- **Most current models are robust against it.** LongPiBench, testing multiple relevant pieces across three commercial and six open-source models, finds "while most current models are more robust against the 'lost in the middle' issue, there also exist noticeable biases related to the **spacing** of relevant information pieces."[tian-longpibench](#tian-longpibench) The bias did not vanish — it moved.
- **It may not be information loss at all.** Training models from scratch on human-memory paradigms reproduces the U-curve, leading the authors to argue the pattern is "not simply a flaw indicative of information loss but an adaptation to different information retrieval demands during pre-training."[salvatore-emergent-property](#salvatore-emergent-property)
- Even the recency half is task-dependent: the one dedicated serial-position study finds "Transformers show weak or absent recency effects in item recognition, a pattern which differs from human behavior."

**Consequence for the module.** Keep the design advice — "beginning or end, never the middle" is still the safest placement, and it is independently supported by query-position work.[shaier-context-before-question](#shaier-context-before-question), [ok-prompt-order](#ok-prompt-order) — but **stop teaching the mechanism as settled fact.** The honest framing: position affects use in *some* models and tasks, the size and even the sign of the effect is task-dependent, and the middle is a slot to keep small because the cost of being wrong is asymmetric, not because the failure is proven universal.

### 2. The module's *premise* has its strongest support from a source it does not cite

There is a cleaner justification for budgeting context than position bias, and it is worth leading with: **length alone hurts, independent of retrieval and independent of distraction.**

- Across five open- and closed-source LLMs on math, QA, and coding, "even when models can perfectly retrieve all relevant information, their performance still degrades substantially (**13.9%–85%**) as input length increases but remains well within the models' claimed lengths."[du-context-length-alone](#du-context-length-alone)
- The controls are what make this decisive: the failure persists "even when the irrelevant tokens are replaced with minimally distracting whitespace, and, more surprisingly, when they are all masked and the models are forced to attend only to the relevant tokens," and even "when all relevant evidence is placed immediately before the question."[du-context-length-alone](#du-context-length-alone)

- A related ceiling holds beyond 100K: long-context LLMs "still require significant advancements to effectively process 100K+ context," where simply retrieving a few passages is "not sufficient."[zhang-infinity-bench](#zhang-infinity-bench)
**Consequence.** This is the citation the module's thesis should rest on. It says: shrink the window because *length itself is a tax*, not merely because information might land in an unlucky position — and it survives every objection that the position-bias literature is now facing.

### 3. "Formatting is information" is the weakest *design* claim in the module

The module asserts that structure which "would be noise to a person is signal to it," and that deterministic structure "makes the model's job of *finding* the right thing cheaper." Format sensitivity is well established — but it is **not established as reliably positive**, which is the part the module needs:

- **A single character moves the score by ±23%.** On MMLU, "performance … can vary by ±23% depending on the choice of delimiter," and "one can manipulate model rankings to put any model in the lead by only modifying the single character separating examples." The brittleness "pervades topics, model families, and doesn't improve with scale."[su-single-character](#su-single-character)
- **Structured output can *cost* capability.** JSON, XML, LaTeX, and Markdown "substantially degrade reasoning and writing performance across open-weight models," and "format-requesting instructions alone cause most of the accuracy loss" — before any constrained decoding is applied. The paper's own mitigation is to decouple reasoning from formatting, not to add more markup.[lee-format-tax](#lee-format-tax)
- Even Anthropic's own guidance hedges, treating heavy format scaffolding as "likely becoming less important as models become more capable."[anthropic-prompting-best-practices](#anthropic-prompting-best-practices)

**Consequence.** **Format is a high-leverage design variable whose effect is empirically uncertain in sign, and must be A/B-tested per model.** The worked example's numbered `[1] <chunk>` block is a reasonable hypothesis, not a best practice. The one strongly supported formatting rule in the module is the *order*, not the markup — and that is §1 above.

### 4. Tool-schema bloat has *two* mechanisms, and the module names only the wrong one

The module's table says bloated tool schemas "Steal attention from the task." The measurements show two distinct failure modes, and the module conflates them:

- **Budget exhaustion** — tool schemas "consume the same context window needed for retrieval-augmented generation." The effect is binary rather than gradual: at an 8K budget, "JSON-schema tool definitions overflow the context window entirely, yielding near-zero EM," while compressed schemas restore functionality with "+20.5 pp average exact-match lift." But "at 32K — where both formats fit — four of five tested models show delta ≤ 1 pp, confirming the effect is purely budget-driven."[sakizli-tool-schema-compression](#sakizli-tool-schema-compression)
- **Selection confusion** — and this one *is* the attention story the module wants. Even when the tools fit comfortably, selection still fails: given 46 tools on a model with a 16K context window that "can fit all the tools, it fails to select the correct one… when only 19 tools are passed, the LLM chooses the correct tool." The reported cause is "the large number of available options confusing the LLM," not overflow.[paramanayakam-less-is-more](#paramanayakam-less-is-more)

So the module's mechanism claim is not wrong — it is *incompletely* right, naming the mechanism that only bites under pressure while missing the one that bites always. The practical consequence is the same either way: **retrieve a shortlist of tools rather than dumping every schema.** Prompt bloat drops tool-selection accuracy to a "13.62% baseline," and showing only retrieved candidates "more than triples" it to 43.13% while cutting prompt tokens by over 50%.[gan-rag-mcp](#gan-rag-mcp)

**A caveat on the fix.** "Retrieve a shortlist" is not universally safe: retrieval narrowing "can at-times hurt performance" when the retriever misses, and one evaluation found a 50-tool shortlist and a 7-tool shortlist achieving near-identical coverage (90.3% vs 90.8%).[repantis-how-many-tools](#repantis-how-many-tools) Shortlisting trades a selection problem for a recall problem — which is M5's subject, not a solved detail.

### 5. System instructions do not reliably outrank later text — and compaction is *documented* to lose them

The module treats the system/user boundary as a working primitive and treats the standing instruction as something you "never evict." Both halves are contradicted.

**The hierarchy is not reliable.**

- "The widely-adopted system/user prompt separation **fails to establish a reliable instruction hierarchy**," across six state-of-the-art models and "even for simple formatting conflicts."[geng-control-illusion](#geng-control-illusion)
- Worse, "societal hierarchy framings (e.g., authority, expertise, consensus) show **stronger influence** on model behavior than system/user roles," functioning as "latent behavioral priors with potentially greater impact than post-training guardrails."[geng-control-illusion](#geng-control-illusion)

**And the harness cannot simply refuse to evict it.** The most authoritative available artifact on this exact question is Claude Code's own context-window documentation, and it says the opposite of "never evict": its table of what survives compaction marks path-scoped rules and nested instruction files as summarized away with everything else, and instructs developers to fix this by moving rules out of the compacted span — "If a rule must persist across compaction, drop the `paths:` frontmatter or move it to the project-root CLAUDE.md," which is "re-injected from disk."[claude-code-context-window](#claude-code-context-window)

**Consequence.** "Never evict the standing instruction" is not a property the harness can guarantee from inside the window; it is a **design pattern** — keep the policy in a slot re-injected from outside the compacted span each turn. That is exactly what the ADK stable prefix and Claude Code's re-injection both implement. The placement rule is a *bias-toward-use*, not a guarantee of rank, and anything that must be enforced belongs in a capability boundary (a tool that refuses) rather than in prose — the conclusion M2's Tahoe case already reaches.

### 6. "A naive summarizer keeps the narrative and drops the specifics" — this one is empirically backwards

This is the module's most concrete compaction claim, and the one paper that actually measures the *composition* of gist-compression loss reports the opposite ordering:

- Gist abstraction "preserves relational and event structure while discarding dates and times."
- Quantitatively: an approximately **20-fold** improvement in temporal-expression preservation (3.05% → 62.39%) was achieved by a one-sentence prompt fix, "while named entity and event preservation rates **barely change** (×1.02 and ×1.11)."[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent)

So: narrative ✓, entities ✓, **time and quantities ✗** (3.05% preserved before the fix). The suffix needs its noun corrected. The right compactor rule is not "never summarize these fields" in general — it is specifically **"preserve dates, times, and quantities verbatim,"** because those are what a gist abandons by default.[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent)

**And the loss is not a bug you can engineer away.** Context compaction has now been given a formal treatment: the authors "prove an equivalence between the Context Generation Game and one-way communication complexity," so "the minimum context compaction budget for answering a set of queries within a target error is equal to the one-way communication complexity of the induced communication problem."[tirmazi-context-compaction-theory](#tirmazi-context-compaction-theory) Loss is an **information-theoretic floor**, which strengthens the module's "belongs in an ADR" instinct — you are choosing where to spend the loss, not whether to have any.

**The one detail that does need a benchmark:** a dedicated specificity/detail-retention benchmark for summarization does not appear to exist. The Sleeping Agent preservation analysis[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent) is the closest instrument located, and it measures temporal and entity preservation specifically rather than "specificity" generally.

### 7. Compression is not uniformly lossy — *what* is compressed is what matters

The module frames compaction as an exchange of fidelity for budget. The literature does not agree that loss is inherent to compression as a technique:

- **Targeted compression can *raise* accuracy.** LongLLMLingua "boosts performance by up to 21.4% with around 4x fewer tokens," improving "LLMs' perception of the key information" — addressing position bias and cost together.[jiang-longllmlingua](#jiang-longllmlingua)
- **Learned compression can substitute for raw context.** AutoCompressors produce summary vectors that are "good substitutes for plain-text demonstrations, increasing accuracy while reducing inference costs."[chevalier-autocompressors](#chevalier-autocompressors)
- **But detail loss is real and measurable.** Semantic compression reduces redundancy before the context reaches the model, and shows the technique is task-dependent rather than free.[fei-semantic-compression](#fei-semantic-compression)

**Consequence.** "Compaction is lossy, and its loss is invisible" describes *the module's own recommended implementation* — a general-purpose narrative summarizer over old turns — not compression as a technique. The defensible claim is narrower: **generic narrative summarization of history is lossy in a specific, predictable direction (time and quantities first); utility-gated or query-conditioned compression is measurably better.** That is an argument for making the compactor a designed artifact — which the module already urges — not an argument against compression.

### 8. "The agent will not tell you it's reasoning from a lossy memory" — restate as a harness gap

The module frames this as a model limitation. The model half is partly refuted: a GPT-3 model can "learn to express uncertainty about its own answers in natural language," with levels that "map to probabilities that are well calibrated."[lin-uncertainty-in-words](#lin-uncertainty-in-words)

The defensible version is narrower and better, and it points at the harness: **there is no channel through which compaction loss surfaces.** Claude Code's own documentation records that "the summarization happens without appearing in your terminal,"[claude-code-context-window](#claude-code-context-window) and work on parallel compaction finds retained information "fluctuate[s] substantially from run to run." The claim to teach is observability, not metacognition: *the model may be capable of reporting a degraded memory, but nothing in the harness asks it to, and the loss is not logged.*

### 9. The module's cost claim rests on complexity arguments, not measured NLP latency

The module says an irrelevant token costs "a cash charge, plus latency (input size scales response time)." The *direction* is solid, but be aware of what the evidence actually is: the quadratic-cost, prefill-versus-decode, and KV-cache-growth results come from architecture and serving-systems work,[fu-long-context-deployment](#fu-long-context-deployment) and the one in-scope NLP paper that states latency and cost growth does so as a one-line aside — "Using more than 20 retrieved documents only marginally improves reader performance (∼1.5% GPT-3.5-Turbo, ∼1% Claude-1.3), while significantly increasing the input context length (and thus latency and cost)"[liu-lost-in-the-middle](#liu-lost-in-the-middle) — not as a measured dependent variable. No controlled context-length-versus-wall-clock NLP study was located. Teach this claim from complexity and serving measurements, and say so.

### 10. Keep the window small — the counter-position the module never names

The module's thesis is that the window is a budget to *spend down*, and the worked example claims that the three-hours-ago question "is answered just as well as it was in minute one" once the window is held at 10–12k. There is a live counter-position: **long context can obviate retrieval and summarization for corpus-loading tasks.** The M2 literature review records the head-to-head — "when resourced sufficiently, LC consistently outperforms RAG in terms of average performance. However, RAG's significantly lower cost remains a distinct advantage" — i.e. the tradeoff is cost-versus-accuracy, with hybrid routing between them.

**Consequence.** That claim is a design assertion, not a measured result. Keeping the window small buys cost and latency; it can cost accuracy on tasks where the full corpus *is* the prerequisite — exactly the "context is the prerequisite" inapplicability case M2 flags. Note that §2 above cuts the other way and is better evidence: length alone hurts even with perfect retrieval. The two findings are not in conflict — one says long context is unavoidable for some tasks, the other says it is expensive even when retrieval succeeds — and together they are the real argument for a hybrid.

### 11. Framework claims: verified against the docs, with three corrections

Checked against the live ADK documentation and `google/adk-python` source rather than against the module's prose:

- **Confirmed exactly:** `ContextCacheConfig` defaults `ttl_seconds=1800` and `cache_intervals=10`;[adk-context-caching](#adk-context-caching) `EventsCompactionConfig` with `token_threshold`/`event_retention_size` and `compaction_interval`/`overlap_size`, plus `LlmEventSummarizer` with a configurable model;[adk-context-compaction](#adk-context-compaction) `InvocationContext`, `Runner`, and `run_async`;[adk-context](#adk-context) `static_instruction` as "a way to amend the system instructions for a generative model."[adk-context-caching](#adk-context-caching)
- **Correction 1 — `min_tokens` defaults to `0`.[adk-context-caching](#adk-context-caching)** The module's gloss "don't bother caching tiny requests" describes *intended use*, not the default; avoiding small-request caching is opt-in. (The doc's own example uses `min_tokens=2048, ttl_seconds=600, cache_intervals=5` — example values that are easy to mistake for defaults.)
- **Correction 2 — caching is not Gemini-only in implementation.** The public page is titled "Context caching with Gemini," but the same `ContextCacheConfig` is routed to Anthropic (`cache_control` breakpoints) and through LiteLLM. The module's "with LiteLLM/Azure backends … at the *provider* layer" is directionally right; the caveat is that Azure support is narrower than Anthropic's.
- **Correction 3 — `static_instruction` "persist[s] across a session" is the module's wording, not the docs'.** It is a constant on the agent, re-sent every turn, and the source notes that setting it "alone does NOT enable caching automatically."

A useful side-benefit of checking a real harness: Claude Code publishes representative startup token counts — a 4,200-token system prompt, 1,800 tokens of project instructions, ~970 tokens of MCP and skill listings.[claude-code-context-window](#claude-code-context-window) That is a concrete instance of "fixed overhead," and it is worth more than a borrowed across-the-board percentage, which remains unavailable.

---

## Sources (ADK docs)

- [Agent context](https://adk.dev/context/index.md)[adk-context](#adk-context)
- [Context caching with Gemini](https://adk.dev/context/caching/index.md)[adk-context-caching](#adk-context-caching)
- [Compress agent context (compaction)](https://adk.dev/context/compaction/index.md)[adk-context-compaction](#adk-context-compaction)
- [Session, State & Memory](https://adk.dev/sessions/index.md)[adk-sessions](#adk-sessions)

---

## Bibliography

*Literature behind the module's claims, with the framework documentation the module itself cites. **Citations use stable identifier keys, not position numbers.** Every inline citation is written `[key](#key)` and resolves to the bullet carrying that key, so entries can be added, removed, or reordered without rewriting a single citation — the BibTeX model, minus a backend to assign numbers. The bibliography is therefore an unordered bullet list, not a ranked one: the order of entries carries no meaning, and no entry's identity changes if you move it. Every entry hyperlinks to the paper's PDF. Items tagged (industry doc) are vendor documentation, (preprint) are not yet peer-reviewed, and (own synthesis) are the module's inferences rather than sourced claims. `cf.` marks a source that qualifies or contradicts the sentence it follows. `unsupported` is the module's unsupported-claims bucket and `own-synthesis` collects the course's own un-sourced synthesis: anything asserted above that no located source supports is cited there rather than to an invented reference.*

### Framework documentation (industry docs)

- <a id="adk-context-compaction"></a>[adk-context-compaction](#adk-context-compaction) · [**Compress agent context for performance (context compaction)** — Google ADK documentation](https://adk.dev/context/compaction/index.md) (industry doc)
- <a id="adk-context-caching"></a>[adk-context-caching](#adk-context-caching) · [**Context caching with Gemini** — Google ADK documentation](https://adk.dev/context/caching/index.md) (industry doc)
- <a id="adk-context"></a>[adk-context](#adk-context) · [**Agent context** — Google ADK documentation](https://adk.dev/context/index.md) (industry doc)
- <a id="adk-sessions"></a>[adk-sessions](#adk-sessions) · [**Session, State & Memory** — Google ADK documentation](https://adk.dev/sessions/index.md) (industry doc)

### Assembly discipline: ordering, instructions, formatting

- <a id="wallace-instruction-hierarchy"></a>[wallace-instruction-hierarchy](#wallace-instruction-hierarchy) · [**The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions** — Eric Wallace, Kai Xiao, Reimar Leike, Lilian Weng, Johannes Heidecke, Alex Beutel](https://arxiv.org/pdf/2404.13208) — arXiv:2404.13208, 2024.
- <a id="geng-control-illusion"></a>[geng-control-illusion](#geng-control-illusion) · [**Control Illusion: The Failure of Instruction Hierarchies in Large Language Models** — Yilin Geng, Haonan Li, Honglin Mu, Xudong Han, Timothy Baldwin, Omri Abend, Eduard Hovy, Lea Frermann](https://arxiv.org/pdf/2502.15851) — *AAAI-26* (main technical track), 2026. *cf.* — contradicts the assumption that the system/user split confers rank.
- <a id="shaier-context-before-question"></a>[shaier-context-before-question](#shaier-context-before-question) · [**It Is Not About What You Say, It Is About How You Say It: A Surprisingly Simple Approach for Improving Reading Comprehension** — Sagi Shaier, Lawrence E. Hunter, Katharina von der Wense](https://arxiv.org/pdf/2406.16779) — *Findings of ACL*, 2024.
- <a id="ok-prompt-order"></a>[ok-prompt-order](#ok-prompt-order) · [**Lost in the Prompt Order: Revealing the Limitations of Causal Attention in Language Models** — Hyunjong Ok, Jaeho Lee](https://arxiv.org/pdf/2601.14152) — *Findings of ACL*, 2026.
- <a id="su-single-character"></a>[su-single-character](#su-single-character) · [**A Single Character can Make or Break Your LLM Evals** — Jingtong Su, Jianyu Zhang, Karen Ullrich, Léon Bottou, Mark Ibrahim](https://arxiv.org/pdf/2510.05152) — arXiv:2510.05152, 2025. *cf.* — format sensitivity is large but not reliably positive.

### Formatting and selection

- <a id="lee-format-tax"></a>[lee-format-tax](#lee-format-tax) · [**The Format Tax** — Ivan Yee Lee, Loris D'Antoni, Taylor Berg-Kirkpatrick](https://arxiv.org/pdf/2604.03616) — arXiv:2604.03616, 2026. *cf.* — structured output can reduce reasoning accuracy.
- <a id="anthropic-prompting-best-practices"></a>[anthropic-prompting-best-practices](#anthropic-prompting-best-practices) · [**Prompting best practices — long-context prompting and XML structuring** — Anthropic Claude Platform documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) (industry doc)
- <a id="he-prompt-formatting"></a>[he-prompt-formatting](#he-prompt-formatting) · [**Does Prompt Formatting Have Any Impact on LLM Performance?** — Jia He, Mukund Rungta, David Koleczek, Arshdeep Sekhon, Franklin X Wang, Sadid Hasan](https://arxiv.org/pdf/2411.10541) — arXiv:2411.10541, 2024.
- <a id="zhao-calibrate-before-use"></a>[zhao-calibrate-before-use](#zhao-calibrate-before-use) · [**Calibrate Before Use: Improving Few-Shot Performance of Language Models** — Tony Z. Zhao, Eric Wallace, Shi Feng, Dan Klein, Sameer Singh](https://arxiv.org/pdf/2102.09690) — *ICML*, 2021.

### Measuring the cost: attention, position, and latency

- <a id="fu-long-context-deployment"></a>[fu-long-context-deployment](#fu-long-context-deployment) · [**Challenges in Deploying Long-Context Transformers: A Theoretical Peak Performance Analysis** — Yao Fu](https://arxiv.org/pdf/2405.08944) — arXiv:2405.08944, 2024. *cf.* — a serving-systems analysis; the latency case rests on architecture and systems work rather than a controlled NLP measurement.
- <a id="liu-lost-in-the-middle"></a>[liu-lost-in-the-middle](#liu-lost-in-the-middle) · [**Lost in the Middle: How Language Models Use Long Contexts** — Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang](https://arxiv.org/pdf/2307.03172) — *TACL*, 2023.
- <a id="hsieh-ruler"></a>[hsieh-ruler](#hsieh-ruler) · [**RULER: What's the Real Context Size of Your Long-Context Language Models?** — Cheng-Ping Hsieh, Simeng Sun, Samuel Kriman, Shantanu Acharya, Dima Rekesh, Fei Jia, Yang Zhang, Boris Ginsburg](https://arxiv.org/pdf/2404.06654) — *COLM*, 2024.
- <a id="veseli-positional-biases"></a>[veseli-positional-biases](#veseli-positional-biases) · [**Positional Biases Shift as Inputs Approach Context Window Limits** — Blerta Veseli, Julian Chibane, Mariya Toneva, Alexander Koller](https://arxiv.org/pdf/2508.07479) — *COLM*, 2025. *cf.* — the LiM effect weakens and then disappears above ~50% window utilization.
- <a id="packer-memgpt"></a>[packer-memgpt](#packer-memgpt) · [**MemGPT: Towards LLMs as Operating Systems** — Charles Packer, Sarah Wooders, Kevin Lin, Vivian Fang, Shishir G. Patil, Ion Stoica, Joseph E. Gonzalez](https://arxiv.org/pdf/2310.08560) — arXiv:2310.08560, 2023.
- <a id="hsieh-found-in-the-middle"></a>[hsieh-found-in-the-middle](#hsieh-found-in-the-middle) · [**Found in the Middle: Calibrating Positional Attention Bias Improves Long Context Utilization** — Cheng-Yu Hsieh, Yung-Sung Chuang, Chun-Liang Li, Zifeng Wang, Long T. Le, Abhishek Kumar, James Glass, Alexander Ratner, Chen-Yu Lee, Tomas Pfister, Ranjay Krishna](https://arxiv.org/pdf/2406.16008) — *Findings of ACL*, 2024. *(deep dive → [found-in-the-middle.md](paper-details/found-in-the-middle.md))*
- <a id="rahimi-not-lost-after-all"></a>[rahimi-not-lost-after-all](#rahimi-not-lost-after-all) · [**Not Lost After All: How Cross-Encoder Attribution Challenges Position Bias Assumptions in LLM Summarization** — Elahe Rahimi, Hassan Sajjad, Domenic Rosati, Abeer Badawi, Elham Dolatabadi, Frank Rudzicz](https://aclanthology.org/2025.findings-emnlp.846.pdf) — *Findings of EMNLP*, 2025. *cf.* — argues the U-shape is partly an n-gram-attribution artifact.
- <a id="tian-longpibench"></a>[tian-longpibench](#tian-longpibench) · [**Distance between Relevant Information Pieces Causes Bias in Long-Context LLMs** — Runchu Tian, Yanghao Li, Yuepeng Fu, Siyang Deng, Qinyu Luo, Cheng Qian, Shuo Wang, Xin Cong, Zhong Zhang, Yesai Wu, Yankai Lin, Huadong Wang, Xiaojiang Liu](https://aclanthology.org/2025.findings-acl.28.pdf) — *Findings of ACL*, 2025. *cf.* — most current models are said to be robust to LiM, with a spacing bias instead.
- <a id="salvatore-emergent-property"></a>[salvatore-emergent-property](#salvatore-emergent-property) · [**Lost in the Middle: An Emergent Property from Information Retrieval Demands in LLMs** — Nikolaus Salvatore, Hao Wang, Qiong Zhang](https://arxiv.org/pdf/2510.10276) — arXiv:2510.10276, 2025. *cf.* — argues the U-curve is an adaptation, not information loss.
- <a id="du-context-length-alone"></a>[du-context-length-alone](#du-context-length-alone) · [**Context Length Alone Hurts LLM Performance Despite Perfect Retrieval** — Yufeng Du, Minyang Tian, Srikanth Ronanki, Subendhu Rongali, Sravan Bodapati, Aram Galstyan, Azton Wells, Roy Schwartz, Eliu A. Huerta, Hao Peng](https://arxiv.org/pdf/2510.05381) — *Findings of EMNLP*, 2025. — isolates length from retrieval failure: 13.9%–85% degradation with perfect retrieval.
- <a id="shi-irrelevant-context"></a>[shi-irrelevant-context](#shi-irrelevant-context) · [**Large Language Models Can Be Easily Distracted by Irrelevant Context** — Freda Shi, Xinyun Chen, Kanishka Misra, Nathan Scales, David Dohan, Ed Chi, Nathanael Schärli, Denny Zhou](https://arxiv.org/pdf/2302.00093) — *ICML*, 2023.

### Tool-definition budget and tool-selection scaling

- <a id="gan-rag-mcp"></a>[gan-rag-mcp](#gan-rag-mcp) · [**RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection via Retrieval-Augmented Generation** — Tiantian Gan, Qiyao Sun](https://arxiv.org/pdf/2505.03275) — arXiv:2505.03275, 2025.
- <a id="paramanayakam-less-is-more"></a>[paramanayakam-less-is-more](#paramanayakam-less-is-more) · [**Less is More: Optimizing Function Calling for LLM Execution on Edge Devices** — Varatheepan Paramanayakam, Andreas Karatzas, Iraklis Anagnostopoulos, Dimitrios Stamoulis](https://arxiv.org/pdf/2411.15399) — *DATE*, 2025. *cf.* — selection fails even when every tool fits in the window.
- <a id="ding-mcp-performance"></a>[ding-mcp-performance](#ding-mcp-performance) · [**Network and Systems Performance Characterization of MCP-Enabled LLM Agents** — Zihao Ding, Mufeng Zhu, Yao Liu](https://arxiv.org/pdf/2511.07426) — arXiv:2511.07426, 2025.
- <a id="repantis-how-many-tools"></a>[repantis-how-many-tools](#repantis-how-many-tools) · [**How Many Tools Should an LLM Agent See? A Chance-Corrected Answer** — Vyzantinos Repantis, Ameya Gawde, Harshvardhan Singh, Joey Blackwell II](https://arxiv.org/pdf/2605.24660) — arXiv:2605.24660, 2026. *cf.* — shortlisting trades selection error for recall error; coverage can be near-identical at very different shortlist sizes.
- <a id="sakizli-tool-schema-compression"></a>[sakizli-tool-schema-compression](#sakizli-tool-schema-compression) · [**Tool-Schema Compression Enables Agentic RAG Under Constrained Context Budgets** — Furkan Sakizli](https://arxiv.org/pdf/2605.26165) — arXiv:2605.26165, 2026. *cf.* — isolates the budget-exhaustion mechanism: with adequate room the cost is "≤ 1 pp."
- <a id="zhang-h2o"></a>[zhang-h2o](#zhang-h2o) · [**H₂O: Heavy-Hitter Oracle for Efficient Generative Inference of Large Language Models** — Zhenyu Zhang, Ying Sheng, Tianyi Zhou, Tianlong Chen, Lianmin Zheng, Ruisi Cai, Zhao Song, Yuandong Tian, Christopher Ré, Clark Barrett, Zhangyang Wang, Beidi Chen](https://arxiv.org/pdf/2306.14048) — *NeurIPS*, 2023. *cf.* — an inference-level KV-cache eviction policy; a different mechanism from prefix caching, and one that does discard content.
- <a id="xiao-streamingllm"></a>[xiao-streamingllm](#xiao-streamingllm) · [**Efficient Streaming Language Models with Attention Sinks** — Guangxuan Xiao, Yuandong Tian, Beidi Chen, Song Han, Mike Lewis](https://arxiv.org/pdf/2309.17453) — *ICLR*, 2024. *cf.* — same inference-level caveat as [zhang-h2o](#zhang-h2o).
- <a id="zhang-infinity-bench"></a>[zhang-infinity-bench](#zhang-infinity-bench) · [**∞Bench: Extending Long Context Evaluation Beyond 100K Tokens** — Xinrong Zhang, Yingfa Chen, Shengding Hu, Zihang Xu, Junhao Chen, Moo Khai Hao, Xu Han, Zhen Leng Thai, Shuo Wang, Zhiyuan Liu, Maosong Sun](https://arxiv.org/pdf/2402.13718) — *ACL*, 2024.

### Prompt caching

- <a id="anthropic-prompt-caching"></a>[anthropic-prompt-caching](#anthropic-prompt-caching) · [**Prompt caching** — Anthropic Claude Platform documentation](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) (industry doc) — also the source of the cache-diagnostics behaviour, the per-level invalidation matrix, and the "identical response" assertion.
- <a id="anthropic-tool-caching"></a>[anthropic-tool-caching](#anthropic-tool-caching) · [**Tool use with prompt caching** — Anthropic Claude Platform documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-use-with-prompt-caching) (industry doc) — the MCP-toolset breakpoint rule, the `defer_loading`/tool-search cache-preservation rule, and the tool-definition invalidation row.
- <a id="anthropic-tool-search"></a>[anthropic-tool-search](#anthropic-tool-search) · [**Tool search tool** — Anthropic Claude Platform documentation](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) (industry doc) — the `defer_loading` wire-payload caveat (full schemas still transit), the deferred-tool `cache_control` 400 rule, and the MCP `mcp_toolset` `default_config` for deferred loading.
- <a id="anthropic-mid-conversation"></a>[anthropic-mid-conversation](#anthropic-mid-conversation) · [**Mid-conversation system messages and tool changes** — Anthropic Claude Platform documentation](https://platform.claude.com/docs/en/build-with-claude/mid-conversation-system-messages) (industry doc) — append-don't-edit: mid-conversation `system` messages, `tool_addition`/`tool_removal` blocks, and turn-scoped `clear_at`, all preserving the cached prefix.
- <a id="openai-tool-search"></a>[openai-tool-search](#openai-tool-search) · [**Tool search** — OpenAI API documentation](https://developers.openai.com/api/docs/guides/tools-tool-search) (industry doc) — `defer_loading` on functions/MCP servers plus `{"type": "tool_search"}`, with discovered tools appended at the end of context to preserve cache.
- <a id="mastra-tool-search"></a>[mastra-tool-search](#mastra-tool-search) · [**ToolSearchProcessor** — Mastra documentation](https://mastra.ai/reference/processors/tool-search-processor) (industry doc) — client-side `search_tools`/`load_tool` meta-tools; append-only loads keep the cached prefix stable.
- <a id="openai-prompt-caching"></a>[openai-prompt-caching](#openai-prompt-caching) · [**Prompt caching** — OpenAI API documentation](https://developers.openai.com/api/docs/guides/prompt-caching) (industry doc) — "the entire rendered prefix must match"; a settings table of what invalidates, but no per-level hierarchy.
- <a id="gemini-context-caching"></a>[gemini-context-caching](#gemini-context-caching) · [**Context caching** — Google Gemini API documentation](https://ai.google.dev/gemini-api/docs/caching) (industry doc) — implicit caching on "similar prefix"; explicit `CachedContent` fields (`tools`, `systemInstruction`, `contents`) are all "Immutable".
- <a id="mastra-prompt-caching"></a>[mastra-prompt-caching](#mastra-prompt-caching) · [**Prompt caching** — Mastra documentation](https://mastra.ai/articles/prompt-caching) (industry doc) — "a single character change anywhere in the cached prefix invalidates the match"; binary append-preserves vs modify-system-breaks.
- <a id="yao-cacheblend"></a>[yao-cacheblend](#yao-cacheblend) · [**CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion** — Jiayi Yao, Hanchen Li, Yuhan Liu, Siddhant Ray, Yihua Cheng, Qizheng Zhang, Kuntai Du, Shan Lu, Junchen Jiang](https://arxiv.org/pdf/2405.16444) — *EuroSys*, 2025. *cf.* — supplies the causal-attention argument for prefix safety *and* the counter-case for non-prefix reuse.
- <a id="patodiya-cache-divergence"></a>[patodiya-cache-divergence](#patodiya-cache-divergence) · [**Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence in LLM Serving** — Aditi Patodiya](https://arxiv.org/pdf/2609.04748) — arXiv:2609.04748, 2026 (preprint; submitted to *IEEE Access*). *cf.* — measures cache-induced trajectory divergence against a bit-identical cache-off control.

### Context compression and compaction

- <a id="jiang-longllmlingua"></a>[jiang-longllmlingua](#jiang-longllmlingua) · [**LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression** — Huiqiang Jiang, Qianhui Wu, Xufang Luo, Dongsheng Li, Chin-Yew Lin, Yuqing Yang, Lili Qiu](https://arxiv.org/pdf/2310.06839) — *ACL*, 2024.
- <a id="chevalier-autocompressors"></a>[chevalier-autocompressors](#chevalier-autocompressors) · [**Adapting Language Models to Compress Contexts** — Alexis Chevalier, Alexander Wettig, Anirudh Ajith, Danqi Chen](https://arxiv.org/pdf/2305.14788) — *EMNLP*, 2023.
- <a id="fei-semantic-compression"></a>[fei-semantic-compression](#fei-semantic-compression) · [**Extending Context Window of Large Language Models via Semantic Compression** — Weizhi Fei, Xueyan Niu, Pingyi Zhou, Lu Hou, Bo Bai, Lei Deng, Wei Han](https://arxiv.org/pdf/2312.09571) — arXiv:2312.09571, 2023.
- <a id="kyrkewood-sleeping-agent"></a>[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent) · [**The Sleeping Agent: What Gist-Based Context Compression Loses and Why** — Nicholas E. Kyrkewood](https://arxiv.org/pdf/2608.11775) — arXiv:2608.11775, 2026 (preprint). *cf.* — measures the composition of compaction loss: temporal expressions are what gist abstraction discards (3.05% preserved), while entity and event preservation barely move.
- <a id="tirmazi-context-compaction-theory"></a>[tirmazi-context-compaction-theory](#tirmazi-context-compaction-theory) · [**Context Compaction Theory** — Hayder Tirmazi, Sam Markelon, Allison Bishop, Michael Mitzenmacher](https://arxiv.org/pdf/2608.01326) — arXiv:2608.01326, 2026 (preprint; preliminary version). *cf.* — proves compaction loss is an information-theoretic floor, not an implementation defect.
- <a id="lin-uncertainty-in-words"></a>[lin-uncertainty-in-words](#lin-uncertainty-in-words) · [**Teaching Models to Express Their Uncertainty in Words** — Stephanie Lin, Jacob Hilton, Owain Evans](https://arxiv.org/pdf/2205.14334) — arXiv:2205.14334, 2022. *cf.* — partly refutes the module's framing that a model cannot report its own degraded state.

### Harness behaviour: what compaction actually preserves

- <a id="claude-code-context-window"></a>[claude-code-context-window](#claude-code-context-window) · [**Explore the context window (what survives compaction)** — Claude Code documentation](https://code.claude.com/docs/en/context-window.md) (industry doc) — first-party account of what compaction discards and what is re-injected from outside the window; also the source of representative startup token counts.

### Session memory and selective assembly

- <a id="rasmussen-zep"></a>[rasmussen-zep](#rasmussen-zep) · [**Zep: A Temporal Knowledge Graph Architecture for Agent Memory** — Preston Rasmussen, Pavlo Paliychuk, Travis Beauvais, Jack Ryan, Daniel Chalef](https://arxiv.org/pdf/2501.13956) — arXiv:2501.13956, 2025.
- <a id="chhikara-mem0"></a>[chhikara-mem0](#chhikara-mem0) · [**Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory** — Prateek Chhikara, Dev Khant, Saket Aryan, Taranjeet Singh, Deshraj Yadav](https://arxiv.org/pdf/2504.19413) — arXiv:2504.19413, 2025.

### Unsupported claims and own synthesis

- <a id="unsupported"></a>[unsupported](#unsupported) · **Unsupported.** Claims made in this module that no located source supports. Cited inline as [unsupported](#unsupported) rather than to an invented reference. Currently:
- <a id="own-synthesis"></a>[own-synthesis](#own-synthesis) · **Own synthesis (not sourced).** Claims this module makes that are the course's framing rather than literature findings, flagged so they are not mistaken for citations:
