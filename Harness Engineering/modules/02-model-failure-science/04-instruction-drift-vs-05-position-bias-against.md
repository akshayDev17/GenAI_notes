# Class 4 and Class 5 Are Not Confusable

**Disputed question:** Can an AI engineer mistake, or plausibly confuse, failure class 4 (instruction drift & compliance decay) with failure class 5 (position & ordering bias)?

**Position:** AGAINST — distinct mechanisms, failure objects, independent variables, shapes, owners and fixes.

**Verdict:** One axis, two failure curves and two non-interchangeable fixes separate them; the module's recorded overlap is an upstream-enabling relationship, not an identity, and one controlled sweep — no production replay — reveals it.

---

## 1. The discriminating axis — what has been lost

- Class 4 loses the **authority of a norm**: the model is choosing to do otherwise, and the question is *which text outranks which*. Class 5 loses the **availability of a datum**: the model is not disobeying, it is not seeing, and the question is *where the text sat*.
- The module's mechanisms match: class 4 is instructions competing with retrieved text, tool results and user messages for salience (L59) — a *competition*, needing a rival; class 5 is positional attention patterns from training (L65) — a *geometry*, needing none.

## 2. The failure curve — the strongest structural discriminator

- Class 4's signature — obeyed in a short session, violated in a long one (L60) — is about *distance from the instruction*, predicting **monotone decay**.
- Class 5's signature — the same fact moved middle→end flips correctness (L66) — is about *offset at fixed budget*, predicting a **U-curve**: strong head, strong tail, weak middle.
- A U is not a decay: one has an interior minimum, the other cannot. A single sweep at identical content and instruction set, sampled by offset, separates them — you need offsets, not a replay.
- Corollary: drift needs *competing text of higher apparent authority*; position bias needs only *text at the wrong offset*, and occurs even with nothing competing.

## 3. Different independent variables cannot be one class

- Class 4 varies instruction-to-action distance and competing authority; class 5 holds content and instruction set fixed and varies absolute position. Two knobs, two classes — unless §2's sweep shows one knob doing all the work.

## 4. Probes, each with a verdict rule

### Content-neutrality test (sharpest)

- Swap the suspected competitor for neutral filler of equal length and position.
- Verdict: disappears → authority mattered → class 4. Persists at the same offsets → class 5.
- Sharpest because class 5 is content-neutral — unread text cannot cause anything — while class 4 is content-specific: a request-shaped competitor is the cause.

### Move the fact, hold the instruction

- Move only the fact middle→end; policy untouched.
- Verdict: correctness flips → class 5 (the module's own signature, L66).

### Re-inject the rule near the action, changing no content

- Add only a restatement of the rule immediately before the action.
- Verdict: compliance returns → class 4. Under class 5 it is just more text, and the buried datum stays buried.

### Shorten the session, preserve content order

- Same content, same relative order, truncated to a short session.
- Verdict: compliance returns → class 4 (L60). Surviving at equal relative offsets means position did it.

### Pad with neutral text at fixed offsets

- Content and instruction constant; neutral padding only.
- Verdict: correctness tracks padding position, not competing authority → class 5.

## 5. Two owners, two durable fixes — so the confusion is not free

### Wrong fix #1: reordering or padding for a drift problem

- Position is not authority. A policy at the end is still prose; a customer's direct request at the end is still a request. Class 4 is salience (L59), not offset.
- The module's primary class-4 fix is not positional: the refund tool enforces the $50 ceiling, so an over-limit refund is impossible without a separate escalation action (L298).

### Wrong fix #2: instruction-layer redesign for a position problem

- "Always follow policy X" does nothing for a fact buried mid-document: nothing is disobeyed, so nothing is reinforced and the fact stays unread.

### The asymmetry the module encodes

- Class 5's map row: one primary layer, **no secondary** (L121). Class 4's: instruction layer plus memory primary, orchestration re-grounding secondary (L120).
- Scenario C repeats it: capability boundary as the class-4 remedy; the positional context-assembly remedy explicitly secondary and "weaker than the tool fix" (L299).
- Severity coherence: class 5 medium, cheaply fixable (L67); class 4 high, "the mechanism behind most 'it worked in the demo' governance failures" (L61). One class, and one grade must be wrong.

## 6. The overlap conceded, then contained

- Conceded: class 5 compounds with class 4 (L67); Scenario C names class 5 as the mechanism inside a class-4 incident (L295) and borrows a positional remedy (L299).
- Contained: class 5 is an **upstream enabler** of class 4 producing a look-alike — bury the rule mid-context and the violation presents as drift. Symptom shared; mechanism not.
- Being the cause of a look-alike is not being the same class. If shared upstream cause collapsed downstream mechanisms, nine classes would compress to about three, and the module's job of turning vague alarm into a work item (L244) would fail.
- The module permits combinations without merging them: the exercise calls most incidents combinations while still demanding a named class and primary layer (L255–L257).

## 7. The professional claim

- The opening scene calls "the model hallucinated the discount policy" a *category error* (L13); the thesis is that "the model was wrong" is never a diagnosis (L30).
- Collapsing a deterministic placement fault into an authority fault repeats that vice one layer down: authority redesign funded when reordering sufficed, or reordering while the violation ships again.

## 8. Catalog evidence, and a telling absence

- **Air Canada (L138) — clean class 4:** a standing bereavement policy was overridden by the customer's request, so the bot stated an entitlement the airline did not grant. Authority, not position, was the variable.
- **Bard demo (L148) — clean class 1, and a control:** no competitor, no positional manipulation, just a fluent false claim. Both disputed classes are absent by construction.
- **Mata v. Avianca (L139) — clean class 1 primary, class 8 in the delivery path:** fabricated citations filed as real; nothing outranked, nothing buried.
- **AutoGPT loops (L222) — genuinely mixed:** class 6 reasoning degradation, class 8 loop pathology, class 9 goal misspecification (L73, L85, L91), with neither disputed class present.
- **The absence:** no catalog entry (L135–L231) is a class-5 incident — no headline story about a fact that sat in the middle — while class 4 has several, including the opening scene (L11–L13). Class 5 surfaces in swap tests (L66) because it is a property of how the model reads; class 4 produces named incidents because it is an agent choosing. Different objects enter the record differently.

## 9. The org-chart consequence

- Class 4 buys instruction-layer and memory headcount plus re-grounding and governance escalation (L120): recurring, cross-team work.
- Class 5 buys context-assembly engineering — deterministic ordering, a stable prefix for standing rules — one-shot placement work, "cheaply fixable in the context-assembly layer" (L67).
- Evidence required before funding either, none of it needing a replay: a position sweep at fixed content (monotone → 4; U → 5), a neutrality substitution with matched filler (disappears → 4; persists → 5), the short-session control with order preserved (returns → 4).

## 10. The strongest attack on this position, and the rebuttal

- The attack: both are attention allocation over a growing context, class 5 compounds with class 4 (L67), and the class-4 answer key is positional (L299) — so they are one thing.
- Rebuttal 1: that same answer makes the positional remedy secondary and weaker and the capability boundary primary (L298–L299). Different fixes, different diagnoses.
- Rebuttal 2: if position explained class 4, every long-context compliance task would fail. The module instead describes decay with a competitor that won on salience (L59), and a fix in the tool's authority ceiling (L298).
- Rebuttal 3: a U and a decay are different functions fitted from the same sweep; offsets separate them, not a second incident.

## The decision

- **Fund two line items with two owners:** context-assembly placement for class 5; instruction-layer and memory authority for class 4.
- **Believe either only with the sweep, the substitution and the short-session control on the table** — all three are cheap, all three discriminate.
- **If I am right:** long-session compliance incidents route to whoever owns ordering, are fixed once, and close.
- **If I am wrong:** the classes merge, the map collapses to one row, and placement is the whole remedy — a falsifiable outcome.
