# Agent Orchestration Frameworks — Reference Map

A cross-reference appendix: how each open-source agent framework maps onto this course's modules (M3–M16). It is the same "which module is covered by which framework component" mapping the modules already carry for **ADK** and **DSH** — extended to the wider field.

## How to read this

- The **verification summary** is the honest gate: *is this actually open source?* — with source URL, license, and any caveats.
- The **master matrix** is a quick-glance "who's strong at what."
- The **per-framework notes** are the granular map: for each framework, which module(s) its primitives implement, and — just as important — which modules it *does not* cover (the "gaps" line).
- Direction: the notes answer "framework X's component Y covers course module Z." The modules' own `In DSH:` / `ADK at a glance` notes answer the reverse.

## Verification summary

| Framework | Source | License | Verdict |
|---|---|---|---|
| LangGraph | github.com/langchain-ai/langgraph | MIT | ✅ open source |
| CrewAI | github.com/crewAIInc/crewAI | MIT (core; paid Enterprise tier) | ✅ open-core |
| AutoGen → **Microsoft Agent Framework** | github.com/microsoft/autogen (superseded) · github.com/microsoft/agent-framework · community fork github.com/ag2ai/ag2 | MIT | ⚠️ renamed/split |
| Semantic Kernel | github.com/microsoft/semantic-kernel | MIT | ✅ |
| OpenAI Agents SDK | github.com/openai/openai-agents-python | MIT | ✅ |
| Pydantic AI | github.com/pydantic/pydantic-ai | MIT | ✅ |
| smolagents | github.com/huggingface/smolagents | Apache-2.0 | ✅ |
| Agno | github.com/agno-agi/agno | MPL-2.0 (was MIT) | ✅ |
| LlamaIndex | github.com/run-llama/llama_index | MIT | ✅ |
| Haystack | github.com/deepset-ai/haystack | Apache-2.0 | ✅ |
| Mastra | github.com/mastra-ai/mastra | MIT core + **Enterprise Edition (commercial)** | ⚠️ open-core |
| Vercel AI SDK | github.com/vercel/ai | Apache-2.0 | ✅ |
| Genkit | github.com/genkit-ai/genkit | Apache-2.0 | ✅ |
| Dify | github.com/langgenius/dify | **Dify Open Source License** (Apache-2.0 + multi-tenant-SaaS restriction) | ⚠️ source-available, not OSI |
| Eino (ByteDance) | github.com/cloudwego/eino | Apache-2.0 | ✅ |
| Qwen-Agent (Alibaba) | github.com/QwenLM/Qwen-Agent | Apache-2.0 | ✅ |
| DeepSeek Harness | github.com/deepseek-ai/deepseek-harness | MIT | ✅ |

**Caveats, stated plainly:** three entries aren't plain open source — **AutoGen** was folded into Microsoft Agent Framework (with AG2 as the community continuation of the AutoGen line); **Dify** is source-available but adds a multi-tenant-SaaS restriction (not OSI); **Mastra** is open-core (MIT framework + a separately-licensed Enterprise Edition). Everything else is a clean MIT/Apache/MPL repo.

## Two layers before the map

Not every "framework" is the same kind of thing, and the map treats them differently:

- **Orchestration frameworks** — give you the *control flow* and the *agent composition* (graph/crew/conversation). These get the full module map below.
- **Thin SDKs** — give you *agents + tools* but leave orchestration to you. These get a one-liner, not a full map.
- **App platforms** — a running product you configure, not a library (Dify, and DSH itself). These get a map via their config surface.

## Master matrix (at a glance)

| Framework | Language | Strongest at | Biggest gap |
|---|---|---|---|
| LangGraph | Python/JS | M10/M11 (graphs, cycles, multi-agent) | M12–M15 (eval/guardrails → LangSmith) |
| CrewAI | Python | M11 (crews), M6 (role/goal persona) | M12–M16 |
| Microsoft Agent Framework (AutoGen) | Python/.NET | M11 (agent conversation) | M4/M12/M14/M15 |
| Semantic Kernel | C#/Python/Java | M8 (plugins), M10 (planners) | M12/M14/M15 |
| OpenAI Agents SDK | Python | M8 (tools), M11 (handoffs), M14 (guardrails) | M4/M5/M7/M12 |
| Pydantic AI | Python | M8 (typed tools) | M10/M11 (thin) |
| smolagents | Python | M8 (code-as-tool), M10 (CodeAgent loop) | M11–M16 |
| Agno | Python | M3/M8/M11 (teams) | M12–M16 |
| LlamaIndex | Python/TS | M4/M5 (retrieval), M10/M11 (workflows) | M14/M15 |
| Haystack | Python | M4/M5 (RAG pipelines), M12 (eval) | M11/M14/M15 |
| Mastra | TypeScript | M10 (workflows), M12 (evals), M16 (observability) | M14/M15 |
| Vercel AI SDK | TypeScript | M8 (tools), streaming | M10/M11 (thin) |
| Genkit | TS/Go | M12 (evals), M16 (tracing), M8 (tools) | M14/M15 |
| Dify | Python/TS (platform) | M10/M11 (visual workflows), M4/M5 (RAG) | M14/M15 (platform, not library) |
| Eino | Go | M10 (Chain/Graph/Workflow), M8 (tools) | M12–M16 |
| Qwen-Agent | Python | M8 (tools), M4/M5 (RAG), M11 (group chat) | M12–M16 |

---

## Orchestration frameworks (full map)

### [LangGraph](https://github.com/langchain-ai/langgraph) (MIT, Python/JS)
- **Thesis:** a *graph* runtime — explicit nodes, edges, and typed state; the flow is data you write, not a loop you inherit.
- **Covers:** M3 (StateGraph + nodes/edges = named seams; typed state = the contract) · M4/M5 (state as the context carrier; retrieval via nodes) · M6 (system message in state) · M7 (checkpointer = persisted state/memory) · M8 (`@tool` + `ToolNode`) · M10 (cycles, recursion limits = the loop budget; conditional edges = routing) · M11 (subgraphs, supervisor, `Send` map-reduce) · M13 (retry policies, `interrupt()` = human-in-the-loop) · M16 (checkpointer = replay).
- **Gaps (resolved in production):**
  - *Eval:* LangSmith (de-facto) — datasets + LLM-as-judge in CI; OSS alt Langfuse ([monday](https://www.langchain.com/blog/customers-monday), [Lyft](https://www.langchain.com/blog/lyft-built-a-self-serve-ai-agent-platform-for-customer-support-with-langgraph-and-langsmith)).
  - *Guardrails:* as graph structure — guardrail nodes + edges ([official example](https://github.com/langchain-ai/langgraph-guardrails-example)); heavier policy via [NeMo Guardrails](https://docs.nvidia.com/nemo/guardrails/integration-with-third-party-libraries/langchain/langgraph-integration) / Guardrails AI.
  - *Observability:* LangSmith or Langfuse.

### [CrewAI](https://github.com/crewAIInc/crewAI) (MIT core, Python)
- **Thesis:** role-based **crews** — `Agent`(role/goal/backstory) + `Task` + `Crew`, with a `Process` (sequential or hierarchical).
- **Covers:** M6 (role/goal/backstory = the instruction, as *structured persona fields* rather than free text) · M7 (short-term/long-term/entity memory, built in) · M8 (tools) · M10 (`Process.sequential` = pipeline; `Process.hierarchical` = manager-agent) · M11 (the whole thing is multi-agent — a crew *is* a team).
- **Gaps (resolved in production):**
  - *Eval:* `crewai test` baseline → [Patronus AI](https://docs.crewai.com/v1.15.10/en/observability/patronus-evaluation) or DeepEval/LangWatch/Promptfoo.
  - *Guardrails:* task guardrails + enterprise HallucinationGuardrail + [agent-control](https://github.com/crewAIInc/agent-control) / guardrail-crew gate.
  - *Observability:* OTel → Langfuse/LangSmith/Weave/Datadog or AMP.

### Microsoft Agent Framework (AutoGen) — github.com/microsoft/agent-framework (MIT, Python/.NET); community fork AG2
- **Thesis:** multi-agent **conversation** — agents talk to each other, not through a fixed graph.
- **Covers:** M8 (tools/function calling) · M10 (orchestrators — round-robin, selector, swarm) · M11 (the core: group chats, handoffs, termination conditions) · M13 (handoff + termination as the loop's stop conditions).
- **Gaps (resolved in production):** mostly closed natively — [LocalEvaluator + Foundry](https://learn.microsoft.com/en-us/agent-framework/agents/evaluation) (eval), [FIDES](https://learn.microsoft.com/en-us/agent-framework/agents/security) + Azure Content Safety (guardrails), OTel → [Langfuse](https://langfuse.com/integrations/frameworks/microsoft-agent-framework)/Monitor/SigNoz (observability), AI Context Providers (RAG).
- **Note:** the original `microsoft/autogen` line was superseded; treat "AutoGen" as this framework's lineage, with AG2 as the community continuation.

### Semantic Kernel — github.com/microsoft/semantic-kernel (MIT, C#/Python/Java)
- **Thesis:** an *enterprise SDK* — a `Kernel` hosting **plugins** (functions), **planners**, and **connectors**.
- **Covers:** M3 (Kernel = the host/seam) · M6 (prompts-as-functions, prompt templates) · M8 (plugins/functions = the tool surface) · M10 (planners — Handlebars/Stepwise — = deterministic orchestration) · M11 (its Agent Framework layer for multi-agent).
- **Gaps (resolved in production):**
  - *Eval:* Foundry prompt flow + LLM-as-judge ([QualityCheck](https://github.com/microsoft/semantic-kernel/tree/main/dotnet/samples/Demos/QualityCheck)).
  - *Guardrails:* [filter pipeline](https://learn.microsoft.com/en-us/semantic-kernel/concepts/enterprise-readiness/filters) + Azure Content Safety / Prompt Shields.
  - *Observability:* OTel → App Insights / [Langfuse](https://js-sdk-v3.docs-snapshot.langfuse.com/integrations/frameworks/semantic-kernel/) / [SigNoz](https://signoz.io/docs/semantic-kernel-observability/).

### OpenAI Agents SDK — github.com/openai/openai-agents-python (MIT, Python)
- **Thesis:** lightweight agents + **handoffs** (the successor to Swarm) — minimal ceremony, fast loops.
- **Covers:** M3 (Agent abstraction) · M6 (instructions as strings) · M8 (`@function_tool`) · M10 (the agentic loop, model-driven; no explicit graphs) · M11 (**handoffs** = agent-to-agent, agents-as-tools) · M14 (**input/output guardrails** — one of the few frameworks with first-class guardrails) · M16 (built-in tracing).
- **Gaps (resolved in production):**
  - *Grounding:* `FileSearchTool`/`WebSearchTool` or custom RAG tools.
  - *Memory:* Sessions + storage (SQLite/Redis/Postgres) + [mem0](https://mem0.ai/blog/how-to-add-memory-to-openai-agents-sdk)/Zep.
  - *Eval:* trace-derived on [DeepEval](https://deepeval.com/integrations/frameworks/openai-agents)/LangSmith/Braintrust/Arize (OpenAI Evals deprecated, Nov 2026).

### LlamaIndex — github.com/run-llama/llama_index (MIT, Python/TS)
- **Thesis:** a *data* framework first — the strongest retrieval story in the field — with agent workflows layered on top.
- **Covers:** M4/M5 (the reference retrieval stack: indexing, query engines, retrieval) · M6 (system prompts) · M7 (chat memory buffers) · M8 (FunctionTool) · M10/M11 (`Workflow` event-driven graphs, `AgentWorkflow`, multi-agent) · M12 (has eval — `Correctness`, `Faithfulness` = the groundedness check).
- **Gaps (resolved in production):**
  - *Observability:* OTel/OpenInference → Langfuse / Arize Phoenix / LlamaTrace.
  - *Guardrails:* [Guardrails AI](https://guardrailsai.com/guardrails/docs/integrations/llamaindex) / LLM Guard / NeMo / Bedrock Guardrails.

### Haystack — github.com/deepset-ai/haystack (Apache-2.0, Python)
- **Thesis:** production **pipelines** (RAG) → agents, with a strong evaluation story.
- **Covers:** M4/M5 (pipelines, retrievers, RAG) · M8 (tools) · M10 (pipelines = deterministic orchestration; the `Agent` component = the agentic loop) · M12 (built-in eval — faithfulness, MRR) · M16 (pipelines are introspectable).
- **Gaps (resolved in production):**
  - *Multi-agent:* LangGraph (GitLab's Duo [rejected Haystack](https://gitlab.com/gitlab-org/gitlab/-/work_items/596718)) or [Hayhooks](https://deepset-ai.github.io/hayhooks/concepts/agent-deployment/) A2A/MCP.
  - *Guardrails:* moderation-LLM routers + 3.0 [Agent Hooks](https://haystack.deepset.ai/blog/haystack-3-release).
  - *Observability:* Langfuse / Phoenix / deepset Traces.

### Mastra — github.com/mastra-ai/mastra (MIT core + EE, TypeScript)
- **Thesis:** the TypeScript answer to LangGraph — agents + deterministic workflows + RAG + evals + observability in one.
- **Covers:** M3/M6 (agents + instructions) · M4/M5 (built-in RAG) · M8 (tools) · M10 (workflows = deterministic; agents = the loop) · M11 (networks/sub-agents) · M12 (evals + judge) · M16 (observability).
- **Gaps (resolved in production):** guardrails now first-class via [`processors`](https://mastra.ai/docs/agents/guardrails) (`PromptInjectionDetector`, `ModerationProcessor`, `PIIDetector`) + a safety-classifier model. **Note:** open-core — MIT core, separately-licensed Enterprise Edition.

### Genkit — github.com/genkit-ai/genkit (Apache-2.0, TypeScript/Go)
- **Thesis:** Google's (Firebase) framework — **flows** (deterministic) + **agents** (loops) + tools + a *first-class eval and tracing* story.
- **Covers:** M3/M6 (agents, system prompts) · M4/M5 (retrieval/RAG) · M8 (`defineTool`) · M10 (flows vs. agents — the exact pipeline-vs-loop split) · M11 (sub-agents) · M12 (evalFlow = eval harness) · M16 (tracing/telemetry built in).
- **Gaps (resolved in production):** [Model Armor](https://genkit.dev/docs/js/integrations/google-cloud/) + Checks AI Safety as `use:` middleware; auth-context/least-privilege for injection; Gemini safety settings baseline.

### Dify — github.com/langgenius/dify (source-available, Python/TS)
- **Thesis:** a *visual* LLM-app/agent **platform** — drag-and-drop workflows, no-code/low-code, a knowledge base, and an agent runtime.
- **Covers:** M4/M5 (knowledge base / RAG) · M7 (conversation memory) · M8 (built-in + custom tools) · M10 (visual workflow orchestration) · M11 (multi-agent nodes) · M16 (logs/observability).
- **Gaps (resolved in production):**
  - *Guardrails:* marketplace plugins (Palo Alto, Azure, Alibaba) or APISIX+Lakera gateway + Enterprise RBAC/SSO.
  - *Eval:* [Arize Phoenix](https://dify.ai/blog/dify-arize-how-to-evaluate-monitor-and-improve-agents) / LangSmith / Langfuse / promptfoo.
  - *Platform caveat:* configured, not programmed; **License:** multi-tenant-SaaS restriction.

### Eino — github.com/cloudwego/eino (Apache-2.0, Go)
- **Thesis:** ByteDance's Go framework — typed, component-based composition (`Chain` / `Graph` / `Workflow`).
- **Covers:** M3 (component/graph abstractions) · M6 (ChatTemplate) · M8 (Tool interface) · M10 (Chain = pipeline, Graph = branching, Workflow = loops) · M11 (ReAct agent, multi-agent orchestration).
- **Gaps (resolved in production):**
  - *Eval:* hand-built Go suite + LLM-as-judge in CI (thinly documented).
  - *Guardrails:* `ApprovalMiddleware` HITL + Volcano Engine LLM firewall.
  - *Observability:* vendor callbacks (Langfuse/LangSmith/APMPlus/CozeLoop) or hand-rolled OTel.

### Qwen-Agent — github.com/QwenLM/Qwen-Agent (Apache-2.0, Python)
- **Thesis:** Alibaba's framework, tuned for Qwen models — LLM + tools + RAG + multi-agent.
- **Covers:** M3/M6 (Agent + system prompts) · M4/M5 (doc parsing + retrieval) · M7 (memory) · M8 (tools) · M10/M11 (agent group chat).
- **Gaps (resolved in production):**
  - *Eval:* DeepEval + Langfuse (thinly documented).
  - *Guardrails:* Alibaba Cloud/DashScope moderation (code interpreter not sandboxed — containerize it).
  - *Observability:* [Langfuse](https://langfuse.com/integrations/model-providers/qwen) + wrapper hooks.

---

## Thin SDKs (one-liner)

- **Pydantic AI** (github.com/pydantic/pydantic-ai, MIT, Python) — type-safe agents where tools are typed models; covers M8 (typed tool contracts) and M3 (agent/runner), but leaves orchestration (M10/M11) to you.
- **smolagents** (github.com/huggingface/smolagents, Apache-2.0, Python) — *code-first* agents: the agent writes a Python snippet to call tools; covers M8 (tools) and M10 (the `CodeAgent` loop), but is intentionally minimal on M11–M16.
- **Agno** (github.com/agno-agi/agno, MPL-2.0, Python) — lightweight multi-modal agents and teams; covers M3/M8/M11 (teams), minimal on the rest.
- **Vercel AI SDK** (github.com/vercel/ai, Apache-2.0, TypeScript) — the streaming/AI SDK for chat and agents; covers M8 (tools) and M16 (streaming), thin on orchestration.

---

## Appendix: the two this course already maps

- **ADK** — mapped throughout the modules via `ADK at a glance`, and contrasted with DSH in [M3](../modules/03-harness-architecture/README.md).
- **DSH (DeepSeek Harness)** — mapped per-module via `In DSH:` notes, and it is the *only* framework whose own docs formalize the "seam" concept this course teaches (`docs/capability-seams.md`: a seam is a swappable capability with Service Definition + Provider + Consumer).
