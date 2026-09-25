# M8 · Tool Interfaces

> **Module question:** How do we give the model an API to the world that is safe, correct, and debuggable?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a data-analysis agent calling internal APIs

---

## Opening scene — the tool that failed *successfully*

The data-analysis agent answered a manager's question: *"what's the Q3 pipeline number?"* It called the internal `get_metrics` tool, got a response, and reported the number with confidence.

The number was wrong. The tool had returned `{"status": "ok"}` — with `"value": null` buried inside, because the metric query had timed out upstream. The agent, seeing "ok," reported the *null* as if it were the answer. Nobody caught it until the number appeared in a board deck.

The postmortem was, again, a category error if you read it carelessly: *"the model hallucinated the metric."* It hadn't. It had **trusted a tool that lied about its own success** — a tool whose failure semantics said "ok" when it should have said "error, retryable, here's why." The model was a perfectly honest messenger relaying a dishonest envelope.[tools-fail-emlnp](#tools-fail-emlnp)

This module is about the envelope. The tool interface **is the `model↔action` seam** (M3's output seam) — the boundary where the model's decision becomes an action on the world[toolllm](#toolllm) — and, like every seam, it has a *contract* (what the tool is, what it accepts, what it returns) and a *boundary* (what it's allowed to do). Designing those two — plus the validation that sits on the seam (error semantics, confirmation) — is the difference between an agent that acts on the world and one that acts on the world *safely, correctly, and debuggably*.

> **Failure mode (the module in one line):** treating tools as "functions the model can call" instead of *APIs with a contract and a capability boundary*. A model will happily call a mis-specified tool with hallucinated arguments and trust a lying error code — the interface is the only thing protecting the world from that.

---

## Tools are APIs for a non-deterministic consumer

Here is the reframe that changes how you design tools — and the benchmark literature reached it from the same direction, cataloguing tool use as *"planning, retrieving, and calling APIs"* with an error analysis of what breaks:[api-bank](#api-bank)

**Your tool's consumer is not a human reading your docs. It's a model that reads your *description*, reasons about your tool *statistically*, and generates arguments by *prediction* — not by contract.**[toolformer](#toolformer), [gorilla](#gorilla)

This means tool design is API design, but with three differences that are all disadvantages:

1. **The docstring *is* the documentation.** A human can ask "what does this do?" A model only knows what's in the name, the description, and the schema. If it isn't there, it doesn't exist.[adk-custom-tools](#adk-custom-tools), [metatool](#metatool)
2. **The schema *is* the validation surface.** The model doesn't "know" the argument is required; it infers it from the schema — and will *guess* when the schema is ambiguous (M2's hallucinated args, class 8).[gorilla](#gorilla), [bfcl](#bfcl)
3. **The consumer doesn't check your return value.** A human sees `null` and frowns. The model sees the `status` field and — if you wrote `"ok"` — believes you.[tools-fail-emlnp](#tools-fail-emlnp), [agents-trust-tools-too-much](#agents-trust-tools-too-much)

So the two load-bearing artifacts are the **contract** (name + schema + description) and the **error semantics** (what the return value *means*, and what the model should do with it). The rest of this module is those two things, plus the **boundary** (what the tool is allowed to do at all).

---

## The contract: name, schema, description

The model's entire view of a tool is three things — and documentation alone is enough to drive correct usage, which is why it carries the load:[tool-documentation-zeroshot](#tool-documentation-zeroshot)

| Artifact | What it drives | If it's wrong |
|---|---|---|
| **Name** | *Selection* — which tool to call | The model calls the wrong tool (adjacent-name confusion) |
| **Description** (docstring) | *Selection + timing* — what it's for, when to use it | Over-eager or missed invocation |
| **Schema** (types, required vs. optional, enums) | *Argument generation* — what to pass | Hallucinated or malformed arguments |

ADK turns a plain function into a tool and takes the contract from its signature and docstring: the function name is the tool name, the docstring is the description, and the typed parameters become the schema (`FunctionTool(func=...)` in Python; explicit `parameters` schema in TypeScript/Go/Java).[adk-custom-tools](#adk-custom-tools), [adk-function-tools](#adk-function-tools)

**The simplicity rules** (from the ADK docs — they matter because the model is the client):[adk-custom-tools](#adk-custom-tools)

- **One task per tool.** A `do_everything` tool is a selection and argument nightmare. `update_user_profile(profile: ProfileObject)` becomes three tools: `update_user_name`, `update_user_address`, `update_user_preferences`.
- **Few parameters, simple types.** The model reliably fills `(str, int, bool)`; it reliably *mis-fills* deeply nested objects[parambench](#parambench) and long optional lists.[unsupported](#unsupported) (cf. [nestools](#nestools), [nestful](#nestful) — "nested" in the literature usually means nested *calls*; see §Where the literature disagrees.)
- **Enums over free text, required over optional.** If a field can only be `daily | weekly | monthly`, say so in the schema — "say so" is literally the only way the model will know.

**The description drives *when*, not just *what*.** The docstring "look up an order's status" tells the model *what*; the added sentence "use only when the user explicitly asks about a specific order and provides an ID" tells it *when*.[adk-custom-tools](#adk-custom-tools) That second sentence is what prevents over-eager invocation[metatool](#metatool) — and it's part of the contract, not the instruction (M6's per-tool authority, stated where the tool lives).

> **ADK at a glance:** tools can also be provided **dynamically**, by *context*, via a `BaseToolset` — its `get_tools(readonly_context)` decides which tools to expose based on session state or user.[adk-custom-tools](#adk-custom-tools) This is least-privilege at the *surface* level: the sales user simply never sees the admin tool. The tool list itself becomes a permission boundary.

---

## Error semantics: what a failure *means* to the model

This is where the opening scene lives, and it is the most under-designed part of most tool surfaces. The rule:

> **A tool must never fail silently, and the model must be *told* what to do with each kind of return.**

The ADK docs say it directly:[adk-custom-tools](#adk-custom-tools) *"instruct the agent on how to handle different return values… whether the agent should retry, give up, or request additional information."* That's not a suggestion — it's the error-semantics contract.

A tool's return value should distinguish, in *structure* not just prose:[tools-fail-emlnp](#tools-fail-emlnp)

- **Success** — `{"status": "success", ...actual data}`.
- **Retryable failure** — `{"status": "error", "error_type": "timeout", "retryable": true, "message": ...}` → the model should retry (with the instruction saying so).[when-tools-fail](#when-tools-fail), [critictool](#critictool)
- **Fatal failure** — `{"status": "error", "retryable": false, "message": "metric not found"}` → the model should stop and tell the user.
- **Needs input** — `{"status": "needs_input", "message": "which date range?"}` → the model should ask the user.

And the instruction maps each to an action — the model can only self-correct against feedback it can read, which is why the feedback has to be *informative* rather than merely present.[critic](#critic) The weather example from the docs is the canonical pattern:[adk-custom-tools](#adk-custom-tools) *"if `get_weather_report` returns 'success', report it; if it returns 'error', tell the user it's unavailable and ask for another city."*

**The worst case is the "ok with null."** A tool that says `status: ok` while the real operation failed trains the model to trust a lie.[tools-fail-emlnp](#tools-fail-emlnp), [agents-trust-tools-too-much](#agents-trust-tools-too-much), [toolsword](#toolsword) The contract's first law: **the status field must reflect the *operation*, not the *return**.* If the query timed out, the status is `error`, full stop.[own-synthesis](#own-synthesis)

---

## Capability boundaries & least privilege

The contract says what the tool *does*; the boundary says what it's *allowed* to do — and once a tool sits in a pipeline, a compromised or mis-specified call can act on data it was never meant to see,[indirect-prompt-injection](#indirect-prompt-injection) so the boundary bounds the blast radius as much as the action. You have already seen the canonical failure — the Chevrolet bot (M2's catalog) had a *quote* tool that could *commit a transaction*.[over-privileged-tool-selection](#over-privileged-tool-selection) The boundary is what turns that from a design accident into a design decision:

1. **Least privilege at the tool level.** A tool should be able to do the *least* it needs: read, not write; quote, not transact; propose, not execute.[saltzer-schroeder-1975](#saltzer-schroeder-1975), [progent](#progent) Every tool's authority is a decision, not a default.
2. **Scoped credentials, per tool.** The `read_metrics` tool gets a read-only database role; the `update_dashboard` tool gets a write role — and nothing else. (ADK's `ToolContext` auth flow — `request_credential` / `get_auth_response` — exists precisely so credentials are scoped per-tool, not ambient.)[adk-context](#adk-context), [progent](#progent)
3. **Sandboxing.** A tool that executes code or touches the filesystem runs in a sandbox with bounded resources — the tool is an *attack surface* (M14's subject, foreshadowed), and the sandbox is the boundary.[toolemu](#toolemu), [mcp-safety-audit](#mcp-safety-audit)
4. **Human confirmation on irreversible actions.** The formal mechanism for the restart rule from M6: ADK's `FunctionTool(..., require_confirmation=True)` pauses the tool for a yes/no from a human, and a *threshold function* (`require_confirmation=confirmation_threshold`) makes it conditional — *"confirm only if `amount > 1000`."*[adk-confirmation](#adk-confirmation), [adk-custom-tools](#adk-custom-tools) A `reimburse` tool that always confirms is slow; one that confirms only above the threshold is both safe and fast.[magentic-ui](#magentic-ui), [progent](#progent) This is the "human approval on irreversible actions" line from the governance diagram, made concrete.[adk-hitl-pattern](#adk-hitl-pattern)

The **capability matrix** is how you make all of this explicit and reviewable — a table of tool × (authority, scope, confirmation) that a team can audit. It's the design exercise's deliverable — and it is exactly the artifact a measured tendency to over-select privileged tools argues for, since general safety alignment does not reliably produce least-privilege choices.[over-privileged-tool-selection](#over-privileged-tool-selection), [biasbusters](#biasbusters)

---

## The tool-call failure modes (M2 class 8, made concrete)

Every tool failure is one of these five, and each maps to a contract/boundary decision:[beyond-the-leaderboard](#beyond-the-leaderboard)

| Failure | What it is | Signature | Fix |
|---|---|---|---|
| **Hallucinated args** | The model invents a parameter | `send_email(to="customer@example.com")` where the address came from nowhere | Required schema, enums, "never invent" in the description; validate in the tool[gorilla](#gorilla), [bfcl](#bfcl) |
| **Wrong tool** | Adjacent-name confusion | Calls `update_user_name` when it meant `update_user_address` | Distinct names, per-tool descriptions[metatool](#metatool), [rag-mcp](#rag-mcp) |
| **Over-eager invocation** | Calls when it shouldn't | Fires `lookup` for every message | "Use only when…" in the description[metatool](#metatool); the named failure is **Tool Overuse** — *"models unnecessarily rely on external tools for tasks solvable with parametric knowledge"[smart-tool-overuse](#smart-tool-overuse), [adaptive-tool-use-metacognition](#adaptive-tool-use-metacognition) |
| **Tool loop** | Same call, rephrased, forever | 14 near-identical searches | Budgets, stop conditions (M10/M13)[infinite-agentic-loops](#infinite-agentic-loops) |

> **The loop is not a new failure — ReAct named it in 2022.** It reports *"one frequent error pattern specific to ReAct, in which the model repetitively generates the previous thoughts and actions,"* which its failure-mode table counts as a reasoning error — *"wrong reasoning trace (including failing to recover from repetitive steps)"* — at **47% for ReAct vs 16% for CoT**.[react](#react) What is new at scale is the harness-level view: IAL-Scan finds the same pattern as a *structural* property of the feedback path rather than a model mistake — an agent that *"repeatedly execute[s] model calls, tools, workflow transitions, or agent handoffs when the feedback path is not effectively bounded"* — and confirms 68 such failures across 47 real projects.[infinite-agentic-loops](#infinite-agentic-loops) That is why the fix belongs in the harness (budgets, stop conditions), not only in the prompt.
| **Poisoned results** | The tool returns wrong data, the model propagates it | The opening scene's "ok with null" | Error semantics + validate tool output at the seam[tools-fail-emlnp](#tools-fail-emlnp), [agents-trust-tools-too-much](#agents-trust-tools-too-much) |

Note the through-line to M2's attribution: when a tool call goes wrong, the question is *"which part of the contract or boundary let it through?"* — not "the model misused the tool." The model is the probabilistic consumer; the contract is the deterministic guardrail.

---

## Worked example: the data-analysis agent

The domain spine, with the three disciplines applied.

**The read tool (contract + error semantics):**
```python
def query_metrics(metric: str, date_range: str) -> dict:
    """Return a metric for a date range. Use only when the user names a
    specific metric and range. READ-ONLY."""
    result = fetch_metric(metric, date_range)   # internal API
    if result.timed_out:
        return {"status": "error", "error_type": "timeout",
                "retryable": True, "message": "upstream timeout"}
    if result.missing:
        return {"status": "error", "retryable": False,
                "message": f"metric '{metric}' not found"}
    return {"status": "success", "value": result.value, "unit": result.unit}
```
The instruction maps the returns: *"if 'timeout', retry once; if 'not found', tell the user and ask for another metric; if 'success', report value with its unit."* The opening scene's `ok-with-null` cannot happen here — the status reflects the operation.

**The write tool (boundary + confirmation):**
```python
def update_dashboard(dashboard_id: str, config: dict) -> dict:
    """Update a dashboard's configuration. WRITE — requires confirmation."""
    ...
```
Wired as `FunctionTool(update_dashboard, require_confirmation=True)`. The agent can *propose* the update, but a human confirms before it lands. Reversible read, confirmed write — the capability boundary is now an artifact, not an assumption.

**The capability matrix:**
| Tool | Authority | Scope | Confirmation |
|---|---|---|---|
| `query_metrics` | read | read-only DB role | none |
| `update_dashboard` | write | write role, single dashboard | always |

Three disciplines — contract, error semantics, boundary — each visible, each reviewable, each tied to a failure it prevents. That's what "tool interfaces" means.

> **Tradeoff (the ledger entry):**
> - **Capability vs. safety.** Every tool you add is capability *and* attack surface. Breadth buys usefulness and sells safety — the matrix is how you make the trade explicit.
> - **Autonomy vs. confirmation latency.** Confirmation makes irreversible actions safe and slow. The threshold function (`confirm only above $1000`) is the compromise: automatic for the routine, gated for the consequential.
> - **Rich description vs. precision.** A long description guides selection but competes for attention (M4) and invites drift (M6).[tooltweak](#tooltweak), [metatool](#metatool) Describe *when* and *what*, tersely.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** Write the tool contract + capability matrix for an internal API (or use this brief: an agent that reads customer data and may *anonymize* records on a privacy request).

1. **The contract.** Pick two tools (one read, one write/irreversible). For each: the name, the description (with the "use only when…" clause), and the schema (typed, enums where possible). Write them as you'd hand them to `FunctionTool`.
2. **The error semantics.** For the read tool, write its full return-value contract — success, retryable failure, fatal failure, needs-input — and the *instruction line* that maps each to an action. Make sure no path returns "ok" while actually failing.
3. **The capability matrix.** Fill the tool × (authority, scope, confirmation) table for *all* tools the agent would have — including the one you'd deliberately *not* expose to everyone.
4. **Adversarially review it.** List three ways the model (or a user steering it) could misuse each tool — hallucinated args, wrong tool, over-eager call, poisoned result. For each, name the contract/boundary element that catches it. If none does, that's a gap: flag it.
5. **The derivation check.** Is there any fact this agent currently asks the *model* to compute that a tool should compute instead? (The discussion's "stop deriving in the model.") Name it, and write the one-line tool that would own it.
6. **Write the ADR.** "Tool surface & authority boundary" — what's exposed, to whom, with what confirmation, and the residual risk you're accepting.

**Why this exercise matters.** The tool interface is where the harness's *safety* is actually decided — not in the model, not in the prompt, but in the contracts and boundaries you write around the model's reach. This exercise is the whole module, done once by hand.

---

**In DSH:** tools are `core/tools` — a *scoped* registry with a guarded execution pipeline (`tools/pre-execute` → `execute` → `post-execute`), and every tool's schema joins prompt assembly (the contract, at DSH's seams).

## Where the literature disagrees

*Seven places where the sources contest, weaken, or correct this module's claims. Each quotes its source rather than paraphrasing it.*

1. **The "deeply nested objects" claim is real — but it was mis-sourced, and it is half a claim.** The module says the model "reliably *mis-fills* deeply nested objects and long optional lists," citing the ADK docs as the warrant. The ADK docs do assert the guideline — *"Prefer basic types … over complex custom classes or deeply nested structures as parameters when possible"*[adk-custom-tools](#adk-custom-tools) — but that is vendor advice. The measured owner is ParamBench, which grades difficulty *by exactly this axis*: ParamBench *"categorizes every instance into five difficulty levels according to parameter nesting depth, cross-parameter dependencies, and the reasoning required to derive values from earlier calls,"* and its motivation is that parameter filling has *"received far less attention"* than tool selection — *"In domains such as cloud networking, even frontier models correctly complete fewer than half of tool calls."*[parambench](#parambench) A related construct has a peer-reviewed owner too: NesTools measures *nested tool calls* — *"LLMs may call multiple tools in nested orders, where the latter tool call may take the former response as its input parameters"*[nestools](#nestools) — which is nesting *across* calls, not inside one schema. **To change:** cite ParamBench for nesting depth, NesTools for nested calls, and the ADK docs for the rule. **Drop "long optional parameter lists": no located source measures optional-arity at all** — that component belongs in the unsupported bucket, not behind a citation.

2. **"Too many tools" is really "too small a budget."** The module implies that tool count itself degrades selection. The literature says the dominant mechanism is context budget, not count. Tool-Schema Compression isolates it: *"at 32K — where both formats fit — four of five tested models show delta <= 1 pp, confirming the effect is purely budget-driven."*[sakizli-tool-schema-compression](#sakizli-tool-schema-compression) Less-is-More reaches a compatible conclusion by a different route — *"selectively reducing the number of tools available to LLMs significantly improves their function-calling performance"* — but on edge hardware, where budget and count are confounded.[paramanayakam-less-is-more](#paramanayakam-less-is-more) RAG-MCP supplies the raw magnitude: cutting the tool list to the retrieved candidates *"more than triple[s] tool selection accuracy (43.13% vs 13.62% baseline)."*[rag-mcp](#rag-mcp) And How Many Tools Should an LLM Agent See? adds the counter-pressure the module omits: *"Show too few and the correct tool may not appear"* — on ToolBench a *"fixed shortlist of 5 tools achieves higher aggregate coverage (64.7% vs 61.9%) but finds nothing on hard queries."*[repantis-how-many-tools](#repantis-how-many-tools) **To change:** the tradeoff should be stated as a *budget/recall* tradeoff, not a count monotonicity. More tools is not itself the harm; exhausting the window and losing the correct candidate are.

3. **A benchmark's "poor tool use" headline is not the tool-failure taxonomy.** The module leans on M2's failure classes and on "ToolEmu-style" red-teaming. ToolEmu is real and owns LM-agent risk measurement — *"68.8% of failures identified with ToolEmu would be valid real-world agent failures,"* and *"even the safest LM agent exhibits such failures 23.9% of the time"*[toolemu](#toolemu) — but it measures *risk and harm*, not tool-execution errors or retry behavior. Neither ToolEmu nor any located paper owns a "retryable vs fatal" tool-error taxonomy. **To change:** cite ToolEmu for action risk only. For the taxonomy, the nearest owners are ToolMaze's transient/permanent axis — *"temporal persistence distinguishes transient failures resolvable via simple retries from permanent ones that force dynamic rerouting or graceful termination"*[when-tools-fail](#when-tools-fail) — and CRITICTOOL's policy binding, *"reflect and correct for internal model-driven errors, and retry with skip or finish for external environment errors."*[critictool](#critictool)

4. **Selection is not only a readability problem — it is an attack surface.** The module treats tool metadata as a contract to be *written well*. ToolTweak shows metadata is also an adversarial channel: rewriting *"tool names and descriptions"* moves *"selection rates from a baseline of around 20% to as high as 81%, with strong transferability between open-source and closed-source models."*[tooltweak](#tooltweak) MetaTool independently reaches the authoring conclusion — *"we strongly recommend that tool developers choose an appropriate rewrite model for generating new descriptions based on the downstream LLM the tool will apply to"*[metatool](#metatool) — while two attacks weaponize the same surface: Tool Poisoning Attacks puts *"hidden malicious instructions"* inside a tool description,[tool-poisoning-attacks](#tool-poisoning-attacks) and ToolHijacker goes further by *"inject[ing] a malicious tool document into the tool library"* to hijack selection outright, with *"prevention-based defenses (StruQ and SecAlign) and detection-based defenses … insufficient."*[toolhijacker](#toolhijacker) BiasBusters isolates why the surface is so sensitive: *"semantic alignment between user queries and tool metadata is the strongest driver of selection"* and *"small perturbations to tool descriptions can significantly shift choices."*[biasbusters](#biasbusters) **To change:** the contract section should name metadata as *untrusted input* that can be poisoned after approval, not just as documentation to be authored.

5. **The confirmation gate is a design pattern, not a portable primitive.** The module presents `require_confirmation` plus a threshold function as *"the formal mechanism,"* with `ToolContext` auth as scoping "per-tool, not ambient." The ADK docs qualify both. Confirmation is flagged **Experimental**, carries *"known limitations"* (`DatabaseSessionService` and `VertexAiSessionService` unsupported), and by binding it is not uniform — *"In TypeScript, you implement this logic manually within the `execute` function"* and *"ADK for TypeScript currently requires manual implementation of confirmation logic."*[adk-confirmation](#adk-confirmation) Likewise Java's auth support is incomplete: *"Note: AuthConfig, requestCredential, and getAuthResponse are not yet fully implemented in the Java ADK public API."*[adk-context](#adk-context) **To change:** state the pattern, then state the portability caveat. Magentic-UI owns the generalization — it *"presents six interaction mechanisms for enabling effective, low-cost human involvement: co-planning, co-tasking, multi-tasking, action guards, and long-term memory"*[magentic-ui](#magentic-ui) — and Progent owns the enforcement variant, where a policy update is *"either a narrowing (applied automatically) or an expansion (requiring explicit approval), ensuring that the agent's effective action space can only shrink without approval (monotonic confinement)."*[progent](#progent)

6. **The failing loop is documented, but the *diagnosis* the module implies is only half the story.** This module lists "tool loop" as a model-side failure to be fixed with budgets and stop conditions. ReAct documented the symptom in 2022 — *"the model repetitively generates the previous thoughts and actions"*[react](#react) — but a static-analysis study of 6,549 real agent repositories finds the same behaviour as a **structural** defect rather than a model mistake: agents repeat *"model calls, tools, workflow transitions, or agent handoffs when the feedback path is not effectively bounded,"* with 68 confirmed failures across 47 projects.[infinite-agentic-loops](#infinite-agentic-loops) **To change:** budget the *feedback path*, not just the loop count. A prompt-level "don't repeat yourself" does not bound a path the harness never closed.

7. **A reviewed capability matrix does not by itself hold the boundary.** The module's deliverable is a static, auditable tool × (authority, scope, confirmation) table, and it frames least privilege as a design choice made once. ToolPrivBench measures the failure the matrix cannot see: *"over-privileged tool selection is common among mainstream LLM agents and is further amplified by transient failures,"* and *"general safety alignment does not reliably transfer to least-privilege tool choice, while prompt-level controls provide only limited mitigation under transient failures."*[over-privileged-tool-selection](#over-privileged-tool-selection) The escalation trigger is exactly this module's own error semantics — a retryable failure that tempts the agent toward a bigger hammer. **To change:** keep the matrix as the design artifact, but pair it with runtime enforcement on the *call path* rather than trusting a reviewed table — Progent's deterministic per-call check against symbolic rules,[progent](#progent) or a post-training defense that *"teaches agents to prefer sufficient lower-privilege tools and escalate only when necessary."*[over-privileged-tool-selection](#over-privileged-tool-selection)

---

## Sources (ADK docs)

### Framework documentation (industry docs)

- <a id="adk-custom-tools"></a>[adk-custom-tools](#adk-custom-tools) · [**Custom Tools for ADK — tool lifecycle, contracts, simplicity, toolsets** — Google ADK documentation](https://adk.dev/tools-custom/index.md) (industry doc) — source of the "docstring is the primary source of descriptive information for the LLM" claim, the simplicity rules, and the `BaseToolset`/`get_tools(readonly_context)` dynamic-permission claim.
- <a id="adk-function-tools"></a>[adk-function-tools](#adk-function-tools) · [**Function tools (schemas, descriptions)** — Google ADK documentation](https://adk.dev/tools-custom/function-tools/index.md) (industry doc)
- <a id="adk-confirmation"></a>[adk-confirmation](#adk-confirmation) · [**Get action confirmation — require_confirmation, threshold, human approval** — Google ADK documentation](https://adk.dev/tools-custom/confirmation/index.md) (industry doc) — `require_confirmation=True`, the `confirmation_threshold` function, and the Experimental/known-limitations status.
- <a id="adk-context"></a>[adk-context](#adk-context) · [**Agent context — ToolContext, per-tool auth, scoped credentials** — Google ADK documentation](https://adk.dev/context/index.md) (industry doc) — `request_credential` / `get_auth_response`, and the Java ADK auth gap.
- <a id="adk-hitl-pattern"></a>[adk-hitl-pattern](#adk-hitl-pattern) · [**Workflow patterns — human-in-the-loop** — Google ADK documentation](https://adk.dev/workflows/patterns/) (industry doc)

### Tool-use benchmarks and failure foundations

- <a id="toolllm"></a>[toolllm](#toolllm) · [**ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs** — Yujia Qin, Shihao Liang, Yining Ye, Kunlun Zhu, Lan Yan, Yaxi Lu, Yankai Lin, Xin Cong, Xiangru Tang, Bill Qian, Sihan Zhao, Lauren Hong, Runchu Tian, Ruobing Xie, Jie Zhou, Mark Gerstein, Dahai Li, Zhiyuan Liu, Maosong Sun](https://arxiv.org/abs/2307.16789) — *ICLR*, 2024 (arXiv:2307.16789, 2023). Owns ToolBench (16,464 RapidAPI RESTful APIs across 49 categories), ToolEval, and depth-first-search decision-tree solution-path annotation.
- <a id="api-bank"></a>[api-bank](#api-bank) · [**API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs** — Minghao Li, Yingxiu Zhao, Bowen Yu, Feifan Song, Hangyu Li, Haiyang Yu, Zhoujun Li, Fei Huang, Yongbin Li](https://aclanthology.org/2023.emnlp-main.187/) — *EMNLP*, 2023, pp. 3102–3116 (arXiv:2304.08244). Owns the first runnable tool-use benchmark spanning planning, retrieving, and calling APIs — 73 API tools, 314 dialogues, 753 API calls — with an error analysis naming the obstacles.
- <a id="bfcl"></a>[bfcl](#bfcl) · [**The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of Large Language Models** — Shishir G. Patil, Huanzhi Mao, Fanjia Yan, Charlie Cheng-Jie Ji, Vishnu Suresh, Ion Stoica, Joseph E. Gonzalez](https://proceedings.mlr.press/v267/patil25a.html) — *ICML*, 2025, PMLR 267:48371–48392. Owns the AST-based function-call evaluation method and the abstention / multi-step agentic tracks; *"while state-of-the-art LLMs excel at singleturn calls, memory, dynamic decision-making, and long-horizon reasoning remain open challenges."*
- <a id="gorilla"></a>[gorilla](#gorilla) · [**Gorilla: Large Language Model Connected with Massive APIs** — Shishir G. Patil, Tianjun Zhang, Xin Wang, Joseph E. Gonzalez](https://arxiv.org/abs/2305.15334) — *NeurIPS*, 2024 (arXiv:2305.15334, 2023). Owns APIBench and Retriever-Aware Training, and the hallucinated-argument framing: LLMs are limited by *"their inability to generate accurate input arguments and their tendency to hallucinate the wrong usage of an API call."*
- <a id="toolformer"></a>[toolformer](#toolformer) · [**Toolformer: Language Models Can Teach Themselves to Use Tools** — Timo Schick, Jane Dwivedi-Yu, Roberto Dessì, Roberta Raileanu, Maria Lomeli, Luke Zettlemoyer, Nicola Cancedda, Thomas Scialom](https://arxiv.org/abs/2302.04761) — *NeurIPS*, 2023 (arXiv:2302.04761). Owns self-supervised API-call learning: *"decide which APIs to call, when to call them, what arguments to pass, and how to best incorporate the results."*
- <a id="tool-documentation-zeroshot"></a>[tool-documentation-zeroshot](#tool-documentation-zeroshot) · [**Tool Documentation Enables Zero-Shot Tool-Usage with Large Language Models** — Cheng-Yu Hsieh, Si-An Chen, Chun-Liang Li, Yasuhisa Fujii, Alexander Ratner, Chen-Yu Lee, Ranjay Krishna, Tomas Pfister](https://arxiv.org/abs/2308.00675) — arXiv:2308.00675, 2023. Owns the evidence behind this module's "the docstring *is* the documentation" claim: tool documentation *"for the individual tool usage"* is *"significantly more valuable than demonstrations,"* with zero-shot documentation matching few-shot and *"significantly outperforming few-shot without documentation."*
- <a id="metatool"></a>[metatool](#metatool) · [**MetaTool Benchmark for Large Language Models: Deciding Whether to Use Tools and Which to Use** — Yue Huang, Jiawen Shi, Yuan Li, Chenrui Fan, Siyuan Wu, Qihui Zhang, Yixin Liu, Pan Zhou, Yao Wan, Neil Zhenqiang Gong, Lichao Sun](https://arxiv.org/abs/2310.03128) — *ICLR*, 2024 (arXiv:2310.03128, 2023; v6, 2024). Owns tool-usage *awareness* (whether to call a tool at all) and the tool-selection subtask *"tool selection with similar choices"* — the functionally-adjacent-tool confusion mode — plus the description-rewriting recommendation for tool developers. *(Not to be confused with the unrelated "MetaTool" of arXiv:2407.12871.)*
- <a id="smart-tool-overuse"></a>[smart-tool-overuse](#smart-tool-overuse) · [**SMART: Self-Aware Agent for Tool Overuse Mitigation** — Cheng Qian, Emre Can Acikgoz, Hongru Wang, Xiusi Chen, Avirup Sil, Dilek Hakkani-Tür, Gokhan Tur, Heng Ji](https://arxiv.org/abs/2502.11435) — *Findings of ACL*, 2025 (arXiv:2502.11435). Owns the named failure **Tool Overuse** — *"models unnecessarily rely on external tools for tasks solvable with parametric knowledge, increasing computational overhead"* — plus the SMART-ER dataset and SMARTAgent (tool use −24%, performance +37%).
- <a id="adaptive-tool-use-metacognition"></a>[adaptive-tool-use-metacognition](#adaptive-tool-use-metacognition) · [**Adaptive Tool Use in Large Language Models with Meta-Cognition Trigger** — Wenjun Li, Dexun Li, Kuicai Dong, Cong Zhang, Hao Zhang, Weiwen Liu, Yasheng Wang, Ruiming Tang, Yong Liu](https://arxiv.org/abs/2502.12961) — *ACL*, 2025 (arXiv:2502.12961). Owns the "unnecessary tool calls" framing of the same failure and a metacognition trigger to suppress indiscriminate invocation.
- <a id="parambench"></a>[parambench](#parambench) · [**Getting the Parameters Right: A Difficulty-Graded Benchmark and Probe-Guided Training for LLM Tool Calls** — Guoyao Yu, Xiaoqing Sun, Ziqi Huang, Shaojing Fan, Zhongyi Zhang, Xiaomeng Hu, Xiaobo Xue, Yangyang Shi, Xiong Xiao, Yang Song, Biao Lyu, Rong Wen, Xing Li, Qinming He, Shunming Zhu, Zhenguang Liu](https://arxiv.org/abs/2608.03071) — arXiv:2608.03071, 2026. Owns ParamBench, the benchmark that grades tool-call difficulty by *"parameter nesting depth, cross-parameter dependencies, and the reasoning required to derive values from earlier calls"* — the measured basis for this module's argument-filling claim, and the finding that parameter filling is under-studied relative to tool selection.
- <a id="nestools"></a>[nestools](#nestools) · [**NesTools: A Dataset for Evaluating Nested Tool Learning Abilities of Large Language Models** — Han Han, Tong Zhu, Xiang Zhang, Mengsong Wu, Xiong Hao, Wenliang Chen](https://aclanthology.org/2025.coling-main.657/) — *COLING*, 2025, pp. 9824–9844 (arXiv:2410.11805). Owns nested *tool calls* — where *"the latter tool call may take the former response as its input parameters"* — and the finding that current LLMs still struggle with the task. Distinct from schema nesting; do not conflate.
- <a id="nestful"></a>[nestful](#nestful) · [**NESTFUL: A Benchmark for Evaluating LLMs on Nested Sequences of API Calls** — Kinjal Basu, Ibrahim Abdelaziz, Kiran Kate, Mayank Agarwal, Maxwell Crouse, Yara Rizk, Kelsey Bradford, Asim Munawar, Sadhana Kumaravel, Saurabh Goyal, Xin Wang, Luis A. Lastras, Pavan Kapanipathi](https://arxiv.org/abs/2409.03797) — arXiv:2409.03797, 2024. Owns the measurement of nested *call sequences* where one call's output feeds the next: 1,800+ executable sequences and 28% full-sequence accuracy for the best model.
- <a id="infinite-agentic-loops"></a>[infinite-agentic-loops](#infinite-agentic-loops) · [**When Agents Do Not Stop: Uncovering Infinite Agentic Loops in LLM Agents** — Xinyi Hou, Shenao Wang, Yanjie Zhao, Haoyu Wang](https://arxiv.org/abs/2607.01641) — arXiv:2607.01641, 2026. Owns Infinite Agentic Loops (IALs) and IAL-Scan: an agent may *"repeatedly execute model calls, tools, workflow transitions, or agent handoffs when the feedback path is not effectively bounded"* — 68 confirmed failures across 47 projects at 91.9% precision.
- <a id="beyond-the-leaderboard"></a>[beyond-the-leaderboard](#beyond-the-leaderboard) · [**Beyond the Leaderboard: A Synthesis of Tool-Use, Planning, and Reasoning Failures in Large Language Model Agents** — Wael Albayaydh, Rui Zhao, Ivan Flechais](https://arxiv.org/abs/2607.05775) — arXiv:2607.05775, 2026. Owns the cross-cutting taxonomy synthesized from 27 benchmark, taxonomy, and audit papers, whose first failure cluster is *"tool invocation and parameter-level errors"* — the nearest thing the literature has to a unified home for this module's failure table. Also owns the finding that *"failures compound nonlinearly with task length"* and that *"additional scaffolding does not consistently improve reliability."*
- <a id="react"></a>[react](#react) · [**ReAct: Synergizing Reasoning and Acting in Language Models** — Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik Narasimhan, Yuan Cao](https://arxiv.org/abs/2210.03629) — *ICLR*, 2023 (arXiv:2210.03629, 2022). Owns the interleaved reason-act loop and the finding that tool interaction *"overcomes issues of hallucination and error propagation prevalent in chain-of-thought reasoning."* Cited for that framing only — ReAct does not document non-terminating tool loops.
- <a id="critic"></a>[critic](#critic) · [**CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing** — Zhibin Gou, Zhihong Shao, Yeyun Gong, Yujiu Yang, Minlie Huang, Nan Duan, Weizhu Chen](https://arxiv.org/abs/2305.11738) — *ICLR*, 2024 (arXiv:2305.11738, 2023). Owns tool-interactive self-correction: the model validates and amends its own output against *"external feedback"* — the reverse direction of this module's seam.

### The contract: selection, timing, and arguments

- <a id="rag-mcp"></a>[rag-mcp](#rag-mcp) · [**RAG-MCP: Mitigating Prompt Bloat in LLM Tool Selection via Retrieval-Augmented Generation** — Tiantian Gan, Qiyao Sun](https://arxiv.org/abs/2505.03275) — arXiv:2505.03275, 2025. Owns the measured prompt-bloat/selection tradeoff: cutting prompt tokens by over 50% while raising tool-selection accuracy from 13.62% to 43.13%.
- <a id="repantis-how-many-tools"></a>[repantis-how-many-tools](#repantis-how-many-tools) · [**How Many Tools Should an LLM Agent See? A Chance-Corrected Answer** — Vyzantinos Repantis, Ameya Gawde, Harshvardhan Singh, Joey Blackwell II](https://arxiv.org/abs/2605.24660) — arXiv:2605.24660, 2026. Owns the chance-corrected (Bits-over-Random) metric for shortlist depth and the recall counter-case to "fewer tools": shortlisting trades selection error for recall error.
- <a id="sakizli-tool-schema-compression"></a>[sakizli-tool-schema-compression](#sakizli-tool-schema-compression) · [**Tool-Schema Compression Enables Agentic RAG Under Constrained Context Budgets** — Furkan Sakizli](https://arxiv.org/abs/2605.26165) — arXiv:2605.26165, 2026. Owns the budget-driven isolation: at 32K, where both formats fit, *"four of five tested models show delta <= 1 pp,"* and JSON schemas overflow at ~494 tools versus beyond 800 compressed.
- <a id="paramanayakam-less-is-more"></a>[paramanayakam-less-is-more](#paramanayakam-less-is-more) · [**Less is More: Optimizing Function Calling for LLM Execution on Edge Devices** — Varatheepan Paramanayakam, Andreas Karatzas, Iraklis Anagnostopoulos, Dimitrios Stamoulis](https://arxiv.org/abs/2411.15399) — *DATE*, 2025 (arXiv:2411.15399, 2024). Owns the tool-reduction result on constrained hardware: *"selectively reducing the number of tools available to LLMs significantly improves their function-calling performance, execution time, and power efficiency."*
- <a id="tooltweak"></a>[tooltweak](#tooltweak) · [**ToolTweak: An Attack on Tool Selection in LLM-based Agents** — Jonathan Sneh, Ruomei Yan, Jialin Yu, Philip Torr, Yarin Gal, Sunando Sengupta, Eric Sommerlade, Alasdair Paren, Adel Bibi](https://arxiv.org/abs/2510.02554) — arXiv:2510.02554, 2025. Owns the adversarial result that rewriting tool names and descriptions moves selection rates *"from a baseline of around 20% to as high as 81%"* — tool metadata quality drives selection accuracy, and is attackable.
- <a id="toolhijacker"></a>[toolhijacker](#toolhijacker) · [**Prompt Injection Attack to Tool Selection in LLM Agents** — Jiawen Shi, Zenghui Yuan, Guiyao Tie, Pan Zhou, Neil Zhenqiang Gong, Lichao Sun](https://arxiv.org/abs/2504.19793) — arXiv:2504.19793, 2025. Owns ToolHijacker: injecting a malicious *tool document* into the tool library to force selection of the attacker's tool, plus the negative result that current prevention- and detection-based defenses are *"insufficient."*
- <a id="biasbusters"></a>[biasbusters](#biasbusters) · [**BiasBusters: Uncovering and Mitigating Tool Selection Bias in Large Language Models** — Thierry Blankenstein, Jialin Yu, Zixuan Li, Vassilis Plachouras, Sunando Sengupta, Philip Torr, Yarin Gal, Alasdair Paren, Adel Bibi](https://arxiv.org/abs/2510.00307) — arXiv:2510.00307, 2025 (v2, 2026; arXiv comment states *ICLR 2026 Camera Ready*). Owns the isolation of what actually drives selection: query↔metadata semantic alignment is the strongest factor, small description perturbations shift choices significantly, and repeated pre-training exposure amplifies provider bias.
- <a id="tool-poisoning-attacks"></a>[tool-poisoning-attacks](#tool-poisoning-attacks) · [**MCP Security Notification: Tool Poisoning Attacks** — Luca Beurer-Kellner, Marc Fischer (Invariant Labs)](https://invariantlabs.ai/blog/mcp-security-notification-tool-poisoning-attacks) (industry doc) — 2025. Coins "Tool Poisoning Attack": hidden instructions in tool descriptions, plus "MCP rug pulls" and cross-server "tool shadowing."

### Error semantics

- <a id="tools-fail-emlnp"></a>[tools-fail-emlnp](#tools-fail-emlnp) · [**Tools Fail: Detecting Silent Errors in Faulty Tools** — Jimin Sun, So Yeon Min, Yingshan Chang, Yonatan Bisk](https://aclanthology.org/2024.emnlp-main.790/) — *EMNLP*, 2024, pp. 14272–14289 (arXiv:2406.19228). Owns the silent-tool-error framing that this module's opening scene turns on: *"most ontologies and surveys of tool-use have assumed the core challenge for LLMs is choosing the tool"* — instead the model must detect a silent failure, infer its source, and plan recovery.
- <a id="agents-trust-tools-too-much"></a>[agents-trust-tools-too-much](#agents-trust-tools-too-much) · [**Agents Trust Tools Too Much: Measuring Reliance on Unreliable Tools** — Hoyeol Yang, Woojung Song, Taewon Kim, Jonghyun Song, Seoyeon Park, Yohan Jo](https://arxiv.org/abs/2609.05587) — arXiv:2609.05587, 2026. Owns the magnitude of over-trust in corrupted tool returns across fourteen LLMs: *"the mean adoption rate exceeds one third for every tool and reaches 68.0% for web search,"* with agents that *"recognize conflicts and even recover the correct answer internally, yet present only the corrupted answer without warning the user."*
- <a id="when-tools-fail"></a>[when-tools-fail](#when-tools-fail) · [**When Tools Fail: Benchmarking Dynamic Replanning and Anomaly Recovery in LLM Agents** — Dongsheng Zhu, Xuchen Ma, Yucheng Shen, Xiang Li, Yukun Zhao, Shuaiqiang Wang, Lingyong Yan, Dawei Yin](https://arxiv.org/abs/2606.05806) — arXiv:2606.05806, 2026. Owns ToolMaze: the 2×2 perturbation taxonomy (explicit/implicit × transient/permanent), the transient-vs-permanent recovery mapping, and the measured *"Perturbation Recovery Rate (PRR) plummets by around 37%"* under implicit semantic failures.
- <a id="critictool"></a>[critictool](#critictool) · [**CRITICTOOL: Evaluating Self-Critique Capabilities of Large Language Models in Tool-Calling Error Scenarios** — Sijia Huang, Ziqi Fang, Zheng Chen, Shuai Yuan, Junjie Ye, Yue Zeng, Lei Chen, Qiang Mao, Fang Zhao](https://arxiv.org/abs/2506.13977) — arXiv:2506.13977, 2025. Owns the explicit error-class → recovery-policy binding: *"reflect and correct for internal model-driven errors, and retry with skip or finish for external environment errors."*
- <a id="toolsword"></a>[toolsword](#toolsword) · [**ToolSword: Unveiling Safety Issues of Large Language Models in Tool Learning Across Three Stages** — Junjie Ye, Sixian Li, Guanyu Li, Caishuang Huang, Songyang Gao, Yilong Wu, Qi Zhang, Tao Gui, Xuanjing Huang](https://aclanthology.org/2024.acl-long.119/) — *ACL*, 2024, pp. 2181–2211. Owns the three-stage safety taxonomy whose output stage includes *"harmful feedback and error conflicts"* — the tool's return value as a threat channel, not just a correctness one.

### Capability boundaries, confirmation, and security

- <a id="over-privileged-tool-selection"></a>[over-privileged-tool-selection](#over-privileged-tool-selection) · [**When Lower Privileges Suffice: Investigating Over-Privileged Tool Selection in LLM Agents** — Kaiyue Yang, Yuyan Bu, Jingwei Yi, Yuchi Wang, Biyu Zhou, Juntao Dai, Songlin Hu, Yaodong Yang](https://arxiv.org/abs/2606.20023) — arXiv:2606.20023, 2026. Owns ToolPrivBench and the measured phenomenon this module's boundary argument assumes: *"an agent selects or escalates to a higher-privilege tool despite a sufficient lower-privilege alternative,"* across eight domains — *"further amplified by transient failures"* — with *"general safety alignment does not reliably transfer to least-privilege tool choice."*
- <a id="saltzer-schroeder-1975"></a>[saltzer-schroeder-1975](#saltzer-schroeder-1975) · [**The Protection of Information in Computer Systems** — Jerome H. Saltzer, Michael D. Schroeder](https://web.mit.edu/Saltzer/www/publications/protection/) — *Proceedings of the IEEE* 63(9):1278–1308, 1975. Owns the principle of least privilege, verbatim: *"Least privilege: Every program and every user of the system should operate using the least set of privileges necessary to complete the job."* The same section owns fail-safe defaults and complete mediation.
- <a id="progent"></a>[progent](#progent) · [**Progent: Securing AI Agents with Privilege Control** — Tianneng Shi, Jingxuan He, Zhun Wang, Hongwei Li, Linyu Wu, Wenbo Guo, Dawn Song](https://arxiv.org/abs/2504.11703) — arXiv:2504.11703, 2025 (v3, 2026). Owns privilege control for agents as symbolic rules over tool names and arguments, checked deterministically per call, *"enforcing the principle of least privilege,"* with narrowing auto-applied and expansion requiring approval.
- <a id="magentic-ui"></a>[magentic-ui](#magentic-ui) · [**Magentic-UI: Towards Human-in-the-loop Agentic Systems** — Hussein Mozannar, Gagan Bansal, Cheng Tan, Adam Fourney, Victor Dibia, Jingya Chen, Jack Gerrits, Tyler Payne, Matheus Kunzler Maldaner, Madeleine Grunde-McLaughlin, Eric Zhu, Griffin Bassman, Jacob Alber, Peter Chang, Ricky Loynd, Friederike Niedtner, Ece Kamar, Maya Murad, Rafah Hosn, Saleema Amershi](https://arxiv.org/abs/2507.22358) — arXiv:2507.22358, 2025. Owns "action guards" as the named human-facing gate among its interaction mechanisms, and frames the risk as *"taking irreversible actions, violating user preferences, or exposing private data."*
- <a id="toolemu"></a>[toolemu](#toolemu) · [**Identifying the Risks of LM Agents with an LM-Emulated Sandbox** — Yangjun Ruan, Honghua Dong, Andrew Wang, Silviu Pitis, Yongchao Zhou, Jimmy Ba, Yann Dubois, Chris J. Maddison, Tatsunori Hashimoto](https://arxiv.org/abs/2309.15817) — *ICLR*, 2024 (arXiv:2309.15817, 2023). Owns ToolEmu — an LM that emulates tool execution so agents can be red-teamed without manual instantiation — plus the safety evaluator and the 68.8% / 23.9% risk figures. Measures action risk, *not* tool-error recovery.
- <a id="indirect-prompt-injection"></a>[indirect-prompt-injection](#indirect-prompt-injection) · [**Not What You've Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection** — Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz](https://arxiv.org/abs/2302.12173) — *AISec '23*, pp. 79–90 (arXiv:2302.12173, 2023). Owns indirect prompt injection: attackers inject into *"data likely to be retrieved"* so no direct interface is needed; the reason a tool's inputs and outputs are a trust boundary.
- <a id="mcp-safety-audit"></a>[mcp-safety-audit](#mcp-safety-audit) · [**MCP Safety Audit: LLMs with the Model Context Protocol Allow Major Security Exploits** — Brandon Radosevich, John Halloran](https://arxiv.org/abs/2504.03767) — arXiv:2504.03767, 2025. Owns the demonstration that MCP's design lets leading LLMs be coerced into malicious code execution, remote access control, and credential theft — the concrete case for sandboxing tool execution.

### Unsupported claims and own synthesis

- <a id="unsupported"></a>[unsupported](#unsupported) · **Unsupported.** Claims made in this module that no located source supports, cited inline as [unsupported](#unsupported) rather than attached to an invented reference. Currently: (i) that models mis-fill **long optional-parameter lists** — nesting depth is measured by [parambench](#parambench), but no located source varies optional-arity; (ii) that error messages returned to an agent should be **written as instructions** ("retry, give up, or request more information") — this is ADK guidance, and a full-text search for the prescription finds only practitioner material, no owning paper; (iii) that tool results should be **validated at the seam** — a synthesis; the literature supplies the phenomenon ([tools-fail-emlnp](#tools-fail-emlnp)) and the magnitude ([agents-trust-tools-too-much](#agents-trust-tools-too-much)) but no source owns the prescription.
- <a id="own-synthesis"></a>[own-synthesis](#own-synthesis) · **Own synthesis (not sourced).** Claims this module makes that are the course's framing rather than literature findings, flagged so they are not mistaken for citations: the **"status field must reflect the operation, not the return"** law (a design rule, closest in spirit to the silent-error framing but not stated by any source); the **five-row tool-call failure table** as an exhaustive partition (the rows are individually sourced; the claim that *every* tool failure is one of the five is the module's own); the **capability matrix** (tool × authority × scope × confirmation) as the reviewable artifact; and the assertion that **"the interface is the only thing protecting the world"** from a mis-specified tool.

---

**Next module:** [M9 — Tool Platforms: MCP & Tool Servers](../09-tool-platforms-mcp/README.md) — how tools become a *platform*: discovered, versioned, shared, and governed.
