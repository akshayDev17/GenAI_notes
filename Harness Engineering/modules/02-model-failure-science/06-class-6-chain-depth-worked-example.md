# Class 6 — "Shorten the chain": the corrected worked example

> Corrects the probe and the remedy in `06-reasoning-load-vs-04-instruction-drift-against.md`. The earlier reading of "shorten the chain" as "pre-compute the intermediates" was wrong: it removed the task instead of shortening the chain. This note states the correct operation and a worked example.

## 1. What was wrong

- "Shorten the chain" cannot mean "hand the model steps 1–7 as given facts".
  - That is not a shorter chain; it is a solved subproblem, and a model that succeeds on the leftover steps proves nothing about chain depth.
- It also cannot be a general instruction to the coder, because the coder cannot pre-compute a decomposition they cannot predict.
  - A support agent's input is an arbitrary email; the step list is discovered at runtime, not written at design time.

## 2. What chain depth actually means

- Chain depth = **the number of dependent steps whose intermediate value must survive inside a single call's attention** — not the number of logical steps, tool calls, or tokens.
- The module's mechanism is the definition: "the model has no persistent scratchpad unless you give it one; intermediate results live in attention, which is lossy" (L70).
- Nine logical steps can be depth 9 (one monolithic call) or depth ~1 (each step's result written to a scratchpad or state that the next call reads).
- "Shorten the chain" therefore means **externalize the handoffs at runtime** — never pre-compute them.
  - Nothing is computed in advance; the model still does every step; the harness simply carries the handoff instead of the model's attention carrying it.

## 3. Tool calls vs. derivations — where the loss actually bites

- In a real agent, some steps are tool calls and some are the model's own derivations:
  - **Tool outputs are already externalized** (fresh tokens), so they are the *safe* part of the chain.
  - **Derivations are computed in the model's head and never written down** — comparisons, arithmetic, judgments — and *that* is where class 6 lives.
- Corollary: shortening the chain means externalizing the **derivations**, not fetching fewer facts.

## 4. The two task kinds (the original conflation)

- **Fixed pipeline** — the step list is known at design time (e.g. "given an invoice ID, compute the refund").
  - Here the coder *can* pre-script the stages; decomposition in advance is valid, and it is a pipeline, not an agent.
- **Open task** — arbitrary input → unknown decomposition (e.g. customer support).
  - Here the coder *cannot* decompose in advance. What the coder can always build is **generic externalization**: a scratchpad, structured working-memory, or a one-step-per-call loop.
  - The model supplies the decomposition at runtime; the harness supplies the persistence.
- The original example treated an open task as a fixed pipeline. That was the error.

## 5. The corrected probe — a worked example

- Scenario: subscription refund agent. Customer email: "I think I was double-charged in March and April, and I changed plans mid-March."
- Nine steps; derivations are marked:
  1. parse the request into two claims
  2. lookup March invoice → $120 *(tool)*
  3. lookup April invoice → $120 *(tool)*
  4. compare → duplicate confirmed *(derivation)*
  5. lookup plan-change date → Mar 14 *(tool)*
  6. pro-rate March across the change → $78 *(derivation)*
  7. lookup Feb credit → $20 *(tool)*
  8. net owed = 78 − 20 = $58 *(derivation)*
  9. apply the $50 escalation ceiling *(derivation + action)*

- **Monolithic arm (depth 9):** one call, no scratchpad; $78, $20, $58 held in attention.
- **Externalized arm (depth ~1 per call):** a loop with written state — call 1 reads the email and empty state, does one step, appends `duplicate=true`; call 2 reads `{duplicate=true}`, pro-rates, appends `prorated=78`; … call 9 reads `{net=58}`, applies the ceiling, issues.
  - Same nine logical steps, same decomposition, same inputs. Nothing pre-computed; only the handoff moved from attention into state.

### How the confusion manufactures itself

- Suppose step 6 is wrong: the model computes $30 instead of $78.
  - Then step 8 gives net = 30 − 20 = $10, step 9 sees $10 under the $50 ceiling, and the agent issues the refund without escalating.
  - That is a class-4-shaped outcome (an unauthorized refund) produced entirely by a class-6 error six hops earlier.
- Two readings separate it, neither needing a replay:
  - **First error vs derived error:** step 6 is the first error; step 9 is its descendant. Class 4's violating step is the origin.
  - **Re-inject the escalation rule:** compliance does not return, because the agent is applying the ceiling correctly to a false premise. The rule was never the lost object.

### Readings

| Result | Verdict |
|---|---|
| Monolithic fails at step 6; externalized succeeds | class 6 — and externalization is the fix |
| Both fail | not (only) class 6 — look at 4/5/8 |
| Both succeed | not reproduced — a variable is missing |

## 6. The tradeoff

- Externalization shortens the attention-held chain but lengthens the context: the state document grows, and early state plus standing rules sink toward the middle of a long context.
- The same task can therefore fail as class 6 (depth) first and as class 4/5 (length) later. The remedy relocates the failure surface; it does not remove it.
- So orchestration work (M10/M11) must ship with re-grounding and context-assembly discipline (M4/M10), not alone as "fixed".

## 7. Rectified remedy, in one line

- **Class 6:** externalize the derived values at runtime — scratchpad, per-step sub-agents, or compute-in-tool — paired with re-grounding, because the fix trades depth for length.
- **Not class 6:** re-grounding the instruction, and never pre-computing the answer.
