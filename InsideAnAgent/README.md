# Inside an Agent

Low-level design notes on what actually happens *within* a single agent: the loop, how tools are
attached, how a function call is emitted and dispatched, how the model "decides" between a tool
call and prose, and the token economics of shipping tool schemas on every call.

> **Companion doc:** [`OutsideAnAgent/`](../OutsideAnAgent/README.md) covers the system the agent
> sits in — evaluation, observability, security, supervision UX, multi-agent. This doc stops at the
> harness boundary.

Course-plan altitude: topics are named and framed, not taught in depth. Per-topic depth belongs in
its own file.

Sections are ordered so that no section *requires* anything below it to be understood. Forward
references (§n) mark elaboration, not prerequisites; backward references mark dependencies.

<details>
<summary><strong>§1–§11 and resources (click to expand)</strong></summary>

---

## 1. The loop

Everything else in this document is decoration on this:

```python
messages = [system, user]
while True:
    resp = llm(messages, tools=tool_schemas)   # schemas re-sent EVERY call — see §6
    messages.append(resp)

    if not resp.tool_calls:                    # exit condition
        return resp.text

    for call in resp.tool_calls:
        result = registry[call.name](**call.args)      # *you* execute it
        messages.append(tool_result(call.id, result))
```

- Under 30 lines. A working agent is this plus tool definitions.
- **The LLM never executes anything.** It emits a *request*. Your code dispatches it. The "function
  call" is a dict you `json.loads` and route through a name → callable map.
- The loop is **stateless between turns** — no plan object, no scratchpad. Everything the model
  knows on turn *n* is in `messages`.
- The exit condition is *"emitted no tool calls."* That is a **proxy** for "the task is done," not
  a check of it. See §9.
- Three tools make a complete code agent: `read_file`, `list_files`, `edit_file` — discover,
  inspect, mutate. That closure generalizes: for any domain, find the minimal discover/inspect/
  mutate triple.

---

## 2. There is no privileged channel

The root fact. Almost everything below is a consequence of it.

> **Everything is tokens in one context. `system`, `user`, `tool schema`, `tool result` — all of it
> is concatenated into a single string before the model sees any of it.**

- "Roles" are **string delimiters**, not a type system: `<|start_header_id|>user<|end_header_id|>`,
  `<|im_start|>system`. §5 shows the concatenation happening, literally, in template source.
- There is no memory protection, no ring 0, no tainted-pointer bit. One input, undifferentiated.
- The model cannot *know* that the text at position 4,000 came from a hostile web page rather than
  from you. It can only infer it, from prose.

### What this single fact causes

| Consequence | Covered in |
|---|---|
| Tool schemas are re-tokenized on every call → they cost money every turn | §6 |
| Tool calls need a **delimiter** the model was trained to emit, or parsing is guesswork | §4, §5 |
| Prompt injection works — *provenance* is untyped | [Outside §3](../OutsideAnAgent/README.md) |
| Jailbreak works — *policy* is untyped, and competes with the attacker's prose | [Outside §3](../OutsideAnAgent/README.md) |
| Context is a single contended budget, not per-channel quotas | §6, §11 |

- Corollary: if untrusted content can contain literal delimiter tokens, the boundary doesn't blur,
  it **breaks**. Most inference servers strip special tokens from user and tool content for exactly
  this reason — a structural guardrail almost nobody knows they depend on.

---

## 3. Tools: schema, attachment, dispatch

### What a tool *is*

Four things bundled together:

| Part | Consumed by | Purpose |
|---|---|---|
| `name` | Model | What it emits to select this tool |
| `description` | Model | **When to use it and when not to** |
| `input_schema` (JSON Schema) | Model | Argument shape |
| `function` (callable) | Your code | What actually runs |

- The first three are **prompt**. Only the fourth is code. This split is the whole subject.

### Schema generation

- Nobody hand-writes JSON Schema. It's reflected off the function signature — Go struct tags via
  `jsonschema.Reflector` (Ball), Python type hints via pydantic (`pydantic-ai`, `smolagents`).
- Read `tools.py` in smolagents or the schema layer in pydantic-ai to see this end to end.

### Attachment

- "Attaching" a tool = including its schema in the request body. That's all it is.
- It happens **on every single call**. The API is stateless; the model has no memory of turn
  *n−1*'s schemas (§2). Cost consequences in §6.

### Dispatch

```
model emits  →  {"name": "read_file", "arguments": {"path": "cmd/main.go"}}
your code    →  parse → registry lookup → validate args → execute → stringify → append as tool result
```

- Validate **before** dispatch. The model can emit a well-formed call to a path that doesn't exist.
- Enforce uniqueness on destructive edits. `edit_file(old_str, new_str)` that matches twice will
  silently corrupt the file — real implementations require a unique match and error otherwise.

### The description is code

The single most important LLD insight, and Ball demonstrates it without naming it:

- `edit_file`'s description says *"if the file doesn't exist, create it."*
- There is **no branch in the Go source** for file creation.
- The behavior is implemented in English, in the schema, and **the model is the interpreter**.

> Your tool description is not documentation. It is the part of the implementation you chose not to
> write in code.

### Errors are prompts

- Same principle, inverted. Return the error as a tool-result string and a capable model reads it
  and retries *differently*.
- Therefore **your error-handling strategy is a prompting strategy**. `Error: 1` caps what any model
  can do with the failure. See §9 — recovery is a capability the weights supply, and your error text
  is its only input.

### Which tool gets selected

Selection quality is a pure function of what you wrote:

- Distinct, non-overlapping names.
- Descriptions that state **when not to** use the tool, not just when to.
- Enum-constrain arguments wherever the domain is closed.
- Keep the count low — degradation is measurable well before 30–50 tools.

---

## 4. Tool call vs. text: the decision that isn't one

The most commonly misunderstood part of agent internals.

> There is no classifier, no router, no decision step. It is the **same next-token prediction**.

- Models are post-trained so tool-calling turns begin with a recognizable marker.
- If those tokens win the softmax → tool call. If prose tokens win → text.
- `stop_reason: "tool_use"` / `finish_reason: "tool_calls"` is a **post-hoc label** on what the
  sampler already did — not a mode the model was put into.

### Three marker strategies, weakest to strongest

| Strategy | Example | Reliability |
|---|---|---|
| Bare JSON, no delimiter | `llama3.2` via Ollama | **Weak** — parser must guess prose vs. call |
| XML sentinel | qwen3's `<tool_call>…</tool_call>` | Strong — trained tag, unambiguous |
| Reserved special token | Llama's official `<\|python_tag\|>` | Strong — single token, in-vocabulary |

Both live examples are dissected in §5.

### Consequences

- Tool-calling reliability is a **fine-tuning + template** property. Not a prompting one.
- You can force it: `tool_choice` (`auto` / `required` / named tool) biases or hard-constrains that
  first token. `required` is how you get guaranteed structured output.
- Failure modes follow mechanically:
  - **Call emitted as prose** — `"I'll call get_weather(city='Paris')"`. The marker lost.
  - **Hallucinated tool name** — decoded from vocabulary, only *biased* by your schema.
  - **Over-calling** — a tool name occupying context is an attractor.
  - **Under-calling** (irrelevance failure) — answering from parametric memory when a tool was
    required.

---

## 5. Chat templates: ground truth for local models

`ollama show --template <model>` prints the **actual concatenation** described in §2. Everything
above it is abstraction.

The `.Tools` branch is the part to read in both: it is where the JSON Schema you pass to
`/api/chat` gets **string-interpolated into the prompt**. Captured from local installs 2026-08-15.

<details>
<summary><code>ollama show --template llama3.2:latest</code></summary>

```gotemplate
<|start_header_id|>system<|end_header_id|>

Cutting Knowledge Date: December 2023

{{ if .System }}{{ .System }}
{{- end }}
{{- if .Tools }}When you receive a tool call response, use the output to format an answer to the orginal user question.

You are a helpful assistant with tool calling capabilities.
{{- end }}<|eot_id|>
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 }}
{{- if eq .Role "user" }}<|start_header_id|>user<|end_header_id|>
{{- if and $.Tools $last }}

Given the following functions, please respond with a JSON for a function call with its proper arguments that best answers the given prompt.

Respond in the format {"name": function name, "parameters": dictionary of argument name and its value}. Do not use variables.

{{ range $.Tools }}
{{- . }}
{{ end }}
{{ .Content }}<|eot_id|>
{{- else }}

{{ .Content }}<|eot_id|>
{{- end }}{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- else if eq .Role "assistant" }}<|start_header_id|>assistant<|end_header_id|>
{{- if .ToolCalls }}
{{ range .ToolCalls }}
{"name": "{{ .Function.Name }}", "parameters": {{ .Function.Arguments }}}{{ end }}
{{- else }}

{{ .Content }}
{{- end }}{{ if not $last }}<|eot_id|>{{ end }}
{{- else if eq .Role "tool" }}<|start_header_id|>ipython<|end_header_id|>

{{ .Content }}<|eot_id|>{{ if $last }}<|start_header_id|>assistant<|end_header_id|>

{{ end }}
{{- end }}
{{- end }}
```

</details>

<details>
<summary><code>ollama show --template qwen3:8b</code></summary>

```gotemplate
{{- $lastUserIdx := -1 -}}
{{- range $idx, $msg := .Messages -}}
{{- if eq $msg.Role "user" }}{{ $lastUserIdx = $idx }}{{ end -}}
{{- end }}
{{- if or .System .Tools }}<|im_start|>system
{{ if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end -}}
<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}
{{- if and $.IsThinkSet (eq $i $lastUserIdx) }}
   {{- if $.Think -}}
      {{- " "}}/think
   {{- else -}}
      {{- " "}}/no_think
   {{- end -}}
{{- end }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if (and $.IsThinkSet (and .Thinking (or $last (gt $i $lastUserIdx)))) -}}
<think>{{ .Thinking }}</think>
{{ end -}}
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ if and $.IsThinkSet (not $.Think) -}}
<think>

</think>

{{ end -}}
{{ end }}
{{- end }}
```

</details>

### What the diff teaches

**1. Delimiter strategy — the single biggest reliability factor** (mechanism in §4).

- **qwen3** wraps calls in `<tool_call>…</tool_call>` sentinels. Trained tags, unambiguous signal.
- **llama3.2** has *no delimiter at all* — bare JSON plus a prose instruction. Note it does **not**
  use `<|python_tag|>`; that token belongs to Llama's *official* built-in tool format, not this
  template.
- Consequence: on llama3.2 the tool-call-vs-text decision is resolved by **post-hoc parsing of free
  text**. That, plus 3B parameters, is why small Llama tool-calling is unreliable — the failure is
  structural, not a prompting problem.

**2. Where tools are injected** — the caching consequence (§6).

- **qwen3** puts tools in the **system** block. Stable across turns → cache-friendly prefix.
- **llama3.2** splices tools into the **last user message** (`if and $.Tools $last`). The block
  *moves* every turn, defeating prefix caching and re-tokenizing schemas at a new position each time.

**3. Argument key naming.** llama3.2 says `"parameters"`, qwen3 says `"arguments"`. Same concept,
incompatible wire formats — exactly what a provider abstraction layer exists to paper over.

**4. Tool-result role.** llama3.2 has a dedicated `ipython` header; qwen3 has **no tool role at all**
and smuggles results back as a **user** turn wrapped in `<tool_response>`. Matters when reasoning
about how the model attends to its own tool output.

**5. Thinking modes.** qwen3's template carries `/think`, `/no_think`, and `<think>…</think>` blocks
— reasoning tokens are part of the same undifferentiated stream (§2), consume the same budget (§6),
and interleave with tool calls. Not covered in depth here; see the substrate roadmap in §11.

---

## 6. Token economics

Direct consequence of §2: schemas are tokens, and tokens are re-sent.

- **Tool schemas go over the wire on every single call.** The API is stateless.
- A 20-turn conversation with 8k tokens of tools = **160k input tokens** of pure re-transmission.
- Real numbers: GitHub's official MCP server alone is ~42k tokens of tool definitions. Four or five
  servers stacked hits 60k+ before the user types anything.

### Four mitigations, in order of reach-for-it-ness

1. **Prompt caching** — the correct default.
   - Order the request `[system, tools, …stable…, volatile user input]`, breakpoint after tools.
   - Cached prefix reads cost ~10% of input rate.
   - Requires building the tools array **once** and never mutating it mid-session — any byte change
     invalidates the prefix.
   - Locally, Ollama doesn't bill you, but prefix KV-cache reuse gives the same latency win — and
     **qwen3's template permits it while llama3.2's does not** (§5, point 2).
2. **Tool subsetting / retrieval over tools** — embed descriptions, retrieve top-k, inject only
   those. Cheap and effective, but it fights caching (prefix changes per turn), so subset *per
   session*, not per turn. (Retrieval mechanics: [`RAG/`](../RAG/README.md).)
3. **Lazy / two-pass schema loading** — pass 1 sends names + one-line descriptions (~300–500
   tokens); when the model picks one, pass 2 sends its full schema. ~10× reduction on turns that use
   no tools. Claude Code's own harness works this way — most tools are listed by name only and
   require a `ToolSearch` call before they become callable.
4. **Code mode** — expose one `execute_code` tool plus an API surface instead of N schemas.
   Collapses schema overhead and lets the model compose calls, filter results, and loop *inside one
   turn* rather than round-tripping every intermediate result through context.

---

## 7. The harness

Everything from §1–§6 is the *atom*. The harness is what surrounds it.

> `Agent = Model + Harness`

Term borrowed from *test harness* in software engineering (the rig you strap around a component to
exercise it) and *evaluation harness* in ML (`lm-evaluation-harness`). Both senses carry: it's the
apparatus that holds the model and drives it.

### What a harness contains

- **The loop** (§1) — and its exit conditions, turn budget, cost caps
- **Context assembly** — what enters the window each turn, in what order
- **Tool registry + dispatch** (§3) — schema generation, routing, validation, sandboxing
- **The error surface** (§3) — what the model *sees* on failure. A design decision, not an accident
- **State and session management** — persistence, resumption, compaction / truncation policy
- **Permissions and approvals** — what executes freely, what needs a human
- **Control affordances** — streaming, cancellation, interruption, steering mid-flight
- **Observability** — tracing, replay, token accounting
- **Provider adapters** — the abstraction over `"parameters"` vs `"arguments"` (§5, point 3)

### Three terms, kept distinct

| Term | Meaning |
|---|---|
| **Framework** | A reusable library for building harnesses — LangGraph, smolagents |
| **Harness** | The concrete runtime of one specific agent — Claude Code, Amp |
| **Scaffolding** | Any harness component that exists to make the *model* succeed, as opposed to making the *system* safe or observable. The subject of §8 |

You can build a harness with no framework at all. Ball's 400 lines *are* a harness.

### Harness engineering

Built on one empirical observation:

> At fixed weights, the harness explains most of the variance in agent quality.

The same model scores wildly differently on the same benchmark under different harnesses. The job is
maximizing capability elicited from weights you don't control. Two levers:

1. **What's in the context window at decision time** — and, more importantly, what isn't. Now
   usually called *context engineering*.
2. **What the environment returns after an action** — the model's only feedback signal. The
   underrated lever, and the one bounded entirely by your design (§3, "errors are prompts").

---

## 8. Compensating, structural, evidentiary

The lens the rest of both documents use. Three kinds of scaffolding, distinguished by **what makes
them necessary**.

| Kind | Exists because | Fate as models improve |
|---|---|---|
| **Compensating** | The model can't do something | **Decays** — delete it later |
| **Structural** | Authority must be bounded regardless of capability | **Permanent** |
| **Evidentiary** | Behavior must be *provable*, not merely correct | **Permanent, orthogonal** |

### The test

> **If the model were actively adversarial, would this still hold?**
> **Yes → structural. No → compensating — and probably also a security hole.**

- A retry loop, a planner, a JSON repairer: all fail the test. They assume cooperation.
- A sandbox, a scoped credential, an egress filter: all pass. They don't consult the model's
  judgment at all.

### The evidentiary category

- Audit logs, approval records, deterministic filters, immutable traces.
- Their job is **not** to change what happens — it's to make what happened provable.
- Invisible to a purely capability-based analysis, and they never decay: a content filter may be
  behaviorally redundant against a well-aligned model and still be **required**, because *"we asked
  it nicely and it's usually good"* is not an audit artifact.

### Why this matters

> **Scaffolding that compensates for model weakness has a half-life.**

- Frameworks that hard-code compensation age badly — every capability jump turns their
  differentiator into overhead. The AutoGPT / early-LangChain era was elaborate because GPT-3.5
  needed all of it; most of that machinery became dead weight when models absorbed it.
- Structural and evidentiary scaffolding never decays. A better model never removes the need for an
  approval prompt before `rm -rf`, or for a log proving one was shown.
- **The line is not fixed.** It's a moving frontier, and the durable skill is judgment about where
  it currently sits. Field-level consequences: [Outside §1, §4](../OutsideAnAgent/README.md).

---

## 9. "It's in the weights"

> Notes from [Thorsten Ball's *How to Build an Agent*](https://ampcode.com/notes/how-to-build-an-agent).
> Thesis: *"it's an LLM, a loop, and enough tokens."* True — and load-bearing in a way the article
> doesn't examine, because it only ever runs one model.

The loop in §1 contains exactly **one** control-flow decision: *did the response contain a tool
call?* Everything else that makes it feel like an agent happens inside the model — software you
didn't write, and will have to, if the model stops supplying it.

### What the model silently supplies

- **Stateless replanning** — no plan object exists (§1). The model re-derives "what next" from the
  raw transcript every turn. Weak models drift once tool output dilutes the original goal.
- **Termination** — the exit condition is a proxy, not a completion check (§1). Fails both ways:
  premature stop, or never stopping (a tool name in context is an attractor). A turn cap is a
  circuit breaker, not a fix.
- **Error recovery** — acting on an error string (§3) needs three abilities: read it, attribute it
  to your own prior action, generate a **different** hypothesis. Small models fail the third and
  re-issue the byte-identical call forever.
- **Argument grounding** — chaining `list_files` → `read_file` means copying a literal string from
  one tool's output into the next tool's argument, unmutated. Small models emit *plausible* paths
  instead of *observed* ones (`main.go` when the listing said `cmd/main.go`).
- **Restraint** — knowing when *not* to call a tool (§4, under-calling). BFCL scores it as its own
  category. Ball never mentions it because Claude just does it.
- **Schema conformance under load** — well-formed nested JSON *while* reasoning. Degrades with
  schema depth and context pressure; correct on turn 1, malformed on turn 9.

### The compensation table

Each absent capability forces a specific, predictable piece of **compensating** scaffolding (§8):

| Capability the weights stop providing | Code you now have to write |
|---|---|
| Planning | Explicit plan step; plan stored in state, re-injected every turn |
| Termination | Turn cap, plus an "are we done?" call or a mandatory `finish` tool |
| Recovery | Loop detection (hash last N calls), error-specific hints, retry with forced variation |
| Argument grounding | Validate args against reality *before* dispatch; reject and re-ask |
| Schema conformance | Constrained decoding / GBNF grammar, JSON repair, retry-on-parse-fail |
| Restraint | `tool_choice` gating, classifier pre-step, few-shots of *not* calling |
| Tool selection | Cut to 2–3 tools, or route with a separate model |

- That table is the 3000 lines. **Every row is a control structure re-externalized from the weights
  into your source code.**
- Every row also fails the adversarial test in §8 — which is the formal reason they all decay.

### Why the article structurally cannot tell you this

- One model, one run. Capability and architectural elegance are **perfectly confounded** —
  everything Claude does for free reads as evidence that *agents are simple*.
- Ball's minimalism is therefore a **bet on model improvement**, not merely an aesthetic. It has
  been the winning bet.
- Add a second model and the confound breaks:

> The delta between two models running the **identical** harness is a direct measurement of what the
> weights were doing for free.

- That isn't a limitation of the comparison, it *is* the experiment. An implicit capability can't be
  observed directly — only its absence can. Model-swapping is the only available instrument for
  reading the contents of the black box.

---

## 10. The exchange rate

### Definition

> **Exchange rate** — the substitution ratio between *model capability* and *harness complexity*,
> holding task success constant.
>
> Fix a task set `T`, an architecture `A`, and a target success rate `s`. For a model `M`, let
> `E(M)` be the minimum scaffolding `S` such that `success(A + S, M, T) ≥ s`. The exchange rate is
> `ΔE / ΔM` — how much scaffolding must be added to buy back one unit of lost model capability.

- Borrowed from economics: a **marginal rate of technical substitution** along a constant-success
  isoquant. Capability and scaffolding are substitutable inputs to the same output.
- Units for `E`: lines of harness code, extra LLM calls per task, or tokens per task. Pick one and
  it becomes measurable.
- Key property: **`E` is a function of the triple `(M, A, T)`, not of the model alone.** That is why
  no leaderboard reports it.

### The ladder — what breaks, in what order

Approximate; an estimate to be tested, not a published finding.

| Tier | What still works | What you must add |
|---|---|---|
| **Frontier** (Claude / GPT-5 class) | §1's loop verbatim; chains, recovery, restraint all free | Nothing for a demo. Structural scaffolding only |
| **Strong open, 30–70B** (`qwen3:30b`, llama3.3:70b) | Reliable structured calls; 2–3 step chains mostly hold | Turn cap, loop detection, tools ≤ ~10 |
| **Mid, 7–14B** (`qwen3:8b`, `llama3.1`) | Single call reliable *given delimiters*; chains fray past 2 steps; recovery ≈ 0 | Plan injection, arg validation, few-shots in descriptions, trim tool results |
| **Small, ~3B** (`llama3.2:latest`) | Tool-call *emission itself* unreliable — no delimiter (§5) | Constrained decoding / grammar, or a single forced call instead of multi-tool |

- The bottom row causes a specific and common debugging confusion: **at 3B with that template you
  are not testing your agent, you are testing Ollama's parser.** The loop can be flawless and the run
  still fails because the model wrote prose *containing* JSON. People tune prompts for days against
  what is actually a delimiter problem — §5 catches it before you write a line.

### Why it isn't published

- BFCL measures single-turn tool selection. SWE-bench measures end-to-end task success. τ-bench is
  the closest proxy for multi-turn agentic behavior.
- None answer *"how much scaffolding does model X need under architecture Y to hit rate Z?"* —
  because that's a property of the triple.
- Every benchmark **holds the harness fixed and varies the model**. Measuring `E` requires the
  opposite.

### The cost curve is non-monotonic

- Scaffolding isn't free at inference: plan steps, validation retries, loop-breaking re-prompts, and
  "are we done?" checks are all **extra LLM calls**.
- A model 10× cheaper per token that needs 4× the calls and 3× the context is not 10× cheaper. Often
  not cheaper at all — and always slower and less reliable.
- The "use a small model to save money" instinct fails precisely because `E` is invisible at
  procurement time.

### Experiment to run

- Four rungs already local: `llama3.2` (3B), `llama3.1` (8B), `qwen3:8b`, `qwen3:30b`.
- One loop (§1), four models, one fixed task. Measure where each rung breaks and the minimum
  scaffolding that restores it.
- Same comparative methodology as the faithfulness suite in `Prompt Writing/`.
- Output: the exchange-rate table for this setup — the thing nobody has published.

---

## 11. What's durable inside an agent

The harness proper (§7) — per-turn concerns that survive capability improvements.

- **Context engineering** — what enters the window, compaction policy, what spills to disk behind a
  handle, what gets re-retrieved. *Gets harder as models improve*: better models get handed bigger
  tasks, so context pressure rises with capability. Longer windows don't rescue you — attention
  degrades over distance, relevance dilutes, cost is superlinear in practice.
- **Environment / tool design** — the action space is entirely yours (§3). A better model *exploits
  a better environment harder*, so the investment appreciates.
- **The error surface** — errors are prompts (§3); error text is a control mechanism.
- **Memory** — mostly a subset of context engineering, plus an unsolved product problem: what to
  remember, when to forget, how to stop stale memory from poisoning behavior.
- **Termination & budget** — turn caps, cost caps, loop breaking. Structural, not compensating.
- **Dispatch-time permission gating** — the enforcement point where a call is allowed or blocked.
- **Provider adapters** — template, delimiter, and wire-format differences (§5).

### Roadmap — named here, not yet written

| Topic | Where it fits |
|---|---|
| **Context engineering mechanics** | Compaction strategies, hierarchical summarization, handles vs. inline, what to drop first |
| **Memory systems** | Episodic vs. semantic, write policies, retrieval triggers, staleness and poisoning |
| **Constrained decoding** | GBNF grammars, Outlines, JSON mode — the real fix for §5's delimiter problem |
| **Model substrate** | Tokenization, sampling, KV cache, quantization, thinking modes, inference servers. *Below* the agent, not inside it — arguably its own directory |

Retrieval as a pattern lives in [`RAG/`](../RAG/README.md); prompting technique in
[`Prompt Writing/`](../Prompt%20Writing/README.md).

---

## Appendix — resources

### Tier 1 — read the source, end to end

| Resource | Why |
|---|---|
| [How to Build an Agent](https://ampcode.com/notes/how-to-build-an-agent) — Thorsten Ball (Amp/Sourcegraph) | ~400 lines of Go, builds a real code-editing agent from an empty file. Single best answer to "what happens inside an agent." Critiqued in §9. Ports: [Python](https://medium.com/@jbrathnayake98/how-to-build-an-agent-by-thorsten-ball-python-version-ebbabb8665f6), [JavaScript](https://kevinyank.com/posts/how-to-build-an-agent-in-javascript/) |
| [huggingface/smolagents](https://github.com/huggingface/smolagents) | A few thousand lines of readable Python. `agents.py` (the loop, §1), `tools.py` (schema generation, §3), model adapters. Also ships `tiny-agents`, an MCP-driven agent in ~70 lines |
| [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | Best code for *how a Python function becomes the JSON Schema the model sees* (§3), and for structured-output-as-a-tool |
| [openai/openai-agents-python](https://github.com/openai/openai-agents-python) | `run.py` is the agent loop with turn limits, guardrails, handoffs. Provider-agnostic — works against Ollama via the OpenAI-compatible endpoint |
| [RajMandaliya/mini-agent](https://github.com/RajMandaliya/mini-agent) | Rust, deliberately minimal: clean ReAct loop, provider abstraction, JSON-schema tools, Ollama support |

### Tier 2 — conceptual scaffolding

| Resource | Why |
|---|---|
| [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) | Skip the workflow-patterns section (multi-agent). Read the part defining agent = LLM in a loop with tools + environment feedback |
| [Model Context Protocol spec](https://modelcontextprotocol.io/) | Worth reading because it *separates tool discovery/transport from the agent loop*. Clarifies which parts of "an agent" are protocol plumbing |
| [Gorilla / Berkeley Function Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) | How tool-selection accuracy is measured — including irrelevance detection (§4, restraint) |
| [τ-bench — Sierra Research](https://github.com/sierra-research/tau-bench) | Closest published proxy for multi-turn agentic behavior (§10) |
| [Tool Attention Is All You Need](https://arxiv.org/html/2604.21816v1) | Dynamic tool gating and lazy schema loading — directly on §6 |

### Tier 3 — ground truth for local models

`ollama show --template <model>`. The Go text/template is the ground truth of how tool schemas get
flattened into the prompt. Everything above it is abstraction. Captured outputs in §5.

### Further reading on token overhead

- [Cutting AI Context Costs at Scale: Tool Overhead, Caching, Compaction](https://www.mindstudio.ai/blog/advanced-context-engineering-token-savings)
- [MCP Tool Overload: Why More Tools Make Your Agent Worse](https://dev.to/thedailyagent/mcp-tool-overload-why-more-tools-make-your-agent-worse-5a49)
- [Comparing Progressive Discovery and Semantic Search for Dynamic MCP](https://www.speakeasy.com/blog/100x-token-reduction-dynamic-toolsets/)

</details>

# Course Plan — Inside an Agent

Build-driven path through §1–§11. **Read one day, build four.** A module is not complete because the
reading is done; it's complete when the artifact runs.

**Where this fits:** modules 0–2 come first in the overall sequence. Module 3 can follow immediately,
but **module 4 requires an eval suite** — do [Outside module 1](../OutsideAnAgent/README.md) before
attempting the capstone.

### Module 0 — Prerequisites (1 week)

The only module with no section behind it. These docs assume it and never teach it.

- **Read:** tokenization (BPE — [RAG §4](../RAG/README.md) is the entry point), sampling parameters,
  KV cache, quantization formats.
- **Build:** a token counter for your own prompts; the same prompt at `temperature` 0 / 0.7 / 1.2 on
  `llama3.2` and `qwen3:8b`; the same model at two quantization levels, output quality diffed.
- **Done when:** she can explain why 8k tokens of tool schemas cost what they cost, and what changes
  when a prefix is cached.

### Module 1 — Mechanism (2 weeks) → §1–§6

- **Read:** §1 → §6, in order. Then Ball's article, typed by hand, not copy-pasted.
- **Build:**
  - Port Ball's agent to Python against Ollama. Three tools: `read_file`, `list_files`, `edit_file`.
  - **Dump every raw `/api/chat` frame to disk.** Read them against the templates in §5 and find the
    exact bytes where the tool schema was interpolated.
- **Then break it deliberately**, one at a time, naming the §4 failure mode each induces:
  - Remove the tool delimiter
  - Malform a schema
  - Return `Error: 1` instead of a real message
  - Give two tools near-identical descriptions
- **Done when:** she can point at a raw request body and say which bytes came from which template
  branch, and name which of §4's four failure modes she just caused.

### Module 2 — Harness (2 weeks) → §7, §11

- **Read:** §7 (anatomy, the three terms), §11 (what's durable inside).
- **Build** — add to the module 1 agent, roughly one per day:
  - Turn cap and cost cap
  - Loop detection (hash the last N calls)
  - Dispatch-time permission gate
  - Structured tracing — one span per turn, one per tool call
  - Streaming, then cancellation mid-stream
  - Context compaction when the window fills
- **Then:** add GBNF-constrained tool emission and re-test `llama3.2`.
- **Done when:** `llama3.2` reliably emits tool calls under constrained decoding. She has personally
  moved a model up §10's ladder — the first time the exchange rate is concrete rather than theoretical.

### Module 3 — The lens (1 week) → §8, §9

- **Read:** §8 (compensating / structural / evidentiary), §9 (it's in the weights).
- **Build:** audit her own module 2 harness. Classify every component she added as compensating,
  structural, or evidentiary. Predict which ones a frontier model would make redundant.
- **Done when:** she can defend each classification using the adversarial test in §8, without
  re-reading it.

### Module 4 — Capstone: the exchange rate (1 week) → §10

**Prerequisite:** a working eval suite ([Outside module 1](../OutsideAnAgent/README.md)).

- **Read:** §10 in full.
- **Build** — the experiment §10 proposes:
  - Four rungs, all local: `llama3.2` (3B), `llama3.1` (8B), `qwen3:8b`, `qwen3:30b`
  - One harness. The eval suite as the success criterion.
  - Per rung: add minimum scaffolding from §9's compensation table until it clears the bar.
    Record `E` in extra-LLM-calls-per-task.
- **Done when:** the exchange-rate table exists for this setup — a real measurement nobody has
  published, and the portfolio artifact of the whole path.

> **The lesson that only lands here:** she will have written compensating scaffolding for the 3B rung
> that is dead weight at 30B. §8 *states* that scaffolding has a half-life. This module is where she
> feels it.

### Module 5 — Scaling the tool surface (1 week, advanced) → §6, §8

**Prerequisites:** module 4, plus [RAG modules 1–3](../RAG/README.md) and
[Outside module 2](../OutsideAnAgent/README.md). The tools tax doesn't exist without a real tool
surface, and can't be optimized without cost attribution.

- **Read:** [*Tool Attention Is All You Need: Dynamic Tool Gating and Lazy Schema Loading for
  Eliminating the MCP/Tools Tax in Scalable Agentic Workflows*](https://arxiv.org/html/2604.21816v1).
  Then re-read §6 (mitigations 2 and 3, which the paper formalizes) and §8.
  - Note on the numbers: the 95% token reduction is measured on a **synthetic 120-tool testbed**;
    the downstream metrics (task success, cost, latency) are **projections**, not live-agent
    measurements. The authors flag this themselves.
- **Build:**
  - Grow the tool surface to 50+ — real MCP servers, or synthetic if faster.
  - **Measure the tax on your own setup first**, using Outside module 2's cost attribution. Baseline
    before optimizing.
  - Implement two-phase lazy loading: compact summaries always in context, full schemas promoted on
    demand.
  - Implement ISO-style retrieval gating over tool descriptions (dense embedding + cosine rank —
    the same machinery as [RAG §1B](../RAG/README.md), with tools as the corpus).
  - Measure **three** things, not one: token reduction, **added round-trips**, and end-to-end
    latency and cost.

> Mirror image of §10's cost curve: compensating scaffolding *adds* LLM calls; two-phase loading
> *saves tokens but adds a round trip*. Same curve, opposite direction — whether it nets out is
> empirical, and depends on your tool count.

### Level markers

| Signal | Level |
|---|---|
| Debugs a failing tool call by reading the raw request body | Junior → Mid |
| Predicts a failure mode from the model tier *before* running it | Mid |
| Argues a piece of scaffolding is compensating and should be deleted later | Mid → Senior-track |
