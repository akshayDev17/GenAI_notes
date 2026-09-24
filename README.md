# Janus 1.3B
- lightweight image understanding and generating LLM

## Preface
- multimodal understanding vs visual generation
    - former: understanding a given image, latter: generating an image given instructions
    - former: necessitates maximum information-retention, hence requires high-dimensional encoding; latter: generated image should be coherent(global consistency) + key details of instructions to be followed ===> no need of unnecessary complexities ===> low-dimensional encoding.
- most models: unified, i.e. use the same encoder for both tasks.
    - **performance tradeoff**: multimodal understanding suffers if the encoder is a low-dimensional encoder OR coherence of the generated image suffers if a high-dimensional encoder is used instead.
- Janus resolves this by having a separate encoding pathway for each of these tasks.
    - i.e. it decouples visual encoding from the task at hand.
    - this architectural principle can be extended to other kinds of inputs, such as EEG-signals, point clouds, audio data.

## Reference papers
- easy to understand but lacks detail: [Janus: Decoupling Visual Encoding for Unified Multimodal Understanding and Generation](https://arxiv.org/pdf/2410.13848)
- more complex but details the architecture: [JanusFlow: Harmonizing Autoregression and Rectified Flow for Unified Multimodal Understanding and Generation](https://arxiv.org/pdf/2411.07975)

## Notes
- LLM is the autoregressive transformer used commonly for both tasks.
- the generation decoder is the SDXL-VAE (stable diffusion XL variational autoencoder) as its the one that translates the codeblock-space generated image(by the LLM) back to the latent space(which is continuous in nature).
- velocity vector is the output of the image generation task part of Janus
    - given the prompt, i.e. $x^{con}$(conditioned on the prompt), the velocity(i.e. current timestep LLM output) is $v(z_t, t|x^{con})$, and for the same timestep if a forward pass would've been performed with no condition, the velocity is $v(z_t, t | \phi)$. the final velocity term used ($v(z_t)$) is a weighted sum of these 2 quantities, with the weights being $w$ and $1-w$ respectively.
    - this approach =  *classifier-free guidance*
    - higher w ==> higher <font color="red">semantic alignment</font>. (whatever this means w.r.t. images)
- [perplexity chat session on Janus 1.3B](https://www.perplexity.ai/search/janus-1-3-b-explain-_BCBwkNFSy.epxJvXxLjpQ)

# Project Ideas

## Company-specific potential usecases
### Marketing Content
1. Develop visually appealing promotional graphics and social media content that align with game themes and narratives.([Wooga, Germany](https://www.wooga.com))
2. Develop engaging advertisements that combine compelling visuals and informative text about Tesla's innovations.
3. Create personalized marketing materials that showcase local restaurants and dishes tailored to user preferences. ([Delivery Hero, Germany](https://www.deliveryhero.com))
4. Generate personalized marketing content showcasing local offers and services available through the Gojek app.

# Concepts

## Agentic AI Study Roadmap (suggested learning order)

### 1. Foundations (prerequisites before "agentic" makes sense)
- prompting fundamentals & context windows
- evals — how to measure whether a model/agent is actually good
- RAG (retrieval-augmented generation) — grounding responses in external data
- benchmaxing — recognizing when a model is overfit to a benchmark rather than genuinely capable; why held-out/private evals matter

### 2. Tool use & interoperability protocols
- function calling / tool use — the basic primitive that turns an LLM into an agent
- MCP (Model Context Protocol) — standardized way to connect models to tools/data (donated to the Linux Foundation, Dec 2025)
- A2A (Agent2Agent protocol, Google) — standardized agent-to-agent coordination, complements MCP

### 3. Core agentic design patterns
- ReAct (reason + act + observe loop)
- Reflection / Reflexion (generate → critique → refine)
- Plan-and-Execute vs. dynamic/exploratory (ReAct-style) planning
- ReWOO (plan once, reduce redundant LLM calls)
- Tree-of-Thoughts / search over candidate plans
- Anthropic's 5 composable workflow patterns: prompt chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer

### 4. Memory & context
- agentic memory — working, episodic, semantic, and procedural memory, retrieved in parallel and merged into context
- context engineering — the discipline of curating what goes into the context window (broader than prompt engineering)

### 5. Multi-agent systems
- orchestration architectures: hierarchical, peer-to-peer, blackboard, marketplace
- shared memory fabric / structured message passing between agents
- when multi-agent is (and isn't) worth the coordination overhead

### 6. Training & verification loop
- post training (harness) — RLHF/RLAIF, fine-tuning on agent trajectories
- verifiers — reward models / automatic checkers used to score rollouts for RL and evals

### 7. Production concerns
- guardrails & safety — validation, sandboxing, human-in-the-loop approval gates
- observability & tracing for agent runs (structured logs, spans, replay)
- cost/latency optimization — caching, model routing, distillation

## System Design (agentic focus)
- classic fundamentals (if new to you): load balancing, caching, queues, horizontal scaling
- LLM inference serving: prefill vs. decode phases, KV-cache, continuous batching, quantization, speculative decoding
- agents as distributed systems: idempotency (every real-world action must be safely retryable), state machines for workflow steps, circuit breakers, dead-letter queues
- durable execution / workflow engines for long-running, resumable agent tasks
- deployment strategies for agents: blue-green, shadow testing, canary releases
- security: prompt-injection defense, sandboxed tool execution, least-privilege tool access, secrets handling

## Docs/MCP tooling specifically for agentic concepts
- [Context7](https://context7.com) already indexes docs for many agent frameworks (LangGraph, LlamaIndex, CrewAI, etc.) — good first stop even though it's general-purpose library docs, not agentic *concepts* per se
- no single "Context7-for-agentic-concepts" server has emerged yet as of this writing; closest practical options:
  - [DeepWiki MCP](https://docs.devin.ai/work-with-devin/deepwiki-mcp) — query any public GitHub repo's wiki on the fly; point it at pattern-catalog repos
  - [Agent Patterns Catalog](https://github.com/agentpatternscatalog/patterns) — canonical, community-curated, vendor-neutral, machine-readable catalog of agent design patterns (pure data, no code) — pair with DeepWiki or a self-hosted docs server
  - [docs-mcp-server](https://github.com/arabold/docs-mcp-server) — open-source, self-hostable MCP doc-indexer; point it at [agentic-design.ai](https://agentic-design.ai) (280+ patterns/techniques catalog) or Anthropic's "Building Effective Agents" guide to build your own always-current agentic-concepts index
  - other Context7 alternatives worth knowing about: Docfork, Deepcon