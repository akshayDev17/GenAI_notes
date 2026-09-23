# Plan — M4 · Context Engineering I: Assembly & Budgets

> **status:** `approved` — both gates are current.

## How to review


| gate | what it reviews | state |
|---|---|---|
| 1 — structure | every section and linked file appears below with the right `kind`; resolve any `⚠ DECIDE` item | **APPROVED** 2026-09-23T20:36:45+00:00 by Akshay Prabhakant (git) — `8bc0496b5f399011` |
| 2 — checklists | every claim is grounded in the source (follow each leaf's `[src …]` anchor); nothing invented, nothing load-bearing dropped | **APPROVED** 2026-09-23T20:46:10+00:00 by Akshay Prabhakant (git) — `c0314059b1f56ac2` |

An approval fingerprints the plan it reviewed, so it survives rebuilds of the
same plan and **lapses the moment the plan changes** — the plan can never
change silently (SPEC §15).

## Coverage: 3 classified · 0 ignored · 0 needs-review · 42 sections · 98 leaves · 13 collapsibles · 0 mermaid

# M4 · Context Engineering I: Assembly & Budgets  [src README.md:1]
  - (checklist: empty)
## Contents  [src README.md:9]
    - (checklist: empty)
## Opening scene — the agent that got dumber as it worked  [src README.md:55]
    - The research agent started sharp. "Summarize the merger filings," it said, and produced a tight, sourced brief in forty seconds.
    - Three hours later, deep into the same session, the same agent was asked a question it had *answered correctly that morning* — and got it wrong, slowly, at five times the cost.
    - The team's diagnosis: "the model degraded." It hadn't. The model was identical.
    - What had changed, steadily, silently, all session long, was the **context window** - the single block of text the model reads every time it thinks.
    - Every turn had appended a tool result here, a retrieved chunk there, a scratch-pad note, a user clarification.
    - By hour three the window held ~90,000 tokens, most of them irrelevant to the current question, all of them being paid for and — worse — all of them *competing for the model's attention*.
    - The agent didn't get dumber. It got **drowned**. And nobody had budgeted the one resource that was doing the drowning.
    - *The scene above is a composite illustration, not a reported case study — the token counts and durations are invented to show the shape of the failure. The claims this module makes about the mechanisms behind it are sourced below.*
    - This module is the first half of the cognitive layer: **assembly and budgets** — what goes into the window, in what form, and what it costs. The *second* half (how the right facts get there, and how we know they're right) is M5.
    narrative (compacted):
      - [bullet] A research agent started sharp, delivering a tight sourced brief on merger filings in forty seconds.
      - [bullet] Hours later in the same session it answered wrongly - slowly, at five times the cost - a question it had aced that morning.
      - [bullet] The team blamed model degradation, but the model itself was identical.
      - [bullet] What changed steadily was the context window: the one block of text the model reads at every step.
      - [bullet] Each turn appended a tool result, a retrieved chunk, a scratch note, a clarification.
      - [bullet] By hour three it held ~90,000 tokens: mostly irrelevant, all paid for, all competing for attention.
      - [prose] The agent wasn't dumber - it drowned, and nobody had budgeted the resource doing the drowning.
      - [prose] An illustrative composite, not a case study: the token counts and durations are invented; the mechanism claims are sourced below.
      - [prose] First half of the cognitive layer, covering assembly and budgets: what enters the window, in what form, and at what cost. M5 handles sourcing and verifying facts.
    prompt: A long agent session returns a wrong, slow, five-times-costlier answer to a question it handled correctly hours earlier, on a model that never changed. What is the correct diagnosis, and through which two channels does the material accumulated over the session do its damage?
    reveal: Diagnosis: not degradation — drowning. The model is identical; the only thing that changed steadily, silently, all session long, is the context window, the single block of text the model reads every time it thinks. Each turn appended something — a tool result, a retrieved chunk, a scratch-pad note, a clarification — so by hour three the window held ~90,000 tokens. The damage runs through two channels. (1) Every one of those tokens is billed on every turn, so cost and latency grow with the session. (2) They compete for the model's finite attention, so correctness falls even though most of that material is irrelevant to the current question. The resource doing the drowning was never budgeted. Keep it honest: the scene is a composite illustration, not a reported case study — the token counts and durations are invented to show the shape of the failure, and only the mechanism claims are sourced. Scope of the module that follows: the first half of the cognitive layer, assembly and budgets — what goes into the window, in what form, and at what cost. How the right facts get there, and how we know they are right, is the second half.
## The context window is a budget, not a canvas  [src README.md:72]
    - Every model call carries **three** costs, and beginners track only one:
    - [table 4×3] (line 76)
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
    narrative (compacted):
      - [prose] Every model call carries three costs, and beginners track only one.
      - [table] Cost What it is Consequence of ignoring it
      - [table] **Token cost** You pay for every input token, every turn, at your input price Linear cost blowup as sessions grow[fu-long-context-deployment](#fu-long-context-deployment)
      - [table] **Attention cost** The model's attention is finite and *positional*; more context dilutes it Correctness falls, especially for facts in the middle[liu-lost-in-the-middle](#liu-lost-in-the-middle)
      - [table] **Format cost** Asking for a *shape* (JSON, XML, LaTeX, Markdown) taxes the capability you asked for — *on top of* the token (since formatting instructions will be represented as tokens) and attention cost (since formatting instructions will compete with other tokens to occupy context window) those instructions already incur Accuracy drops on the same task, with the same content[lee-format-tax](#lee-format-tax)
      - [bullet] Money is the first.
      - [bullet] The second concerns quality, and it is what produces the 'model got dumber' misdiagnosis.
      - [bullet] You have met this failure class: M2's position bias (lost in the middle) and instruction drift, where policy is drowned by later text.
      - [bullet] Both are context-assembly failures, and both are yours to design away.
      - [bullet] The third goes unbudgeted because it resembles a rendering detail.
    prompt: Every model call carries three costs and beginners track one. Name all three with the failure each produces, and explain why format cost is not already covered by the other two.
    reveal: Token cost — you pay for every input token, every turn, at your input price; ignore it and cost blows up linearly as sessions grow. Attention cost — the model's attention is finite and positional, so more context dilutes it; ignore it and correctness falls, especially for facts in the middle (position bias, lost-in-the-middle) and for policy drowned by later text (instruction drift). This is the cost that produces the 'the model got dumber' misdiagnosis, and both of its failure modes are context-assembly failures, which makes them yours to design away. Format cost — asking for a shape (JSON, XML, LaTeX, Markdown) taxes the capability you asked for, so accuracy drops on the same task with the same content. It is additive to the other two, not reducible to them: the formatting instruction is itself tokens, so it carries token cost, and it competes with other tokens, so it carries attention cost — and on top of both it degrades the work. That is why it goes unbudgeted: it looks like a rendering detail. The framing the section title carries: the window is a budget to spend, not a canvas to fill.
    [diagram] mermaid (agent-authored):
      ```mermaid
      mindmap
        costs[Three costs]
          token[Token cost]
          attention[Attention cost]
          format[Format cost]
      ```
#### Why format is its own budget line  [src README.md:88]
      - Format cost is scoped narrowly: it is the cost of **constraining the model's output shape**, and nothing else. (Formatting on the *input* side — examples, templates, delimiters — is a different sensitivity with a different mechanism, treated under attention cost.)
      - The measured quantity is a difference of two performances on the same task:
      - Format tax = Perf(freeform) − Perf(format-constrained)
      - Positive means requiring a shape degraded the work.
      - The measurement uses two setups that need names, because the result turns on the difference between them:
      - **1-Turn (GET·):** one generation; the model produces its answer *and* the required format in the same pass. The prompt carries the format spec (G), examples (E), and the task (T).
      - **2-Turn (··T· → GET·):** two generations. First the model answers freeform (no format instruction at all); then a second pass reformats that answer under the *same* format instructions.
      - Same format instructions in both — only *when* the format is applied changes, and that is what isolates the tax. On the LaTeX writing task, one open-weight model paid **15.7 quality points** in 1-Turn and **7.0** in 2-Turn.[lee-format-tax](#lee-format-tax)
      - So the fix is real but partial: 2-Turn recovers **8.7 of the 15.7** — just over half — and it is not uniform (one model's tax *grew* in 2-Turn). It also buys the recovery with an extra call and roughly doubled token consumption.[lee-format-tax](#lee-format-tax) Decoupling reasoning from formatting is a mitigation, not a cure, and it costs the same currency this module is about.
      - **Practical rule, stated once:** keep format requests late and narrow rather than pinning a heavy output schema into the standing instruction, where it is re-applied — and re-charged — every turn.
      - **Caveats.** Most recent closed-weight models show little to no tax, so it is a gap open-weight models have yet to close rather than a permanent property of structured generation.[lee-format-tax](#lee-format-tax) The evidence rests on one systematic study; treat the magnitude as provisional and A/B it on your own model.[unsupported](#unsupported)
      narrative (compacted):
        - [prose] Format cost means only this: constraining the output shape. Input-side formatting - examples, templates, delimiters - is a separate sensitivity with its own mechanism, under attention cost.
        - [prose] The measured quantity is the gap between two performances on one task.
        - [prose] Format tax equals freeform performance minus format-constrained performance.
        - [prose] A positive value means demanding a shape hurt the work.
        - [prose] Two setups, needing names because the result hinges on their difference.
        - [bullet] 1-Turn (GET·): a single generation produces the answer and the required format together, with format spec, examples, and task in the prompt.
        - [bullet] 2-Turn (··T· → GET·): two generations - a freeform answer first, then a second pass reformatting it under identical format instructions.
        - [prose] Only when the format is applied differs, which isolates the tax. On LaTeX writing one open-weight model lost 15.7 quality points in 1-Turn and 7.0 in 2-Turn.
        - [prose] The fix is partial: 2-Turn recovers 8.7 of 15.7, non-uniformly, costing an extra call and roughly double tokens - mitigation, not cure.
        - [prose] Practical rule: keep format requests late and narrow; do not pin a heavy output schema into standing instructions, where every turn re-applies and re-charges it.
        - [prose] Caveats: recent closed-weight models show almost no tax - a gap open weights have not closed. One study only, so treat the magnitude as provisional.
      prompt: Define the format tax as a measured difference, explain what the 1-Turn versus 2-Turn comparison isolates about its cause, and report how much of the tax the decoupled setup recovers and at what price.
      reveal: Scope first: format cost means only the cost of constraining the output shape. Input-side formatting — examples, templates, delimiters — is a different sensitivity with a different mechanism, filed under attention cost. Measured quantity: format tax = Perf(freeform) − Perf(format-constrained) on the same task; a positive value means demanding a shape degraded the work. Two setups, because the result turns on their difference. 1-Turn (GET·): one generation produces the answer and the required format together, with format spec (G), examples (E), and task (T) in the prompt. 2-Turn (··T· → GET·): two generations — a freeform answer first with no format instruction at all, then a second pass reformatting it under the same format instructions. The format instructions are identical in both; only when they are applied changes, and that is precisely what isolates the tax from the content. On LaTeX writing, one open-weight model paid 15.7 quality points in 1-Turn and 7.0 in 2-Turn — recovering 8.7, just over half, non-uniformly (one model's tax grew), bought with an extra call and roughly doubled token consumption. Decoupling reasoning from formatting is a mitigation in the same currency, not a cure. Practical rule: keep format requests late and narrow; do not pin a heavy output schema into standing instructions where every turn re-applies and re-charges it. Caveats: recent closed-weight models show little to no tax, and this rests on one study — treat the magnitude as provisional.
      [diagram] mermaid (agent-authored):
        ```mermaid
        flowchart TD
          f[Same format instructions] --> a[1-Turn answer and shape]
          f --> b[2-Turn freeform then reformat]
          b --> c[Recovers half the tax]
        ```
##### Is code output a format?  [src README.md:111]
        - The definition above turns on a phrase worth pulling out: format "specifies presentation, not content — a **pure transduction** (a rewriting that preserves all content, changing only its form) that should leave task performance unchanged."[lee-format-tax](#lee-format-tax) That is a testable criterion, not a slogan:
        - **Something is a format when the content is determined independently of it** — when you could re-render the same content another way without loss.
        - The answer to a math problem is fixed before you choose JSON. Re-render to XML, content unchanged. **Format.**
        - The text of an essay is fixed before you choose Markdown. **Format.**
        - *"Compute the median"* in Python versus Rust is **not** the same program re-rendered — algorithms, data structures, memory and error handling, and what's idiomatic all change. **Not format: task specification.**
        - So most code requests are not format, and this budget line does not apply to them.
        - A real sub-class *does* satisfy pure transduction, and the tax should apply to it: *"write the provided algorithm in Go"* (algorithm fixed elsewhere), transpilation and codemods, and schema-constrained artifacts such as a JSON Schema, a `.proto`, or a config file.
        - **So the answer is not yes-or-no.** Code is format-ambiguous; the discriminator is whether the language choice is transparent to the solution.
        - [details] Why this matters beyond pedantry
        - [details] Why the code case stays open
        - \
        - **The mental model that carries this whole module:** the context window is **live currency**.
        - You spend it every turn, and you spend it on *attention* as much as on money — and on *format* as much as either.
        - A token that is present but irrelevant is not free — it is a *distraction tax* on every other token,[shi-irrelevant-context](#shi-irrelevant-context), [unsupported](#unsupported) plus a cash charge, plus latency (input size scales response time).[fu-long-context-deployment](#fu-long-context-deployment)
        - The discipline of context engineering is deciding, deliberately, what earns a place — and in what form.
        - **Failure mode (the module in one line):** treating the context window as a place to *put* things rather than a budget to *spend*. The default agent — append everything, forever — is not "simple," it's a slow, expensive degradation curve with a correctness cliff at the end.[liu-lost-in-the-middle](#liu-lost-in-the-middle)
        narrative (compacted):
          - [prose] The definition turns on one phrase: format fixes presentation, not content - a lossless re-rendering that should leave task performance unchanged. That is a testable criterion, not a slogan.
          - [bullet] Content counts as a format when it is determined independently, re-renderable another way without loss.
          - [bullet] A math answer is fixed before you choose JSON; re-rendered as XML the content is unchanged. Format.
          - [bullet] An essay's text is fixed before you choose Markdown. Format.
          - [bullet] 'Compute the median' in Python versus Rust is not the same program re-rendered: algorithms, data structures, memory, error handling and idiom all change. Not format but task specification.
          - [bullet] Most code requests are therefore not format, and this budget line does not apply to them.
          - [bullet] A genuine sub-class does satisfy pure transduction and should be taxed: 'write the provided algorithm in Go', transpilation, codemods, and schema-constrained artifacts like JSON Schema, .proto, or config files.
          - [bullet] So it is not yes-or-no: code is format-ambiguous, and what settles it is whether the solution stays transparent to the language choice.
          - [details] Why this is more than pedantry.
          - [details] Why the code case remains unresolved.
          - [prose] \
          - [prose] The mental model carrying the module: the context window is live currency.
          - [bullet] You spend it each turn on attention as much as on money, and on format as much as either.
          - [bullet] A present but irrelevant token is not free: it taxes attention as distraction, plus cash and latency, since input size scales response time.
          - [prose] Context engineering is deciding deliberately what earns a place, and in what form.
          - [prose] Failure mode in one line: treating the window as somewhere to put things, not a budget to spend. Append-everything is not simple - just costly decline into a correctness cliff.
        prompt: What single criterion decides whether an output shape counts as a format, and therefore whether the format tax applies at all? Apply it to 'compute the median, in Python vs Rust' and to 'write the provided algorithm in Go', and explain why the code case is left open.
        reveal: Criterion: format specifies presentation, not content — a pure transduction, a rewriting that preserves all content and changes only its form, so it should leave task performance unchanged. Its operational test: the content is determined independently of the shape, i.e. you could re-render the same content another way without loss. A math answer is settled before you choose JSON, and re-rendered as XML the content is unchanged; an essay's text is settled before you choose Markdown — both are format. 'Compute the median' in Python versus Rust fails the test: algorithms, data structures, memory and error handling, and what is idiomatic all change, so it is task specification, not format — and most code requests fall on that side, where this budget line does not apply. But it is not yes-or-no: code is format-ambiguous. A genuine sub-class does satisfy pure transduction and should be taxed — 'write the provided algorithm in Go' (algorithm fixed elsewhere), transpilation, codemods, and schema-constrained artifacts such as JSON Schema, .proto, or config files. Note the baseline is not 'no structure' but no additional format instruction beyond the task, so structure the task already implies counts as content. The code case stays open because the yardstick changes (JSON and LaTeX can be scored against gold text; code is scored by execution, so the difference is not computable as written) and because almost nothing grammar-constrains Python, leaving whatever tax exists almost entirely prompt-side. Nearby mental model: the window is live currency — a present-but-irrelevant token is not free; it taxes attention as distraction, plus cash, plus latency.
        [diagram] mermaid (agent-authored):
          ```mermaid
          flowchart TD
            q[Content re-renderable without loss] --> y[Format]
            q --> n[Task specification]
          ```
## What actually goes into the window  [src README.md:152]
    - Before you can budget it, you have to name it. Here is the anatomy of a context window, and for each component: who writes it, what it costs, and how it fails.
    - [table 6×4] (line 156)
      | Component | Who writes it | What it costs | Its failure mode |
      |---|---|---|---|
      | **System instructions** | You (the harness) | Fixed, per turn | Drift: drowned or contradicted by later text (M2 class 4)[wallace-instruction-hierarchy](#wallace-instruction-hierarchy), [geng-control-illusion](#geng-control-illusion) |
      | **Tool definitions** | You (the harness) | Fixed, per turn | Steal attention from the task; bloated schemas[gan-rag-mcp](#gan-rag-mcp), [paramanayakam-less-is-more](#paramanayakam-less-is-more) |
      | **Retrieved material** | Retrieval pipeline | Variable, per turn | Wrong/stale/irrelevant → grounding failure (M2 class 1)[hsieh-ruler](#hsieh-ruler) |
      | **Conversation history** | The session (events) | Grows every turn | The biggest budget leak; irrelevant history buries the present[hsieh-ruler](#hsieh-ruler) |
      | **Intermediate results** | Tool outputs, scratchpad | Variable | Verbose tool dumps; dead-end reasoning steps[gan-rag-mcp](#gan-rag-mcp) |
    - Two observations that should reframe how you see the window:
    - 1. **Three of five components are fixed overhead** (instructions, tool definitions, and — in a naive agent — a stable prefix).[unsupported](#unsupported) Fixed overhead is where **caching** pays off (see below).[ding-mcp-performance](#ding-mcp-performance), [gan-rag-mcp](#gan-rag-mcp) Variable components are where **budgeting** pays off.
    - 2. **The conversation history is the silent killer.** In a long session, most of the window ends up being *old turns* — and old turns are the least relevant thing in the room, yet they sit in the most expensive slot (every one of them re-sent every turn).[ding-mcp-performance](#ding-mcp-performance) This is exactly what *compaction* exists for (see below).[adk-context-compaction](#adk-context-compaction)
    narrative (compacted):
      - [prose] Naming precedes budgeting: the anatomy of a window, and for each component who writes it, what it costs, and how it fails.
      - [table] Component Who writes it What it costs Its failure mode
      - [table] **System instructions** You (the harness) Fixed, per turn Drift: drowned or contradicted by later text (M2 class 4)[wallace-instruction-hierarchy](#wallace-instruction-hierarchy), [geng-control-illusion](#geng-control-illusion)
      - [table] **Tool definitions** You (the harness) Fixed, per turn Steal attention from the task; bloated schemas[gan-rag-mcp](#gan-rag-mcp), [paramanayakam-less-is-more](#paramanayakam-less-is-more)
      - [table] **Retrieved material** Retrieval pipeline Variable, per turn Wrong/stale/irrelevant → grounding failure (M2 class 1)[hsieh-ruler](#hsieh-ruler)
      - [table] **Conversation history** The session (events) Grows every turn The biggest budget leak; irrelevant history buries the present[hsieh-ruler](#hsieh-ruler)
      - [table] **Intermediate results** Tool outputs, scratchpad Variable Verbose tool dumps; dead-end reasoning steps[gan-rag-mcp](#gan-rag-mcp)
      - [prose] Two observations should reframe how you see the window.
      - [prose] Three of five components are fixed overhead - instructions, tool definitions, and in a naive agent a stable prefix - where caching pays; variable components are where budgeting pays.
      - [prose] Conversation history is the silent killer: long sessions fill the window with old turns, least relevant yet re-sent every turn in the costliest slot. Compaction exists for this.
    prompt: Name the five components of a context window with who writes each and how it fails. Then say which components are fixed overhead versus variable, why that split decides whether caching or budgeting is the lever, and which component is the silent killer.
    reveal: Naming precedes budgeting: for each component, who writes it, what it costs, how it fails. (1) System instructions — written by you, the harness; fixed per turn; fail by drift, drowned or contradicted by later text. (2) Tool definitions — you, the harness; fixed per turn; fail by stealing attention from the task, worst with bloated schemas. (3) Retrieved material — the retrieval pipeline; variable per turn; fails as wrong, stale or irrelevant grounding. (4) Conversation history — the session's events; grows every turn; the biggest budget leak, where irrelevant history buries the present. (5) Intermediate results — tool outputs and scratchpad; variable; fail as verbose tool dumps and dead-end reasoning steps. Reframe one: three of the five are fixed overhead — instructions, tool definitions, and in a naive agent a stable prefix. Fixed overhead is where caching pays off; the variable components are where budgeting pays off. Reframe two: conversation history is the silent killer. In a long session most of the window ends up being old turns, the least relevant material in the room, yet sitting in the most expensive slot because every one of them is re-sent every turn. Compaction exists for exactly that.
    [diagram] mermaid (agent-authored):
      ```mermaid
      flowchart TD
        w[Window components] --> f[Fixed overhead]
        w --> v[Variable components]
        v --> h[History: the silent killer]
      ```
## Assembly discipline  [src README.md:171]
    - Budgeting is necessary; *ordering and formatting* are where quality actually comes from. Three disciplines:
    narrative (compacted):
      - [prose] Budgeting is necessary, but ordering and formatting are where quality comes from. Three disciplines.
    prompt: Budgeting is called necessary but not sufficient. If ordering and formatting are where quality comes from, state what each discipline claims — and what does 'formatting is information' assert about how the model reads structured input?
    reveal: Framing: budgeting is necessary, but ordering and formatting are where quality actually comes from, so the disciplines are about placement and shape rather than about size. Position is a design input and a stability requirement, and those are two separate reasons to care: where content sits changes whether it is used — beginning for standing policy by primacy, end for the current task and latest messages by recency, middle for supporting material only, since use and attention both dip there — while whether the prefix changes determines whether any of it is cacheable at all. Ordering within a pair is independent of position: context precedes the question that reads it. Formatting is information: the model is not a human reader but a pattern-matching one, so structure that would be noise to a person is signal to it. Concretely the input gets laid out in labelled, predictable sections — retrieved evidence as a numbered chunk list, then the task, then hard constraints — instead of arriving as one undifferentiated block. The point of both disciplines is the same: assembly decisions, not token counts, decide whether the model uses what you gave it.
### 1. Position is a design input — and a stability requirement  [src README.md:175]
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
      narrative (compacted):
        - [bullet] Position and stability are two separate reasons to care about placement, easily conflated.
        - [bullet] Where content sits changes whether it is used.
        - [bullet] Whether the prefix changes determines whether it is cacheable at all.
        - [bullet] Placement rule: the same slots every turn.
        - [bullet] Beginning holds standing policy (primacy); instructions that must persist across turns belong at the start.
        - [bullet] End holds the current task and the latest few messages (recency) - what the model looks at while producing the next token.
        - [bullet] Middle: supporting material only - retrieval, tool results, uncompacted history - since use and attention dip there. Attention walkthrough: found-in-the-middle.md.
        - [bullet] Keep it small: this is the slot compaction exists to drain.
        - [bullet] Ordering within a pair matters independently of position.
        - [bullet] Context precedes the question that reads it, worth up to +31%; the reverse order costs over 14 percentage points.
        - [bullet] Stability is the requirement that position alone does not give you.
        - [bullet] Caching keys off a prefix that is unchanging, not one that is important.
        - [bullet] Policy-first is not enough; policy-first-and-never-changing is what makes the prefix cacheable.
        - [bullet] In ADK, `static_instruction` is the knob: instructions persisting across a session, held in the stable prefix instead of re-sent inside the mutable body.
        - [bullet] Memorability test: position raises the odds of use, it does not guarantee it.
        - [bullet] Load-bearing facts should be re-injected near their point of use instead of trusting end-placement alone.
        - [bullet] The position penalty is fill-dependent, not a fixed law.
      prompt: Why are position and stability two different reasons to care about placement, and which one does caching respond to? Then give the placement rule for beginning, middle and end, plus the ordering rule that holds independently of position.
      reveal: Two reasons, easy to conflate. (1) Where content sits changes whether it is used — a primacy/recency effect. (2) Whether the prefix changes determines whether it is cacheable at all — a stability effect. Caching keys off an unchanging prefix, not an important one, so policy-first is not enough: policy-first-and-never-changing is what makes a prefix cacheable. In ADK the knob is static_instruction — instructions that persist across a session, held in the stable prefix instead of re-sent inside the mutable body. Placement rule, same slots every turn: beginning holds the standing policy, since instructions that must persist across turns belong at the start (primacy); end holds the current task and the latest few messages (recency) — what the model looks at while producing the next token; middle holds supporting material only — retrieved context, tool results, not-yet-compacted history — because use and attention both dip there, so it may carry only what the model may look back at, never what it must act on or remember. Keep that slot small; it is the one compaction exists to drain. Ordering within a pair is independent of position: context precedes the question that reads it, worth up to +31%, while the reverse order costs over 14 percentage points. Memorability test: position raises the odds of use but does not guarantee it, so re-inject load-bearing facts near their point of use rather than trusting end-placement — and the position penalty is fill-dependent, not a fixed law.
      [diagram] mermaid (agent-authored):
        ```mermaid
        flowchart TD
          w[Window slots] --> b[Beginning: standing policy]
          w --> m[Middle: supporting material]
          w --> e[End: current task]
        ```
      - **Paper details — *Found in the Middle: Calibrating Positional Attention Bias Improves Long Context Utilization*** · kind: sidecar · [cited README.md:183]
        - (checklist: empty)
## Datasets, tasks, and models  [src paper-details/found-in-the-middle.md:7]
          - **Tasks:** both are multi-document question answering (QA): given a question, K documents in the prompt, exactly one (the "gold" document) contains the answer, the other K−1 are distractors. Evaluation is whether the model's answer appears in its output, at K ∈ {10, 20} documents.
          - **Datasets** (Appendix A, p. 13):
          - **[NaturalQuestions](https://ai.google.com/research/NaturalQuestions)** — 2,655-query subset (Liu et al., 2023), real Wikipedia paragraphs, Contriever-retrieved distractors.
          - **[SynthWiki](https://github.com/adamlerer/synthwiki)** (Peysakhovich & Lerer, 2023) — 990 synthetic QA entries; GPT-4-generated Wikipedia paragraphs about *fictional* people, to remove pretraining contamination.
          - **Models** (Appendix B, p. 13), both open-weight on Hugging Face, both 7B, 32 layers × 32 heads:
          - **[Vicuna-7b-v1.5-16k](https://huggingface.co/lmsys/vicuna-7b-v1.5-16k)** — LMSYS, 16k context
          - **[Tulu-2-7B](https://huggingface.co/allenai/tulu-2-7b)** — Allen Institute for AI, 8k context
          - **The problem this paper attacks (Liu et al. 2023):** *"LLMs struggle to locate relevant documents when they are placed in the middle of their input prompts… They call this the **lost-in-the-middle** phenomenon."*
          - **The paper's hypothesis (p. 2):** the loss is not an inability to *see* the middle, it is a **positional attention bias** that out-shouts relevance. The model does attend to relevant mid-context content "but are eventually distracted by leading/ending contexts." The fix follows: **calibrate attention** so it is weighted by relevance instead of position — *"found-in-the-middle… disentangles the effect of U-shape attention bias and allows models to attend to relevant context regardless [of] their positions."*
          - ![Figure 1 — four panels: (a) the lost-in-the-middle U-shaped accuracy, (b) the matching U-shaped attention, (c) the gold document attended but overwhelmed in the middle, (d) calibration surfacing it](fig1-four-panel-concept.png)
          - *Figure 1 (p. 1) — the paper's whole argument in one picture.* **(a)** the behavioral fact from Liu: accuracy is U-shaped in the gold document's position. **(b)** the proposed cause: attention is U-shaped in position *regardless of content*. **(c)** the crux — the model *does* attend to the gold document in the middle (orange circle), but the ends still dominate. **(d)** the paper's fix: calibrate, i.e. subtract the positional baseline, so the gold document surfaces as a peak wherever it sits.
          - Page numbers below refer to the arXiv PDF (14 pages; references begin on p. 10).
          narrative (compacted):
            - [prose] Tasks: multi-document QA - one question, K documents, one gold document with the answer and K-1 distractors; scored on answer appearance, at K in {10, 20}.
            - [prose] Datasets (Appendix A, p. 13):
            - [bullet] NaturalQuestions - a 2,655-query subset (Liu et al., 2023), real Wikipedia paragraphs, Contriever-retrieved distractors.
            - [bullet] SynthWiki (Peysakhovich & Lerer, 2023) - 990 synthetic entries; GPT-4-written paragraphs about fictional people, removing pretraining contamination.
            - [prose] Models (Appendix B, p. 13): both open-weight on Hugging Face, both 7B with 32 layers x 32 heads.
            - [bullet] Vicuna-7b-v1.5-16k - LMSYS, 16k context.
            - [bullet] Tulu-2-7B - Allen Institute for AI, 8k context.
            - [prose] The problem attacked (Liu et al. 2023): models struggle to locate relevant documents placed in the middle of the prompt - the lost-in-the-middle phenomenon.
            - [prose] Hypothesis (p. 2): not blindness to the middle but positional bias out-shouting relevance; the model attends mid-context yet the ends distract it. So calibrate attention by relevance, not position.
            - [prose] Figure 1's four panels: the lost-in-the-middle U-shaped accuracy; the matching U-shaped attention; the gold document attended but overwhelmed in the middle; calibration surfacing it.
            - [prose] Figure 1 (p. 1): accuracy U-shaped by gold position; attention U-shaped regardless of content; the middle gold attended (orange circle) but ends dominating; calibration surfacing it anywhere.
            - [prose] Citations below use the arXiv PDF's page numbers (14 pages, references from p. 10).
          prompt: Set up the study: what is the task shape and how is an answer scored, which datasets and models are used, and what exactly is the paper's hypothesis about why mid-context documents get missed?
          reveal: Task: multi-document question answering — one question, K documents in the prompt, exactly one gold document containing the answer and K−1 distractors; scored on whether the model's answer appears anywhere in its output, at K ∈ {10, 20}. Datasets: NaturalQuestions, a 2,655-query subset from Liu et al. with real Wikipedia paragraphs and Contriever-retrieved distractors; and SynthWiki (Peysakhovich & Lerer), 990 synthetic entries of GPT-4-written paragraphs about fictional people, which removes pretraining contamination. Models: two open-weight 7B transformers on Hugging Face, both 32 layers × 32 heads — Vicuna-7b-v1.5-16k with 16k context, and Tulu-2-7B with 8k context. Problem inherited from Liu et al. 2023: models struggle to locate relevant documents placed in the middle of the prompt — the lost-in-the-middle phenomenon. Hypothesis: the loss is not an inability to see the middle. The model does attend to relevant mid-context content, but is eventually distracted by the leading and ending contexts; a positional attention bias out-shouts relevance. The fix therefore is not reordering documents but calibrating attention so it is weighted by relevance instead of position, letting the model attend to relevant context regardless of where it sits. Figure 1 carries the argument in four panels: U-shaped accuracy, matching U-shaped attention, a mid-sequence gold document attended but overwhelmed, and calibration surfacing it. Cited pages follow the 14-page arXiv PDF.
## The notation: `x_prompt`, `x_k^doc`, `x_{k,i}^doc`  [src paper-details/found-in-the-middle.md:31]
          - The paper defines this **twice, and the two definitions disagree**.
          - **Page 3 (§2 setup):** the query is repeated before and after the documents.
          - $$x^{prompt} = [x_q,\ x^{doc}_1,\ \dots,\ x^{doc}_k,\ x_q]$$
          - Footnote 1 on the same page explains why: *"We repeat the question before and after the documents so that the model can better attend to relevant contexts (Liu et al., 2023; Xu et al., 2023b)."*
          - **Page 4 (§2.1, "More formally"):** the query has vanished.
          - $$x^{prompt} = [x^{doc}_1,\ \dots,\ x^{doc}_K]$$
          - **Note the inconsistency.** The formalization silently drops the query that page 3 says is present twice, and the index case changes (`k` → `K`). Anyone reproducing this must decide which construction they mean — it changes what "position" even refers to.
          narrative (compacted):
            - [prose] The paper defines this twice, and the two definitions disagree.
            - [prose] Page 3 (section 2 setup): the query is repeated before and after the documents.
            - [prose] Formula: prompt = [query, documents 1..k, query] - the query bracketing the documents.
            - [prose] Footnote 1 explains why: repeating the question before and after the documents helps the model attend to relevant contexts (Liu et al., 2023; Xu et al., 2023b).
            - [prose] Page 4 (section 2.1, 'More formally'): the query has vanished.
            - [prose] Formula: prompt = [documents 1..K] - documents only, no query.
            - [prose] Note the inconsistency: the formalization silently drops the twice-present query and shifts the index k to K. Reproducers must choose a construction - it changes what position means.
          prompt: The paper defines the prompt twice and the two definitions disagree. State both constructions, explain why the query appears twice in the first, and say why the discrepancy matters to anyone reproducing the method.
          reveal: Page 3 (§2 setup): the prompt is the query, then documents 1..k, then the query again — the query bracketing the documents. Footnote 1 gives the reason: repeating the question before and after the documents helps the model attend to relevant contexts (following Liu et al. 2023 and Xu et al. 2023b). Page 4 (§2.1, 'More formally'): the prompt is documents 1..K only — the query has vanished, and the index shifts from k to K. The inconsistency is real and unremarked: the formalization silently drops a query that page 3 says is present twice. It matters because position is the variable under study — the entire method is attention as a function of position — so a construction that adds two query segments at the ends changes what position refers to, which tokens the U-shape is measured across, and where each document begins and ends. A reproducer must choose one construction and state which, because the choice is baked into every downstream positional measurement.
### The containment hierarchy  [src paper-details/found-in-the-middle.md:47]
            - [table 6×3] (line 49)
              | Symbol | What it is | Defined |
              |---|---|---|
              | `x_prompt` | the entire input prompt — the ordered list of all K documents (plus, per p. 3, the query at both ends) | p. 3, p. 4 |
              | `x_k^doc` | the k-th document, i.e. `{x_{k,i}^doc}_{i=1}^{N_k}` — a sequence of `N_k` tokens | p. 4 |
              | `x_{k,i}^doc` | token `i` of document **at position `k`** — the atomic unit the attention weight is measured on | p. 4 |
              | `N_k` | number of tokens in document `k` | p. 4 |
              | `K` | number of documents | p. 4 |
            - So: `x_prompt` ⊃ `x_k^doc` ⊃ `x_{k,i}^doc`. The averaging in `Attn(x_prompt, k)` runs over exactly the `N_k` tokens that make up document `k`.
            - **Experimental setting (p. 3):** Vicuna-7b-v1.5-16k, **K = 20** documents, gold document at position **10** (the middle).
            narrative (compacted):
              - [table] Symbol What it is Defined
              - [table] `x_prompt` the entire input prompt — the ordered list of all K documents (plus, per p. 3, the query at both ends) p. 3, p. 4
              - [table] `x_k^doc` the k-th document, i.e. `{x_{k,i}^doc}_{i=1}^{N_k}` — a sequence of `N_k` tokens p. 4
              - [table] `x_{k,i}^doc` token `i` of document **at position `k`** — the atomic unit the attention weight is measured on p. 4
              - [table] `N_k` number of tokens in document `k` p. 4
              - [table] `K` number of documents p. 4
              - [prose] Containment: prompt contains document k, which contains its tokens, and `Attn(x_prompt, k)` averages over exactly those N_k tokens.
              - [prose] Experimental setting (p. 3): Vicuna-7b-v1.5-16k, K = 20 documents, gold document at position 10, the middle.
            prompt: Give the containment chain from the prompt down to the atomic unit the attention weight is measured on, and say exactly which set the averaging in Attn(x_prompt, k) runs over.
            reveal: The chain is x_prompt ⊃ x_k^doc ⊃ x_{k,i}^doc. x_prompt is the entire input prompt — the ordered list of all K documents, plus, per p. 3, the query at both ends. x_k^doc is the k-th document, the sequence {x_{k,i}^doc} for i = 1..N_k, so a sequence of N_k tokens. x_{k,i}^doc is token i of the document at position k — the atomic unit the attention weight is measured on; note the indices do different jobs, since k is the document's place in the prompt and i is the token's index inside that document. N_k is the number of tokens in document k, and K is the number of documents. The averaging in Attn(x_prompt, k) runs over exactly the N_k tokens that make up document k: token-level weights are averaged within that document, not across the whole prompt. Experimental setting: Vicuna-7b-v1.5-16k, K = 20 documents, with the gold document at position 10 — the middle, which is the position the phenomenon is about.
            [diagram] mermaid (agent-authored):
              ```mermaid
              flowchart TD
                p[Full prompt] --> d[Document k]
                d --> t[Token i]
              ```
## What the paper actually does: attention calibration  [src paper-details/found-in-the-middle.md:64]
          - The U-shape itself has no algorithm. The paper's contribution is the **calibration method**, in **§3.1 "Two main factors in model attention", page 5, Equation (1)**:
          - $$\text{Attn}(x^{prompt}, k) = f\big(\text{rel}(x_k^{doc}),\ \text{bias}(k)\big)$$
          - *(Hsieh's Equation (1). The number collides with Vaswani's Equation (1) quoted further down — two papers, two numbering schemes.)*
          - "where `rel(·)` measures the relevance of an input document, `bias(·)` characterizes the positional attention bias, and `f(·)` is some unknown monotonically increasing function w.r.t. both."
          narrative (compacted):
            - [prose] The U-shape has no algorithm; the contribution is the calibration method in section 3.1, page 5, Equation (1).
            - [prose] Formula: attention over prompt and document k is f(relevance of document k, positional bias k).
            - [prose] This is Hsieh's Equation (1); the number collides with Vaswani's Equation (1) quoted further down, two papers with two numbering schemes.
            - [prose] The terms: rel(.) measures a document's relevance, bias(.) characterizes positional attention bias, and f(.) is some unknown function monotonically increasing in both.
          prompt: Write the paper's Eq. (1) decomposition, say which of its parts are unobservable and what is assumed about the function, and distinguish the paper's own contribution from the U-shape finding it rests on.
          reveal: Eq. (1): Attn(x_prompt, k) = f(rel(x_k^doc), bias(k)) — attention on document k is some function of that document's relevance and a positional bias term. The terms: rel(·) measures a document's relevance, bias(·) characterizes the positional attention bias, and f(·) is some unknown function monotonically increasing in both arguments. What is not observable: f itself, and with it rel and bias — the paper does not observe f directly, which is why it tests implications of monotonicity rather than the function. The contribution: the U-shape is a finding the paper inherits (Liu et al.); the paper's own contribution is the calibration method in §3.1, p. 5, Equation (1) — this decomposition and the procedure built on it. Carry one numbering trap: this is Hsieh's Equation (1), and the number collides with Vaswani's Equation (1) — scaled dot-product attention — quoted later in the module. Two papers, two numbering schemes.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart LR
              r[Document relevance] --> f[Unknown monotone f]
              b[Positional bias] --> f
              f --> a[Attention]
            ```
### What monotonicity is claimed to imply — Conditions 1 & 2  [src paper-details/found-in-the-middle.md:74]
            - The paper does not observe `f` directly. It tests the two implications that monotonicity in each argument forces (p. 5):
            - **Condition 1 (antecedent: relevance fixed, consequent: position varies):** for any two documents `x_doc1`, `x_doc2`, if `Attn(x_doc1, k) > Attn(x_doc1, l)`, then it must also hold that `Attn(x_doc2, k) > Attn(x_doc2, l)`. In words: *the cross-position ordering of attention is the same for every document*, i.e. position `k` beats position `l` regardless of which document sits there.
            - **Condition 2 (position fixed, relevance varies):** if `Attn(x_doc1, k) > Attn(x_doc2, k)`, then `Attn(x_doc1, l) > Attn(x_doc2, l)`. In words: *the cross-document ordering is the same at every position*, i.e. a more-relevant document outranks a less-relevant one regardless of where they sit.
            narrative (compacted):
              - [prose] Because f is not observed directly, the paper tests the two implications that monotonicity in each argument forces (p. 5).
              - [bullet] Condition 1 (relevance fixed, position varies): the cross-position ordering of attention is the same for every document - position k beats l regardless of occupant.
              - [bullet] Condition 2 (position fixed, relevance varies): the cross-document ordering holds at every position, so a more relevant document outranks a less relevant one wherever they sit.
            prompt: Because f cannot be observed, the paper tests what monotonicity in each argument forces. State both conditions with antecedent and consequent, and say which quantity is held fixed in each.
            reveal: Condition 1 — relevance fixed, position varies. For any two documents x_doc1 and x_doc2: if Attn(x_doc1, k) > Attn(x_doc1, l), then it must also hold that Attn(x_doc2, k) > Attn(x_doc2, l). In words: the cross-position ordering of attention is the same for every document — position k beats position l regardless of which document occupies it. Condition 2 — position fixed, relevance varies. If Attn(x_doc1, k) > Attn(x_doc2, k), then Attn(x_doc1, l) > Attn(x_doc2, l). In words: the cross-document ordering is the same at every position — a more relevant document outranks a less relevant one wherever the two sit. The symmetry is the point: Condition 1 fixes the occupant and varies the slot, Condition 2 fixes the slot and varies the occupant, so each isolates one argument of f and makes a failure attributable to that argument. Both are consequences forced by monotonicity, not monotonicity itself.
            [diagram] mermaid (agent-authored):
              ```mermaid
              flowchart TD
                m[Monotonicity] --> c1[Condition 1: position ordering]
                m --> c2[Condition 2: relevance ordering]
              ```
### What a "violation" is  [src paper-details/found-in-the-middle.md:81]
            - A pair **violates** a condition when the *antecedent* holds but the *consequent* fails. Concretely for Condition 1: document 1 gets more attention at position `k` than at `l`, yet document 2 does **not** — it reverses or ties. That breaks "attention = relevance + a position-only bias", because a position effect should apply identically to every document.
            - **What is violated is the separability premise** — that `Attn(x_doc, k)` splits into a term depending only on the document plus a term depending only on the position.
            narrative (compacted):
              - [prose] Violation: antecedent true, consequent false. In Condition 1, one document draws more attention at k than l while the other ties or reverses - impossible for a position-only bias.
              - [prose] What is violated is the separability premise: attention splitting into a document-only term plus a position-only term.
            prompt: Define a violation formally, give the concrete Condition-1 shape of one, and name the premise that a violation actually falsifies.
            reveal: Formally, a pair violates a condition when the antecedent holds and the consequent fails. Concretely for Condition 1: document 1 draws more attention at position k than at position l, yet document 2 does not follow — it ties or reverses. That is impossible under a position-only bias, because a purely positional effect should apply identically to every document. What is falsified is not f's monotonicity directly but the separability premise: that Attn(x_doc, k) splits into a term depending only on the document plus a term depending only on the position. A violation shows attention cannot be decomposed that way — which is exactly the assumption the dummy-subtraction calibration is built on, so the frequency of violations is a direct measure of how much the method's premise is strained.
### How weak the support is — the percentages  [src paper-details/found-in-the-middle.md:87]
            - Validated on 100 randomly sampled NaturalQuestions examples, K = 20 (p. 5, Table 2):
            - **Condition 1: 83% valid pairs → 17% violate**
            - **Condition 2: 72% valid pairs → 28% violate**
            - These are weak for three reasons: they test a *consequence* of monotonicity, not monotonicity itself; they are far from 100% (a genuinely monotone `f` should satisfy all pairs); and they only confirm rank ordering, which cannot single out the additive form the method needs.
            narrative (compacted):
              - [prose] Validated on 100 randomly sampled NaturalQuestions examples at K = 20 (p. 5, Table 2).
              - [bullet] Condition 1: 83% of pairs valid, so 17% violate.
              - [bullet] Condition 2: 72% valid, so 28% violate.
              - [prose] Weak three ways: it tests a consequence, not monotonicity; falls far short of the 100% a monotone f should reach; and rank ordering cannot isolate the needed additive form.
            prompt: Report the validation setup and both validity percentages, then separate the distinct reasons this evidence is weak support for the monotonicity claim.
            reveal: Setup: 100 randomly sampled NaturalQuestions examples at K = 20 (p. 5, Table 2). Condition 1: 83% of pairs valid, so 17% violate. Condition 2: 72% valid, so 28% violate. Three separate weaknesses, not one. First, what is tested is a consequence of monotonicity, not monotonicity itself — passing does not establish the premise. Second, the rates fall far short of 100%, and a genuinely monotone f should satisfy every pair, so the numbers read as evidence against the model as stated rather than merely noisy support for it. Third, all that is confirmed is rank ordering, and rank ordering cannot single out the additive form the method needs: calibration requires bias(k) to cancel exactly, a far stronger claim than one ordering.
### The additive form — taken for convenience, not derived  [src paper-details/found-in-the-middle.md:96]
            - Nothing in Eq. (1) forces additivity; monotonicity admits infinitely many forms. Additivity is chosen for **one reason**: it is the simplest form under which `bias(k)` cancels exactly when a dummy document is subtracted (Eqs. 3–4 below). The paper's "Occam's razor" (p. 5) is a label for "simplest thing that works", not a derivation.
            - $$\text{Attn}(x^{doc}, k) = \text{rel}(x^{doc}) + \text{bias}(k) + \epsilon$$
            - Equation (4) is the subtraction that isolates relevance: `rel(x_doc) = Attn(x_doc, k) − Attn(x_dum, k) + rel(x_dum)`. Note `bias(k)` is **cancelled, not estimated** — it appears in both terms and disappears in the subtraction.
            - if the dummy doc is kept the same for all docs across all types of experiments, the results become comparable
            - here the `Attn(x_doc, k)` is the self-attention weight of that document when positioned at position `k`.
            - [code: python] (line 106)
              ```python
              def calibrated_attention(Attn, x_doc, x_dum, k):
                  # Eq. 3 - Eq. 2 = Eq. 4: bias(k) cancels; rel up to an additive constant
                  return Attn(x_doc, k) - Attn(x_dum, k)
              ```
            - Validation is Spearman rank correlation between calibrated scores and ground-truth relevance (linear ≈ 0.76, log-linear ≈ 0.75).
            narrative (compacted):
              - [prose] Eq. (1) permits infinitely many monotone forms — additivity isn't forced. It is picked solely because dummy subtraction cancels `bias(k)` exactly (Eqs. 3–4); "Occam's razor" signals simplicity, not derivation.
              - [prose] Eq. (3): document attention decomposes additively into relevance plus a positional term `bias(k)`, plus noise ε.
              - [prose] Eq. (4) isolates relevance by subtracting dummy-document attention at the same position: `bias(k)` is cancelled rather than estimated, appearing in both terms.
              - [bullet] A dummy document held fixed across all documents and experiment types keeps results comparable.
              - [bullet] Here `Attn(x_doc, k)` is that document's self-attention weight when positioned at position `k`.
              - [code] def calibrated_attention(Attn, x_doc, x_dum, k):
    # Eq. 3 - Eq. 2 = Eq. 4: bias(k) cancels; rel up to an additive constant
    return Attn(x_doc, k) - Attn(x_dum, k)
              - [prose] Validation uses Spearman rank correlation between calibrated scores and ground-truth relevance: ≈0.76 linear, ≈0.75 log-linear.
            prompt: What forces the additive decomposition, and why is it described as chosen rather than derived? Then say what the dummy subtraction does to bias(k) and what the reported correlation does and does not establish.
            reveal: Not derived. Nothing in Eq. (1) forces additivity — monotonicity admits infinitely many forms. It is picked for one reason: it is the simplest form under which bias(k) cancels exactly when a dummy document is subtracted (Eqs. 3–4). The paper's 'Occam's razor' is a label for 'the simplest thing that works', not a derivation. Eq. (3): Attn(x_doc, k) = rel(x_doc) + bias(k) + ε. Eq. (4) isolates relevance: rel(x_doc) = Attn(x_doc, k) − Attn(x_dum, k) + rel(x_dum). The mechanism to notice: bias(k) is cancelled, not estimated. It appears in both terms because both are read at the same position k, so it disappears in the subtraction and relevance comes out up to an additive constant. That requires the dummy document to stay fixed across all documents and all experiment types so results remain comparable; Attn(x_doc, k) here is that document's self-attention weight when positioned at k. In code it is just the two-term difference. Validation is a Spearman rank correlation between calibrated scores and ground-truth relevance, ≈0.76 linear and ≈0.75 log-linear — rank agreement with ground truth, which does not certify the additive form itself.
## Vanilla attention  [src paper-details/found-in-the-middle.md:114]
          - ![Figure 4 — average attention weight by document position, original vs. shuffled order: a U-shape peaking at both ends](fig4-u-shaped-attention.png)
          - *Figure 4 (p. 3): the U-shape. Documents at positions 1 and 20 get the most attention; the middle gets the least. The orange line is the **shuffled** control — the U survives, so the bias is positional, not content-driven. Note the spike at position 10 in the blue line only: that is the gold document when placed in the middle.*
          - What the paper calls **vanilla attention** (p. 6: "Using uncalibrated attention `Attn(x_prompt,k)` to rank the documents") is the raw self-attention weight — the number that feeds the calibration above. The paper never writes its formula, and never states "vanilla attention = Vaswani's scaled dot-product attention", but the models are standard transformers, so that is what the number *is*.
          - [details] What Hsieh says it is — page 4, §2.1
          - [details] The computation it inherits — Attention Is All You Need (Vaswani et al., 2017)
          - [details] Reading the two together — why it's the last row
          - [code: python] (line 151)
            ```python
            import torch, math
            
            def attn_weight_row(Q, K, d_k, mask=None):
                S = (Q @ K.transpose(-2, -1)) / math.sqrt(d_k)
                if mask is not None:
                    S = S.masked_fill(mask, float('-inf'))
                return torch.softmax(S, dim=-1)   # A[q, i] = weight on key i
            ```
          - [details] Caveats the paper does not resolve
          - [details] Why they trust attention weights at all
          narrative (compacted):
            - [prose] Figure 4 image: average attention weight per document position, original versus shuffled order — a U-shape peaking at both ends.
            - [prose] Figure 4 (p. 3): positions 1 and 20 attract most attention, the middle least. The shuffled control (orange) keeps the U, so the bias is positional, not content-driven; the blue-only position-10 spike is the gold document mid-sequence.
            - [prose] The paper's **vanilla attention** (p. 6) is the raw, uncalibrated self-attention weight `Attn(x_prompt,k)` used to rank documents, which feeds calibration above. Its formula is never written; standard transformers mean it is Vaswani's scaled dot-product attention.
            - [details] Hsieh's own definition — page 4, §2.1
            - [details] The inherited computation — Attention Is All You Need (Vaswani et al., 2017)
            - [details] Reading both together — why it's the last row
            - [code] import torch, math

def attn_weight_row(Q, K, d_k, mask=None):
    S = (Q @ K.transpose(-2, -1)) / math.sqrt(d_k)
    if mask is not None:
        S = S.masked_fill(mask, float('-inf'))
    return torch.softmax(S, dim=-1)   # A[q, i] = weight on key i
            - [details] Caveats the paper leaves unresolved
            - [details] Why attention weights are trusted at all
          prompt: What is 'vanilla attention' in this paper, what computation does the number actually come from, and why must the measurement be read off the last query row? What does the shuffled control in Figure 4 rule out?
          reveal: Vanilla attention is the raw, uncalibrated self-attention weight Attn(x_prompt, k) used to rank documents — the number that feeds the calibration step. The paper never writes its formula and never equates it with Vaswani's scaled dot-product attention, but the models are standard transformers, so that is what the number is: softmax(QKᵀ/√d_k) over keys, inside multi-head, causally masked decoder self-attention. Hsieh's own definition: average the attention weight allocated to a document's tokens when predicting the next token — averaged over all its tokens, all decoder layers, and all heads. The paper never defines the per-token weight itself, and says nothing about pre- versus post-softmax or which query position attends. Why the last row: the mask is causal, so only the final query position can attend to every preceding token; 'when predicting the next token' therefore pins the read to the last row of the attention matrix, and averaging all rows would be a different quantity. Figure 4's evidence: attention peaks at positions 1 and 20 and dips in the middle, and the shuffled-order control keeps the U — so the shape is positional, not content-driven. The single spike at position 10 in the unshuffled line is the gold document itself, sitting mid-sequence.
## How Recall@3 is computed  [src paper-details/found-in-the-middle.md:189]
          - For each of the K documents, compute a relevance score (Eq. 4):
          - $$\text{rel}(x^{doc}) \approx \text{Attn}(x^{doc}, k) - \text{Attn}(x^{dum}, k)$$
          - **Rank** the K documents by that score, descending.
          - **Recall@3** = fraction of queries where the gold document lands in the **top 3** of that ranked list.
          - The ranking key **is** the calibrated attention — the relevance score is the dummy-subtracted attention, so Recall@3 rides directly on calibrated attention.
          - [table 5×3] (line 199)
            | Method (Table 3) | Score used to rank | Recall@3 (K=10 / K=20) |
            |---|---|---|
            | Vanilla attention | raw `Attn(x_prompt, k)` | 0.3638 / 0.2052 |
            | Query generation | likelihood of generating the query from the doc | 0.6851 / 0.5815 |
            | Relevance generation | prompt "is this relevant?" | 0.5521 / 0.4012 |
            | **Calibrated attention** | `Attn(x_doc,k) − Attn(x_dum,k)` | **0.7427 / 0.6832** |
          - The paper's own words (p. 6): *"Eq. 4 allows us to leverage calibrated attention to estimate and rank the relevance of different documents."* So the relevance scores **are** the calibrated attention.
          narrative (compacted):
            - [bullet] Compute a relevance score for each of the K documents (Eq. 4):
            - [prose] Relevance approximated as document attention minus dummy-document attention at the same position.
            - [bullet] Sort the K documents by that score, highest first.
            - [bullet] **Recall@3** = the share of queries whose gold document falls in the **top 3** of that ordering.
            - [bullet] The ranking key **is** calibrated attention — relevance is dummy-subtracted attention, so Recall@3 rides directly on it.
            - [table] Method (Table 3) Score used to rank Recall@3 (K=10 / K=20)
            - [table] Vanilla attention raw `Attn(x_prompt, k)` 0.3638 / 0.2052
            - [table] Query generation likelihood of generating the query from the doc 0.6851 / 0.5815
            - [table] Relevance generation prompt "is this relevant?" 0.5521 / 0.4012
            - [table] **Calibrated attention** `Attn(x_doc,k) − Attn(x_dum,k)` **0.7427 / 0.6832**
            - [prose] The paper (p. 6) says Eq. 4 lets calibrated attention estimate and rank document relevance — so relevance scores **are** calibrated attention.
          prompt: State the score used to rank documents for Recall@3, how the metric turns that ranking into a number, and give the four compared methods' Recall@3 at K = 10 and K = 20.
          reveal: Score: the calibrated relevance of Eq. (4), rel(x_doc) ≈ Attn(x_doc, k) − Attn(x_dum, k) — document attention minus dummy-document attention at the same position. Procedure: compute that score for each of the K documents, sort them descending, then Recall@3 is the fraction of queries whose gold document lands in the top 3 of that ranked list. The ranking key is the calibrated attention itself — the relevance score is dummy-subtracted attention — so the metric rides directly on calibration rather than on a separate estimator. Table 3, Recall@3 at K = 10 / K = 20: vanilla attention, ranking on raw Attn(x_prompt, k), 0.3638 / 0.2052; query generation, ranking on the likelihood of generating the query from the document, 0.6851 / 0.5815; relevance generation, a prompt asking 'is this relevant?', 0.5521 / 0.4012; calibrated attention, Attn(x_doc, k) − Attn(x_dum, k), 0.7427 / 0.6832 — best of the four, and the one that degrades least as K grows. The paper's own reading is that Eq. (4) lets calibrated attention estimate and rank document relevance, so the relevance scores are the calibrated attention.
## The meat: rescaling the model's token attention  [src paper-details/found-in-the-middle.md:210]
          - (checklist: empty)
### Why ranking is not enough  [src paper-details/found-in-the-middle.md:212]
            - Locating the relevant document (Table 3) does not fix *utilization*. The paper's Introduction is explicit that re-ranking *"does not fundamentally improve LLMs' ability to utilize and capture relevant information."* Even after you move the relevant doc to the front, the model's **attention still favors the terminals positionally** — the bias lives in the model's weights, not in the document order.
            narrative (compacted):
              - [prose] Table 3's localization doesn't fix *utilization*: the Introduction states re-ranking *"does not fundamentally improve LLMs' ability to utilize and capture relevant information."* Moving the relevant doc first leaves attention still favoring the terminals — the bias lives in the model's weights, not the document order.
            prompt: Calibrated attention ranks the gold document well. Why does the paper still say localization is not the fix — what stays broken, and where does the bias live?
            reveal: Finding the relevant document is not the same as getting the model to use it. The paper's Introduction states explicitly that re-ranking does not fundamentally improve LLMs' ability to utilize and capture relevant information. Even after the relevant document is moved to the front, the model's attention still favors the terminal positions — because the bias lives in the model's weights, not in the document order. So a ranking or re-ordering fix leaves utilization untouched: you can know which document matters and still watch the model allocate its attention elsewhere. That gap — good localization, unchanged utilization — is what motivates the paper's second half, intervening inside the model's attention instead of rearranging its input.
### What the paper recommends instead — §4.1, Equations 5–6 (p. 6)  [src paper-details/found-in-the-middle.md:216]
            - *"To allow the model to attend to contexts **without being dictated by positional bias**, we propose to **intervene the model's attention**… instead of allocating `rel(x_k^doc) + bias(k)` attention to the k-th document, our ideal model attention would reflect **only the relevance** `rel(x_k^doc)`."*
            - Per token within each document (token `i` in document `k`):
            - $$\text{attn}_{calibrated}(x_{k,i}^{doc}) = \frac{\alpha_k}{\text{Attn}_{original}(x_k^{doc})} \cdot \text{attn}_{original}(x_{k,i}^{doc}) \cdot C$$
            - $\alpha_k = \text{Softmax}(\text{rel}(x_k^{doc}),\ t)$ — temperature-scaled softmax over document relevances
            - $C$ — a normalizer so total attention is unchanged
            - Net effect (Eq. 6):
            - $$\text{Attn}_{calibrated}(x_k^{doc}) \propto \text{Softmax}(\text{rel}(x_k^{doc}),\ t)$$
            narrative (compacted):
              - [prose] The paper proposes intervening in the model's attention so context is attended **without positional bias dictating it**: instead of allocating `rel(x_k^doc) + bias(k)`, ideal attention should reflect **only** `rel(x_k^doc)`.
              - [prose] Applied per token `i` within each document `k`:
              - [prose] Eq. (5): calibrated attention for a token = (α_k / original document attention mass) × original token attention × normalizer `C`.
              - [bullet] `α_k` — a temperature-scaled softmax over the documents' relevance scores.
              - [bullet] `C` — a normalizer keeping total attention unchanged.
              - [prose] Net effect (Eq. 6):
              - [prose] Eq. (6): calibrated document attention is proportional to the temperature-scaled softmax of its relevance.
            prompt: Instead of allocating rel(x_k^doc) + bias(k) to a document, what does the paper's intervention allocate, and what is each factor in Eq. (5) doing?
            reveal: The proposal is to intervene in the model's attention so context is attended without positional bias dictating it: instead of allocating rel(x_k^doc) + bias(k) to the k-th document, ideal attention should reflect only rel(x_k^doc). Eq. (5), applied per token i within each document k: calibrated token attention = (α_k / Attn_original(x_k^doc)) × attn_original(x_{k,i}^doc) × C. The factors: α_k = Softmax(rel(x_k^doc), t), a temperature-scaled softmax over the documents' relevance scores — the share of attention that relevance says document k deserves. Attn_original(x_k^doc), the document's original attention mass, is the denominator that normalizes away how much attention the document currently receives. C is a normalizer keeping total attention unchanged. Eq. (6) states the net effect: calibrated document attention is proportional to the temperature-scaled softmax of that document's relevance. The structural point is that relevance now sets the allocation and position has dropped out of the formula entirely.
### What that equation actually means, operationally  [src paper-details/found-in-the-middle.md:231]
            - 1. **$\alpha_k$ is one scalar per document, computed once per query.** $\alpha_k = \text{softmax}(\text{rel}(x_k^{doc}), t)$ — the *same* value applies to every token `i` inside document `k`. It is the output of a softmax over all K documents' relevance scores, so $\alpha_k \in (0,1)$ and $\sum_k \alpha_k = 1$.
            - 2. **The denominator is the document's attention mass.** $\text{Attn}_{original}(x_k^{doc}) = \sum_{i} \text{attn}_{original}(x_{k,i}^{doc})$ — the sum of attention over all of document `k`'s tokens (the uppercase `Attn`). Dividing by it normalizes out how much attention the document *currently* gets, so the ratio $\alpha_k / \text{Attn}_{original}(x_k)$ is a pure re-weighting factor.
            - 3. **$C$ is mass preservation, not decoration.** After re-weighting every document, the attention matrix's rows must still sum to 1 for the next-token distribution to be valid. $C$ rescales the whole thing so total attention is unchanged. Without it, the softmax row breaks.
            - 4. **It happens inside the forward pass, per layer/head, at inference — and per query.** Attention is recomputed every generation step, so the intervention runs every step. Appendix B (p. 13): they apply it to the **last 16 of 32 decoder layers, all heads**. And because $\text{rel}(x_k)$ comes from Eq. 4 (calibrated attention against the *current* query), the rescaling is **query-dependent** — there is no static weight.
            - [details] Implementation sketch
            - [code: python] (line 244)
              ```python
              import torch
              import torch.nn.functional as F
              
              # One decoder layer, one head, at the generation step for query x^q.
              # prompt_tokens : [T]   token ids of the whole prompt, T = prompt length in tokens
              # doc_spans     : list of (start, end) spans for the K documents
              # x_dum_tokens  : [N_dum]   token ids of the FIXED dummy document
              
              def replace_span(tokens, span, replacement):
                  """Swap the token slice [s, e) with `replacement`, padded/truncated to the same length."""
                  s, e = span
                  length = e - s
                  rep = replacement[:length] + [0] * max(0, length - len(replacement))  # 0 = pad id
                  return torch.cat([tokens[:s], torch.tensor(rep), tokens[e:]])
              
              def attention_mass(attn, span):
                  """Attn(x_doc, k): total attention on a token span, summed over the last query row."""
                  s, e = span
                  return attn[-1, s:e].sum()          # last row = the position predicting the next token
              
              def calibrated_relevance(model, prompt_tokens, doc_spans, x_dum_tokens):
                  """Eq. 4, done faithfully: compare doc vs dummy AT THE SAME position k."""
                  rel = []
                  # pass A: the REAL prompt.
                  # attn_A : [T, T]  — T = |prompt_tokens| = query(doubled) + K documents
                  attn_A = model(prompt_tokens)["attention"]
              
                  for k, (s, e) in enumerate(doc_spans):
                      # pass B: swap doc k's tokens for the dummy, SAME span -> SAME position k.
                      # prompt_B has the SAME length as prompt_tokens, so attn_B is also [T, T].
                      prompt_B = replace_span(prompt_tokens, (s, e), x_dum_tokens)
                      attn_B = model(prompt_B)["attention"]             # [T, T]
              
                      a_doc = attention_mass(attn_A, (s, e))            # Attn(x_doc, k): scalar
                      a_dum = attention_mass(attn_B, (s, e))            # Attn(x_dum, k): scalar  <- same k
                      rel.append(a_doc - a_dum)                          # bias(k) cancels; scalar
              
                  return torch.stack(rel)                               # [K]; rel up to a constant
              
              def temp_scaled_softmax(rel, temp):
                  """alpha_k = softmax(rel / temp). temp -> 0: sharper (argmax); temp -> inf: uniform."""
                  return F.softmax(rel / temp, dim=-1)
              
              def rescale(model, prompt_tokens, doc_spans, x_dum_tokens, temp):
                  rel   = calibrated_relevance(model, prompt_tokens, doc_spans, x_dum_tokens)   # [K], Eq. 4
                  alpha = temp_scaled_softmax(rel, temp)                                        # [K], alpha_k
              
                  attn_A = model(prompt_tokens)["attention"]
                  attn_calibrated = attn_A.clone()
              
                  for k, (s, e) in enumerate(doc_spans):
                      Attn_k = attention_mass(attn_A, (s, e))
                      attn_calibrated[:, s:e] *= (alpha[k] / Attn_k)     # same scalar for every token i
              
                  # C: keep total attention mass unchanged (rows still sum to 1)
                  attn_calibrated *= (attn_A.sum() / attn_calibrated.sum())
                  return attn_calibrated
              ```
            - [details] Where does T come from? — a NaturalQuestions walkthrough
            - Run for each of the last 16 layers and all heads, at every generation step, with `rel` recomputed per query.
            narrative (compacted):
              - [prose] α_k is one scalar per document, computed once per query as a softmax over all K relevance scores — so α_k ∈ (0,1), Σα_k = 1, and every token inside document `k` shares it.
              - [prose] The denominator is the document's attention mass: the summed attention over all its tokens (uppercase `Attn`). Dividing by it removes how much attention the document currently gets, making α_k / mass a pure re-weighting factor.
              - [prose] `C` preserves mass rather than decorating: attention rows must still sum to 1 for a valid next-token distribution, so `C` rescales everything to keep total attention unchanged. Without it the softmax row breaks.
              - [prose] It runs inside the forward pass, per layer/head and per query, at every generation step. Appendix B (p. 13): the last 16 of 32 decoder layers, all heads. Relevances come from Eq. 4 against the *current* query, so no static weight exists.
              - [details] Code sketch of the implementation
              - [code] import torch
import torch.nn.functional as F

# One decoder layer, one head, at the generation step for query x^q.
# prompt_tokens : [T]   token ids of the whole prompt, T = prompt length in tokens
# doc_spans     : list of (start, end) spans for the K documents
# x_dum_tokens  : [N_dum]   token ids of the FIXED dummy document

def replace_span(tokens, span, replacement):
    """Swap the token slice [s, e) with `replacement`, padded/truncated to the same length."""
    s, e = span
    length = e - s
    rep = replacement[:length] + [0] * max(0, length - len(replacement))  # 0 = pad id
    return torch.cat([tokens[:s], torch.tensor(rep), tokens[e:]])

def attention_mass(attn, span):
    """Attn(x_doc, k): total attention on a token span, summed over the last query row."""
    s, e = span
    return attn[-1, s:e].sum()          # last row = the position predicting the next token

def calibrated_relevance(model, prompt_tokens, doc_spans, x_dum_tokens):
    """Eq. 4, done faithfully: compare doc vs dummy AT THE SAME position k."""
    rel = []
    # pass A: the REAL prompt.
    # attn_A : [T, T]  — T = |prompt_tokens| = query(doubled) + K documents
    attn_A = model(prompt_tokens)["attention"]

    for k, (s, e) in enumerate(doc_spans):
        # pass B: swap doc k's tokens for the dummy, SAME span -> SAME position k.
        # prompt_B has the SAME length as prompt_tokens, so attn_B is also [T, T].
        prompt_B = replace_span(prompt_tokens, (s, e), x_dum_tokens)
        attn_B = model(prompt_B)["attention"]             # [T, T]

        a_doc = attention_mass(attn_A, (s, e))            # Attn(x_doc, k): scalar
        a_dum = attention_mass(attn_B, (s, e))            # Attn(x_dum, k): scalar  <- same k
        rel.append(a_doc - a_dum)                          # bias(k) cancels; scalar

    return torch.stack(rel)                               # [K]; rel up to a constant

def temp_scaled_softmax(rel, temp):
    """alpha_k = softmax(rel / temp). temp -> 0: sharper (argmax); temp -> inf: uniform."""
    return F.softmax(rel / temp, dim=-1)

def rescale(model, prompt_tokens, doc_spans, x_dum_tokens, temp):
    rel   = calibrated_relevance(model, prompt_tokens, doc_spans, x_dum_tokens)   # [K], Eq. 4
    alpha = temp_scaled_softmax(rel, temp)                                        # [K], alpha_k

    attn_A = model(prompt_tokens)["attention"]
    attn_calibrated = attn_A.clone()

    for k, (s, e) in enumerate(doc_spans):
        Attn_k = attention_mass(attn_A, (s, e))
        attn_calibrated[:, s:e] *= (alpha[k] / Attn_k)     # same scalar for every token i

    # C: keep total attention mass unchanged (rows still sum to 1)
    attn_calibrated *= (attn_A.sum() / attn_calibrated.sum())
    return attn_calibrated
              - [details] Where does T come from? — a NaturalQuestions walkthrough
              - [bullet] Run over the last 16 layers and all heads, every generation step, recomputing `rel` per query.
            prompt: Operationally, what are α_k, the denominator, and C in Eq. (5)? Then say where and when the intervention runs, and why there is no static weight to precompute.
            reveal: α_k: one scalar per document, computed once per query as a softmax over all K documents' relevance scores, temperature-scaled. Being a softmax output, α_k ∈ (0,1), Σ_k α_k = 1, and every token inside document k shares it — the document is re-weighted as a unit, not token by token. Denominator: Attn_original(x_k^doc) equals the sum of attention over all of document k's tokens, the uppercase Attn, i.e. the document's attention mass. Dividing by it normalizes out how much attention the document currently gets, so α_k / mass is a pure re-weighting factor rather than a second helping of the existing bias. C: mass preservation, not decoration — after re-weighting, the attention matrix's rows must still sum to 1 for the next-token distribution to stay valid, so C rescales everything to keep total attention unchanged; without it the softmax row breaks. Where and when: inside the forward pass, per layer and per head, at inference, and per query — attention is recomputed at every generation step, so the intervention runs every step. Appendix B places it in the last 16 of 32 decoder layers, all heads. There is no static weight because rel(x_k) is measured by Eq. 4 against the current query, making the rescaling query-dependent.
### The impact — numbers  [src paper-details/found-in-the-middle.md:323]
            - ![Figure 5 — accuracy vs. gold-document position, vanilla vs. calibrated attention, across 4 model/dataset panels](fig5-calibrated-vs-vanilla.png)
            - *Figure 5 (p. 7): calibrated (orange) sits above vanilla (blue) in 22 of 24 cases. The dip in the middle is the lost-in-the-middle effect; calibration lifts exactly that dip — 6–15 points where the gold document is mid-sequence.*
            - **Fig. 5 (p. 7):** calibrated attention lies "almost entirely above standard vanilla attention (on **22 out of 24** cases)."
            - **Middle positions — the hard case:** "attention calibration provides **6–15 points** improvements."
            - **Overall:** "improvements over standard model generation by **up to 15 percentage point** on NaturalQuestion."
            narrative (compacted):
              - [prose] Figure 5 image: accuracy against gold-document position for vanilla versus calibrated attention, across four model/dataset panels.
              - [prose] Figure 5 (p. 7): calibrated (orange) exceeds vanilla (blue) in 22 of 24 cases. The mid-sequence dip is the lost-in-the-middle effect, and calibration lifts exactly that dip by 6–15 points where the gold document is mid-sequence.
              - [bullet] **Fig. 5 (p. 7):** calibrated attention sits "almost entirely above standard vanilla attention" in **22 of 24** cases.
              - [bullet] **Middle positions — the hard case:** calibration gives **6–15 points** of improvement.
              - [bullet] **Overall:** up to **15 percentage points** over standard model generation on NaturalQuestion.
            prompt: From the paper's Figure 5 result: in how many of the 24 model/dataset cases does calibrated attention beat vanilla, roughly how big is the gain where the gold document sits mid-sequence, and what is the largest overall improvement reported on NaturalQuestions? State what the shape of the gain tells you about what calibration actually fixes.
            reveal: Figure 5 (p. 7) plots accuracy against the gold document's position, vanilla attention (blue) vs calibrated (orange), across four model/dataset panels.

- Calibrated attention lies almost entirely above vanilla in **22 of 24** cases.
- The middle of the sequence is the hard case: calibration buys **6–15 points** exactly where the gold document is mid-sequence.
- Overall, improvements over standard model generation reach **up to 15 percentage points** on NaturalQuestions.

The shape matters more than the totals. Vanilla accuracy dips in the middle — the lost-in-the-middle effect — and calibration lifts precisely that dip. The gain is not spread evenly across positions; it is concentrated where positional bias had suppressed correct documents. That is the operational signature of the paper's causal claim: position was never the problem, distorted attention mass was, and correcting the mass restores the positions that were being ignored.

So the numbers support a positional diagnosis: the failure being repaired is mid-sequence under-attention, and the fix earns its 6–15 points there rather than everywhere.
## The science, compressed  [src paper-details/found-in-the-middle.md:335]
          - The causal claim is: **attention-mass allocation is the bottleneck, not document position.** Position only matters because it *distorts* attention mass (the U-shape). Fix the mass — rescale it ∝ relevance — and position stops mattering.
          - Two steps, mirroring the paper's two halves:
          - 1. **Estimate relevance without position** — subtract a fixed dummy document at the same position (Eq. 4), cancelling `bias(k)`.
          - 2. **Allocate attention by relevance without position** — rescale per-document attention to `softmax(relevance)` (Eq. 5).
          - **One honest caveat the paper carries:** attention "correlate[s] with models' generations, **although not necessarily causal**." Directly editing attention moves accuracy, which is strong intervention evidence — but "attention is the mechanism" is the best available account, not a settled proof.
          narrative (compacted):
            - [prose] The causal claim: **attention-mass allocation is the bottleneck, not document position.** Position matters only because it distorts attention mass (the U-shape); rescale mass ∝ relevance and position stops mattering.
            - [prose] Two steps, mirroring the paper's two halves:
            - [prose] 1. **Estimate relevance without position** — subtract a fixed dummy document at the same position (Eq. 4), cancelling `bias(k)`.
            - [prose] 2. **Allocate attention by relevance without position** — rescale per-document attention to `softmax(relevance)` (Eq. 5).
            - [prose] **One honest caveat the paper carries:** attention correlates with generations "although not necessarily causal." Editing attention directly moves accuracy — strong intervention evidence — yet "attention is the mechanism" is the best available account, not settled proof.
          prompt: State the causal claim in one sentence, then give the two-step recipe that implements it — what step 1 estimates and how the dummy document delivers it, and what step 2 allocates. What caveat does the paper attach to the causal reading?
          reveal: **The claim:** attention-mass allocation is the bottleneck, not document position. Position matters only because it distorts attention mass into the U-shape; fix the mass — rescale it proportional to relevance — and position stops mattering.

**Two steps, mirroring the paper's two halves:**

1. **Estimate relevance without position.** Subtract a fixed dummy document placed at the same position (Eq. 4). The dummy absorbs the positional bias term `bias(k)`, so the subtraction cancels position out of the estimate and leaves relevance.
2. **Allocate attention by relevance without position.** Rescale per-document attention to `softmax(relevance)` (Eq. 5) — the same relevance weights, now determining how much mass each document actually receives rather than where it happens to sit.

Step 1 is estimation, step 2 is allocation; the dummy-document subtraction is what makes the allocation position-free.

**The caveat the paper carries:** attention "correlate[s] with models' generations, although not necessarily causal." Directly editing attention and watching accuracy move is strong intervention evidence, but "attention is the mechanism" is the best available account, not a settled proof.

That is the whole compression: position is a symptom, relevance-scaled attention mass is the target, and causality is inferred rather than demonstrated.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart LR
              a[Subtract dummy document] --> b[Relevance without position]
              b --> c[Rescale to softmax relevance]
              c --> d[Position stops mattering]
            ```
### 2. Formatting is information  [src README.md:195]
      - The model is not a human reader; it is a *pattern-matching* reader. Structure that would be noise to a person is signal to it.[unsupported](#unsupported) Prefer:
      - [code: text] (line 199)
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
      - over a wall of prose where the task, the evidence, and the constraints are all one paragraph. Deterministic structure makes the model's job of *finding* the right thing cheaper[lee-format-tax](#lee-format-tax) — which is, in effect, more attention budget for the actual reasoning.
      - **ADK at a glance:** the framework's `InvocationContext` (the object threaded through every run) is how your code and tools read the current session state;[adk-context](#adk-context) `static_instruction` is the knob for the stable instruction prefix;[adk-context-caching](#adk-context-caching) and the `Runner`/`run_async` loop is where the window gets assembled each turn.[adk-context](#adk-context), [unsupported](#unsupported) We'll go deep on the runtime in M16 — for now the point is architectural: *something* assembles the window every turn, and that something is a decision surface, not a black box.
      narrative (compacted):
        - [prose] The model is a *pattern-matching* reader, not a human one: structure that is noise to a person is signal to it. Prefer:
        - [code] ## Retrieved evidence (cite these)
[1] <chunk>
[2] <chunk>

## Task
<the actual question>

## Constraints
- <hard limits>

## Format
<required output shape>
        - [prose] …over a single wall of prose holding task, evidence and constraints together. Deterministic structure makes *finding* the right thing cheaper, which in effect buys more attention budget for reasoning.
        - [prose] **ADK at a glance:** `InvocationContext` exposes session state to your code and tools; `static_instruction` holds the stable instruction prefix; the `Runner`/`run_async` loop assembles the window every turn. M16 goes deep on the runtime — architecturally, that assembler is a decision surface, not a black box.
      prompt: Why does a structural layout — headed blocks for retrieved evidence, task, constraints, format — count as an attention decision rather than mere cosmetics, and how does that argument connect formatting to the position/stability discipline of the section above it?
      reveal: The premise: the model is not a human reader but a *pattern-matching* reader. Structure that would be noise to a person is signal to it.

So the discipline is to prefer named, deterministic blocks:

```
## Retrieved evidence (cite these)
[1] <chunk>
## Task
<the actual question>
## Constraints
- <hard limits>
## Format
<required output shape>
```

over a wall of prose in which task, evidence and constraints are one paragraph.

The mechanism is budget, not aesthetics. Deterministic structure makes the model's job of *finding* the right thing cheaper; that saving is, in effect, more attention budget for the actual reasoning. Formatting spends (or saves) the same scarce resource that position does, which is why the module lists it as its own budget line rather than a style preference.

How it connects to the position section: both are *placement/ordering* decisions made by the harness, and both interact with caching. The same stable-prefix discipline applies — anything you want cacheable has to keep the same bytes, so a stable headed block is simultaneously easier for the model to parse and safer to reuse. Related ADK surface: `InvocationContext` is how code and tools read session state, `static_instruction` is the knob for the stable instruction prefix, and the `Runner`/`run_async` loop is where the window is assembled each turn. The architectural point is that *something* assembles the window every turn, and that something is a decision surface, not a black box.
## Prompt caching — the practical playbook  [src README.md:220]
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
    - [details] Example A — OpenAI's default: one fused prefix (implicit breakpoint)
    - [code: typescript] (line 251)
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
    - [code: text] (line 324)
      ```text
      1 cold write: input=141 cached=0 write=141
      2 append turn: input=152 cached=141 write=152
      3 append turn: input=162 cached=152 write=162
      4 tool description edited: input=175 cached=0 write=175
      ```
    - [details] Example B — explicit breakpoints: the closest OpenAI gets to Anthropic's ordering
    - [code: typescript] (line 336)
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
    - [code: text] (line 418)
      ```text
      1 cold write: input=106 cached=0 write=186
      2 same prefix, new question: input=107 cached=99 write=0
      3 tier 2 (rubric) edited: input=107 cached=87 write=100
      4 tier 1 (policy) edited: input=107 cached=0 write=188
      5 one tool description edited: input=108 cached=0 write=190
      ```
    - **Mastra — binary, no levels.** Prompt caching is a provider pass-through (`providerOptions`); the only documented rule is append-vs-modify — *"preserves prompt caching because it appends a signal instead of modifying system messages."* `ToolSearchProcessor` loads are append-only (prefix stays stable); unloading shifts the prefix into a cache write.[mastra-prompt-caching](#mastra-prompt-caching), [mastra-tool-search](#mastra-tool-search)
    - [details] Anthropic-ordered example — providerOptions at tool and instruction level
    - [code: typescript] (line 432)
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
    narrative (compacted):
      - [bullet] **In one line:** caching reuses the already-computed prompt prefix, so the repeated part is billed at a cheap read rate and returns faster — nothing is dropped from what the model sees.
      - [bullet] The server caches a **prefix**; a byte-identical prefix in the next request means that computation is reused.
      - [bullet] Result: lower latency, with cached tokens billed at a much cheaper cache-read rate.
      - [bullet] **When it pays off — you need a repeatable, byte-identical prefix.**
      - [bullet] **Conversational agents** — system prompt, tool schemas and prior turns are re-sent every turn.
      - [bullet] **Large document processing** — a fixed corpus held in context across queries, without full latency each time.
      - [bullet] **Tool-heavy prompts** — a large tool-schema prefix identical across calls.
      - [bullet] Not limited to multi-turn: any *repeated static block* (system prompt, uploaded doc, tool set) benefits, even across unrelated single-turn requests.
      - [bullet] **How to design for cache hits** — same rule as [stable prefix, variable tail].
      - [bullet] Put the **stable, large** material first — system instruction, tool schemas, big static policy — so it forms the cacheable prefix.
      - [bullet] Keep the **variable** material (per-turn retrieval, latest messages) *after* it.
      - [bullet] **Don't interleave a changing token into the middle of the stable prefix.** One changed byte breaks the cache from that point on — the key is a cumulative hash and hits need 100% byte-identical segments.
      - [bullet] **That is the memory rule, concretely.** The docs name a *varying suffix* — "timestamps, per-request context, the incoming message" — as the cache-killers, and dynamic memory/state is per-request context.
      - [bullet] **Stable — safe in the prefix:** the **procedural** instruction ("static, versioned"). ([M7 · Memory & State](../07-memory-state/README.md))
      - [bullet] **Dynamic — belongs in the tail:** **working** (this turn's message/tool result), **semantic** (`search_memory` hits), **episodic** (`load_memory` hits), **external/retrieval** (fetched docs) — all differ per turn. ([M7 · Memory & State](../07-memory-state/README.md))
      - [bullet] **Neither breaks a cache:** **parametric** memory is the weights and never enters the prompt; **prospective** memory lives in a scheduler, not the prompt. ([M7 · Memory & State](../07-memory-state/README.md))
      - [bullet] **Both memory *and* cache hits is possible** — retrieve into the tail past the breakpoint, or load out-of-band (tool search / `defer_loading`, appended `system` messages) leaving the prefix untouched.
      - [bullet] **Anthropic TTL:** automatic caching defaults to a 5-minute TTL; a 1-hour TTL costs 2× the base input token price.
      - [bullet] **Invalidation** — what a change actually kills, per framework.
      - [bullet] **Anthropic — the only per-level model.** The cache is assembled `tools` → `system` → `messages`, and "changes at each level invalidate that level and all subsequent levels."
      - [bullet] A `messages` change invalidates **only the messages cache** — tools ✓ and system ✓ survive.
      - [bullet] A `system` change invalidates system **and** messages; tools ✓ survives.
      - [bullet] A `tools` change invalidates **the entire cache** (✘ ✘ ✘).
      - [bullet] The full matrix also covers web-search/citations/speed toggles (system-level), `tool_choice` and images (messages-only), and thinking/effort (messages always; tools/system model-dependent).
      - [bullet] **OpenAI — no levels; your breakpoints *are* the levels.** Render order is fixed (hidden internal instructions → `tools` → developer messages → messages), but nothing invalidates "a level": "Cache reuse requires the entire rendered prefix to match," and lookup walks breakpoints longest → shortest.
      - [bullet] A change at or before breakpoint *k* kills prefix *k* **and every longer prefix built on it**; earlier-ending prefixes still hit. Editing the stable developer block kills both tiers; editing a branch suffix kills only the longer one.
      - [bullet] **The `tools` tier is unreachable.** Breakpoints attach only to *content blocks inside input messages*; `tools` render before all messages and `additional_tools` rejects breakpoints — so every message breakpoint necessarily swallows the tool schemas.
      - [details] Example A — OpenAI's default: one fused prefix (implicit breakpoint)
      - [code] import OpenAI from "openai";

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
      - [code] 1 cold write: input=141 cached=0 write=141
2 append turn: input=152 cached=141 write=152
3 append turn: input=162 cached=152 write=162
4 tool description edited: input=175 cached=0 write=175
      - [details] Example B — explicit breakpoints: the closest OpenAI gets to Anthropic's ordering
      - [code] import OpenAI from "openai";

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
      - [code] 1 cold write: input=106 cached=0 write=186
2 same prefix, new question: input=107 cached=99 write=0
3 tier 2 (rubric) edited: input=107 cached=87 write=100
4 tier 1 (policy) edited: input=107 cached=0 write=188
5 one tool description edited: input=108 cached=0 write=190
      - [bullet] **Mastra — binary, no levels.** Caching passes through as `providerOptions`; the only rule is append-versus-modify, which "preserves prompt caching because it appends a signal instead of modifying system messages." `ToolSearchProcessor` loads are append-only (prefix stable); unloading becomes a cache write.
      - [details] Anthropic-ordered example — providerOptions at tool and instruction level
      - [code] import { Agent } from '@mastra/core/agent'
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
      - [bullet] **Google ADK / Gemini — only "the prefix changed".** No order, no levels: ADK reuses a cache until `expireTime`, `cacheIntervals`, or a prefix change; Gemini advises large common content early and "similar prefix."
      - [bullet] **Mid-conversation changes** — append-don't-edit, and who else can do it.
      - [bullet] **Anthropic** — append a `{"role": "system"}` message instead of editing the top-level `system` field (prefix untouched, operator priority retained); `tool_addition`/`tool_removal` reference tools by name so the `tools` array never changes; **turn-scoped** `clear_at: "next_user_message"` reminders cost nothing after their turn.
      - [bullet] **OpenAI** — `developer` role plus *"append new messages rather than rewriting earlier turns"* (guidance, not a primitive); `additional_tools` **adds** mid-thread but there is **no removal** — dropping a tool *"will break the model's cache from that point forward."*
      - [bullet] **Mastra** — no mid-conversation `role: "system"`; its cache-safe mid-loop move is a `<system-reminder>` *user* message, and `ToolSearchProcessor` load/unload mutates the real `tools` array (no name-referenced add/remove).
      - [bullet] **Google ADK / Gemini** — `static_instruction` pins the static instruction and pushes the per-turn `instruction` into *user* content (inverted seam, same intent); **no** mid-conversation tool changes.
      - [bullet] **MCP servers share the tool-schema prefix — and are its most fragile level.**
      - [bullet] MCP toolsets resolve into the `tools` block — cached *first*, before system and messages. The breakpoint lands on the `mcp_toolset` entry, not on individual tools.
      - [bullet] **A new server, renamed tool, or changed docstring/parameter invalidates the whole cache** — "entire cache (tools, system, messages)."
      - [bullet] **Fix: keep the always-loaded set stable, discover the rest dynamically.** `defer_loading`/tool search appends discovered tools *after* the prefix — *"the prefix is untouched, so prompt caching is preserved."*
      - [bullet] **But `defer_loading` saves the *window*, not the wire.** Full schemas still transit every request — it only keeps deferred tools out of the cached prefix. A deferred tool can't also carry `cache_control` (API 400), so the breakpoint goes on a non-deferred tool.
      - [bullet] **OpenAI:** same idea, own flag — `defer_loading: true` plus `{"type": "tool_search"}`; discovered tools are injected at the context window's end, preserving the cache across requests. Agents API MCP tools defer automatically; changing the loaded set "will break the model's cache from that point forward."
      - [bullet] **Mastra (provider-agnostic):** no `defer_loading` — `ToolSearchProcessor` supplies `search_tools`/`load_tool` meta-tools instead; activated tools are appended after existing ones, keeping the cached prompt prefix stable, so loads stay cache-friendly. Unloading shifts the prefix, costing the next turn a cache write instead of a hit.
      - [bullet] **Even JSON key order counts:** Swift/Go randomize map-key order during serialization, which alone changes the block bytes and breaks the cache.
      - [bullet] **ADK is silent** on tools/MCP in caching — it keys only on a "cacheable prefix" that must not change.
      - [bullet] **How to write the system instruction for it:** keep it byte-stable across turns — no timestamps, no per-request context injected into it — and put all per-turn variation in the tail, not the head.
      - [bullet] **ADK knobs** — `ContextCacheConfig` on the `App`:
      - [bullet] `ttl_seconds` — cache lifetime, **default 1800**.
      - [bullet] `cache_intervals` — max uses before refresh, **default 10**.
      - [bullet] `min_tokens` — skip caching tiny requests; note the **default is `0`**, so this is a setting you choose.
      - [bullet] With **LiteLLM/Azure backends** the same principle applies at the *provider* layer — your provider's prompt-caching keys off the stable prefix, and LiteLLM passes it through.
      - [bullet] **Cache pre-warming** — buy the first turn's latency back.
      - [bullet] **Mechanism:** send `max_tokens: 0` — the API reads the prompt, writes the cache at the breakpoint, returns no output.
      - [bullet] **Why it isn't redundant though the first send is "full-priced":** the pre-warm call is what absorbs the **cache write** (1.25× base); the first *real* request then finds the entry already written and pays only the **cache read** (0.1× base) and skips the re-prefill.
      - [bullet] The stated payoff is **latency**, not cost alone: *"eliminates the cache-miss latency penalty on the first user interaction, reducing time-to-first-token (TTFT)."*
      - [bullet] **Requirements:** breakpoint on the *shared* prefix (not the placeholder), the same thinking/effort config as real traffic, re-warm inside the TTL (5 min, or the 1-hour cache).
      - [bullet] **When not worth it:** the docs never state it — they scope pre-warming to *latency-sensitive* apps. The first real turn performs the same cache write anyway; pre-warming only moves that write earlier so the first turn reads instead.
      - [bullet] **In ADK:** no pre-warm knob — `ContextCacheConfig` has only `min_tokens`, `ttl_seconds`, `cache_intervals`, `create_http_options`; the first turn is a plain cache miss.
      - [bullet] **Tradeoff (the ledger entry).**
      - [bullet] Caching is a *structure* reward: you get it only by assembling the window with a **stable prefix**.
      - [bullet] That means accepting the instruction and tool schemas must be **fixed and ordered early** rather than free-form.
      - [bullet] You trade a little assembly rigidity for a large cost/latency win — a decision you make, not a default you inherit.
    prompt: You have a stable system instruction, a large tool-schema block, and a per-turn retrieval block. Where do they go, what exactly breaks a cache hit, and how do the invalidation semantics differ between Anthropic, OpenAI, and Mastra/ADK? Include what a change to one tool description costs on each.
    reveal: **The one-liner:** caching reuses the already-computed prefix, so the repeated part is billed at a cheap read rate and returns faster — and nothing is dropped from what the model sees. The key is a cumulative hash over byte-identical segments.

**Layout — stable prefix, variable tail.** Put the stable, large material first (system instruction, tool schemas, big static policy); put per-turn material after it (retrieval, latest messages). Never interleave a changing token into the middle of the stable prefix: one changed byte breaks the cache from that point on. The docs name the killers as a varying suffix — timestamps, per-request context, the incoming message. Procedural (static, versioned) instructions are safe in the prefix; working memory, semantic/episodic memory hits, and retrieved docs all differ per turn and belong in the tail. Parametric memory never enters the prompt; prospective memory lives in a scheduler, so neither breaks a cache.

**Invalidation, per framework:**

- **Anthropic — per level.** The cache assembles `tools` → `system` → `messages`, and a change at a level invalidates that level and all subsequent ones. Editing a *message* kills only the messages cache (tools and system survive). Editing the *system* field kills system and messages, tools survive. Editing *tools* kills the entire cache.
- **OpenAI — no levels; your breakpoints are the levels.** The rendered prefix must match; lookup walks breakpoints longest → shortest. By default there is one implicit breakpoint and one fused entry: hidden instructions + **all tool schemas** + developer message + turns. The `tools` tier is unreachable — breakpoints attach only to content blocks inside input messages. So editing one tool description takes cached from 152 to **0**. Explicit breakpoints can carve tiers, but tools stay welded into tier 1.
- **Mastra — binary, append-vs-modify.** Cache is a provider pass-through; appending keeps the prefix stable, unloading a tool shifts it into a cache write.
- **ADK/Gemini — nothing but "the prefix changed."** No order, no levels; only "large and common contents at the beginning" and a similar prefix.

**Practical extras:** TTL defaults to 5 minutes (1 hour at 2× input price); pre-warm with `max_tokens: 0` so the write (1.25×) lands first and the real turn pays the read (0.1×); ADK knobs are `ttl_seconds` (1800), `cache_intervals` (10), `min_tokens` (0 by default). Tradeoff: caching is a structure reward — accept rigid instruction/tool ordering for a large cost and latency win.
    [diagram] mermaid (agent-authored):
      ```mermaid
      flowchart TD
        t[Tools change] --> a[Tools cache dies]
        a --> s[System cache dies]
        s --> m[Messages cache dies]
      ```
### The science behind prompt caching (collapse-by-default)  [src README.md:508]
      - [details] Why a reused prefix is safe, what is conserved, and when it can still bite
      narrative (compacted):
        - [details] Why reusing a prefix is safe, what the cache conserves, and when it still harms.
      prompt: A review asks: "prefix caching is free, so it can't change model behaviour." Defend or refute — why is reusing a prefix causally safe, what is actually conserved on a hit, and under what measured conditions does reuse still diverge? Also: why can't the bare word "caching" be treated as harmless?
      reveal: **Why a prefix is safe.** Causal attention: "The KV cache of a prefix is not affected by the succeeding text." The model reads the full prefix; only the recomputation is skipped. Anthropic states the response is identical to what you would get without caching. The safety is specific to *prefix* reuse — non-prefix reuse that ignores cross-attention with preceding text can produce a wrong response.

**What is conserved.** On a hit the model does not re-run the forward pass over the cached prefix; only the new suffix is computed and the cached part is read back. What is saved is compute — the prefill of the prefix and its GPU time — and that saving is what the provider passes back as a lower price. No token is omitted from the model's context: the discount is for *not recomputing*, not for *not reading*.

**Where it can still bite.**

- **Numerical divergence.** Recomputing vs reusing cached KV can differ because reduction order differs between prefill and decode. Vendors conflict: OpenAI says identical requests are not guaranteed to produce identical outputs; Anthropic says the response is identical.
- **Measured, quantization-amplified.** Fixed model, params, seed, order, batch size one: cache changed the trajectory on **36.2%** of episodes at 16-bit and **75.0%** at 4-bit, against a cache-off control that was bit-identical in 0 of 800 episodes. Aggregate accuracy did not move.
- **Stale/wrong key.** Serving the wrong chunk or an expired block is a cache-*correctness* bug, distinct from grounding. Vendor keys are coarse enough that mismatches usually degrade to a miss — the safer failure; Anthropic reports hits only for byte-for-byte identical prefixes and calls mismatches "your bug." Real wrong-key hazard exists for non-text modalities, where the key can cover the text but not the image.

**Why "caching" is not one thing.** Other caching mechanisms *do* drop content: KV-cache *eviction* (H₂O discards ~80% with significant degradation), and *semantic* caching can return a wrong stored answer because it matches meaning, not exact text. Those are not prefix caching — which is exactly why the bare word can't mean "harmless."
      [diagram] mermaid (agent-authored):
        ```mermaid
        flowchart TD
          h[Cache hit] --> p[Skips prefix prefill]
          h --> r[Reads full prefix anyway]
        ```
## Context budgeting: the three dials  [src README.md:537]
    - Now the spend side. When a session grows, you have three dials, and you turn them in this order:
    narrative (compacted):
      - [prose] The spend side: a growing session hands you three dials, turned in this order.
    prompt: Name the three dials in the order you turn them, and for each say in one line what it decides. Why is the order itself part of the answer — what does dial 1 do that the other two cannot?
    reveal: Three dials, turned in this order, on the spend side of a growing session:

1. **Per-turn budget** — set a ceiling: the maximum tokens you will ever send in one call (e.g. never assemble more than ~20k for this agent).
2. **Eviction** — decide what to drop first when you must shed tokens.
3. **Summarization-in-the-loop (compaction)** — decide how old conversation history gets compressed and how much recent history stays verbatim.

**Why the order matters:** dial 1 is not a strategy, it is the tripwire. It is the absolute safety net that stops the unbounded-growth failure, and it is the only dial that is purely a limit — it names the bound the other two must operate inside. Dial 2 is the first real policy (what goes), dial 3 is the last resort for history specifically (what gets rewritten).

Turning them in this order means you degrade the cheapest, least-informative material first and only reach compaction — the lossy option — after the easy evictions are exhausted. Inverting the order gets you summarizing history to make room for outputs you could simply have deleted.
### Dial 1 — the per-turn budget  [src README.md:541]
      - Before anything, set a **ceiling**: the maximum number of tokens you will ever send in one call (e.g., "never assemble more than ~20k tokens for this agent"). This is the absolute safety net that stops the unbounded-growth failure.[fu-long-context-deployment](#fu-long-context-deployment) It is not a strategy by itself — it's the tripwire that tells you the other two dials must be turned.
      narrative (compacted):
        - [prose] First fix a ceiling on tokens per call (say ~20k with fu-long-context-deployment): the tripwire against unbounded growth, not a strategy, which signals the other two dials must move.
      prompt: What exactly does the per-turn budget dial set, and why does the module insist it is not a strategy? What failure does it stop, and what does crossing it tell you to do?
      reveal: **What it sets.** A ceiling — the maximum number of tokens you will ever send in one call, expressed concretely per agent, e.g. "never assemble more than ~20k tokens for this agent."

**Why it is not a strategy.** It decides nothing about *which* content is worth keeping; it only bounds the total. It is the absolute safety net that stops the unbounded-growth failure, and the tripwire that tells you the other two dials must be turned.

**What it stops.** Unbounded growth: the append-everything-forever default in which the window keeps inflating because the session keeps inflating, with cost and latency scaling on every input token every turn and with no correctness return.

**What crossing it means.** Not "evict something arbitrary" — it means the policy dials now have to act: evict in the prescribed order (dead results, verbose tool outputs, old retrieved material, then compact history), while never evicting the standing instruction or the current task/question.

So the budget's role is diagnostic as much as preventive: it converts a silent accumulation problem into a signal that forces a named decision.
### Dial 2 — eviction (what to drop first)  [src README.md:545]
      - When you must shed tokens, drop in this order:
      - 1. **Dead intermediate results** — failed tool attempts, abandoned scratchpad steps, superseded drafts.
      - 2. **Verbose tool outputs** — truncate to the fields the task needs; store the full result in an artifact, keep a pointer.[ding-mcp-performance](#ding-mcp-performance)
      - 3. **Old retrieved material** — evidence from turns ago, unless the current task still needs it.
      - 4. **Compacted history** — summarize old turns (Dial 3) rather than keeping them verbatim.[adk-context-compaction](#adk-context-compaction)
      - And the two things you **never** evict: the **standing instruction** (that's your policy — losing it is how instruction drift happens)[wallace-instruction-hierarchy](#wallace-instruction-hierarchy), [geng-control-illusion](#geng-control-illusion) and the **current task/question**.[shaier-context-before-question](#shaier-context-before-question)
      - **Sizing note — how many tool definitions belong in the prefix at all.** This is a budget decision, not a fixed cost: tool selection degrades as the candidate set grows, so the practical fix is to show the model a retrieved *shortlist* rather than every schema you own.[repantis-how-many-tools](#repantis-how-many-tools), [gan-rag-mcp](#gan-rag-mcp) The scaling limits are concrete — JSON schemas begin to overflow constrained windows by roughly 500 tools, while compressed schemas keep working past 800.[sakizli-tool-schema-compression](#sakizli-tool-schema-compression) "How many tools should this agent see?" is a question with a number attached; M8 is where you answer it.
      - **Note the level.** The eviction policies you will meet in the systems literature — H₂O's heavy-hitter oracle,[zhang-h2o](#zhang-h2o) StreamingLLM's attention sinks[xiao-streamingllm](#xiao-streamingllm) — operate on the **KV cache inside the inference server**. They change which tokens the model *attends to*, not which tokens you *send*. The dial above is the harness-level version: it changes the request. Don't conflate them.[own-synthesis](#own-synthesis)
      narrative (compacted):
        - [prose] Shed tokens in this order:
        - [prose] Dead intermediate results: failed tool attempts, abandoned scratchpad steps, superseded drafts.
        - [prose] Verbose tool outputs: truncate to the fields the task needs, archive the full result, keep a pointer (ding-mcp-performance).
        - [prose] Old retrieved material: evidence from earlier turns, unless the current task still needs it.
        - [prose] Compacted history: summarize old turns (Dial 3) rather than holding them verbatim (adk-context-compaction).
        - [prose] Never evict the standing instruction (your policy; losing it causes instruction drift) or the current task/question.
        - [prose] Tool definitions belong to the budget, not to fixed cost: selection degrades as candidates grow, so inject a retrieved shortlist. JSON schemas overflow constrained windows near 500 tools; compressed ones work past 800. M8 supplies the number.
        - [prose] Mind the level: H2O and StreamingLLM evict inside the inference server's KV cache, changing what the model attends to, not what you send. This dial is harness-level and changes the request; don't conflate them.
      prompt: Give the eviction order when you must shed tokens, and explain what property of each item justifies its rank. Which two things are never evicted, and why? Add the level distinction: how does harness-level eviction differ from the eviction discussed in systems papers?
      reveal: **Eviction order:**

1. **Dead intermediate results** — failed tool attempts, abandoned scratchpad steps, superseded drafts. Zero remaining value: nothing downstream can use them.
2. **Verbose tool outputs** — truncate to the fields the task needs; store the full result in an artifact and keep a pointer. The information is recoverable, so what you drop is the redundant rendering.
3. **Old retrieved material** — evidence from turns ago, unless the current task still needs it.
4. **Compacted history** — summarize old turns (dial 3) rather than keeping them verbatim.

The ranking is by remaining value per token. Ranks 1–3 are disposable because the material is either dead or reconstructible (the pointer keeps the full text reachable); rank 4 is the fallback that degrades gracefully — compaction converts history rather than deleting it, and it is last because it is the only one that rewrites content the model may still need.

**Never evicted:**

- The **standing instruction** — that is your policy; losing it is how instruction drift happens.
- The **current task/question** — the thing everything else exists to serve.

**Sizing note (part of this dial):** how many tool definitions belong in the prefix is itself a budget decision, because tool selection degrades as the candidate set grows. The practical fix is to show a retrieved shortlist rather than every schema; JSON schemas begin to overflow constrained windows around 500 tools, while compressed schemas keep working past 800.

**The level distinction:** the eviction policies in the systems literature — H₂O's heavy-hitter oracle, StreamingLLM's attention sinks — operate on the **KV cache inside the inference server**. They change which tokens the model *attends to*, not which tokens you *send*. This dial is the harness-level version: it changes the request. Don't conflate them.
      [diagram] mermaid (agent-authored):
        ```mermaid
        flowchart TD
          a[Drop dead results] --> b[Drop verbose outputs]
          b --> c[Drop old retrieved material]
          c --> d[Compact old history]
          n[Never evict: policy and question]
        ```
### Dial 3 — summarization-in-the-loop (compaction)  [src README.md:560]
      - For the conversation history specifically, the right tool is **compaction**: periodically summarize older turns into a short running summary, keep only the recent few turns verbatim, and continue.[adk-context-compaction](#adk-context-compaction), [packer-memgpt](#packer-memgpt) It's lossy compression of the agent's memory — you trade *fidelity of old turns* for *attention and cost on the current turn*.
      - This is exactly what ADK's **context compaction** feature automates, via `EventsCompactionConfig` on the `App`, with two strategies:[adk-context-compaction](#adk-context-compaction)
      - **Token-based (primary):** trigger when actual token volume crosses `token_threshold`, and keep the last `event_retention_size` events raw. This is the safety net for unpredictable workloads (a user pastes a 50k-token code block; a file upload floods the window).
      - **Sliding-window (turn-based):** trigger every `compaction_interval` turns, with `overlap_size` prior events carried over for continuity. Predictable chats.
      - And you can supply a custom **`LlmEventSummarizer`** with a dedicated (often cheaper) model so compaction doesn't compete with the main task's model budget.[adk-context-compaction](#adk-context-compaction)
      - The honest caveat, because it's the whole point: **compaction is lossy, and its loss is invisible.[unsupported](#unsupported)** A summarized turn has dropped the exact wording, the exact numbers, the exact caveat — and the agent will not tell you it's reasoning from a lossy memory of its own past.[unsupported](#unsupported) Compaction is a *deliberate* acceptance of degraded history in exchange for attention on the present. Like every tradeoff in this course, it belongs in an ADR, not a config comment. And note the counter-evidence before you conclude that compression must hurt: targeted compression can *raise* accuracy while cutting tokens,[jiang-longllmlingua](#jiang-longllmlingua) and learned context compression can substitute for raw demonstrations.[chevalier-autocompressors](#chevalier-autocompressors) The loss is a property of *what* you compress, not of compressing.[fei-semantic-compression](#fei-semantic-compression) And it is not merely an implementation defect: compaction has been shown equivalent to one-way communication complexity, so a minimum loss is a property of the problem, not of your summarizer.[patodiya-cache-divergence](#patodiya-cache-divergence)
      - **Failure mode (compaction):** summarizing away the *load-bearing* detail — the exact contract clause, the exact error message, the exact user requirement — while preserving the chit-chat.[unsupported](#unsupported) A naive summarizer keeps the narrative and drops the specifics; the agent then "remembers" the conversation without remembering any of the facts that mattered. The compaction prompt itself is a harness artifact that needs its own scrutiny.
      narrative (compacted):
        - [prose] For history the tool is compaction: roll older turns into a short running summary, keep the recent few verbatim, continue. That is lossy compression of memory, trading old-turn fidelity for attention and cost now.
        - [prose] ADK automates exactly this through EventsCompactionConfig on the App, with two strategies:
        - [bullet] Token-based (primary): fires when token volume crosses token_threshold, keeping the last event_retention_size events raw; the safety net for unpredictable loads like a pasted 50k-token block.
        - [bullet] Sliding-window (turn-based): fires every compaction_interval turns, carrying overlap_size earlier events for continuity; suited to predictable chats.
        - [prose] A custom LlmEventSummarizer can run on a dedicated, cheaper model so compaction does not compete with the main task's budget.
        - [prose] The point: compaction is lossy and invisibly so - the agent will not admit reasoning from degraded memory, so ADR it. Counter-evidence: targeted and learned compression cut tokens while preserving accuracy, and one-way communication complexity sets a floor on the loss.
        - [prose] Failure mode: the summarizer drops load-bearing specifics - the exact clause, error message, user requirement - while keeping the chit-chat, so the agent remembers the conversation but none of its facts. The compaction prompt itself needs scrutiny.
      prompt: Describe compaction's policy and the tradeoff it makes. Then compare ADK's two trigger strategies. Finally, answer the hard part: if compaction is lossy, why is its loss described as *invisible*, and what exactly is the failure mode — and what do the counter-evidence and complexity result say about blaming the compressor?
      reveal: **Policy.** For conversation history: periodically summarize older turns into a short running summary, keep only the recent few turns verbatim, and continue. It is lossy compression of the agent's memory — fidelity of old turns traded for attention and cost on the current turn.

**ADK's two strategies** (`EventsCompactionConfig` on the `App`):

- **Token-based (primary)** — trigger when actual token volume crosses `token_threshold`, keeping the last `event_retention_size` events raw. The safety net for unpredictable workloads (a pasted 50k-token block, a file upload flooding the window).
- **Sliding-window (turn-based)** — trigger every `compaction_interval` turns, with `overlap_size` prior events carried for continuity. For predictable chats.

A custom `LlmEventSummarizer` with a dedicated (often cheaper) model keeps compaction from competing with the main task's budget.

**Why the loss is invisible.** A summarized turn has dropped the exact wording, the exact numbers, the exact caveat — and the agent will not tell you it is reasoning from a lossy memory of its own past. Nothing errors; nothing is flagged. Compaction is a deliberate acceptance of degraded history, which is why it belongs in an ADR rather than a config comment.

**The failure mode.** Summarizing away the load-bearing detail — the exact contract clause, the exact error message, the exact user requirement — while preserving the chit-chat. A naive summarizer keeps the narrative and drops the specifics; the agent then "remembers" the conversation without remembering any of the facts that mattered. The compaction prompt is itself a harness artifact needing scrutiny.

**Against blaming the compressor.** Targeted compression can *raise* accuracy while cutting tokens; learned context compression can substitute for raw demonstrations. So the loss is a property of *what* you compress, not of compressing. And a minimum loss is not merely an implementation defect: compaction has been shown equivalent to one-way communication complexity, so a floor is a property of the problem.
      [diagram] mermaid (agent-authored):
        ```mermaid
        flowchart TD
          a[Compaction config] --> b[Token threshold strategy]
          a --> c[Turn interval strategy]
          c --> d[Overlap for continuity]
        ```
## Beyond budgets: selecting by *content*, not position  [src README.md:577]
    - The three dials above are all **positional** — they decide how much history to keep and how far back, not *which* turns matter to this question. But a user never says "give me turn 5" — they say *"remember when we discussed the Kunal Kamra Super-Thanks figure?"* or *"document the discussion from 'the problem with unions' through 'how to structure unions.'"* That is a different selector entirely: the assembly layer must resolve a **semantic reference** into the right turns, retrieve that span, and exclude what doesn't belong — *content-based selection*, not budget-based eviction.
    - This is where the "append everything, forever" default finally gets its full answer. **Session state is the source of truth** (the whole transcript); **the context window is a per-turn projection** of it;[adk-context](#adk-context) and **the assembly layer is the selector.** For the mechanism end to end — reference resolution, topic segmentation, span retrieval, relevance filtering, and the named systems that already do it (MemGPT/Letta,[packer-memgpt](#packer-memgpt) Zep,[rasmussen-zep](#rasmussen-zep) Mem0[chhikara-mem0](#chhikara-mem0)) — read the deep dive:
    - **[Selective context assembly — the context window as a projection of session state](selective-context-assembly.md)** · the content-based selector, worked case by case, with the active-research frontier flagged honestly.
    narrative (compacted):
      - [prose] The three dials are positional: how much history, how far back - not which turns matter. Users reference content instead, naming a figure or a topic span, so assembly must resolve the semantic reference, retrieve that span, and exclude the rest: content-based selection.
      - [prose] This answers append-everything-forever: session state is truth, the context window a per-turn projection, and the assembly layer the selector. The deep dive covers reference resolution, segmentation, span retrieval, filtering, and the named systems - MemGPT/Letta, Zep, Mem0.
      - [prose] Pointer to the deep dive on selective context assembly: the content-based selector worked case by case, with the active-research frontier flagged honestly.
    prompt: All three dials are called positional. What precisely do they fail to decide, and what does a user utterance look like that exposes the gap? Name the three things the module says must happen instead, and state the two-object framing that concludes the section.
    reveal: **What the dials decide — and don't.** The three dials are all *positional*: they decide how much history to keep and how far back, not *which* turns matter to this question. Recency, eviction thresholds and compaction windows never ask what a turn is about.

**The utterance that exposes the gap.** A user never says "give me turn 5." They say things like *"remember when we discussed the Kunal Kamra Super-Thanks figure?"* or *"document the discussion from 'the problem with unions' through 'how to structure unions.'"* That is a **semantic reference**, and no positional rule can resolve it.

**What must happen instead** — content-based selection, not budget-based eviction:

1. resolve the semantic reference into the right turns,
2. retrieve that span,
3. exclude what doesn't belong.

**The framing that closes it** — and the full answer to "append everything, forever":

- **Session state is the source of truth** — the whole transcript.
- **The context window is a per-turn projection** of it.
- **The assembly layer is the selector.**

The mechanism end to end — reference resolution, topic segmentation, span retrieval, relevance filtering, and the named systems that already do it (MemGPT/Letta, Zep, Mem0) — lives in the companion deep dive, *Selective context assembly: the context window as a projection of session state*.
    - **Selective context assembly — the context window as a projection of session state** · kind: sidecar · [cited README.md:583]
      - (checklist: empty)
## Table of contents  [src selective-context-assembly.md:7]
        - (checklist: empty)
## TL;DR  [src selective-context-assembly.md:48]
        - **Session state holds the full record** — every turn: user messages, agent replies, tool calls, in chronological order.
        - **Not all of it goes into the context window.** Deliberately. The window is a *per-turn projection* assembled to answer the current question.
        - **The context assembly layer is the selector** — its job is to decide *which* turns, in *what form*, get injected for *this* question.
        - **Positional** — keep the last N turns (recency).
        - **Summarization** — compact old turns into a running summary.
        - **Content-based retrieval** — keep the full history in a store, and pull only the turns *relevant to the current question*.
        - **This document is about the third flavor** — the only one that can answer "which turns are about X" rather than "which turns are recent."
        - **It is a real, named, productized architecture** — MemGPT/Letta, Zep, Mem0, LangMem all implement it — not a fringe idea.
        - **Its hard part** — resolving a *semantic* reference ("remember when we discussed X") into the right turns — is active research. **Recall is the acknowledged bottleneck.**
        narrative (compacted):
          - [bullet] Session state keeps the full record: every turn - user messages, agent replies, tool calls - in chronological order.
          - [bullet] Not all of it enters the context window, deliberately; the window is a per-turn projection assembled for the current question.
          - [bullet] The context assembly layer is the selector, deciding which turns, in what form, are injected for this question.
          - [bullet] Positional: retain the last N turns by recency.
          - [bullet] Summarization: compact old turns into a running summary.
          - [bullet] Content-based retrieval: keep full history in a store and pull only turns relevant to the current question.
          - [bullet] This document covers the third flavor, the only one answering which turns are about X rather than which are recent.
          - [bullet] It is a real, named, productized architecture - MemGPT/Letta, Zep, Mem0, LangMem all implement it - not a fringe idea.
          - [bullet] Its hard part, resolving a semantic reference into the right turns, is active research; recall is the acknowledged bottleneck.
        prompt: Name the three selector families and what each keeps. Which one answers a question the other two structurally cannot, and what is the acknowledged bottleneck for that one?
        reveal: - **Session state holds the full record** — every turn: user messages, agent replies, tool calls, chronologically.
- **Not all of it goes into the context window**, deliberately. The window is a *per-turn projection* assembled to answer the current question; **the context assembly layer is the selector**, deciding which turns, in what form, are injected for *this* question.

**The three flavors of selection:**

1. **Positional** — keep the last N turns (recency).
2. **Summarization** — compact old turns into a running summary.
3. **Content-based retrieval** — keep the full history in a store and pull only the turns relevant to the current question.

**Which one is different.** Only content-based retrieval can answer "which turns are about X" rather than "which turns are recent." That is the family this document is about; the other two are positional by construction.

**The bottleneck.** Its hard part is resolving a *semantic* reference ("remember when we discussed X") into the right turns — active research, with **recall** named as the acknowledged limiting factor. It is not a fringe idea: MemGPT/Letta, Zep, Mem0 and LangMem all implement it, so the architecture is productized even though the selection quality is not solved.
        [diagram] mermaid (agent-authored):
          ```mermaid
          mindmap
            s[Three selectors]
              p[Positional recency]
              m[Summarization compaction]
              c[Content-based retrieval]
          ```
## The two objects: session state and the context window  [src selective-context-assembly.md:63]
        - The whole mechanism rests on one distinction that is easy to skip because the naive agent hides it: **the record and the view are two different objects.**
        narrative (compacted):
          - [prose] One easily skipped distinction underlies the mechanism, because the naive agent hides it: the record and the view are separate objects.
        prompt: Selective context assembly rests on one distinction the naive agent hides. Name the two objects, say which one is ground truth and which is derived, and state the governing invariant that keeps the derived one honest.
        reveal: **The distinction:** the record and the view are two different objects. The naive agent hides this by behaving as if the window *were* the conversation.

**Object 1 — session state (the record).** The complete, append-only transcript of one conversation thread. In ADK, `Session` is the chronological sequence of `Event`s (user messages, agent replies, tool calls), `State` is the scratchpad, and a `SessionService` persists and retrieves sessions, appending each new event via `append_event`. In DSH, the `SessionEvent` log in `core/session` is the single source of truth. Its properties: **complete** (nothing is dropped — the ground truth of what actually happened), **ordered** (chronology preserved), and **not read by the model** — the model never sees the `Session` object; it is storage, not input.

**Object 2 — the context window (the view).** The single block of text the model reads every time it thinks. The harness assembles it fresh each turn (ADK: the `Runner` loop; DSH: prompt assembly in `core/system-prompt`). It contains a *selection* — from the session, plus standing instructions, tool definitions, and retrieved material.

**The governing invariant (DSH): "model-visible means logged."** Everything the model sees must be reconstructable from the session log. The window is a *derived view*; the log is the *source of truth*.

The one-sentence version: session state is the truth; the context window is a decision about which sliver of that truth to show, in what form, at what cost.
### Session state is the record  [src selective-context-assembly.md:67]
          - **What it is:** the complete, append-only transcript of one conversation thread.
          - In ADK: `Session` = the chronological sequence of `Event`s (user messages, agent replies, tool calls); `State` = the scratchpad; a `SessionService` persists and retrieves sessions, appending each new `Event` via `append_event`.
          - In DSH: the `SessionEvent` log in `core/session` — the single source of truth.
          - **Complete** — nothing is dropped; it is the ground truth of "what actually happened."
          - **Ordered** — chronology is preserved; turn 5 comes before turn 6.
          - **Not read by the model** — the model never sees the `Session` object itself. It is *storage*, not *input*.
          narrative (compacted):
            - [bullet] What it is: the full, append-only transcript of a single conversation thread.
            - [bullet] In ADK, Session is the chronological sequence of Events (user messages, agent replies, tool calls), State is the scratchpad, and a SessionService persists and retrieves sessions, appending each Event via append_event.
            - [bullet] In DSH, the SessionEvent log in core/session - the single source of truth.
            - [bullet] Complete: nothing is dropped, so it is ground truth for what actually happened.
            - [bullet] Ordered: chronology holds; turn 5 precedes turn 6.
            - [bullet] Not read by the model: the model never sees the Session object, which is storage rather than input.
          prompt: Define session state, list the concrete objects it maps to in ADK and DSH, and give its three key properties — in particular, why is "the model never reads it" a property worth naming?
          reveal: **What it is:** the complete, append-only transcript of one conversation thread.

**Concrete mappings:**

- **ADK** — `Session` = the chronological sequence of `Event`s (user messages, agent replies, tool calls); `State` = the scratchpad; a `SessionService` persists and retrieves sessions, appending each new `Event` via `append_event`.
- **DSH** — the `SessionEvent` log in `core/session`, the single source of truth.

**Key properties:**

- **Complete** — nothing is dropped; it is the ground truth of "what actually happened."
- **Ordered** — chronology is preserved; turn 5 comes before turn 6.
- **Not read by the model** — the model never sees the `Session` object itself. It is *storage*, not *input*.

**Why the third property is load-bearing.** It is the property that makes the whole assembly question possible. If session state were read directly, there would be nothing to select and no projection to design; every turn would be a copy. Because the record is only storage, the window has to be *constructed* per turn from it — which is exactly where the assembly layer, the budget dials, and the three selectors live. Completeness and ordering are what make that construction trustworthy: any selection can be verified against, and reconstructed from, the full append-only record.
### The context window is a per-turn projection  [src selective-context-assembly.md:77]
          - **What it is:** the single block of text the model reads every time it thinks.
          - **How it comes to be:** the harness assembles it fresh each turn (ADK: the `Runner` loop; DSH: prompt assembly in `core/system-prompt`).
          - **What it contains:** a *selection* — from the session, plus standing instructions, tool definitions, and retrieved material (M4's anatomy table).
          - **The governing invariant** (DSH): **"model-visible means logged"** — everything the model sees must be reconstructable from the session log. The window is a *derived view*; the log is the *source of truth*.
          - **The one-sentence version:** session state is the truth; the context window is a decision about which sliver of that truth to show, in what form, at what cost.
          narrative (compacted):
            - [bullet] What it is: the single text block the model reads each time it thinks.
            - [bullet] How it comes to be: the harness assembles it fresh every turn - ADK's Runner loop, DSH's prompt assembly in core/system-prompt.
            - [bullet] What it contains: a selection from the session plus standing instructions, tool definitions, and retrieved material (M4's anatomy table).
            - [bullet] The governing DSH invariant, model-visible means logged: everything the model sees must be reconstructable from the session log, so the window is a derived view over the source of truth.
            - [prose] One sentence: session state is the truth; the window is a decision about which sliver of it to show, in what form, at what cost.
          prompt: What is the context window, who builds it each turn (name the components in ADK and DSH), what does it contain besides the session, and state the governing invariant it must satisfy plus what that invariant implies about which object is authoritative.
          reveal: **What it is:** the single block of text the model reads every time it thinks.

**How it comes to be:** the harness assembles it *fresh each turn* — ADK: the `Runner` loop; DSH: prompt assembly in `core/system-prompt`.

**What it contains:** a *selection*. Not just a slice of the session — also standing instructions, tool definitions, and retrieved material. That is the same anatomy as the module's component table; the window is assembled, not accumulated.

**The governing invariant (DSH): "model-visible means logged."** Everything the model sees must be reconstructable from the session log.

**What that implies.** The window is a *derived view*; the log is the *source of truth*. The arrow runs one way: the log does not depend on the window, but the window must always be reproducible from the log. So a harness change that puts text in front of the model without logging it breaks the invariant — the model saw something the record cannot explain, and nothing downstream can replay or audit that turn.

This is why "projection" is the right word rather than "copy": a projection is computed on demand from something more complete, and it can be recomputed differently for the next question.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart LR
              s[Session log] --> a[Per-turn assembly]
              a --> w[Context window view]
            ```
## Why not put everything in  [src selective-context-assembly.md:88]
        - The obvious question: if the session already holds all turns, why not just send all of it every turn? Three reasons, each a failure class from M4:
        - **Budget.** You pay for every input token every turn; input size also scales latency. Sending 90k tokens because the session *has* 90k tokens is a cost blowup with no correctness return.
        - **Attention.** The model's attention is finite and *positional*. Old turns sit in the middle of the window — the weakest attentional slot (M2's position bias). Irrelevant history doesn't just cost money; it *dilutes* the current question.
        - **Correctness.** A stale or contradicted fact that is present competes with the truth. A turn 5 that was superseded by turn 9, but still sits in the window, is wrongness presenting itself as rightness.
        - **The failure mode in one line:** treating the window as a *copy* of the session instead of a *projection* of it. The naive default — "append everything, forever" — is precisely this mistake, and M4 names it.
        narrative (compacted):
          - [prose] If the session already holds every turn, why not send all of it each time? Three M4 failure classes:
          - [bullet] Budget: every input token is paid each turn and input size scales latency; sending 90k tokens because the session has them buys no correctness.
          - [bullet] Attention: attention is finite and positional, and old turns sit mid-window in the weakest slot (M2's position bias); irrelevant history dilutes the current question.
          - [bullet] Correctness: a stale or contradicted fact competes with the truth; a turn 5 superseded by turn 9 but still present is wrongness presenting as rightness.
          - [prose] In one line: treating the window as a copy of the session rather than a projection of it - the append-everything-forever default M4 names.
        prompt: If the session already holds every turn, give the three independent reasons not to send all of it every turn. Which failure class from M4 does each map to, and what single mistake do all three amount to?
        reveal: **Reason 1 — Budget.** You pay for every input token every turn, and input size also scales latency. Sending 90k tokens because the session *has* 90k tokens is a cost blowup with no correctness return.

**Reason 2 — Attention.** The model's attention is finite and *positional*. Old turns sit in the middle of the window — the weakest attentional slot (position bias). Irrelevant history doesn't just cost money; it *dilutes* the current question.

**Reason 3 — Correctness.** A stale or contradicted fact that is present competes with the truth. A turn 5 that was superseded by turn 9 but still sits in the window is wrongness presenting itself as rightness.

Each maps to a failure class from M4: cost/latency, attention dilution, and grounding/consistency.

**The single mistake:** treating the window as a *copy* of the session instead of a *projection* of it. The naive default — "append everything, forever" — is precisely this mistake, and M4 names it.

Note the asymmetry that makes the argument decisive: the first two reasons are degradations you could imagine tolerating, but the third means the full-history default can make the model *confidently wrong*, not merely slow or expensive.
        [diagram] mermaid (agent-authored):
          ```mermaid
          flowchart TD
            a[Window as session copy] --> b[Cost blowup]
            a --> c[Diluted attention]
            a --> d[Stale fact competes]
          ```
## The three selectors  [src selective-context-assembly.md:100]
        - Given "not everything goes in," the assembly layer needs a *policy* for what does. There are exactly three families of policy — and only one of them is about *content*.
        narrative (compacted):
          - [prose] Given that not everything goes in, the assembly layer needs a policy for what does. Exactly three families of policy exist, and only one concerns content.
        prompt: Given that not everything goes in, the assembly layer needs a policy. Enumerate the three families of policy and, for each, the rule in one line. What is the asymmetry that makes exactly one of them a different kind of thing from the other two?
        reveal: There are exactly three families of policy for what goes into the window.

1. **Positional recency** — keep the last N turns verbatim; drop everything older.
2. **Summarization / compaction** — periodically summarize old turns into a running summary, keeping only the recent few verbatim.
3. **Content-based retrieval** — keep the full session in an external store and, per turn, retrieve only the turns relevant to the current question and inject them.

**The asymmetry.** The first two are *positional*: their selection rule is a position or a distance-from-now, and they never inspect what a turn is about. The third is *semantic*: it answers "which turns are about X," not "which turns are recent."

That difference has a consequence for how each can be implemented. Positional rules are deterministic — a turn number, a token threshold, a turn interval — so they need no judgment. Content-based selection depends on *relevance*, which is a judgment, so it cannot be a deterministic rule unless turns are pre-tagged; it needs machinery of its own (reference resolution, retrieval, span retrieval, filtering, assembly).

That is why the module treats the third family as the subject of its own deep dive rather than a third bullet.
### Selector 1: positional recency  [src selective-context-assembly.md:104]
          - **Policy:** keep the last N turns verbatim; drop everything older.
          - **Why it exists:** it is trivial, deterministic, and predictable.
          - Anything older than N is gone **regardless of relevance**.
          - Fails *case 1*: a reference to a turn-5 figure is dead if N = 4.
          - Fails *case 2*: turns 5–8 are gone if N = 2.
          narrative (compacted):
            - [bullet] Policy: keep the last N turns verbatim and drop all older ones.
            - [bullet] Why it exists: it is trivial, deterministic, and predictable.
            - [bullet] Anything older than N is discarded regardless of relevance.
            - [bullet] Fails case 1: a reference to a turn-5 figure is dead once N is 4.
            - [bullet] Fails case 2: turns 5 through 8 are gone when N is 2.
          prompt: State the positional-recency policy, say what it is genuinely good for, and give both failure modes as concrete counterexamples. Explain why the failure is a structural property of the rule rather than something a larger N fixes.
          reveal: **Policy:** keep the last N turns verbatim; drop everything older.

**Why it exists:** it is trivial, deterministic, and predictable — no model call, no judgment, no variability between turns.

**Where it fails:**

- Anything older than N is gone **regardless of relevance** — the rule never looks at content.
- **Case 1:** a reference to a turn-5 figure is dead if N = 4.
- **Case 2:** turns 5–8 are gone if N = 2.

**Why a bigger N doesn't fix it.** The failure is not that N is too small; it is that relevance and age are unrelated variables. Raising N delays the failure and raises cost proportionally, but any fixed N still drops a turn-5 fact the moment the window is long enough to push it out — and the turns it keeps are chosen for being recent, not for being about the question. The rule has no way to represent "this old turn matters."

Note what the counterexamples have in common: both are *references to specific past content* (a figure, a span) rather than to recency. That is exactly the class of request a positional rule cannot express, and it is the motivation for the third selector.
### Selector 2: summarization and compaction  [src selective-context-assembly.md:113]
          - **Policy:** periodically summarize old turns into a running summary; keep only the recent few verbatim.
          - **ADK:** `EventsCompactionConfig` (token threshold + `event_retention_size`, or turn interval + `overlap_size`), with a custom `LlmEventSummarizer`.
          - **Fidelity loss is invisible.** A summary keeps the narrative and drops the specifics — the exact figure, the exact clause, the exact caveat.
          - Fails *case 1*: "the price you quoted earlier" is unresolvable if the summarizer dropped the number.
          - Fails *case 2*: a summary of turns 5–8 is **not** turns 5–8. You cannot "document the discussion" from a summary; documentation requires the discussion.
          narrative (compacted):
            - [bullet] Policy: periodically summarize old turns into a running summary, keeping only the recent few verbatim.
            - [bullet] ADK: EventsCompactionConfig, with a token threshold plus event_retention_size or a turn interval plus overlap_size, and a custom LlmEventSummarizer.
            - [bullet] Fidelity loss is invisible: a summary keeps the narrative and drops the specifics - the exact figure, clause, or caveat.
            - [bullet] Fails case 1: the price quoted earlier stays unresolvable if the summarizer discarded the number.
            - [bullet] Fails case 2: a summary of turns 5-8 is not turns 5-8; documenting the discussion requires the discussion itself.
          prompt: State the summarization policy and its ADK surface with its two strategies. Then explain why "fidelity loss is invisible" is the real objection, using both counterexamples — especially why a summary cannot substitute for the discussion it summarizes.
          reveal: **Policy:** periodically summarize old turns into a running summary; keep only the recent few verbatim.

**ADK surface:** `EventsCompactionConfig` on the `App`, with a token threshold plus `event_retention_size`, or a turn interval plus `overlap_size`, and a custom `LlmEventSummarizer` (optionally on a cheaper dedicated model).

**Why the loss is invisible — and why that is the objection.** A summary keeps the *narrative* and drops the *specifics*: the exact figure, the exact clause, the exact caveat. Nothing errors, and the agent will not flag that it is reasoning from a compacted account. The information is gone without any signal that it is gone.

**Counterexample 1:** "the price you quoted earlier" is unresolvable if the summarizer dropped the number. Retrieval cannot recover what compaction discarded, because the store's surviving representation no longer contains it.

**Counterexample 2 — the sharper one:** a summary of turns 5–8 is **not** turns 5–8. You cannot "document the discussion" from a summary; documentation requires the discussion. This is a *form* mismatch, not a resolution problem: the task demands verbatim fidelity, and the selector's output is a paraphrase by construction.

So the policy's cost is not merely "some detail is lost" — it is that the lost detail is unrecoverable and unmarked, and that some downstream tasks (documentation, exact figures) are incompatible with the form it produces.
### Selector 3: content-based retrieval  [src selective-context-assembly.md:122]
          - **Policy:** keep the full session in an external store; per turn, retrieve *only the turns relevant to the current question* and inject them.
          - **Why it is different:** it answers **"which turns are about X"**, not "which turns are recent." The other two selectors are positional; this one is *semantic*.
          - *Case 1* — resolve "the Kunal Kamra figure" to the turn that stated it, and pull that turn.
          - *Case 2* — resolve two topic anchors to a *span* of turns, and pull that span.
          - **The catch:** relevance is a *judgment*, so this selector cannot be a deterministic rule unless turns are pre-tagged. It needs the machinery in the next section.
          narrative (compacted):
            - [bullet] Policy: keep the full session in an external store and, each turn, retrieve and inject only the turns relevant to the current question.
            - [bullet] Why it differs: it answers which turns are about X, not which turns are recent - semantic where the other two selectors are positional.
            - [bullet] Case 1: resolve the Kunal Kamra figure to the turn that stated it, and pull that turn.
            - [bullet] Case 2: resolve two topic anchors to a span of turns, and pull the span.
            - [bullet] The catch: relevance is a judgment, so this cannot be a deterministic rule unless turns are pre-tagged; it needs the machinery that follows.
          prompt: State the content-based retrieval policy and what makes it a different kind of selector from the first two. Then give both worked cases as what it makes possible, and state the catch that forces it to need the five-step machinery.
          reveal: **Policy:** keep the full session in an external store; per turn, retrieve *only the turns relevant to the current question* and inject them.

**Why it is a different kind of selector:** it answers **"which turns are about X"**, not "which turns are recent." The other two selectors are positional; this one is *semantic*.

**What it makes possible:**

- **Case 1** — resolve "the Kunal Kamra figure" to the turn that stated it, and pull that turn.
- **Case 2** — resolve two topic anchors to a *span* of turns, and pull that span.

Note what these share: both depend on *content* identifying the target. Recency cannot reach a turn-5 figure; a summary has already destroyed the figure. Only a store that kept the turn verbatim, plus a selector that can find it by meaning, answers either request.

**The catch:** relevance is a *judgment*, so this selector cannot be a deterministic rule unless turns are pre-tagged. Recency needs a number; summarization needs a threshold; content-based selection needs something that can decide whether a given turn is about the asked-about thing.

That is why it needs the machinery of the next section — a five-step pipeline: reference resolution (rewrite the user's mention into a query), retrieval over history, span retrieval, relevance/role filtering, and assembly. Each step is a named, separable component, and the first (turning a mention into something searchable) is where the hardest failures live.
## The mechanism, end to end  [src selective-context-assembly.md:133]
        - Content-based selection is not one step. It is a pipeline of five, and each is a named, separable component.
        narrative (compacted):
          - [prose] Content-based selection is not one step but a pipeline of five, each a named, separable component.
        prompt: Content-based selection is a pipeline, not a step. Name all five steps in order. For each, state the problem it solves — and pay special attention to why step 4 needs a role/intent classifier rather than a topic classifier.
        reveal: **Step 1 — reference resolution.** *Problem:* users speak in *mentions*, not queries. "Remember when we discussed the Kunal Kamra YT-Thanks total?" is not a search string; it is a reference. The assembly layer (or a lightweight model) rewrites it into a retrieval query — "Super Thanks total for the Kunal Kamra Naya Bharat video." It is separate because it is coreference/anaphora resolution plus query expansion; without it retrieval has nothing to match on. Hard sub-case: a bare anaphor ("that figure") carries **no content keywords at all**, so step 1 must inject content from context — pure embedding search will fail.

**Step 2 — retrieval over history.** Search the stored turns with the rewritten query and return candidates (case 1: turn 5's agent response). Honestly, it is the same retrieval machinery as RAG, pointed at conversation history instead of a corpus. Scope note: history must include *tool events and intermediate results* — a figure living in a tool result is invisible to a retriever that indexes only prose.

**Step 3 — span retrieval.** Case 2 needs a range, not a hit. Resolve two anchors — the start ("the problem with unions") and the end ("theorized way to structure unions") — and take the turns between. It requires **topic segmentation**: you cannot take the turns between A and B unless you know where each ends. Segmentation is what makes span retrieval possible, and fallible.

**Step 4 — relevance and role filtering.** Inside or around the span, some turns don't belong — the clarification turns 9–10. A filter removes them. **The subtlety:** clarifications are usually *topically close* to the discussion — "what did you mean by X?" *is* about X — so a *topic* filter will not remove them. Exclusion needs a **role/intent classifier**: "is this turn advancing the topic, or asking a clarifying question?" The two ways to get it wrong: include the clarifications (noise), or exclude a substantive turn (**silent omission** — the artifact misses a real part of the discussion and nobody is told).

**Step 5 — assembly.** The selected turns need a *form*: verbatim transcript (fidelity, token cost — required for "document the discussion") or structured summary (topic, decisions, open questions — cheap, lossy, not documentation). It is the compaction ledger applied at selection time, and it belongs in an ADR.
### Step 1: reference resolution  [src selective-context-assembly.md:137]
          - **The problem:** users speak in *mentions*, not queries. "Remember when we discussed the Kunal Kamra YT-Thanks total?" is not a search string — it is a *reference*.
          - **What happens:** a lightweight model (or the assembly layer itself) rewrites the reference into a retrieval query — "Super Thanks total for the Kunal Kamra Naya Bharat video."
          - **Why it is a separate step:** the rewrite is *coreference/anaphora resolution plus query expansion*. Without it, retrieval has nothing to match on.
          - **The hard sub-case:** a bare anaphor — "that figure," "the thing we said" — carries **no content keywords at all**. Step 1 must inject the content from context; pure embedding search will fail on it.
          narrative (compacted):
            - [bullet] The problem: users speak in mentions, not queries - remember when we discussed the Kunal Kamra YT-Thanks total? is a reference, not a search string.
            - [bullet] What happens: a lightweight model, or the assembly layer itself, rewrites the reference into a retrieval query such as the Super Thanks total for the Kunal Kamra Naya Bharat video.
            - [bullet] Why it is separate: the rewrite is coreference and anaphora resolution plus query expansion; without it retrieval has nothing to match on.
            - [bullet] The hard sub-case: a bare anaphor like that figure or the thing we said carries no content keywords, so step 1 must inject content from context; pure embedding search fails on it.
          prompt: A user says "remember when we discussed the Kunal Kamra YT-Thanks total?" Why can't the retrieval layer be handed that utterance as-is, what two operations does step 1 perform on it to produce something retrievable, and with which sub-case does the pipeline fail before retrieval even starts?
          reveal: Users speak in mentions, not queries: the utterance is a reference, not a search string. Step 1 rewrites it into a retrieval query - e.g. "Super Thanks total for the Kunal Kamra Naya Bharat video." That rewrite is two operations stacked: coreference/anaphora resolution (deciding what the mention points at) plus query expansion (supplying the content words that were never actually uttered). It has to be a separate step because without it retrieval has nothing to match on; a lightweight model, or the assembly layer itself, can perform it. The hard sub-case is the bare anaphor - "that figure," "the thing we said" - which carries no content keywords at all. Step 1 must inject the missing content from context, and pure embedding search will fail on it because there is no signal in the string itself.
### Step 2: retrieval over history  [src selective-context-assembly.md:144]
          - **What happens:** search the stored turns by the rewritten query, and return candidate turns (in *case 1*, turn 5's agent response).
          - **What it is, honestly:** the same retrieval machinery as M5's RAG, pointed at **conversation history** instead of a document corpus.
          - **The scope note:** "history" must include *tool events* and *intermediate results*, not just chat text — a figure that lives in a tool result is invisible to a retriever that only indexes prose.
          narrative (compacted):
            - [bullet] What happens: search the stored turns with the rewritten query and return candidate turns - in case 1, turn 5's agent response.
            - [bullet] Honestly: the same retrieval machinery as M5's RAG, pointed at conversation history instead of a document corpus.
            - [bullet] Scope note: history must include tool events and intermediate results, because a figure living in a tool result is invisible to a retriever indexing only prose.
          prompt: Step 2 searches the stored turns with the rewritten query. What is that machinery, honestly speaking, and what must the definition of "history" include that a naive implementation leaves out - and what is the concrete failure when it doesn't?
          reveal: Step 2 runs the rewritten query against the stored turns and returns candidate turns - in case 1, the agent response from turn 5 that stated the figure. It is not new machinery: it is the same retrieval stack as document RAG, retargeted from a document corpus to conversation history. The scope note is the trap. "History" must cover tool events and intermediate results, not only chat text. A figure that lives in a tool result is invisible to a retriever that indexes prose alone, so the turn that answers the question never becomes a candidate - no matter how good the step-1 query was.
### Step 3: span retrieval  [src selective-context-assembly.md:150]
          - **The problem:** *case 2* needs a *range*, not a single hit.
          - **What happens:** resolve two anchors — the start ("the problem with unions") and the end ("theorized way to structure unions") — and take the turns between them.
          - **What it requires:** topic boundaries. You cannot take "the turns between A and B" unless you know where A ends and B ends — that is **topic segmentation**, and it is the step that makes span retrieval possible (and fallible).
          narrative (compacted):
            - [bullet] The problem: case 2 needs a range, not a single hit.
            - [bullet] What happens: resolve both anchors - the start, the problem with unions, and the end, theorized way to structure unions - and take the turns between them.
            - [bullet] What it requires: topic boundaries, since you cannot take the turns between A and B without knowing where each ends; that is topic segmentation, the step that makes span retrieval possible and fallible.
          prompt: Case 2 asks to document a discussion running from one anchor phrase to another. Why is that not answerable by single-hit retrieval, what prerequisite does "take the turns between A and B" impose, and what does that prerequisite simultaneously make of this step?
          reveal: Case 2 needs a range, not a single hit, so step 3 resolves two anchors - the start ("the problem with unions") and the end ("theorized way to structure unions") - and takes the turns between them. The prerequisite is topic boundaries. You cannot take "the turns between A and B" unless you know where A ends and B ends; that is topic segmentation. It is the step that makes span retrieval possible at all, and at the same time what makes it fallible: it is an inference about where topics stop and start, so any boundary error is delivered as a wrong span.
### Step 4: relevance and role filtering  [src selective-context-assembly.md:156]
          - **The problem:** inside (or around) the span, some turns do not belong — the clarification turns 9–10 in *case 2*.
          - **What happens:** a filter removes them.
          - **The subtlety (see the worked case):** clarifications are usually **topically close** to the discussion, so a *topic* filter will not remove them. Exclusion needs a **role/intent classifier** — "is this turn advancing the topic, or asking a clarifying question?" — not a topic classifier.
          narrative (compacted):
            - [bullet] The problem: inside or around the span some turns do not belong - the clarification turns 9-10 in case 2.
            - [bullet] What happens: a filter removes them.
            - [bullet] The subtlety: clarifications are usually topically close to the discussion, so a topic filter keeps them; exclusion needs a role or intent classifier asking whether a turn advances the topic or asks a clarifying question.
          prompt: Inside a retrieved span, some turns do not belong - the clarification turns 9-10 in case 2. Why does the obvious topic-relevance filter fail to remove them, and what kind of signal does exclusion actually require instead?
          reveal: The problem: inside or around the span, some turns do not belong - the clarification turns in case 2 - and a filter removes them. The subtlety is which filter. Clarifications are usually topically close to the discussion, so a topic filter will not remove them: a turn asking "what did you mean by X?" is about X, and topic-based segmentation keeps it in. Exclusion therefore needs a role/intent classifier, not a topic classifier. The question it must answer, evaluated per turn, is "is this turn advancing the topic, or asking a clarifying question?"
### Step 5: assembly  [src selective-context-assembly.md:162]
          - **The problem:** the selected turns must take a *form* before they enter the window.
          - **The two forms, and the tradeoff:**
          - **Verbatim transcript** — fidelity, at token cost. Required for "document the discussion."
          - **Structured summary** (topic, decisions, open questions) — cheap, but lossy. Not documentation.
          - **This is the same ledger as compaction, applied at selection time** — verbatim = faithful and expensive; summary = cheap and lossy — and it belongs in an ADR.
          narrative (compacted):
            - [bullet] The problem: the selected turns must take a form before entering the window.
            - [bullet] The two forms, and the tradeoff:
            - [bullet] Verbatim transcript: fidelity at token cost; required to document the discussion.
            - [bullet] Structured summary (topic, decisions, open questions): cheap but lossy, and not documentation.
            - [bullet] This is the compaction ledger applied at selection time - verbatim is faithful and expensive, summary cheap and lossy - and it belongs in an ADR.
          prompt: Once the right turns are selected, what is still undecided before they enter the window? Name the two forms with their costs - including which one a documentation task forces - and say where this decision belongs.
          reveal: Selection does not finish the job: the selected turns must take a form before entering the window, and there are two. A verbatim transcript buys fidelity at token cost, and it is the required form when the task is "document the discussion." A structured summary - topic, decisions, open questions - is cheap but lossy, and is not documentation. This is the same ledger as compaction, applied at selection time instead of on a schedule: verbatim is faithful and expensive, summary is cheap and lossy. Because it is a genuine policy tradeoff with a use-case dependency, it belongs in an ADR.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart TD
              s[Selected turns] --> v[Verbatim transcript]
              s --> u[Structured summary]
              v --> f[Faithful but expensive]
              u --> l[Cheap but lossy]
            ```
## Worked case 1: a topical reference  [src selective-context-assembly.md:172]
        - *A 10-turn conversation. Turn 11: the user says "hey, how was that Kunal Kamra YT-Thanks total compared to XYZ?" — referring to a figure the agent stated in its turn-5 response.*
        narrative (compacted):
          - [prose] A ten-turn conversation; at turn 11 the user asks how that Kunal Kamra YT-Thanks total compared with XYZ, referring to the figure the agent stated in its turn-5 response.
        prompt: State the worked case 1 setup precisely enough that the five pipeline steps have something to act on: the conversation length, what is said at turn 11, and where the referred figure actually lives.
        reveal: A 10-turn conversation. At turn 11 the user asks "hey, how was that Kunal Kamra YT-Thanks total compared to XYZ?" - a comparative question whose antecedent is a figure the agent stated in its turn-5 response. The load-bearing facts of the setup: the anchor is a topical reference to one specific earlier agent turn, not a request for new work; the figure sits ten turns back in the record; and the current question is a comparison, so answering it requires the original number to be present alongside the new one.
### What happens  [src selective-context-assembly.md:176]
          - **Step 1** — resolve the reference: rewrite into "total Super Thanks for the Kunal Kamra Naya Bharat video."
          - **Step 2** — retrieve: return turn 5 (the agent reply containing the figure).
          - **Steps 3–4** — n/a: a single reference, no span, no exclusion.
          - **Step 5** — assemble: inject turn 5's figure **verbatim** into the window, alongside the current question, so the model can compare it to XYZ.
          - **The naive alternative:** if turn 5 had been compacted into a running summary (or evicted by recency), the figure is gone — and the model either reconstructs it (hallucination) or asks.
          narrative (compacted):
            - [bullet] Step 1 resolves the reference, rewriting it as the total Super Thanks for the Kunal Kamra Naya Bharat video.
            - [bullet] Step 2 retrieves turn 5, the agent reply containing the figure.
            - [bullet] Steps 3-4 do not apply: a single reference means no span and no exclusion.
            - [bullet] Step 5 injects turn 5's figure verbatim beside the current question, letting the model compare it with XYZ.
            - [bullet] The naive alternative: had turn 5 been compacted into a running summary or evicted by recency, the figure is gone and the model hallucinates it or asks.
          prompt: Walk worked case 1 through the pipeline: which steps apply and what does each produce, and what is the naive alternative's failure - what does the model actually do once the turn-5 figure is gone?
          reveal: Step 1 resolves the reference: rewrite into "total Super Thanks for the Kunal Kamra Naya Bharat video." Step 2 retrieves and returns turn 5, the agent reply containing the figure. Steps 3-4 are n/a - a single reference means no span and no exclusion - and that n/a is itself the point: the pipeline is not always five steps. Step 5 assembles: the figure is injected verbatim into the window alongside the current question, so the model can compare it to XYZ. The naive alternative is the contrast case: had turn 5 been compacted into a running summary or evicted by recency, the figure is simply gone - and the model either reconstructs it, i.e. hallucinates, or asks.
### Where it fails  [src selective-context-assembly.md:184]
          - **The reference is a bare anaphor** ("that figure") → step 1 has nothing to search on; retrieval fails before it starts.
          - **Retrieval returns the wrong turn** (a later mention of Kamra, a different video) → the model confidently compares against the wrong figure.
          - **The figure lives in a tool result**, not an agent reply → retrieval that indexes only chat text never finds it.
          narrative (compacted):
            - [bullet] The reference is a bare anaphor such as that figure, leaving step 1 nothing to search on, so retrieval fails before it starts.
            - [bullet] Retrieval returns the wrong turn - a later Kamra mention or a different video - and the model confidently compares against the wrong figure.
            - [bullet] The figure lives in a tool result rather than an agent reply, so retrieval indexing only chat text never finds it.
          prompt: Worked case 1 has three failure modes at three different stages. Name each stage, the failure, and the wrong behavior the user actually sees.
          reveal: Three ways case 1 breaks, each at a different stage. (1) The reference is a bare anaphor - "that figure" - so step 1 has nothing to search on; retrieval fails before it starts. (2) Retrieval returns the wrong turn - a later mention of Kamra, or a different video - and the model confidently compares against the wrong figure. (3) The figure lives in a tool result rather than an agent reply, so retrieval that indexes only chat text never finds it. The shape matters: one failure is upstream of retrieval (nothing to match), one is retrieval precision (a wrong match), one is indexing scope (nothing indexed).
## Worked case 2: span retrieval with exclusions  [src selective-context-assembly.md:192]
        - *Turns 5–8 were a branched discussion ("the problem with unions" → "theorized way to structure unions"). Turns 9–10 were clarifications. The user says: "document the discussion from 'the problem with unions' to 'theorized way to structure unions' — skip the clarification questions."*
        narrative (compacted):
          - [prose] Turns 5-8 were a branched discussion running from the problem with unions to the theorized way to structure unions; turns 9-10 were clarifications. The user asks to document that discussion while skipping the clarification questions.
        prompt: State the worked case 2 setup: the shape of turns 5-8, what turns 9-10 were, and what the user's instruction asks for - including the element that is neither a start nor an end anchor.
        reveal: Turns 5-8 were a branched discussion running from "the problem with unions" to "theorized way to structure unions." Turns 9-10 were clarifications. The user's instruction is: "document the discussion from 'the problem with unions' to 'theorized way to structure unions' - skip the clarification questions." Two things make it harder than case 1: the target is a range defined by two anchor phrases rather than a single turn, and the instruction carries a third element that is neither anchor - an exclusion clause naming a category of turn the user expects to be dropped.
### Decomposition  [src selective-context-assembly.md:196]
          - **Step 1** — two anchors, two queries: "the problem with unions" (start) and "theorized way to structure unions" (end).
          - **Step 2** — locate the start turn and the end turn.
          - **Step 3** — span retrieval: take the turns between the two anchors.
          - **Step 4** — role filtering: exclude 9–10 because they are clarifications, *not* because they are off-topic.
          - **Step 5** — assemble a verbatim transcript of 5–8, then hand it to the documentation task.
          narrative (compacted):
            - [bullet] Step 1: two anchors become two queries - the problem with unions for the start, theorized way to structure unions for the end.
            - [bullet] Step 2: locate the start turn and the end turn.
            - [bullet] Step 3: span retrieval takes the turns between the two anchors.
            - [bullet] Step 4: role filtering excludes 9-10 as clarifications, not as off-topic content.
            - [bullet] Step 5: assemble a verbatim transcript of 5-8 and hand it to the documentation task.
          prompt: Decompose worked case 2 across the five steps - what each takes and produces - and be precise both about the reason step 4 excludes turns 9-10 and about the form step 5 produces.
          reveal: Step 1 - two anchors become two queries: "the problem with unions" (start) and "theorized way to structure unions" (end). Step 2 - locate the start turn and the end turn. Step 3 - span retrieval: take the turns between the two anchors. Step 4 - role filtering: exclude 9-10 because they are clarifications, not because they are off-topic; that distinction is the whole subtlety, since an off-topic justification would not hold for turns that are semantically close to the topic. Step 5 - assemble a verbatim transcript of 5-8, then hand it to the documentation task. The output form is forced by the task: documentation needs the discussion itself, which a summary is not.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart LR
              a[Two anchors] --> b[Locate start and end]
              b --> c[Take the span]
              c --> d[Exclude clarifications]
              d --> e[Verbatim transcript]
            ```
### The clarification-exclusion subtlety  [src selective-context-assembly.md:204]
          - **Why a topic filter fails:** clarifications are semantically *close* to the topic — "what did you mean by X?" *is* about X. Topic-based segmentation will keep them in.
          - **What you actually need:** a **role/intent signal** — "is this turn advancing the topic, or asking a clarifying question?" — evaluated per turn.
          - **How it is done:** a small classifier, or an LLM-as-judge pass, over each turn in the span.
          - **The two ways to get it wrong:**
          - Include the clarifications → noise in the documentation.
          - Exclude a substantive turn → **silent omission** — the documentation is missing a real part of the discussion, and no one is told.
          narrative (compacted):
            - [bullet] A topic filter fails because clarifications sit semantically close to the topic - what did you mean by X? is about X - so topic segmentation keeps them in.
            - [bullet] What you need instead is a per-turn role or intent signal: is this turn advancing the topic, or asking a clarifying question?
            - [bullet] How it is done: a small classifier, or an LLM-as-judge pass, over every turn in the span.
            - [bullet] The two ways to get it wrong:
            - [bullet] Including the clarifications puts noise into the documentation.
            - [bullet] Excluding a substantive turn is a silent omission - the documentation loses a real part of the discussion and nobody is told.
          prompt: Why does a topic-based filter keep clarification turns inside a span you are trying to exclude them from, what signal replaces it and how is that signal evaluated, and what are the two ways this exclusion step goes wrong?
          reveal: A topic filter fails because clarifications are semantically close to their topic: "what did you mean by X?" is about X, so topic-based segmentation keeps them in. What is actually needed is a role/intent signal - "is this turn advancing the topic, or asking a clarifying question?" - evaluated per turn, implemented as a small classifier or an LLM-as-judge pass over each turn in the span. The step errs in two directions: include the clarifications and the documentation carries noise; exclude a substantive turn and you get silent omission - a real part of the discussion is missing from the documentation and no one is told.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart TD
              c[Clarification turn] --> t[Topic filter keeps it]
              c --> i[Intent filter excludes it]
              i --> s[Silent omission if wrong]
            ```
## Is this legitimate: the named architecture  [src selective-context-assembly.md:215]
        - Yes. This is not a hypothetical mechanism; it is the **dominant long-term-memory architecture** for agents, with a formal name and production implementations.
        narrative (compacted):
          - [prose] Legitimate: this is the dominant long-term memory architecture for agents — formally named and shipped in production, not hypothetical.
        prompt: What claim does this section make about content-based selection - is it hypothetical, how established is it, and on what two kinds of backing does the claim rest?
        reveal: The claim is a flat yes: content-based selection is not a hypothetical mechanism. It is the dominant long-term-memory architecture for agents, and it is established on two fronts - it has a formal name, and it has production implementations, the specific ones named in the subsections that follow (MemGPT/Letta, Zep, and the rest of the field). The precise assertion matters: not that some system somewhere does something like this, but that it is the dominant architecture, with formal naming and shipped and peer-reviewed implementations behind it.
### MemGPT and Letta: virtual context management  [src selective-context-assembly.md:219]
          - **The idea:** a fixed *main context* (the window) plus an *external context* (the full history), and a *memory manager* that **pages relevant data in and out each turn**.
          - **Why it matters here:** this is literally "not everything goes into the window; an assembly layer pulls the relevant subset" — formalized and peer-reviewed.
          - **Provenance:** [MemGPT: Towards LLMs as Operating Systems](https://arxiv.org/abs/2310.08560), ICLR 2024. The project is now **Letta**, and it ships in production.
          narrative (compacted):
            - [bullet] Idea: a fixed main context (the window) beside an external context (full history), with a memory manager paging relevant data in and out per turn.
            - [bullet] Relevance here: it formalizes, peer-reviewed, the rule that an assembly layer pulls only the relevant subset into the window.
            - [bullet] Provenance: the MemGPT paper (ICLR 2024); the project is now Letta and ships in production.
          prompt: State MemGPT's virtual context management idea as a structure - the two contexts and what the manager does each turn - and explain why that counts as the same claim as an assembly layer rather than a different one.
          reveal: MemGPT formalizes it as virtual context management: a fixed main context (the window) plus an external context (the full history), with a memory manager that pages relevant data in and out each turn. That is the same claim as an assembly layer stated in operating-system terms - not everything goes into the window, and a layer pulls the relevant subset per turn - except here it is formalized and peer-reviewed rather than merely argued. Provenance: "MemGPT: Towards LLMs as Operating Systems," ICLR 2024; the project is now Letta and ships in production. The paging structure, not the specific system, is the load-bearing part.
          [diagram] mermaid (agent-authored):
            ```mermaid
            flowchart LR
              a[External context] --> b[Memory manager pages turns]
              b --> c[Main context window]
            ```
### Zep: temporal knowledge graph and per-turn tagging  [src selective-context-assembly.md:225]
          - **The idea:** store conversation turns in a temporal knowledge graph; **summarize and tag each turn with topic labels**; retrieve by semantic, temporal, and factual query.
          - **Why it matters here:** the per-turn tagging is exactly the machinery *case 2* needs to find topic boundaries and build a span.
          - **Provenance:** [Zep: A Temporal Knowledge Graph Architecture for Agent Memory](https://arxiv.org/abs/2501.13956); product docs at [help.getzep.com](https://help.getzep.com/langgraph-memory).
          narrative (compacted):
            - [bullet] Idea: conversation turns stored in a temporal knowledge graph, each summarized and tagged with topic labels, retrieved by semantic, temporal, or factual query.
            - [bullet] Relevance: per-turn tagging is the machinery case 2 requires to locate topic boundaries and build a span.
            - [bullet] Provenance: the Zep paper (arXiv 2501.13956) and its product documentation at help.getzep.com.
          prompt: What does Zep store turns in and annotate them with, what three axes does it retrieve along, and which one of its design choices is the direct answer to worked case 2's boundary problem?
          reveal: Zep stores conversation turns in a temporal knowledge graph and - the operative part - summarizes and tags each turn with topic labels. Retrieval runs along three axes: semantic, temporal, and factual. The per-turn tagging is exactly the machinery case 2 needs: a span is only definable once topic boundaries are known, and tagging turns with topic labels up front is what makes those boundaries locatable instead of inferred at query time. Provenance: "Zep: A Temporal Knowledge Graph Architecture for Agent Memory," with product documentation at help.getzep.com.
### The rest of the field  [src selective-context-assembly.md:231]
          - **Mem0** — extracts and retrieves relevant memories per turn ([Zep vs Mem0 comparison](https://mem0.ai/blog/zep-vs-mem0-which-ai-memory-layer-should-you-choose)).
          - **LangMem**, **LangChain's vector-store memory**, **OpenAI's memory feature**, and [Elastic's agent-memory guide](https://www.elastic.co/search-labs/blog/ai-agent-memory-management-elasticsearch) — all "persist everything, retrieve the relevant slice per turn."
          - **LazyMem** — [*Retrieve Broadly, Construct Selectively*](https://arxiv.org/abs/2607.22690): retrieve a broad candidate set from history, then *construct* the window selectively. Your assembly layer in one title.
          - **The surveys** — [A Survey on the Memory Mechanism of LLM-based Agents (ACM TOIS)](https://dl.acm.org/doi/10.1145/3748302) and [Memory for Autonomous LLM Agents](https://ar5iv.labs.arxiv.org/html/2603.07670) — both taxonomize it as **full-window / summarization / retrieval-over-history / hybrid**.
          - **Verdict:** the architecture is settled and standard. Content-based retrieval over conversation history is legitimate, mainstream, and productized.
          narrative (compacted):
            - [bullet] Mem0 extracts and retrieves relevant memories each turn, per a Zep-versus-Mem0 comparison.
            - [bullet] Same shape across LangMem, LangChain's vector-store memory, OpenAI's memory feature and Elastic's agent-memory guide: retain it all, fetch the pertinent slice each turn.
            - [bullet] LazyMem's Retrieve Broadly, Construct Selectively — gather many history candidates, then build the window with a chosen subset; the assembly layer compressed into a title.
            - [bullet] Two surveys (ACM TOIS agent-memory taxonomy; Memory for Autonomous LLM Agents) classify approaches as full-window, summarization, retrieval-over-history, or hybrid.
            - [prose] Verdict: architecture settled, implementation standard. Pulling relevant history by content is accepted practice, mainstream and shipping in products today.
          prompt: Beyond MemGPT and Zep, what do the remaining systems have in common, what taxonomy do the surveys use for memory mechanisms, and what verdict does the section draw?
          reveal: Mem0 extracts and retrieves relevant memories per turn; LangMem, LangChain's vector-store memory, OpenAI's memory feature, and Elastic's agent-memory guidance all land on the same one-line policy - persist everything, retrieve the relevant slice per turn. LazyMem states it in a subtitle: "Retrieve Broadly, Construct Selectively" - pull a broad candidate set from history, then construct the window selectively, which is the assembly layer in one title. The two surveys taxonomize the space as full-window / summarization / retrieval-over-history / hybrid. Verdict: the architecture is settled and standard - content-based retrieval over conversation history is legitimate, mainstream, and productized.
          [diagram] mermaid (agent-authored):
            ```mermaid
            mindmap
              s[Survey taxonomy]
                a[Full window]
                b[Summarization]
                c[Retrieval over history]
                d[Hybrid]
            ```
## Is it valid: the active-research frontier  [src selective-context-assembly.md:242]
        - "Legitimate" and "solved" are different things. The *architecture* is settled; the *quality* of the semantic-selection edge is not — and that edge is exactly your two cases.
        narrative (compacted):
          - [prose] Legitimate is not solved: the architecture is settled, but semantic-selection quality is not — and that edge is precisely the two cases at hand.
        prompt: This section separates two words that are easy to conflate. Which two, what exactly is settled and what is not, and what does the unsettled part have to do with the two worked cases?
        reveal: Legitimate and solved are different things. What is settled is the architecture - content-based retrieval over history is standard and productized. What is not settled is the quality of the semantic-selection edge: resolving a semantic reference to the right turns, spanning a range between two anchors, and excluding the right turns. That edge is exactly the two worked cases, which is why they are presented as the sharp part of a working mechanism rather than as exotic corners. The honest reading: the design decision is safe, the accuracy of the selection is not.
### The recall bottleneck  [src selective-context-assembly.md:246]
          - **What it is:** retrieval only works as well as (a) the query produced in step 1, and (b) the stored representation of the turns.
          - **The evidence:** the surveys and system papers consistently name **recall** — getting the *right* turn back — as the limiting factor, not the generation.
          narrative (compacted):
            - [bullet] What it is: retrieval quality is capped by both the step-1 query and how the turns were stored.
            - [bullet] Evidence: surveys and system papers consistently name recall — returning the right turn — as the limiting factor, not generation.
          prompt: What does this section name as the limiting factor in content-based selection, what two upstream things does that factor depend on, and what does the evidence say it is *not*?
          reveal: The bottleneck is recall - getting the right turn back. Retrieval only works as well as (a) the query produced in step 1 and (b) the stored representation of the turns; both are upstream artifacts, so even a perfect retriever fails on a bad query or a lossy index. The evidence: surveys and system papers consistently name recall as the limiting factor, not the generation. That inversion is the load-bearing part - the failure people expect from an LLM (bad synthesis) is not where these systems report their weakness; the weakness is in what never made it into the window.
### Topic segmentation is imperfect  [src selective-context-assembly.md:251]
          - **What it is:** dividing a conversation into topic segments is itself error-prone; boundaries drift, and a turn can belong to two topics at once.
          - **The evidence:** dialogue topic segmentation is a standing research problem — see [ACL Anthology 2021.emnlp-main.498](https://aclanthology.org/2021.emnlp-main.498.pdf).
          narrative (compacted):
            - [bullet] What it is: splitting conversation into topic segments is error-prone — boundaries drift, and a turn may belong to two topics.
            - [bullet] Evidence: dialogue topic segmentation remains an open research problem (ACL Anthology 2021.emnlp-main.498).
          prompt: Why is topic segmentation an error-prone operation rather than a preprocessing detail? Describe the two concrete ways boundaries misbehave, and what status the section gives the problem.
          reveal: Dividing a conversation into topic segments is itself error-prone. Two concrete failure shapes: boundaries drift - the point where a topic is declared to end does not match where it actually ends - and a single turn can belong to two topics at once, so no boundary placement is uniquely correct. This bears directly on span retrieval, which needs to know where anchor A ends and anchor B ends. The section gives dialogue topic segmentation the status of a standing research problem, citing it as such rather than as a solved preprocessing step.
### Bare references defeat keyword search  [src selective-context-assembly.md:256]
          - **What it is:** "that figure" or "the thing we said" carry no content keywords; retrieval over raw embeddings has nothing to match.
          - **The fix:** step 1 must resolve the reference into content *before* retrieval — coreference/anaphora resolution, then query expansion.
          - **The evidence:** [SeCom: On Memory Construction and Retrieval for Personalized Conversational Agents](https://iclr.cc/virtual/2025/poster/27790), ICLR 2025, is precisely this problem.
          narrative (compacted):
            - [bullet] What it is: phrases like that figure or the thing we said carry no keywords, leaving raw-embedding retrieval nothing to match.
            - [bullet] The fix: resolve references into content before retrieval — coreference or anaphora resolution first, then query expansion.
            - [bullet] Evidence: SeCom (ICLR 2025) addresses exactly this problem.
          prompt: Why do bare references such as "that figure" or "the thing we said" break retrieval over raw embeddings, and what is the prescribed fix including its ordering? What is cited as evidence that this is a real research problem?
          reveal: Bare references carry no content keywords - "that figure" or "the thing we said" gives a retriever nothing to match against, so retrieval over raw embeddings has nothing to work with. The fix is an ordering, not a better embedder: step 1 must resolve the reference into content before retrieval runs - coreference/anaphora resolution first, then query expansion - so the search string actually contains the topic the mention silently pointed at. The evidence cited is SeCom (ICLR 2025), on memory construction and retrieval for personalized conversational agents, presented as precisely this problem.
### What the recent papers are still working on  [src selective-context-assembly.md:262]
          - **TRACE-Memory** — [*Public-Conditioned Retrieval and Utility-Aware Evidence Admission*](https://arxiv.org/html/2608.08446v2) — gates *what gets admitted* to the window by utility, i.e. relevance filtering with a rejection mechanism.
          - **LazyMem** — [*Retrieve Broadly, Construct Selectively*](https://arxiv.org/abs/2607.22690) — still refining the retrieve-then-construct split.
          - **The through-line:** 2025–2026 preprints are still working on the selection *quality*, not the architecture. That is the honest signal that this edge is active, not settled.
          narrative (compacted):
            - [bullet] TRACE-Memory gates window admission on utility — relevance filtering with an explicit rejection mechanism.
            - [bullet] LazyMem (Retrieve Broadly, Construct Selectively) keeps refining the retrieve-then-construct split.
            - [bullet] Through-line: 2025–2026 preprints still target selection quality, not architecture — honest evidence that this edge is active rather than settled.
          prompt: What does each of the two recent papers work on, and what does the section read as the through-line? How does that through-line differ from a claim that the problem is solved?
          reveal: TRACE-Memory - "Public-Conditioned Retrieval and Utility-Aware Evidence Admission" - gates what gets admitted to the window by utility: relevance filtering with a rejection mechanism, i.e. the right to refuse evidence. LazyMem - "Retrieve Broadly, Construct Selectively" - keeps refining the retrieve-then-construct split, the boundary between collecting candidates and constructing the window. The through-line: 2025-2026 preprints are still working on selection quality, not on the architecture. The section reads that as the honest signal that this edge is active rather than settled - a genuinely solved problem stops attracting papers about its accuracy.
## The honest engineering bottom line  [src selective-context-assembly.md:270]
        - (checklist: empty)
### Build vs buy  [src selective-context-assembly.md:272]
          - **Step 1 (reference → query rewrite):** a small model call; cheap to do yourself, or the default in a memory layer. **Build or buy — it is not exotic.**
          - **Steps 2–3 (retrieval and span):** mature; **buy** (Zep, Mem0, LangMem) or build on a vector store.
          - **Step 4 (role/intent filtering for exclusions):** usually **custom** — it is domain-specific ("what counts as a clarification here?"). Plan to build.
          - **Step 5 (form):** a **policy decision** — verbatim vs. summary — recorded in an ADR.
          narrative (compacted):
            - [bullet] Step 1 (reference to query rewrite): one small model call, cheap to build or default in a memory layer — build or buy, nothing exotic.
            - [bullet] Steps 2–3 (retrieval, span): mature — buy from Zep, Mem0 or LangMem, or build on a vector store.
            - [bullet] Step 4 (role and intent filtering for exclusions): normally custom, since what counts as a clarification here is domain-specific — plan to build.
            - [bullet] Step 5 (form): a policy choice between verbatim and summary, recorded in an ADR.
          prompt: For the five-step selective-context-assembly pipeline (reference-to-query rewrite; retrieval; span retrieval; role/intent filtering for exclusions; form selection), state for each step whether to build or buy and why — and identify which step is not a technology question at all.
          reveal: Five steps, with the build/buy call per step:

1. Reference to query rewrite — a small model call. Cheap enough to do yourself, or it is a memory layer's default. Neither exotic nor a differentiator: build or buy.
2. Retrieval and 3. span/segment selection — mature. Buy (Zep, Mem0, LangMem) or build on a vector store; do not expect an advantage here.
4. Role/intent filtering that decides exclusions — usually custom. It is domain-specific ("what counts as a clarification here?"), so plan to build.
5. Form — verbatim vs. summary is not a technology question. It is a policy decision, recorded in an ADR.

The shape: the mature middle is bought, the two ends are yours. The front (a cheap model call) is trivially either; the back (exclusion rules and the fidelity policy) cannot be bought, because it encodes your domain's judgement and the loss you are willing to accept.
          [diagram] mermaid (agent-authored):
            ```mermaid
            mindmap
              s[Five steps]
                a[Step 1 build or buy]
                b[Steps 2-3 buy]
                c[Step 4 build custom]
                d[Step 5 ADR policy]
            ```
### What you will still be tuning in production  [src selective-context-assembly.md:279]
          - **Recall on bare references** ("that figure").
          - **Topic-segmentation boundaries** for span cases.
          - **The exclusion classifier's precision** — the cost of wrongly *including* a clarification is noise; the cost of wrongly *excluding* a substantive turn is silent omission.
          - **The verbatim-vs-summary fidelity decision**, per use case.
          - **The one-line takeaway:** session state is the truth; the window is a decision; content-based selection is the third selector — real, mainstream, and productized. But its sharp edge — semantic reference, span retrieval, and exclusion — is a place you *tune*, not a checkbox.
          narrative (compacted):
            - [bullet] Recall over bare references such as that figure.
            - [bullet] Topic-segmentation boundaries in span cases.
            - [bullet] The exclusion classifier's precision: wrongly including a clarification adds noise; wrongly excluding a substantive turn causes silent omission.
            - [bullet] The verbatim-versus-summary fidelity choice, decided per use case.
            - [prose] Takeaway: session state is truth, the window a choice, content-based selection the third selector — real and productized, but its sharp edge is tuned, not ticked off.
          prompt: Name the four things the module says you will still be tuning in production, and explain why the exclusion classifier's two error types are not symmetric in cost.
          reveal: Four tuning surfaces, all on the sharp edge of content-based selection rather than on the plumbing:

- Recall on bare references — resolving "that figure" to the right turn.
- Topic-segmentation boundaries — where a span starts and stops.
- The exclusion classifier's precision — and this one is asymmetric. Wrongly *including* a clarification costs noise in the window. Wrongly *excluding* a substantive turn is silent omission: a gap nothing announces.
- The verbatim-vs-summary fidelity decision — re-decided per use case.

Takeaway: session state is the truth; the window is a per-turn decision; content-based selection is a third selector alongside the positional dials — real, mainstream, productized. But its sharp edge — semantic reference, span retrieval, exclusion — is a place you tune, not a checkbox you tick.
## Sources  [src selective-context-assembly.md:290]
        - (checklist: empty)
### Core references  [src selective-context-assembly.md:292]
          - (checklist: empty)
### Recent preprints and supplementary  [src selective-context-assembly.md:303]
          - (checklist: empty)
## Worked example: the research agent, budgeted  [src README.md:587]
    - The domain spine, made concrete. A research agent runs a three-hour session over a corpus. Here's what actually accumulates, and how a designed context budget handles it:
    - **Stable prefix (~4k tokens):** system instructions ("cite every claim; if evidence is absent, say so"), tool definitions, output format. *Cacheable — sent once, reused all session.*[adk-context-caching](#adk-context-caching), [anthropic-prompt-caching](#anthropic-prompt-caching)
    - **Per-turn retrieval (~2–4k):** the top chunks for *this* question. *Fresh each turn; evicted after use.*
    - **Tool results (variable):** a `fetch_paper` tool returns 8k tokens of full text; the harness keeps the abstract + relevant excerpt (~500 tokens) and stores the full text as an artifact. *Verbose output truncated at the seam.*[gan-rag-mcp](#gan-rag-mcp), [ding-mcp-performance](#ding-mcp-performance)
    - **Conversation history:** compacted every ~6 turns into a running research-progress summary; the last 4 turns kept verbatim. *History costs stay flat instead of growing linearly.*[adk-context-compaction](#adk-context-compaction)
    - **Scratchpad:** the agent's intermediate reasoning, *not* persisted into the window across turns — kept in working memory (M7) or regenerated when needed.
    - The result: at hour three, the window is ~10–12k tokens — not 90k — the current question sits at the end (recency), the policy sits at the start (primacy), and the three-hours-ago question is answered just as well as it was in minute one.[shaier-context-before-question](#shaier-context-before-question), [hsieh-ruler](#hsieh-ruler) **The agent didn't get dumber, because the window never got fat.**[hsieh-ruler](#hsieh-ruler)
    - **Tradeoff (the ledger entry):** every budget mechanism costs *something*. Truncating tool output can drop a detail the next turn needs.[unsupported](#unsupported) Compacting history loses fidelity.[adk-context-compaction](#adk-context-compaction), [liu-lost-in-the-middle](#liu-lost-in-the-middle) A per-turn budget can force an eviction that was load-bearing. The discipline is not "keep the window small"; it is **"make each eviction and each compaction a named decision, with its cost written down"** — because the failure you're preventing (attention collapse, cost blowup) is invisible until it's catastrophic,[anthropic-prompting-best-practices](#anthropic-prompting-best-practices) while the failure you're causing (a dropped detail) is visible only much later, if ever.[unsupported](#unsupported)
    narrative (compacted):
      - [prose] The domain spine made concrete: a research agent's three-hour corpus session, and how a designed context budget absorbs what accumulates.
      - [bullet] Stable prefix (~4k): system instructions, tool definitions and output format — cached, sent once and reused for the whole session.
      - [bullet] Per-turn retrieval (~2–4k): the top chunks for the current question, fresh each turn and evicted once used.
      - [bullet] Tool results (variable): a fetch_paper call returns 8k tokens; the harness keeps abstract plus excerpt (~500) and truncates at the seam.
      - [bullet] Conversation history: compacted roughly every six turns into a running progress summary, last four turns verbatim, so history cost stays flat.
      - [bullet] Scratchpad: intermediate reasoning is not persisted across turns — held in working memory (M7) or regenerated when needed.
      - [prose] Result: at hour three the window sits at ~10–12k, not 90k — question last, policy first, early questions answered as well as new; it never got fat.
      - [prose] Tradeoff: truncation can drop needed detail, compaction loses fidelity, and budgets force load-bearing evictions — so make every eviction a named decision with its cost written down.
    prompt: In the budgeted three-hour research agent, name each of the five window components and the specific budget mechanism applied to it. Then state what the discipline actually is — and why the two failure directions have different visibility.
    reveal: Five accumulators and the mechanism each gets:

- Stable prefix (~4k): system instructions, tool definitions, output format — cacheable, sent once, reused all session.
- Per-turn retrieval (~2-4k): top chunks for *this* question only — fresh each turn, evicted after use.
- Tool results (variable): an 8k-token `fetch_paper` dump is truncated at the seam to abstract + relevant excerpt (~500 tokens); the full text is stored as an artifact.
- Conversation history: compacted every ~6 turns into a running research-progress summary, last 4 turns kept verbatim — cost stays flat instead of growing linearly.
- Scratchpad: intermediate reasoning is kept out of the window — held in working memory or regenerated when needed.

Result at hour three: ~10-12k, not 90k; current question last (recency), policy first (primacy).

The discipline is not "keep the window small". It is making every eviction and every compaction a named decision with its cost written down — because the two failure directions differ in visibility. The failure you are preventing (attention collapse, cost blowup) is invisible until catastrophic; the failure you are causing (a dropped detail) surfaces much later, if ever. Truncation can drop the detail the next turn needs, compaction loses fidelity, and a per-turn budget can force a load-bearing eviction.
    [diagram] mermaid (agent-authored):
      ```mermaid
      flowchart TD
        a[Stable prefix about 4k] --> b[Per-turn retrieval 2-4k]
        b --> c[Tool excerpt about 500]
        c --> d[Summary plus recent turns]
        d --> e[Window stays 10-12k]
      ```
## Design exercise  [src README.md:603]
    - *Paper-based. Think, then write.*
    - **Task.** Design the context budget for a three-hour research session, as in the worked example — but for **your own** agent (or choose a support agent over a 2,000-document knowledge base).
    - 1. **Draw the anatomy.** List the five window components (instructions, tool definitions, retrieved material, history, intermediate results) and, for each: your target token size, and whether it's *stable* or *variable*.
    - 2. **Order it.** Write the assembly order — what goes first, what goes last, what goes in the marked middle block — and justify it in one sentence against position bias.[shaier-context-before-question](#shaier-context-before-question), [ok-prompt-order](#ok-prompt-order), [liu-lost-in-the-middle](#liu-lost-in-the-middle)
    - 3. **Format it, then test it.** Write the markup for your marked middle block, and name the model you will A/B it on — because delimiter and markup choices move accuracy in *both* directions.[he-prompt-formatting](#he-prompt-formatting), [zhao-calibrate-before-use](#zhao-calibrate-before-use)
    - 4. **Set the dials.** State your per-turn budget (Dial 1), your eviction order (Dial 2, with the two things you'll never evict),[own-synthesis](#own-synthesis) and your compaction settings (Dial 3: token threshold + retention, or interval + overlap — pick one and justify).[adk-context-compaction](#adk-context-compaction)
    - 5. **Name the loss you're accepting.** For your compaction choice, write the single most dangerous thing that could be summarized away, and one sentence about how you'd mitigate it. Be specific about the field type: the measured failure mode is temporal and quantitative detail, so a rule of the form "preserve dates, times, and quantities verbatim" is better targeted than a vague "keep the important bits."[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent)
    - 6. **Write the ADR.** Record the whole thing as a five-field ADR — "Context budget for the research agent" — with the consequence you're accepting stated explicitly.
    - **Why this exercise matters.** This is the first module where the deliverable is a *budget with a written rationale* rather than a piece of code. The instinct you're building — *name every component, order it deliberately, budget it, and record what the budget costs* — is the same instinct you'll apply to tools (M8), orchestration (M10), and evals (M12). Context is just the first place you practice it.
    - **In DSH:** prompt assembly is `core/system-prompt` (composable prompt sections + tool schemas), with `context`/`compaction` owning the budget and compaction, and bundled MCP tool definitions inflating token usage by default[ding-mcp-performance](#ding-mcp-performance) — governed by the invariant *"model-visible means logged"* (everything the model sees must be reconstructable from the session log).
    narrative (compacted):
      - [prose] Paper-based: think first, then write it down.
      - [prose] Task: mirror the worked example's three-hour session budget, applied to your own agent — or to a support agent over a 2,000-document knowledge base.
      - [prose] 1. Draw the anatomy: list the five components (instructions, tool definitions, retrieved material, history, intermediate results), giving each a target token size and a stable or variable label.
      - [prose] 2. Order it: state what goes first, last and in the marked middle, justifying the order in one sentence against position bias.
      - [prose] 3. Format then test: write the marked middle block's markup and name the model for A/B testing, since delimiting choices move accuracy either way.
      - [prose] 4. Set the dials: per-turn budget (Dial 1), eviction order with two never-evicted items (Dial 2), and one justified compaction setting (Dial 3).
      - [prose] 5. Name the accepted loss: the most dangerous thing compaction could drop, plus a mitigation — targeted as preserve dates, times and quantities verbatim rather than vague importance.
      - [prose] 6. Write the ADR: a five-field record titled Context budget for the research agent, stating the accepted consequence explicitly.
      - [prose] Why it matters: the first deliverable that is a budget with rationale, not code — naming, ordering, budgeting and costing components recurs in tools (M8), orchestration (M10) and evals (M12).
      - [prose] In DSH: prompt assembly lives in core/system-prompt, context/compaction owns budget and compaction, bundled MCP tool definitions inflate tokens by default, under the invariant model-visible means logged.
    prompt: The design exercise asks for six deliverables. State them, and give the specific reason its loss-naming step demands a field-type-specific preservation rule rather than "keep the important bits".
    reveal: Six deliverables:

1. Anatomy — the five components (instructions, tool definitions, retrieved material, history, intermediate results), each with a target token size and a stable/variable label.
2. Order — the assembly order: what goes first, what goes last, what sits in the marked middle block, justified in one sentence against position bias.
3. Format, then test — the markup for the marked middle block, plus the named model you will A/B it on, because delimiter and markup choices move accuracy in both directions.
4. Dials — per-turn budget (Dial 1); eviction order with the two things never evicted (Dial 2); compaction settings (Dial 3: token threshold + retention, or interval + overlap — pick one and justify).
5. The accepted loss — the single most dangerous thing compaction could summarize away, plus a mitigation sentence.
6. A five-field ADR naming the consequence accepted explicitly.

Step 5 is field-type-specific because the measured failure mode is temporal and quantitative detail. "Preserve dates, times and quantities verbatim" targets the actual loss; "keep the important bits" does not.

Why it matters: the deliverable is a budget with a written rationale, not code — name every component, order it deliberately, budget it, record what the budget costs. The same instinct recurs for tools (M8), orchestration (M10) and evals (M12).

DSH mapping: assembly in `core/system-prompt`; budget and compaction in `context`/`compaction`; bundled MCP tool definitions inflate tokens by default; governed by "model-visible means logged".
## Where the literature disagrees with this module  [src README.md:624]
    - The claims above are not uniformly settled. Several are contested in print, a few are asserted here more strongly than the sources support, and one is empirically backwards. The sharpest disagreement is about the *central* claim of the module. Recording these is the same discipline this module teaches for budgets — apply it to the module itself.
    narrative (compacted):
      - [prose] Not settled: several claims are contested in print, some overreach their sources, one is empirically backwards, and the sharpest dispute concerns the module's central claim.
    prompt: The "Where the literature disagrees" section grades its disagreements rather than listing them. State the grades it names, which claim carries the sharpest disagreement, and the meta-argument for why the section exists at all.
    reveal: The section grades rather than lists: several claims are contested in print, a few are asserted in the module more strongly than the sources support, and one is empirically backwards. The sharpest disagreement concerns the module's *central* claim.

The meta-argument: recording disagreements about the module is the same discipline the module teaches for budgets — apply it to the module itself.

The eleven it then enumerates:
1. Lost-in-the-middle is genuinely contested, not settled.
2. The module's premise has its strongest support from a source it does not cite (length alone hurts).
3. "Formatting is information" is the weakest design claim — format sensitivity is not established as reliably positive.
4. Tool-schema bloat has two mechanisms, and the module names only the one that bites under pressure.
5. System instructions do not reliably outrank later text, and compaction is documented to lose them.
6. "A naive summarizer keeps the narrative and drops the specifics" is backwards — gist keeps narrative and entities, drops time and quantities.
7. Compression is not uniformly lossy — what is compressed is what matters.
8. "The agent will not tell you it is reasoning from lossy memory" restates as a harness observability gap.
9. The cost claim rests on complexity and serving arguments, not measured NLP latency.
10. Keep-the-window-small has a counter-position the module never names.
11. Framework claims verified against the ADK docs, with three corrections.
### 1. The "lost in the middle" effect is genuinely contested  [src README.md:628]
      - This is not a minor quibble: the module's core mechanism ("facts in the middle go to die") is the one claim on which the literature most visibly splits. Present it as contested, not settled.
      - The original result is real but carefully hedged: performance "can degrade" and is "often highest" when relevant information occurs "at the beginning or end," on two synthetic retrieval tasks.[liu-lost-in-the-middle](#liu-lost-in-the-middle)
      - A follow-up attributes the pattern to attention rather than relevance — models "exhibit a U-shaped attention bias where the tokens at the beginning and at the end of its input receive higher attention, **regardless of their relevance**." That clause is what makes the causation positional.[hsieh-found-in-the-middle](#hsieh-found-in-the-middle)
      - *How Hsieh actually measured attention and derived the calibration → [found-in-the-middle.md](paper-details/found-in-the-middle.md).*
      - Independent of position, effective context falls well short of advertised context: across 17 long-context models all claiming ≥32K, "only half of them can maintain satisfactory performance at the length of 32K."[hsieh-ruler](#hsieh-ruler)
      - The effect is strongest only up to ~50% of a model's context window; beyond that, primacy weakens while recency holds, and "this effectively eliminates the LiM effect," leaving a distance-from-end bias instead.[veseli-positional-biases](#veseli-positional-biases)
      - **The measurement may be an artifact.** In summarization, prior position-bias studies "rely heavily on n-gram matching techniques, which fail to capture semantic relationships in abstractive summaries." Using cross-encoder semantic alignment across five LLMs and six datasets yields "significantly different position bias patterns," and the authors conclude LLMs "use content from all positions more effectively than previously assumed, challenging common claims about 'lost-in-the-middle' behaviour."[rahimi-not-lost-after-all](#rahimi-not-lost-after-all)
      - **Most current models are robust against it.** LongPiBench, testing multiple relevant pieces across three commercial and six open-source models, finds "while most current models are more robust against the 'lost in the middle' issue, there also exist noticeable biases related to the **spacing** of relevant information pieces."[tian-longpibench](#tian-longpibench) The bias did not vanish — it moved.
      - **It may not be information loss at all.** Training models from scratch on human-memory paradigms reproduces the U-curve, leading the authors to argue the pattern is "not simply a flaw indicative of information loss but an adaptation to different information retrieval demands during pre-training."[salvatore-emergent-property](#salvatore-emergent-property)
      - Even the recency half is task-dependent: the one dedicated serial-position study finds "Transformers show weak or absent recency effects in item recognition, a pattern which differs from human behavior."
      - **Consequence for the module.** Keep the design advice — "beginning or end, never the middle" is still the safest placement, and it is independently supported by query-position work.[shaier-context-before-question](#shaier-context-before-question), [ok-prompt-order](#ok-prompt-order) — but **stop teaching the mechanism as settled fact.** The honest framing: position affects use in *some* models and tasks, the size and even the sign of the effect is task-dependent, and the middle is a slot to keep small because the cost of being wrong is asymmetric, not because the failure is proven universal.
      narrative (compacted):
        - [prose] No minor quibble: the module's core mechanism is the claim on which the literature most visibly splits — present it as contested, not settled.
        - [bullet] The original result is real but hedged: performance may degrade, and is often best with relevant information at the beginning or end, across two synthetic retrieval tasks.
        - [bullet] A follow-up attributes it to attention, not relevance: a U-shaped bias gives start and end tokens more attention regardless of relevance, making the causation positional.
        - [bullet] How Hsieh actually measured attention and derived the calibration — see the found-in-the-middle paper notes.
        - [bullet] Independent of position, effective context trails advertised length: of 17 long-context models claiming at least 32K, only half stay satisfactory at 32K.
        - [bullet] The effect peaks within roughly half the window; beyond that primacy fades while recency persists — eliminating the LiM effect and leaving a distance-from-end bias.
        - [bullet] The measurement may be an artifact: n-gram matching misses abstractive semantics, and cross-encoder alignment over five LLMs and six datasets finds different patterns, challenging lost-in-the-middle.
        - [bullet] Most models are now robust: LongPiBench (three commercial, six open-source) finds the middle issue largely handled, yet spacing-related biases remain — the bias moved rather than vanished.
        - [bullet] It may not be information loss at all: models trained from scratch on human-memory paradigms reproduce the U-curve, which the authors read as an adaptation to pre-training retrieval demands.
        - [bullet] Recency is task-dependent too: the lone serial-position study reports transformers with weak or no recency advantage in item recognition, unlike human behaviour.
        - [prose] Consequence: keep the placement advice, but stop teaching the mechanism as settled — effects are task-dependent, and the middle stays small because the cost of error is asymmetric.
      prompt: For the lost-in-the-middle effect, give the supporting evidence and the distinct ways the literature undercuts it — then state the honest framing the module should adopt, including what design advice survives.
      reveal: Present it as contested, not settled: this is the module's core mechanism.

Supports it:
- The original result is carefully hedged — performance "can degrade" and is "often highest" when relevant information sits at the beginning or end, on two synthetic retrieval tasks.
- Hsieh attributes the pattern to attention rather than relevance: a U-shaped attention bias gives beginning and end tokens higher attention *regardless of their relevance*. That clause is what makes the causation positional.
- Independent of position, effective context falls short of advertised: of 17 long-context models claiming at least 32K, only half maintain satisfactory performance at 32K.
- The effect is strongest only up to ~50% of the window; beyond that primacy weakens while recency holds, "effectively eliminating the LiM effect" and leaving a distance-from-end bias.

Undercuts it:
- The measurement may be an artifact: prior summarization studies leaned on n-gram matching, which cannot capture semantic relations in abstractive summaries. Cross-encoder semantic alignment across five LLMs and six datasets yields significantly different position-bias patterns, challenging lost-in-the-middle claims.
- LongPiBench finds most current models robust, with residual bias attached to the *spacing* of relevant pieces — the bias moved, it did not vanish.
- A from-scratch training study reproduces the U-curve and reads it as an adaptation to pre-training retrieval demands, not information loss.
- The recency half is task-dependent too: the dedicated serial-position study finds weak or absent recency in item recognition.

Consequence: keep the design advice — beginning or end, never the middle, independently supported by query-position work — but stop teaching the mechanism as settled fact. Position affects use in some models and tasks; the size and even the sign are task-dependent; the middle is kept small because the cost of being wrong is asymmetric, not because the failure is proven universal.
### 2. The module's *premise* has its strongest support from a source it does not cite  [src README.md:649]
      - There is a cleaner justification for budgeting context than position bias, and it is worth leading with: **length alone hurts, independent of retrieval and independent of distraction.**
      - Across five open- and closed-source LLMs on math, QA, and coding, "even when models can perfectly retrieve all relevant information, their performance still degrades substantially (**13.9%–85%**) as input length increases but remains well within the models' claimed lengths."[du-context-length-alone](#du-context-length-alone)
      - The controls are what make this decisive: the failure persists "even when the irrelevant tokens are replaced with minimally distracting whitespace, and, more surprisingly, when they are all masked and the models are forced to attend only to the relevant tokens," and even "when all relevant evidence is placed immediately before the question."[du-context-length-alone](#du-context-length-alone)
      - A related ceiling holds beyond 100K: long-context LLMs "still require significant advancements to effectively process 100K+ context," where simply retrieving a few passages is "not sufficient."[zhang-infinity-bench](#zhang-infinity-bench)
      - **Consequence.** This is the citation the module's thesis should rest on. It says: shrink the window because *length itself is a tax*, not merely because information might land in an unlucky position — and it survives every objection that the position-bias literature is now facing.
      narrative (compacted):
        - [prose] A stronger ground for budgeting than position bias: sheer length degrades performance by itself, with retrieval and distraction both ruled out.
        - [bullet] Five open- and closed-source LLMs, tested on math, QA and coding, still lose 13.9%–85% of performance as input grows — with retrieval perfect and lengths within claims.
        - [bullet] The controls are decisive: the degradation survives whitespace padding, fully masked irrelevant tokens, and even placing all relevant evidence immediately before the question.
        - [bullet] A related ceiling beyond 100K: long-context LLMs still need significant advances at 100K+, where retrieving a few passages is not sufficient.
        - [prose] Consequence: the thesis should rest on this — shrink the window because sheer length taxes the model, not because evidence might sit badly; it survives the position-bias critiques.
      prompt: Which finding should the module's thesis rest on instead of position bias, what are the controls that make it decisive, and why does it survive the objections now facing the position-bias literature?
      reveal: Length alone hurts — independent of retrieval and independent of distraction — and that is what the thesis should rest on.

The finding: across five open- and closed-source LLMs on math, QA and coding, performance degrades substantially (13.9%-85%) as input length increases while remaining well within the models' claimed lengths — even when all relevant information is perfectly retrievable.

The controls are what make it decisive, because each removes a rival explanation:
- The degradation persists when irrelevant tokens are replaced with minimally distracting whitespace.
- It persists when those tokens are all masked and the model is forced to attend only to the relevant tokens.
- It persists even when all relevant evidence is placed immediately before the question.

So position, distraction and retrieval failure are each ruled out in turn.

A related ceiling beyond 100K: long-context LLMs still require significant advances to process 100K+ context, where simply retrieving a few passages is not sufficient.

Why it matters: it survives every objection the position-bias literature is now facing — measurement artifacts, the robustness of current models, the pre-training-adaptation reading. The argument becomes "shrink the window because length itself is a tax", not "shrink it because information might land in an unlucky slot".
### 3. "Formatting is information" is the weakest *design* claim in the module  [src README.md:659]
      - The module asserts that structure which "would be noise to a person is signal to it," and that deterministic structure "makes the model's job of *finding* the right thing cheaper." Format sensitivity is well established — but it is **not established as reliably positive**, which is the part the module needs:
      - **A single character moves the score by ±23%.** On MMLU, "performance … can vary by ±23% depending on the choice of delimiter," and "one can manipulate model rankings to put any model in the lead by only modifying the single character separating examples." The brittleness "pervades topics, model families, and doesn't improve with scale."[su-single-character](#su-single-character)
      - **Structured output can *cost* capability.** JSON, XML, LaTeX, and Markdown "substantially degrade reasoning and writing performance across open-weight models," and "format-requesting instructions alone cause most of the accuracy loss" — before any constrained decoding is applied. The paper's own mitigation is to decouple reasoning from formatting, not to add more markup.[lee-format-tax](#lee-format-tax)
      - Even Anthropic's own guidance hedges, treating heavy format scaffolding as "likely becoming less important as models become more capable."[anthropic-prompting-best-practices](#anthropic-prompting-best-practices)
      - **Consequence.** **Format is a high-leverage design variable whose effect is empirically uncertain in sign, and must be A/B-tested per model.** The worked example's numbered `[1] <chunk>` block is a reasonable hypothesis, not a best practice. The one strongly supported formatting rule in the module is the *order*, not the markup — and that is §1 above.
      narrative (compacted):
        - [prose] The module claims structure that is noise to a person is signal to the model, making retrieval cheaper. Format sensitivity is established; its reliably positive direction is not.
        - [bullet] One character moves MMLU scores by ±23%: delimiter choice alone can reorder model rankings, and the brittleness spans topics and model families without improving with scale.
        - [bullet] Structured output can cost capability: JSON, XML, LaTeX and Markdown degrade open-weight reasoning and writing, format instructions alone cause most loss, and the fix is decoupling, not more markup.
        - [bullet] Even Anthropic's guidance hedges, calling heavy format scaffolding likely less important as models grow more capable.
        - [prose] Consequence: format is high-leverage but empirically uncertain in sign, so A/B-test per model. The worked example's numbered chunk block is a hypothesis, not best practice; the well-supported rule is order, not markup.
      prompt: Why is "formatting is information" the module's weakest design claim? Give the evidence that format sensitivity is not reliably positive, and state what formatting rule remains supported.
      reveal: Format sensitivity is established; that format sensitivity is reliably *positive* is not — and positivity is the part the module's design advice needs.

Evidence against reliable benefit:
- A single character moves the score by about 23%: on MMLU, performance varies by that much depending on delimiter choice, and model rankings can be rearranged by changing only the character separating examples. The brittleness spans topics and model families, and does not improve with scale.
- Structured output can cost capability: JSON, XML, LaTeX and Markdown substantially degrade reasoning and writing in open-weight models, and format-requesting instructions alone cause most of the accuracy loss — before any constrained decoding. The paper's own mitigation is to decouple reasoning from formatting: less markup, not more.
- Even Anthropic hedges, treating heavy format scaffolding as likely to matter less as models become more capable.

Consequence: format is a high-leverage design variable whose effect is empirically uncertain in sign; it must be A/B tested per model. The worked example's numbered `[1] <chunk>` block is a reasonable hypothesis, not a best practice.

The one strongly supported formatting rule in the module is the *order* — not the markup.
### 4. Tool-schema bloat has *two* mechanisms, and the module names only the wrong one  [src README.md:669]
      - The module's table says bloated tool schemas "Steal attention from the task." The measurements show two distinct failure modes, and the module conflates them:
      - **Budget exhaustion** — tool schemas "consume the same context window needed for retrieval-augmented generation." The effect is binary rather than gradual: at an 8K budget, "JSON-schema tool definitions overflow the context window entirely, yielding near-zero EM," while compressed schemas restore functionality with "+20.5 pp average exact-match lift." But "at 32K — where both formats fit — four of five tested models show delta ≤ 1 pp, confirming the effect is purely budget-driven."[sakizli-tool-schema-compression](#sakizli-tool-schema-compression)
      - **Selection confusion** — and this one *is* the attention story the module wants. Even when the tools fit comfortably, selection still fails: given 46 tools on a model with a 16K context window that "can fit all the tools, it fails to select the correct one… when only 19 tools are passed, the LLM chooses the correct tool." The reported cause is "the large number of available options confusing the LLM," not overflow.[paramanayakam-less-is-more](#paramanayakam-less-is-more)
      - So the module's mechanism claim is not wrong — it is *incompletely* right, naming the mechanism that only bites under pressure while missing the one that bites always. The practical consequence is the same either way: **retrieve a shortlist of tools rather than dumping every schema.** Prompt bloat drops tool-selection accuracy to a "13.62% baseline," and showing only retrieved candidates "more than triples" it to 43.13% while cutting prompt tokens by over 50%.[gan-rag-mcp](#gan-rag-mcp)
      - **A caveat on the fix.** "Retrieve a shortlist" is not universally safe: retrieval narrowing "can at-times hurt performance" when the retriever misses, and one evaluation found a 50-tool shortlist and a 7-tool shortlist achieving near-identical coverage (90.3% vs 90.8%).[repantis-how-many-tools](#repantis-how-many-tools) Shortlisting trades a selection problem for a recall problem — which is M5's subject, not a solved detail.
      narrative (compacted):
        - [prose] The module's table blames tool-schema bloat for stealing task attention; measurements instead reveal two separate failure modes, which the module conflates.
        - [bullet] Budget exhaustion: schemas consume RAG's window. At 8K, JSON definitions overflow entirely (near-zero EM) while compressed schemas add +20.5 pp; at 32K, four of five models differ by at most 1 pp.
        - [bullet] Selection confusion, the attention story the module wants: 46 tools fit a 16K window yet selection fails, while 19 succeed — option count blamed, not overflow.
        - [prose] Incompletely right: it names the pressure-only failure, missing the always-on one. Either way, shortlist tools — selection rises from a 13.62% bloat baseline to 43.13%.
        - [prose] Caveat: shortlisting is not universally safe — narrowing hurts when the retriever misses, and one evaluation found 50- and 7-tool shortlists near-identical in coverage (90.3% vs 90.8%), trading selection for recall.
      prompt: Tool-schema bloat: name both failure mechanisms, give the measurement that separates them, and say which one the module's "steals attention from the task" claim actually describes — then the practical consequence and its caveat.
      reveal: Two mechanisms, not one:

- **Budget exhaustion** — schemas consume the same window retrieval needs. The effect is binary, not gradual: at an 8K budget, JSON-schema tool definitions overflow the context window entirely and exact-match goes near zero, while compressed schemas restore function (+20.5 pp average EM). But at 32K — where both formats fit — four of five tested models show delta of 1 pp or less, confirming the effect is purely budget-driven.
- **Selection confusion** — and this is the attention story the module wants. Given 46 tools on a 16K model that can fit them all, selection still fails; pass only 19 and the model chooses the correct tool. The reported cause is the large number of available options confusing the model, not overflow.

The module's "steal attention from the task" names the mechanism that only bites under pressure and misses the one that bites always. It is incompletely right, not wrong.

The practical consequence is the same either way: retrieve a shortlist of tools rather than dumping every schema. Bloat drops tool selection to a 13.62% baseline; showing only retrieved candidates more than triples it to 43.13% while cutting prompt tokens by over 50%.

Caveat on the fix: shortlisting is not universally safe. Retrieval narrowing can hurt when the retriever misses, and one evaluation found 50-tool and 7-tool shortlists at near-identical coverage (90.3% vs 90.8%). Shortlisting trades a selection problem for a recall problem — M5's subject, not a solved detail.
### 5. System instructions do not reliably outrank later text — and compaction is *documented* to lose them  [src README.md:680]
      - The module treats the system/user boundary as a working primitive and treats the standing instruction as something you "never evict." Both halves are contradicted.
      - **The hierarchy is not reliable.**
      - "The widely-adopted system/user prompt separation **fails to establish a reliable instruction hierarchy**," across six state-of-the-art models and "even for simple formatting conflicts."[geng-control-illusion](#geng-control-illusion)
      - Worse, "societal hierarchy framings (e.g., authority, expertise, consensus) show **stronger influence** on model behavior than system/user roles," functioning as "latent behavioral priors with potentially greater impact than post-training guardrails."[geng-control-illusion](#geng-control-illusion)
      - **And the harness cannot simply refuse to evict it.** The most authoritative available artifact on this exact question is Claude Code's own context-window documentation, and it says the opposite of "never evict": its table of what survives compaction marks path-scoped rules and nested instruction files as summarized away with everything else, and instructs developers to fix this by moving rules out of the compacted span — "If a rule must persist across compaction, drop the `paths:` frontmatter or move it to the project-root CLAUDE.md," which is "re-injected from disk."[claude-code-context-window](#claude-code-context-window)
      - **Consequence.** "Never evict the standing instruction" is not a property the harness can guarantee from inside the window; it is a **design pattern** — keep the policy in a slot re-injected from outside the compacted span each turn. That is exactly what the ADK stable prefix and Claude Code's re-injection both implement. The placement rule is a *bias-toward-use*, not a guarantee of rank, and anything that must be enforced belongs in a capability boundary (a tool that refuses) rather than in prose — the conclusion M2's Tahoe case already reaches.
      narrative (compacted):
        - [prose] Both halves of the module's stance are contradicted: it treats system/user separation as a working primitive and the standing instruction as never evictable.
        - [prose] The instruction hierarchy is not reliable.
        - [bullet] Six state-of-the-art models were tested: separating system from user prompts does not yield a dependable instruction hierarchy, even for simple formatting conflicts.
        - [bullet] Worse, societal framings like authority, expertise and consensus influence behavior more than system/user roles, acting as latent priors that can outweigh post-training guardrails.
        - [prose] Nor can the harness refuse to evict it: Claude Code's docs summarize path-scoped and nested rules away, advising developers to move persistent rules to a re-injected project-root file.
        - [prose] Consequence: never evict is a design pattern, not a guarantee — re-inject the policy from outside the compacted span, and enforce hard rules through a capability boundary, not prose.
      prompt: Two claims are made about system instructions: that the system/user split confers rank, and that the standing instruction is never evicted. State the evidence against each half, then the design pattern that replaces them.
      reveal: Both halves of the module's treatment fail.

**The hierarchy is not reliable.** The widely adopted system/user prompt separation fails to establish a reliable instruction hierarchy across six state-of-the-art models, and even for simple formatting conflicts. Worse, societal hierarchy framings — authority, expertise, consensus — show stronger influence on model behaviour than system/user roles, functioning as latent behavioural priors with potentially greater impact than post-training guardrails.

**And the harness cannot simply refuse to evict it.** Claude Code's own context-window documentation — the most authoritative artifact on this exact question — says the opposite of "never evict": path-scoped rules and nested instruction files are summarized away with everything else. The prescribed fix is to move the rule out of the compacted span — drop the `paths:` frontmatter, or move it to the project-root CLAUDE.md, which is re-injected from disk.

Consequence: "never evict the standing instruction" is not a property the harness can guarantee from inside the window. It is a design pattern — hold the policy in a slot re-injected from outside the compacted span each turn, which is what the ADK stable prefix and Claude Code's re-injection both implement. Placement is a *bias-toward-use*, not a guarantee of rank. Anything that must be enforced belongs in a capability boundary (a tool that refuses) rather than in prose.
### 6. "A naive summarizer keeps the narrative and drops the specifics" — this one is empirically backwards  [src README.md:693]
      - This is the module's most concrete compaction claim, and the one paper that actually measures the *composition* of gist-compression loss reports the opposite ordering:
      - Gist abstraction "preserves relational and event structure while discarding dates and times."
      - Quantitatively: an approximately **20-fold** improvement in temporal-expression preservation (3.05% → 62.39%) was achieved by a one-sentence prompt fix, "while named entity and event preservation rates **barely change** (×1.02 and ×1.11)."[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent)
      - So: narrative ✓, entities ✓, **time and quantities ✗** (3.05% preserved before the fix). The suffix needs its noun corrected. The right compactor rule is not "never summarize these fields" in general — it is specifically **"preserve dates, times, and quantities verbatim,"** because those are what a gist abandons by default.[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent)
      - **And the loss is not a bug you can engineer away.** Context compaction has now been given a formal treatment: the authors "prove an equivalence between the Context Generation Game and one-way communication complexity," so "the minimum context compaction budget for answering a set of queries within a target error is equal to the one-way communication complexity of the induced communication problem."[tirmazi-context-compaction-theory](#tirmazi-context-compaction-theory) Loss is an **information-theoretic floor**, which strengthens the module's "belongs in an ADR" instinct — you are choosing where to spend the loss, not whether to have any.
      - **The one detail that does need a benchmark:** a dedicated specificity/detail-retention benchmark for summarization does not appear to exist. The Sleeping Agent preservation analysis[kyrkewood-sleeping-agent](#kyrkewood-sleeping-agent) is the closest instrument located, and it measures temporal and entity preservation specifically rather than "specificity" generally.
      narrative (compacted):
        - [prose] Its most concrete compaction claim — and the only paper measuring what gist compression actually discards reports the reverse ordering.
        - [bullet] Gist abstraction preserves relational and event structure but discards dates and times.
        - [bullet] Quantitatively, a one-sentence prompt fix raised temporal-expression preservation roughly 20-fold (3.05% to 62.39%) while entity and event preservation barely moved (×1.02, ×1.11).
        - [prose] Narrative and entities survive; time and quantities do not (3.05% before the fix). The correct rule is narrower: preserve dates, times and quantities verbatim, since gists abandon those by default.
        - [prose] The loss is not engineerable away: a formal result equates compaction budget with one-way communication complexity, making loss an information-theoretic floor — you choose where to spend it, not whether.
        - [prose] One detail needs a benchmark: no dedicated specificity or detail-retention benchmark for summarization seems to exist; the Sleeping Agent analysis is closest, measuring temporal and entity preservation rather than specificity broadly.
      prompt: What does the one paper measuring the composition of gist-compression loss report about what survives and what is dropped? What correction does that force on the compactor rule, and why is the loss not something you can engineer away?
      reveal: Backwards. Gist abstraction preserves relational and event structure while discarding dates and times. So the ordering is: narrative preserved, entities preserved, time and quantities dropped.

The quantitative shape: temporal-expression preservation began at 3.05% and a one-sentence prompt fix lifted it to 62.39% — roughly a 20-fold improvement — while named-entity and event preservation rates barely changed (x1.02 and x1.11). The fix was not a better summarizer; it was telling the summarizer what to keep.

So the compactor rule needs its noun corrected. Not "never summarize these fields" in general, but specifically **"preserve dates, times, and quantities verbatim"** — because those are what a gist abandons by default.

And the loss is not a bug to engineer away. Compaction now has a formal treatment proving an equivalence between the Context Generation Game and one-way communication complexity: the minimum context compaction budget for answering a set of queries within a target error equals the one-way communication complexity of the induced communication problem. Loss is an information-theoretic floor — which strengthens the ADR instinct, because you are choosing where to spend the loss, not whether to have any.

The missing instrument: a dedicated specificity/detail-retention benchmark for summarization does not appear to exist. The Sleeping Agent preservation analysis is the closest, and it measures temporal and entity preservation specifically rather than "specificity" in general.
### 7. Compression is not uniformly lossy — *what* is compressed is what matters  [src README.md:706]
      - The module frames compaction as an exchange of fidelity for budget. The literature does not agree that loss is inherent to compression as a technique:
      - **Targeted compression can *raise* accuracy.** LongLLMLingua "boosts performance by up to 21.4% with around 4x fewer tokens," improving "LLMs' perception of the key information" — addressing position bias and cost together.[jiang-longllmlingua](#jiang-longllmlingua)
      - **Learned compression can substitute for raw context.** AutoCompressors produce summary vectors that are "good substitutes for plain-text demonstrations, increasing accuracy while reducing inference costs."[chevalier-autocompressors](#chevalier-autocompressors)
      - **But detail loss is real and measurable.** Semantic compression reduces redundancy before the context reaches the model, and shows the technique is task-dependent rather than free.[fei-semantic-compression](#fei-semantic-compression)
      - **Consequence.** "Compaction is lossy, and its loss is invisible" describes *the module's own recommended implementation* — a general-purpose narrative summarizer over old turns — not compression as a technique. The defensible claim is narrower: **generic narrative summarization of history is lossy in a specific, predictable direction (time and quantities first); utility-gated or query-conditioned compression is measurably better.** That is an argument for making the compactor a designed artifact — which the module already urges — not an argument against compression.
      narrative (compacted):
        - [prose] The module frames compaction as fidelity traded for budget; the literature does not treat loss as inherent to compression as a technique.
        - [bullet] Targeted compression can raise accuracy: LongLLMLingua improves performance up to 21.4% with roughly 4x fewer tokens, addressing position bias and cost together.
        - [bullet] Learned compression can substitute for raw context: AutoCompressors' summary vectors replace plain-text demonstrations, raising accuracy while cutting inference cost.
        - [bullet] But detail loss is real and measurable: semantic compression strips redundancy before the model sees context, and the technique proves task-dependent rather than free.
        - [prose] Consequence: the lossy-and-invisible charge fits the module's own narrative summarizer, not compression; generic summarization drops time and quantities first, while utility-gated compression measures better.
      prompt: Why is "compaction is lossy" the wrong level of description, and what narrower claim about compression does the evidence actually support?
      reveal: The framing is at the wrong level. "Compaction is lossy, and its loss is invisible" describes the module's own recommended implementation — a general-purpose narrative summarizer over old turns — not compression as a technique.

Evidence that loss is not inherent to compression:
- Targeted compression can *raise* accuracy: LongLLMLingua boosts performance by up to 21.4% with around 4x fewer tokens, improving the model's perception of key information — addressing position bias and cost together.
- Learned compression can substitute for raw context: AutoCompressors' summary vectors are good substitutes for plain-text demonstrations, increasing accuracy while reducing inference cost.
- But detail loss is real and measurable: semantic compression strips redundancy before the context reaches the model, and the technique is task-dependent rather than free.

Defensible narrower claim: generic narrative summarization of history is lossy in a specific, predictable direction — time and quantities first — while utility-gated or query-conditioned compression is measurably better. That is an argument for making the compactor a designed artifact, which the module already urges, not an argument against compression.
### 8. "The agent will not tell you it's reasoning from a lossy memory" — restate as a harness gap  [src README.md:716]
      - The module frames this as a model limitation. The model half is partly refuted: a GPT-3 model can "learn to express uncertainty about its own answers in natural language," with levels that "map to probabilities that are well calibrated."[lin-uncertainty-in-words](#lin-uncertainty-in-words)
      - The defensible version is narrower and better, and it points at the harness: **there is no channel through which compaction loss surfaces.** Claude Code's own documentation records that "the summarization happens without appearing in your terminal,"[claude-code-context-window](#claude-code-context-window) and work on parallel compaction finds retained information "fluctuate[s] substantially from run to run." The claim to teach is observability, not metacognition: *the model may be capable of reporting a degraded memory, but nothing in the harness asks it to, and the loss is not logged.*
      narrative (compacted):
        - [prose] The module calls this a model limitation, yet that half is partly refuted: GPT-3 can learn to voice uncertainty in natural language, its levels mapping to well-calibrated probabilities.
        - [prose] The better claim targets the harness: no channel surfaces compaction loss — Claude Code notes summarization absent from the terminal, and parallel-compaction retention fluctuates run to run. Teach observability, not metacognition.
      prompt: The module says the agent will not tell you it is reasoning from a lossy memory. Why is the model-limitation framing wrong, and what is the correct restatement?
      reveal: Because the model half is partly refuted, and the harness half is the real claim.

Model half: a GPT-3 model can learn to express uncertainty about its own answers in natural language, with levels that map to probabilities that are well calibrated. So "the model cannot report a degraded memory" is too strong as stated.

Defensible restatement, which points at the harness: **there is no channel through which compaction loss surfaces.** Claude Code's documentation records that summarization happens without appearing in the terminal, and work on parallel compaction finds retained information fluctuating substantially from run to run. Nothing asks the model about the loss, and the loss is not logged.

The claim to teach is observability, not metacognition: the model may be capable of reporting a degraded memory, but nothing in the harness asks it to — and the loss is not logged.
### 9. The module's cost claim rests on complexity arguments, not measured NLP latency  [src README.md:722]
      - The module says an irrelevant token costs "a cash charge, plus latency (input size scales response time)." The *direction* is solid, but be aware of what the evidence actually is: the quadratic-cost, prefill-versus-decode, and KV-cache-growth results come from architecture and serving-systems work,[fu-long-context-deployment](#fu-long-context-deployment) and the one in-scope NLP paper that states latency and cost growth does so as a one-line aside — "Using more than 20 retrieved documents only marginally improves reader performance (∼1.5% GPT-3.5-Turbo, ∼1% Claude-1.3), while significantly increasing the input context length (and thus latency and cost)"[liu-lost-in-the-middle](#liu-lost-in-the-middle) — not as a measured dependent variable. No controlled context-length-versus-wall-clock NLP study was located. Teach this claim from complexity and serving measurements, and say so.
      narrative (compacted):
        - [prose] Direction right, evidence architectural: quadratic cost, prefill-versus-decode and KV-cache growth come from serving work; the NLP paper mentions latency only in an aside, and no controlled wall-clock study exists.
      prompt: What kind of evidence actually supports the claim that irrelevant context tokens cost latency, and what should be said about how to teach that claim?
      reveal: The direction is solid; the evidence type is not what the sentence implies.

What actually carries the claim: quadratic cost growth, prefill-versus-decode economics, and KV-cache growth — all from architecture and serving-systems work, not from NLP measurement.

The one in-scope NLP paper that mentions latency and cost does so as a one-line aside: using more than 20 retrieved documents only marginally improves reader performance (~1.5% GPT-3.5-Turbo, ~1% Claude-1.3) while significantly increasing input context length, and thus latency and cost. Latency is not a measured dependent variable there — it is inferred from length.

No controlled context-length-versus-wall-clock NLP study was located.

So: teach the claim from complexity and serving measurements, and say so — attribute it to that evidence base rather than presenting it as a measured NLP result.
### 10. Keep the window small — the counter-position the module never names  [src README.md:726]
      - The module's thesis is that the window is a budget to *spend down*, and the worked example claims that the three-hours-ago question "is answered just as well as it was in minute one" once the window is held at 10–12k. There is a live counter-position: **long context can obviate retrieval and summarization for corpus-loading tasks.** The M2 literature review records the head-to-head — "when resourced sufficiently, LC consistently outperforms RAG in terms of average performance. However, RAG's significantly lower cost remains a distinct advantage" — i.e. the tradeoff is cost-versus-accuracy, with hybrid routing between them.
      - **Consequence.** That claim is a design assertion, not a measured result. Keeping the window small buys cost and latency; it can cost accuracy on tasks where the full corpus *is* the prerequisite — exactly the "context is the prerequisite" inapplicability case M2 flags. Note that §2 above cuts the other way and is better evidence: length alone hurts even with perfect retrieval. The two findings are not in conflict — one says long context is unavoidable for some tasks, the other says it is expensive even when retrieval succeeds — and together they are the real argument for a hybrid.
      narrative (compacted):
        - [prose] The module spends the window down, claiming old questions answer as well at 10–12k. Counter-position: for corpus-loading, well-resourced long context outperforms RAG; cost is the tradeoff, implying hybrid routing.
        - [prose] Consequence: not a measurement but an assertion — small windows save cost and latency, yet may lose accuracy where the corpus is prerequisite; §2 shows length alone hurts, arguing for hybrid.
      prompt: State the counter-position to "keep the window small" that the module never names, and explain why it does not conflict with the finding that length alone hurts.
      reveal: The unnamed counter-position: long context can obviate retrieval and summarization entirely for corpus-loading tasks. The M2 literature review records the head-to-head — when resourced sufficiently, LC consistently outperforms RAG on average performance, though RAG's significantly lower cost remains a distinct advantage. That is a cost-versus-accuracy tradeoff, with hybrid routing between the two.

The module's own claim is a design assertion, not a measured result: the worked example's "the three-hours-ago question is answered just as well as it was in minute one" at a 10-12k window. Holding the window small buys cost and latency; it can cost accuracy on tasks where the full corpus *is* the prerequisite — exactly the "context is the prerequisite" inapplicability case M2 flags.

Why this does not conflict with the length-alone finding: the length-alone result says long context is expensive even when retrieval succeeds, in the best case. This counter-position says long context is unavoidable for some tasks. One is about cost, the other about necessity. Together they are the real argument for a hybrid, not a blanket rule in either direction.
### 11. Framework claims: verified against the docs, with three corrections  [src README.md:732]
      - Checked against the live ADK documentation and `google/adk-python` source rather than against the module's prose:
      - **Confirmed exactly:** `ContextCacheConfig` defaults `ttl_seconds=1800` and `cache_intervals=10`;[adk-context-caching](#adk-context-caching) `EventsCompactionConfig` with `token_threshold`/`event_retention_size` and `compaction_interval`/`overlap_size`, plus `LlmEventSummarizer` with a configurable model;[adk-context-compaction](#adk-context-compaction) `InvocationContext`, `Runner`, and `run_async`;[adk-context](#adk-context) `static_instruction` as "a way to amend the system instructions for a generative model."[adk-context-caching](#adk-context-caching)
      - **Correction 1 — `min_tokens` defaults to `0`.[adk-context-caching](#adk-context-caching)** The module's gloss "don't bother caching tiny requests" describes *intended use*, not the default; avoiding small-request caching is opt-in. (The doc's own example uses `min_tokens=2048, ttl_seconds=600, cache_intervals=5` — example values that are easy to mistake for defaults.)
      - **Correction 2 — caching is not Gemini-only in implementation.** The public page is titled "Context caching with Gemini," but the same `ContextCacheConfig` is routed to Anthropic (`cache_control` breakpoints) and through LiteLLM. The module's "with LiteLLM/Azure backends … at the *provider* layer" is directionally right; the caveat is that Azure support is narrower than Anthropic's.
      - **Correction 3 — `static_instruction` "persist[s] across a session" is the module's wording, not the docs'.** It is a constant on the agent, re-sent every turn, and the source notes that setting it "alone does NOT enable caching automatically."
      - A useful side-benefit of checking a real harness: Claude Code publishes representative startup token counts — a 4,200-token system prompt, 1,800 tokens of project instructions, ~970 tokens of MCP and skill listings.[claude-code-context-window](#claude-code-context-window) That is a concrete instance of "fixed overhead," and it is worth more than a borrowed across-the-board percentage, which remains unavailable.
      narrative (compacted):
        - [prose] Verified against the live ADK documentation and the google/adk-python source, not the module's prose.
        - [bullet] Confirmed exactly: ContextCacheConfig defaults (ttl_seconds=1800, cache_intervals=10); EventsCompactionConfig's threshold/retention and interval/overlap fields; LlmEventSummarizer; InvocationContext, Runner, run_async; and static_instruction amending system instructions.
        - [bullet] Correction 1: min_tokens defaults to 0 — the module's don't-cache-tiny-requests gloss is intended use, not the default; the doc's 2048/600/5 values are illustrative and easily mistaken for defaults.
        - [bullet] Correction 2: caching is not Gemini-only — the same ContextCacheConfig routes to Anthropic via cache_control and through LiteLLM, though Azure support is narrower than Anthropic's.
        - [bullet] Correction 3: the docs never promise static_instruction survives a whole session — it is a per-agent constant re-sent each turn, and alone it enables no caching.
        - [prose] Side-benefit: Claude Code publishes startup token counts — 4,200 system prompt, 1,800 project instructions, about 970 MCP and skill listings — concrete fixed overhead, unlike the unavailable percentage.
      prompt: For the ADK framework claims, list what was confirmed exactly and the three corrections — stating, for each correction, the specific distinction that makes it matter.
      reveal: **Confirmed exactly** against the live ADK documentation and `google/adk-python` source: `ContextCacheConfig` defaults `ttl_seconds=1800` and `cache_intervals=10`; `EventsCompactionConfig` with `token_threshold`/`event_retention_size` and `compaction_interval`/`overlap_size`, plus `LlmEventSummarizer` with a configurable model; `InvocationContext`, `Runner`, `run_async`; and `static_instruction` as a way to amend the system instructions for a generative model.

**Correction 1 — `min_tokens` defaults to `0`.** The module's gloss "don't bother caching tiny requests" describes intended use, not the default; avoiding small-request caching is opt-in. The distinction is easy to miss because the doc's own example (`min_tokens=2048, ttl_seconds=600, cache_intervals=5`) uses example values that read like defaults.

**Correction 2 — caching is not Gemini-only in implementation.** The public page is titled "Context caching with Gemini", but the same `ContextCacheConfig` is routed to Anthropic via `cache_control` breakpoints and through LiteLLM. The module's provider-layer claim is directionally right; the caveat is that Azure support is narrower than Anthropic's.

**Correction 3 — `static_instruction` does not "persist across a session".** That is the module's wording, not the docs'. It is a constant on the agent, re-sent every turn, and the source notes that setting it alone does NOT enable caching automatically.

Side-benefit of checking a real harness: Claude Code publishes representative startup token counts — a 4,200-token system prompt, 1,800 tokens of project instructions, ~970 tokens of MCP and skill listings. A concrete instance of fixed overhead, worth more than an unavailable across-the-board percentage.
## Sources (ADK docs)  [src README.md:745]
    - [Agent context](https://adk.dev/context/index.md)[adk-context](#adk-context)
    - [Context caching with Gemini](https://adk.dev/context/caching/index.md)[adk-context-caching](#adk-context-caching)
    - [Compress agent context (compaction)](https://adk.dev/context/compaction/index.md)[adk-context-compaction](#adk-context-compaction)
    - [Session, State & Memory](https://adk.dev/sessions/index.md)[adk-sessions](#adk-sessions)
    narrative (compacted):
      - [bullet] ADK docs: agent context.
      - [bullet] ADK docs: context caching with Gemini.
      - [bullet] ADK docs: compressing agent context (compaction).
      - [bullet] ADK docs: session, state and memory.
## Bibliography  [src README.md:754]
    - (checklist: empty)
### Framework documentation (industry docs)  [src README.md:758]
      - (checklist: empty)
### Assembly discipline: ordering, instructions, formatting  [src README.md:765]
      - (checklist: empty)
### Formatting and selection  [src README.md:773]
      - (checklist: empty)
### Measuring the cost: attention, position, and latency  [src README.md:780]
      - (checklist: empty)
### Tool-definition budget and tool-selection scaling  [src README.md:794]
      - (checklist: empty)
### Prompt caching  [src README.md:805]
      - (checklist: empty)
### Context compression and compaction  [src README.md:819]
      - (checklist: empty)
### Harness behaviour: what compaction actually preserves  [src README.md:828]
      - (checklist: empty)
### Session memory and selective assembly  [src README.md:832]
      - (checklist: empty)
### Unsupported claims and own synthesis  [src README.md:837]
      - (checklist: empty)