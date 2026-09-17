# M8 · Tool Interfaces

> **Module question:** How do we give the model an API to the world that is safe, correct, and debuggable?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger · ADK at a glance
> **Domain spine:** a data-analysis agent calling internal APIs

---

## Opening scene — the tool that failed *successfully*

The data-analysis agent answered a manager's question: *"what's the Q3 pipeline number?"* It called the internal `get_metrics` tool, got a response, and reported the number with confidence.

The number was wrong. The tool had returned `{"status": "ok"}` — with `"value": null` buried inside, because the metric query had timed out upstream. The agent, seeing "ok," reported the *null* as if it were the answer. Nobody caught it until the number appeared in a board deck.

The postmortem was, again, a category error if you read it carelessly: *"the model hallucinated the metric."* It hadn't. It had **trusted a tool that lied about its own success** — a tool whose failure semantics said "ok" when it should have said "error, retryable, here's why." The model was a perfectly honest messenger relaying a dishonest envelope.

This module is about the envelope. The tool interface **is the `model↔action` seam** (M3's output seam) — the boundary where the model's decision becomes an action on the world — and, like every seam, it has a *contract* (what the tool is, what it accepts, what it returns) and a *boundary* (what it's allowed to do). Designing those two — plus the validation that sits on the seam (error semantics, confirmation) — is the difference between an agent that acts on the world and one that acts on the world *safely, correctly, and debuggably*.

> **Failure mode (the module in one line):** treating tools as "functions the model can call" instead of *APIs with a contract and a capability boundary*. A model will happily call a mis-specified tool with hallucinated arguments and trust a lying error code — the interface is the only thing protecting the world from that.

---

## Tools are APIs for a non-deterministic consumer

Here is the reframe that changes how you design tools:

**Your tool's consumer is not a human reading your docs. It's a model that reads your *description*, reasons about your tool *statistically*, and generates arguments by *prediction* — not by contract.**

This means tool design is API design, but with three differences that are all disadvantages:

1. **The docstring *is* the documentation.** A human can ask "what does this do?" A model only knows what's in the name, the description, and the schema. If it isn't there, it doesn't exist.
2. **The schema *is* the validation surface.** The model doesn't "know" the argument is required; it infers it from the schema — and will *guess* when the schema is ambiguous (M2's hallucinated args, class 8).
3. **The consumer doesn't check your return value.** A human sees `null` and frowns. The model sees the `status` field and — if you wrote `"ok"` — believes you.

So the two load-bearing artifacts are the **contract** (name + schema + description) and the **error semantics** (what the return value *means*, and what the model should do with it). The rest of this module is those two things, plus the **boundary** (what the tool is allowed to do at all).

---

## The contract: name, schema, description

The model's entire view of a tool is three things:

| Artifact | What it drives | If it's wrong |
|---|---|---|
| **Name** | *Selection* — which tool to call | The model calls the wrong tool (adjacent-name confusion) |
| **Description** (docstring) | *Selection + timing* — what it's for, when to use it | Over-eager or missed invocation |
| **Schema** (types, required vs. optional, enums) | *Argument generation* — what to pass | Hallucinated or malformed arguments |

ADK turns a plain function into a tool and takes the contract from its signature and docstring: the function name is the tool name, the docstring is the description, and the typed parameters become the schema (`FunctionTool(func=...)` in Python; explicit `parameters` schema in TypeScript/Go/Java).

**The simplicity rules** (from the ADK docs, and they matter because the model is the client):

- **One task per tool.** A `do_everything` tool is a selection and argument nightmare. `update_user_profile(profile: ProfileObject)` becomes three tools: `update_user_name`, `update_user_address`, `update_user_preferences`.
- **Few parameters, simple types.** The model reliably fills `(str, int, bool)`; it reliably *mis-fills* deeply nested objects and long optional lists.
- **Enums over free text, required over optional.** If a field can only be `daily | weekly | monthly`, say so in the schema — "say so" is literally the only way the model will know.

**The description drives *when*, not just *what*.** The docstring "look up an order's status" tells the model *what*; the added sentence "use only when the user explicitly asks about a specific order and provides an ID" tells it *when*. That second sentence is what prevents over-eager invocation — and it's part of the contract, not the instruction (M6's per-tool authority, stated where the tool lives).

> **ADK at a glance:** tools can also be provided **dynamically**, by *context*, via a `BaseToolset` — its `get_tools(readonly_context)` decides which tools to expose based on session state or user. This is least-privilege at the *surface* level: the sales user simply never sees the admin tool. The tool list itself becomes a permission boundary.

---

## Error semantics: what a failure *means* to the model

This is where the opening scene lives, and it is the most under-designed part of most tool surfaces. The rule:

> **A tool must never fail silently, and the model must be *told* what to do with each kind of return.**

The ADK docs say it directly: *"instruct the agent on how to handle different return values… whether the agent should retry, give up, or request additional information."* That's not a suggestion — it's the error-semantics contract.

A tool's return value should distinguish, in *structure* not just prose:

- **Success** — `{"status": "success", ...actual data}`.
- **Retryable failure** — `{"status": "error", "error_type": "timeout", "retryable": true, "message": ...}` → the model should retry (with the instruction saying so).
- **Fatal failure** — `{"status": "error", "retryable": false, "message": "metric not found"}` → the model should stop and tell the user.
- **Needs input** — `{"status": "needs_input", "message": "which date range?"}` → the model should ask the user.

And the instruction maps each to an action. The weather example from the docs is the canonical pattern: *"if `get_weather_report` returns 'success', report it; if it returns 'error', tell the user it's unavailable and ask for another city."*

**The worst case is the "ok with null."** A tool that says `status: ok` while the real operation failed trains the model to trust a lie. The contract's first law: **the status field must reflect the *operation*, not the *return**.* If the query timed out, the status is `error`, full stop.

---

## Capability boundaries & least privilege

The contract says what the tool *does*; the boundary says what it's *allowed* to do. You have already seen the canonical failure — the Chevrolet bot (M2's catalog) had a *quote* tool that could *commit a transaction*. The boundary is what turns that from a design accident into a design decision:

1. **Least privilege at the tool level.** A tool should be able to do the *least* it needs: read, not write; quote, not transact; propose, not execute. Every tool's authority is a decision, not a default.
2. **Scoped credentials, per tool.** The `read_metrics` tool gets a read-only database role; the `update_dashboard` tool gets a write role — and nothing else. (ADK's `ToolContext` auth flow — `request_credential` / `get_auth_response` — exists precisely so credentials are scoped per-tool, not ambient.)
3. **Sandboxing.** A tool that executes code or touches the filesystem runs in a sandbox with bounded resources — the tool is an *attack surface* (M14's subject, foreshadowed), and the sandbox is the boundary.
4. **Human confirmation on irreversible actions.** The formal mechanism for the restart rule from M6: ADK's `FunctionTool(..., require_confirmation=True)` pauses the tool for a yes/no from a human, and a *threshold function* (`require_confirmation=confirmation_threshold`) makes it conditional — *"confirm only if `amount > 1000`."* A `reimburse` tool that always confirms is slow; one that confirms only above the threshold is both safe and fast. This is the "human approval on irreversible actions" line from the governance diagram, made concrete.

The **capability matrix** is how you make all of this explicit and reviewable — a table of tool × (authority, scope, confirmation) that a team can audit. It's the design exercise's deliverable.

---

## The tool-call failure modes (M2 class 8, made concrete)

Every tool failure is one of these five, and each maps to a contract/boundary decision:

| Failure | What it is | Signature | Fix |
|---|---|---|---|
| **Hallucinated args** | The model invents a parameter | `send_email(to="customer@example.com")` where the address came from nowhere | Required schema, enums, "never invent" in the description; validate in the tool |
| **Wrong tool** | Adjacent-name confusion | Calls `update_user_name` when it meant `update_user_address` | Distinct names, per-tool descriptions |
| **Over-eager invocation** | Calls when it shouldn't | Fires `lookup` for every message | "Use only when…" in the description |
| **Tool loop** | Same call, rephrased, forever | 14 near-identical searches | Budgets, stop conditions (M10/M13) |
| **Poisoned results** | The tool returns wrong data, the model propagates it | The opening scene's "ok with null" | Error semantics + validate tool output at the seam |

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
> - **Rich description vs. precision.** A long description guides selection but competes for attention (M4) and invites drift (M6). Describe *when* and *what*, tersely.

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

## Sources (ADK docs)

- [Custom Tools for ADK — tool lifecycle, contracts, simplicity, toolsets](https://adk.dev/tools-custom/index.md)
- [Function tools (schemas, descriptions)](https://adk.dev/tools-custom/function-tools/index.md)
- [Get action confirmation — require_confirmation, threshold, human approval](https://adk.dev/tools-custom/confirmation/index.md)
- [ToolContext — per-tool auth, scoped credentials](https://adk.dev/context/index.md)

---

**Next module:** [M9 — Tool Platforms: MCP & Tool Servers](../09-tool-platforms-mcp/README.md) — how tools become a *platform*: discovered, versioned, shared, and governed.
