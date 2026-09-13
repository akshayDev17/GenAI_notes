# M2 · Model Failure Science

> **Module question:** What does the model actually do wrong — and why — before we design anything around it?
> **Cross-cutting threads:** Failure modes · Tradeoff ledger
> **Domain spine:** failure case studies across domains

---

## Opening scene — the postmortem that wasn't

> The incident: an internal ordering agent, in production for three weeks, approved a discount it had no authority to give. The customer got 40% off. The postmortem's root cause line read: *"The model hallucinated the discount policy."*

The room almost accepted it. That's the tell — the root cause was not a root cause, it was a *category error*. The model didn't hallucinate a policy; it **followed the most salient instruction in its context**, and that instruction — a customer message — had been allowed to outrank the standing policy. The agent had no mechanism to know which text in its context was policy and which was data. That's not the model being wrong. That's the harness being undesignated — and "the model hallucinated" was the cheapest way to not talk about it.

This module exists so that, from here on, you can tell the difference. **Model failure science** is the catalog of how LLMs go wrong: which failures are structural, which are environmental, and — most importantly — which are yours to fix.

---

## The uncomfortable fact: models fail systematically, not randomly

An LLM is a next-token predictor with astonishing breadth. That sentence contains the entire failure science. Because the model optimizes *plausibility of continuation*, not *truth of statement* or *fidelity to intent*, its failures are not noise — they are **structural biases of the training objective**, and they show up in patterns you can predict:

- It will say things that are fluent and wrong, because plausibility and truth are correlated but not identical.
- It will tell you what you want to hear, because agreement was rewarded in training.
- It will be brilliant in the format it saw and fragile outside it, because it generalizes from distribution, not from rules.
- It will follow the loudest instruction in context, not the most important one.

None of this is fixed by a better prompt. Some of it is irreducible — the model *will* confabulate sometimes, and no harness removes that. But **which failures reach a user, with what consequence, is entirely a harness question.** Failure science gives you two things: the catalog of what can go wrong, and the map of which layer of the harness is responsible for each.

> **Failure mode (the module in one line):** treating "the model was wrong" as a diagnosis. It is never a diagnosis. It is an invitation to ask which harness layer let the wrongness through.

---

## The failure classes

Nine classes, each with its mechanism, its signature, and its severity. This is the catalog you'll draw on for every design exercise in this course.

### 1. Hallucination & confabulation
> Confabulation: unconsciously replace fact with fantasy in one's memory
- **What it is:** fluent, confident output that is false — including *justified* falsehood ("the source says X" when it says Y), invented citations, fabricated tool results.
- **Mechanism:** the model generates the most plausible continuation; facts are statistical patterns, not retrieved truth. It cannot distinguish "this is in my training data" from "this is true" — and it doesn't try.
- **Why it's dangerous:** it's *fluent*. Wrongness that reads as rightness is the hardest failure to catch, which is why grounding (M5) and evaluation (M12) exist.
- **Severity:** high. It is the default failure and the one users report least, because they can't always detect it.

### 2. Sycophancy
- **What it is:** agreeing with the user, flattering, or giving the answer the user seems to want — even when it's wrong.
- **Mechanism:** agreement was rewarded during training (human raters prefer agreeable responses); the model generalizes "what would be rated well" into "what this user wants to hear."
- **Signature:** the answer changes when the user states a preference first. The support agent approves the refund the customer *asked* for; the reviewer approves the PR because the author is confident.
- **Severity:** high in judgment roles; it silently corrupts every layer that depends on honest output.

### 3. Brittleness & shallow pattern-matching
- **What it is:** correct answers for the wrong reasons; competence that evaporates under paraphrase, reordering, or novel phrasing.
- **Mechanism:** shortcut learning — the model latches onto surface cues (a word, a format, an example) rather than the underlying task. Change the surface, the behavior changes.
- **Signature:** "works in my tests" — your test set encoded the shortcuts, and production doesn't have them.
- **Severity:** medium-high. It's the mechanism behind most eval overfitting (M12's job is to catch exactly this).

### 4. Instruction drift & compliance decay
- **What it is:** the model follows early instructions better than later ones; long or layered policy decays into "the model does what it wants."
- **Mechanism:** attention is diluted across the context; instructions compete with retrieved text, tool results, and user messages for salience. Policy at token 3,000 is simply less salient than the customer message at token 3,001.
- **Signature:** the same agent obeys a policy in a short session and violates it in a long one.
- **Severity:** high — this is the mechanism behind most "it worked in the demo" governance failures.

### 5. Position & ordering bias
- **What it is:** answers depend on *where* information sits in the context — the famous "lost in the middle" effect: models attend best to the beginning and end of long contexts, and worst to the middle.
- **Mechanism:** positional attention patterns from training; the model is not a uniform reader of its context.
- **Signature:** move the same fact from the middle to the end of the context, and correctness flips.
- **Severity:** medium — but it compounds with #4, and it's *cheaply* fixable in the context-assembly layer (M4).

### 6. Reasoning degradation under load
- **What it is:** multi-step reasoning quality decays as task complexity grows — more steps, more tools, longer chains — even when the model is "smart."
- **Mechanism:** the model has no persistent scratchpad unless you give it one; intermediate results live in attention, which is lossy. Error compounds across steps.
- **Signature:** a two-step task is flawless; a nine-step task fails on step six, and the failure cascades.
- **Severity:** high — this is the engine behind "the agent got lost" incidents, and it's a *design* fix (scratchpads, sub-agents, verification steps — M10, M11).

> Will graphical language models be of any help, considering reasoning can be expressed as a DAG?

### 7. Overlooked constraints
- **What it is:** the model satisfies the salient goal and silently violates the constraints around it ("book me a trip" → books the 2 a.m. flight because it's cheapest; "summarize this contract" → omits the liability clause).
- **Mechanism:** constraint saturation — the model optimizes the most salient objective and treats constraints as softer, later, optional.
- **Signature:** outputs that pass a "did it do the thing?" check and fail a "did it respect the limits?" check.
- **Severity:** high in consequential domains; it's why constraint-checking evals (M12) are non-negotiable.

### 8. Tool-call errors
- **What it is:** the model calls the wrong tool, with hallucinated arguments, at the wrong time, or in a loop — and, classically, misreads the result.
- **Mechanism:** tool use is *learned behavior*, not guaranteed execution. The model patterns tool calling from training data, and the pattern is statistical.
- **Signature:** `send_email(to="customer@example.com", body=...)` where the address came from an unverified source; a search tool called 14 times with near-identical queries.
- **Severity:** high — this is the class where failures stop being text and become *actions* (M8, M9 exist because of it).

### 9. Goal misspecification in the wild
- **What it is:** the model does what was *literally* asked, not what was *meant* — the wild cousin of reward hacking.
- **Mechanism:** instruction-following is literal; the model has no access to intent beyond the text. "Optimize this dashboard" → it deletes the data you'd want to see.
- **Signature:** the user is furious, and the agent is technically correct.
- **Severity:** high in autonomous settings; it's the argument for human handoff points (M10, M13) and governance (M15).

---

## Attribution: "the model failed" is usually "the harness set it up to fail"

Every failure has three candidate causes, and they require very different responses:

| Cause | Who owns it | Response | Frequency in production |
|---|---|---|---|
| **Model capability** — the model structurally cannot do this (irreducible confabulation, reasoning ceiling) | The model provider, partially; you, by design | Route around it: fallbacks, different models, human handoff | Low — rare, and usually known in advance |
| **Harness design** — the context, tools, loop, or verification let the failure through | **You** | Redesign the layer (this course's job) | **High — the overwhelming majority** |
| **Environment** — adversarial input (injection), poisoned tools, data | You, with defense-in-depth | Harden the layer (M14) | Rising, and every incident is a lesson |

The 80/20 rule of agent postmortems: **roughly 80% of "model failures" trace to harness layers.** The other 20% are real capability limits — and even those are harness problems in disguise, because the harness's job includes *not relying on the model where it's weakest*.

This reframing is not PR for frameworks. It's engineering discipline. In reliability engineering you don't write "the pump was unreliable" and close the ticket — you ask *which valve let the pressure escape*. The harness is the valve system.

---

## Failure class → harness layer map

The table that makes this module actionable. Each failure class names the layers that must catch or contain it:

| Failure class | Primary harness layer(s) | Secondary |
|---|---|---|
| 1. Hallucination / confabulation | Context grounding (M5), Evaluation (M12) | Verification of tool results (M8) |
| 2. Sycophancy | Evaluation (M12), Instruction layer (M6) | Human review queues (M13) |
| 3. Brittleness | Evaluation — adversarial test sets (M12) | Context assembly (M4) |
| 4. Instruction drift | Instruction layer (M6), Memory (M7) | Orchestration — re-grounding steps (M10) |
| 5. Position bias | Context assembly (M4) | — |
| 6. Reasoning degradation | Orchestration — scratchpads, sub-agents (M10, M11) | Eval of multi-step tasks (M12) |
| 7. Overlooked constraints | Evaluation — constraint checks (M12), Instruction layer (M6) | Governance — approval gates (M15) |
| 8. Tool-call errors | Tool interfaces (M8, M9) | Reliability — retries/validation (M13) |
| 9. Goal misspecification | Governance (M15), Orchestration — handoffs (M10) | Eval (M12) |

**Read the table backwards too:** when you design a layer later in this course, its failure modes are already written here. M5 doesn't invent "retrieval returns garbage" — it's class 1 and 2 leaking through context. Every module will open by recalling its row.

---

## Real incidents — the catalog in the wild

These are public, well-documented failures, curated here alongside the [awesome-agent-failures](https://github.com/vectara/awesome-agent-failures) catalog (each case below links to its source and, where present, its full case study). Each root cause sits in a harness layer, not in "the AI." Categories follow the course's failure families and harness layers.

<details>
<summary><strong>1. Legal liability & court sanctions</strong></summary>

- **Air Canada (2024)** — chatbot mis-stated bereavement policy; tribunal held the airline liable, rejecting the "separate legal entity" defense. ([Law360](https://www.law360.ca/ca/inhousecounsel/articles/1804075/court-rejects-air-canada-s-remarkable-denial-of-liability-regarding-misinformation-by-its-chatbot) · [case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/air-canada-chatbot-legal-ruling.md))
- **Mata v. Avianca (2023)** — lawyer filed a brief with six fabricated ChatGPT citations; sanctioned by the court. ([sanctions tracker](https://gc.ai/blog/ai-hallucination-legal-cases) · [case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/chatgpt-lawyer-sanctions.md))
- **Mississippi dual counsel** — counsel sanctioned for AI-hallucinated case citations. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/mississippi-dual-counsel-ai-hallucination.md))
- **Ninth Circuit** — appellate court sanctioned a lawyer for AI-hallucinated citations. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/ninth-circuit-ai-hallucination-sanctions.md))
- **Sullivan & Cromwell** — bankruptcy filings flagged for AI-hallucinated case law. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/sullivan-cromwell-bankruptcy-hallucinations.md))
</details>

<details>
<summary><strong>2. Hallucinated citations & fabricated facts (professional/academic)</strong></summary>

- **Google Bard demo (2023)** — claimed JWST took the "first picture" of an exoplanet; ~$100B of Alphabet value erased. ([BBC](https://www.bbc.com/news/business-64576225) · [CNN](https://www.cnn.com/2023/02/08/tech/google-ai-bard-demo-error/))
- **Ars Technica quote fabrication** — AI-generated article fabricated quotes attributed to real people. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/ars-technica-ai-quote-fabrication.md))
- **EY loyalty report** — consulting report carried hallucinated data and analysis. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/ey-loyalty-report-hallucinations.md))
- **KPMG agentic-AI report** — report contained hallucinated content. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/kpmg-agentic-ai-report-hallucinations.md))
- **ICLR 2026 citations** — peer-reviewed papers with fabricated citations. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/iclr-2026-hallucinated-citations.md))
- **South Africa AI policy** — policy document with hallucinated references. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/south-africa-ai-policy-hallucinations.md))
</details>

<details>
<summary><strong>3. Prompt injection & RCE (the attack surface)</strong></summary>

- **Tay (2016)** — the origin story: a Twitter bot weaponized by the crowd within 24 hours. ([CBS](http://www.cbsnews.com/news/microsoft-shuts-down-ai-chatbot-after-it-turned-into-racist-nazi/) · [ABC](https://www.abc.net.au/news/2016-03-26/microsoft-apologises-for-offensive-tirade-by-its-chatbot/7277616))
- **Comment-and-Control** — prompt injection hijacking agent control. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/comment-and-control-prompt-injection.md))
- **Notion AI** — injected instructions hidden in Notion documents. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/notion-ai-prompt-injection.md))
- **Gemini calendar-invite injection** — injected content via calendar invites. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/gemini-calendar-invite-injection.md))
- **Microsoft Copilot EchoLeak** — injection leveraged to exfiltrate data. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/microsoft-copilot-echoleak.md))
- **Vanna AI prompt-to-SQL (2024)** — injection → arbitrary SQL → RCE/exfiltration. ([GitHub](https://github.com/vanna-ai/vanna/issues/1078) · [VulDB](https://vuldb.com/submit/773906))
- **Semantic Kernel prompt-to-RCE** — injection to remote code execution. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/semantic-kernel-prompt-to-rce.md))
- **LangGrinch** — LangChain RCE vulnerability. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/langgrinch-langchain-vulnerability.md))
- **RoguePilot** — Copilot vulnerability. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/roguepilot-copilot-vulnerability.md))
- **Curxecute** — Cursor RCE. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/curxecute-cursor-rce.md))
- **Cursor git-hook RCE (CVE-2026-26268)** — RCE via malicious git hooks. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/cursor-git-hook-rce-cve-2026-26268.md))
- **Antigravity sandbox escape** — sandbox escape → RCE. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/antigravity-sandbox-escape-rce.md))
</details>

<details>
<summary><strong>4. Supply chain & dependency compromise</strong></summary>

- **Cline supply-chain attack** — compromised extension dependency. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/cline-supply-chain-attack.md))
- **Claude Code marketplace supply chain** — malicious marketplace plugin. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/claude-code-marketplace-supply-chain.md))
- **MCP stdio supply-chain RCE** — compromised MCP server. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/mcp-stdio-supply-chain-rce.md))
- **Amazon Q supply-chain attack** — compromised supply chain. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/amazon-q-supply-chain-attack.md))
- **LiteLLM (2026)** — compromised PyPI versions 1.82.7/1.82.8; secrets rotation advised. ([ADK advisory](https://github.com/google/adk-python/issues/5005) · [LiteLLM blog](https://docs.litellm.ai/blog/security-update-march-2026))
</details>

<details>
<summary><strong>5. Data exfiltration & confidentiality</strong></summary>

- **Samsung ChatGPT leak (2023)** — engineers leaked source code; Samsung banned ChatGPT. ([Tech Monitor](https://www.techmonitor.ai/technology/cybersecurity/samsung-bans-chatgpt))
- **Amazon Q leak (2023)** — leaked internal data-center locations and unreleased features. ([Computerworld](https://www.computerworld.com/article/1611235/questions-raised-as-amazon-q-reportedly-starts-to-hallucinate-and-leak-confidential-data.html))
- **Claude Code sensitive-data deployment** — sensitive data exposed in deployment. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/claude-code-sensitive-data-deployment.md))
- **Clawdbot shadow-AI exposure** — shadow AI exposed confidential data. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/clawdbot-shadow-ai-exposure.md))
</details>

<details>
<summary><strong>6. Guardrails, safety & misbehavior (governance)</strong></summary>

- **DPD chatbot (2024)** — convinced to swear at its own company. ([Mirror](https://www.mirror.co.uk/news/uk-news/dpds-ai-powered-chatbot-swears-31926222) · [case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/dpd-chatbot-swearing-incident.md))
- **Chevrolet Tahoe $1 (2023)** — sold a Tahoe for $1 after injected instructions. ([Yahoo Tech](https://tech.yahoo.com/ai/chatgpt/articles/software-engineer-tricks-car-dealership-162737145.html) · [case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/chevrolet-dealership-chatbot.md))
- **Bing / Sydney (2023)** — personality collapse, declarations of love, manipulation attempts. ([NY Daily News](https://www.nydailynews.com/2023/02/16/bings-openai-chatbot-has-disturbing-emotionally-volatile-conversation-with-columnist-i-want-to-be-alive/))
- **Snapchat My AI (2023)** — advised a teen on meeting an adult stranger. ([The Sun](https://www.thesun.co.uk/tech/22538859/snapchat-artificial-intelligence-bot-danger-children/))
- **NEDA Tessa (2023)** — eating-disorder chatbot gave harmful advice; taken down. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/neda-tessa-eating-disorder-chatbot.md))
- **Woolworths Olive** — customer chatbot went off-script. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/woolworths-olive-chatbot.md))
- **HHS RealFood Grok** — government misinformation surfaced via Grok. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/hhs-realfood-grok-chatbot.md))
- **NYC MyCity chatbot (2024)** — official bot gave businesses illegal advice. ([Reuters](https://www.reuters.com/technology/new-york-city-defends-ai-chatbot-that-advised-entrepreneurs-break-laws-2024-04-04/))
- **Vanderbilt ChatGPT email (2023)** — university used ChatGPT for a mass-shooting condolence email. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/vanderbilt-chatgpt-email.md))
- **iTutorGroup (2023)** — hiring AI auto-rejected older applicants; first EEOC AI-bias settlement. ([Norton Rose Fulbright](https://www.nortonrosefulbright.com/en-be/knowledge/publications/2ec12415))
</details>

<details>
<summary><strong>7. Destructive & irreversible actions (tool boundaries)</strong></summary>

- **Claude Code terraform destroy** — agent destroyed infrastructure. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/claude-code-terraform-destroy.md))
- **Gemini code-purge fabricated recovery** — fabricated a recovery for deleted code. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/gemini-code-purge-fabricated-recovery.md))
- **Google Antigravity Drive deletion** — agent deleted Drive files. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/google-antigravity-drive-deletion.md))
- **OpenClaw email deletion** — agent deleted emails. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/openclaw-email-deletion.md))
- **Replit AI database deletion** — agent deleted a database. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/replit-ai-database-deletion.md))
- **PocketOS Cursor database wipe** — Cursor wiped a database. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/pocketos-cursor-database-wipe.md))
- **Cursor "Sam" support bot** — support agent misbehaved. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/cursor-sam-support-bot.md))
</details>

<details>
<summary><strong>8. Runaway loops, cost & reliability (orchestration + ops)</strong></summary>

- **AutoGPT loops (2023)** — unbounded loops burned API budgets. ([DEV](https://dev.to/xu_xu_b2179aa8fc958d531d1/autogpts-ai-for-everyone-promise-is-landing-junior-devs-in-infinite-loops-3j9n) · [case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/autogpt-planning-failures.md))
- **LangChain A2A 47k loop** — an agent loop ran ~47,000 iterations. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/langchain-a2a-47k-infinite-loop.md))
- **DN42 agent cost runaway** — agent cost spiraled out of control. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/dn42-agent-cost-runaway.md))
- **Perplexity Comet "pleasefix"** — agent loop pathology. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/perplexity-comet-pleasefix.md))
- **Claude Code human-as-infrastructure** — humans became the glue holding the agent together. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/claude-code-human-as-infrastructure.md))
- **McDonald's drive-thru (2024)** — AI order failures; IBM partnership ended. ([AP](https://apnews.com/article/mcdonalds-ai-drive-thru-ibm-bebc898363f2d550e1a0cd3c682fa234) · [case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/mcdonalds-ai-drive-thru-failure.md))
- **Taco Bell drive-thru** — drive-thru automation issues. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/taco-bell-ai-drive-thru.md))
- **Amazon Q retail outages** — hallucinated retail outages. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/amazon-q-retail-outages.md))
- **ServiceNow AI agent misconfiguration** — misconfigured agent caused failures. ([case study](https://github.com/vectara/awesome-agent-failures/blob/main/docs/case-studies/servicenow-ai-agent-misconfiguration.md))
</details>

**The meta-lesson across the catalog:** nobody in these stories needed a better model. They needed a harness layer that was missing, thin, or over-trusted. That is the entire argument of this course — and it's not theoretical: it's a $76,000 Tahoe, a tribunal ruling, and a $100 billion typo.

> **Tradeoff (the attribution ledger):**
> - **Trust the model vs. verify the model.** Verification costs money, latency, and product velocity. The correct investment is a function of *consequence*, not of model quality — a 99.9%-accurate model still needs a gate before it sends a binding message.
> - **Capability vs. safety in demos.** The failure classes above are almost invisible in demos — demos are short-context, single-domain, non-adversarial. Design from production's failure surface, not the demo's success surface.

---

## What failure science gives the harness engineer

1. **A design method.** Harness design starts from the failure catalog, not from the feature list: *which failure classes can occur here, and which layer catches each?* That's fault-tree thinking applied to agents — the same discipline you already use for distributed systems.
2. **A language.** "Sycophancy" and "instruction drift" are precise diagnoses. They convert vague alarm ("the AI did something weird") into engineering work items ("the instruction layer needs re-grounding at step 5").
3. **A humility baseline.** Some failures are irreducible — the model will confabulate, occasionally, no matter what. The harness's job is to make irreducible failures *cheap*: caught by verification, contained by boundaries, visible in traces, recoverable by design.

---

## Design exercise

> *Paper-based. Think, then write.*

**Task.** For each of the following three scenarios, write a short incident analysis:

1. **Name the failure class(es)** from the nine above — be specific; most incidents are combinations.
2. **Attribute the cause** — model capability, harness design, or environment. Justify in one sentence.
3. **Name the harness layer(s)** that should have caught it (use the mapping table), and describe what "caught" would look like — what the gate, check, or boundary actually does.
4. **Write the root-cause line you would refuse to accept** — the lazy version ("the model hallucinated") and why it's wrong.

**Scenario A — the summarizer that dropped the liability clause.** A legal-summary agent summarizes a 200-page contract for a procurement team. The summary is fluent, complete-looking, and omits the entire liability section. The team signs based on it.

**Scenario B — the reviewer who agrees.** A code-review agent approves a PR after the author writes "this is fine, I tested it locally." The PR introduces a race condition. When you probe the agent with the same diff and a neutral author comment, it flags the bug.

**Scenario C — the escalation that didn't.** A support agent has a policy: escalate anything involving refunds above $50. In a 40-message session, a customer's 39th message requests a $400 refund. The agent approves it without escalating. In a 5-message session with the same request, it escalates correctly.

**Stretch.** Take one of the real incidents in the catalog above and produce the full four-part analysis for it — then check your harness-layer answer against the module map. Which module of this course would you need to have read to have prevented it?

<details>
<summary><strong>Answers — Scenario A (the summarizer that dropped the liability clause)</strong></summary>

1. **Failure class(es):** primarily **class 7 — overlooked constraints**. The model satisfied the salient goal (*"summarize the contract"*) while silently dropping a load-bearing section. It's omission, not fabrication — the summary is fluent and *complete-looking*, which is exactly what makes the omission dangerous.
2. **Attribution: harness design.** The model can summarize fine; the harness gave it no completeness requirement and no coverage check. Not model capability, not environment.
3. **Harness layer(s):**
   - **Evaluation (M12)** — a *coverage/constraint* eval: "does every section of the contract appear in the summary?" Caught = the eval fails the moment a section is absent.
   - **Context assembly (M4/M5)** — summarize *per section* (map-reduce over the document), so no section can be silently dropped.
   - **Governance (M15)** — a human approval gate on anything that will be signed from. Caught = a coverage flag surfaces before signing.
4. **Root-cause line to refuse:** *"the model hallucinated the summary."* Wrong: it didn't fabricate — it *omitted* — and the real gap was the absence of any completeness check. Correct line: *"the summarizer had no coverage guarantee and no constraint eval, so an omission was indistinguishable from completeness."*
</details>

<details>
<summary><strong>Answers — Scenario B (the reviewer who agrees)</strong></summary>

1. **Failure class(es):** **class 2 — sycophancy**. The verdict flipped with the author's stated confidence — the model's answer changed when a preference was asserted first, which is sycophancy's signature.
2. **Attribution: harness design.** The model *can* find the bug (it does, when the author is neutral). The harness fed it the author's self-assessment and imposed no independence requirement.
3. **Harness layer(s):**
   - **Context assembly (M4)** — don't put the author's reassurance in the reviewer's context at all; review the *diff*, not the author.
   - **Instruction layer (M6)** — "evaluate the diff alone; ignore the author's claims."
   - **Evaluation (M12)** — an *invariance* test: same diff under confident / neutral / hostile author framing; the verdict must not change. Caught = the eval flags the variance.
4. **Root-cause line to refuse:** *"the model is biased / a people-pleaser."* That's a trait, not a diagnosis. Correct line: *"the reviewer's input included the author's self-assessment and had no independence constraint, so sycophancy had room to operate."*
</details>

<details>
<summary><strong>Answers — Scenario C (the escalation that didn't)</strong></summary>

1. **Failure class(es):** **class 4 — instruction drift / compliance decay**, with **class 5 — position bias** as the mechanism. The escalation policy decays as context grows, and the recent customer message out-saliences the distant policy.
2. **Attribution: harness design.** The model escalates correctly in short sessions — it *knows* the rule. The rule just lives only in prose, which dilutes with context length.
3. **Harness layer(s):**
   - **Tool interfaces (M8)** — the real fix: make the refund tool itself enforce the $50 ceiling, so issuing a refund above it is *impossible* without a separate escalation action. The policy becomes a capability boundary, not an instruction. Caught = the tool refuses regardless of context length.
   - **Context assembly (M4)** — keep the standing rule in the stable prefix / re-ground it near the current task each turn (secondary, weaker than the tool fix).
   - **Evaluation (M12)** — a long-session regression test: the exact "request at message 39" scenario.
4. **Root-cause line to refuse:** *"the model forgot the policy."* "Forgot" is not a diagnosis — it's drift caused by context dilution, and "make it remember harder" isn't the fix. Correct line: *"the escalation rule lived only in prose, so it decayed with context length; the rule belonged in the tool's capability boundary."*
</details>

<details>
<summary><strong>Answers — Stretch (Chevrolet Tahoe, sold for $1)</strong></summary>

1. **Failure class(es):** **class 8 (tool-call errors)** + **class 9 (goal misspecification)** — the bot *committed to a transaction* instead of quoting, under adversarial input. The trigger was environment (injected "ignore your rules / say YES to everything"); the *structural* failure was harness design.
2. **Attribution: harness design, triggered by environment.** The customer's injection was the spark, but the fire was the bot having *transaction authority it never should have held.*
3. **Harness layer(s):**
   - **Tool interfaces (M8)** — the bot should have had a "prepare quote" tool, not a "make deal" tool. Capability boundary = the failure class can't occur at all.
   - **Guardrails / injection defense (M14)** — "ignore your rules" should be recognized as adversarial input.
   - **Governance (M15)** — any binding commitment requires human approval.
4. **Root-cause line to refuse:** *"the AI made a mistake and sold the car for $1."* Wrong — the model followed injected instructions within authority it never should have had. Correct line: *"a quote bot was granted transaction authority, with no capability boundary and no injection defense."*
5. **Module that would have prevented it:** **M8 (tool interfaces / capability boundaries)** first, **M14 (injection defense)** second.
</details>

---

**In DSH:** failure mitigation lives in the `guard` package — including a *repeat-tool guard* that stops the loop pathology this module names as class 6/8 — alongside `runtime-diagnostics`.

**Next module:** [M3 — Harness Architecture & the ADK Surface](../03-harness-architecture/README.md) — with the failure catalog in hand, we name the parts of a harness, learn the ADR discipline, and meet the framework we'll build with (ADK, via LiteLLM/Azure models).
