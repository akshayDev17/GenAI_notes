# Definitional audit — M2 Model Failure Science (`README.md`)

Scope: the *course-internal* content that a prior audit (["README-source-audit.md"](./README-source-audit.md), §"Definitional (not auditable)") waved off as non-auditable. Each item below is audited against primary sources where they exist, and against the module READMEs' own text for internal consistency. Verdicts: **verified / contradicted / unsourced / internal-inconsistency**.

---

## 1. The failure classes

- **Exhaustiveness — FAILED.** Established literature names failure modes absent from the nine. The README's own "Real incidents" catalog proves the gap: category **6 "Guardrails, safety & misbehavior"** (DPD, Bing/Sydney, Snapchat My AI, NEDA Tessa, NYC MyCity illegal advice, iTutorGroup discrimination) maps to **no** failure class — none of the nine is "safety violation / harmful output / misbehavior". Same for category **5 "Data exfiltration & confidentiality"** (Samsung, Amazon Q) → no "privacy leakage" class; and category **8 "Runaway loops, cost & reliability"** (AutoGPT, DN42, LangChain 47k, McDonald's) → no "availability/latency" or "cost/inefficiency" class (class 6 is framed as reasoning *quality*, not availability or cost).
  - The safety/trustworthiness literature treats these as first-class dimensions: **Huang et al., "A Survey of Safety and Trustworthiness of LLMs through the Lens of Verification and Validation," arXiv 2305.11391** — https://arxiv.org/abs/2305.11391 (note: the audit brief cited "2312.xxxx"; the canonical survey is 2305.11391); **Sun et al., "TrustLLM," arXiv 2401.05561** — https://arxiv.org/abs/2401.05561 (8 dimensions incl. Safety and Privacy). The course's own **M12** even ships a `safety_v1` eval criterion ("Safety violations (M15)") that maps to *no* M2 class — the taxonomy and its own eval layer are out of sync.
  - **Raj et al., "Model or Harness? An Interaction-Centric Taxonomy for Localizing Agent Failures," arXiv 2607.28802** — https://arxiv.org/abs/2607.28802 — organizes **41 failure modes** across model/harness/user/tool/memory/environment edges, including environment- and grader-side failures the nine never name.

- **Mutual exclusivity — FAILED, and the README admits it.** The "Contested boundaries" section plus its own debate briefs concede overlap: **4 vs 6** ([for](./06-reasoning-load-vs-04-instruction-drift-for.md)) states the two are "the same observation, driven by the same variable, written in the same sentence"; **4 vs 5** ([for](./04-instruction-drift-vs-05-position-bias-for.md)) states they are "one attention-allocation failure described at two altitudes." (Correction: the README's "class 6/8" is *not* an overlap claim — it names the *loop symptom* that class 6 (reasoning degradation) and class 8 (repeated tool calls) share; DSH's `repeat-tool-reminder` guard addresses that shared symptom, verified against `packages/guard/`.)

- **Mechanism vs. class conflation — CONFIRMED.** Class 5 "position & ordering bias" is a *mechanism* (positional attention), not a failure mode; the README itself uses it as a mechanism — Scenario C is classified "class 4 … with **class 5 — position bias as the mechanism**," and the 4-vs-5 brief shows class 4's own example borrows class 5's positional vocabulary ("policy at token 3,000 … less salient than the customer message at token 3,001"). Classes 3 (shortcut learning), 4 (attention dilution), 5 (positional attention), and 6 (lossy attention) are all mechanisms; only 1, 2, 7, 8, 9 are observable failure *modes*. This is precisely the repair-assignment problem 2607.28802 states it exists to fix ("localize failures to the interactions in which they originate and identify the responsible component").

- **Alignment with the hallucination literature — PARTIAL.** **Huang et al., "A Survey on Hallucination in Large Language Models," arXiv 2311.05232** — https://arxiv.org/abs/2311.05232 — splits hallucination into *factuality* vs *faithfulness* (instruction/context/logical inconsistency). The README's class 1 ("confabulation … fluent, confident output that is false") covers only the factuality half, while the faithfulness half (instruction inconsistency) is split off into classes 4/7/9 — a defensible harness-oriented cut, but one the README never flags as *diverging* from the canonical taxonomy. The borrowed clinical term "confabulation: unconsciously replace fact with fantasy" is a known point of debate, not settled usage.

---

## 2. Failure class → harness layer map

All six flagged mislabels are **CONFIRMED** against the module READMEs:

- **Class 3 → "adversarial test sets (M12)" — CONFIRMED wrong.** M12's eval taxonomy (tool trajectory, response match, rubric, groundedness, safety, multi-turn) contains **no** "adversarial test sets." "Adversarial probes" and "invariance tests" live in **M6** ("Adversarial probes. Actively try to break the policy … Invariance tests … This is M2's brittleness, tested."). The README's own class-3 audit line already says so: "'adversarial test sets' is actually M6's content."
- **Class 4 → "M10 re-grounding steps" — CONFIRMED absent.** M10 (autonomy spectrum, agentic loop, hybrid shell, human handoff) never contains "re-grounding." Re-grounding-the-policy-near-the-task is M4's concept (stable prefix / primacy-recency; "re-ground it near the current task each turn" appears in M4's Scenario C answer). The README's class-4 audit line admits it: "M10's 're-grounding steps' are absent — they live in M2 and M4."
- **Class 2 → "M13 human review queues" / "M6 strip-the-flatterer" — CONFIRMED absent.** M13 has a "human handoff" *rung* (retry→fallback→degrade→handoff→safe-fail), not "human review queues," and never mentions sycophancy. M6 never names sycophancy at all. The README's class-2 audit line concedes it: "the map's 'invariance eval' does not exist anywhere; M6 and M13 never name it."
- **Class 7 → "M15 approval gates" — CONFIRMED category error.** M15's approval flows gate *consequential/irreversible actions* ("the irreversible or consequential action is gated by a human decision"), not *omitted content*. A gate cannot catch a liability clause silently dropped from a summary. README's class-7 audit line: "M15's approval gates gate actions, not omitted content."
- **Class 8 → "M13 retries/validation" — CONFIRMED no validation.** M13 provides retry/fallback/degrade/handoff/safe-fail and budgets, but **no** validation of tool arguments or outputs (that is M8's error semantics). README's class-8 audit line: "M13 is mislabeled — 'validation' is absent, it is retroactive containment."
- **Class 9 → "M10/M12" — CONFIRMED silent; M15 declares it unsolved.** Neither M10 nor M12 names "goal misspecification." M15 names it only to declare it unsolved ("Emergent misbehavior … M2 class 9 … " under "What remains genuinely unsolved"). README's class-9 audit line: "M10 and M12 never name it."

**Overall map accuracy: POOR.** Of nine rows, at least **seven** contain a wrong, absent, or mismatched cell: row 1's secondary ("Verification of tool results (M8)") is itself a mismatch per the README's class-1 audit line ("M8 … its 'poisoned results' is not the model fabricating a result"), plus rows 2, 3, 4, 7, 8, 9 as above. Only rows 5 and 6 are clean-ish, and row 5 is flagged as "mitigation-by-convention, with no detection."

---

## 3. Attribution ("frequency in production")

- **The Low / High / Rising column is UNSOURCED.** "Model capability … Low — rare, and usually known in advance," "Harness design … High — the overwhelming majority," "Environment … Rising" are quantitative claims with no citation, just like the 80/20 line. The prior audit already found the 80/20 split unsourced; this extends that finding to the whole frequency column.
- **2607.28802 contradicts the framing of a global frequency split.** Its abstract is explicit that attribution is *per-failure-mode* localization, not a global ratio: "the same visible failure may call for model post-training, harness engineering, environment redesign, or benchmark repair depending on its source." It provides a fault side per mode, not a "harness = High" blanket. — https://arxiv.org/abs/2607.28802
- **2605.26731 directly undercuts "Model capability = Low … known in advance."** Cho, "It's Not the Capability: Harness Sensitivity Is Non-Monotone Across LLM Agent Tiers," arXiv 2605.26731 — https://arxiv.org/abs/2605.26731 — shows harness sensitivity is **non-monotone** across capability tiers (the "monotone inverse" assumption is refuted on two fronts) and that its six-label taxonomy has "format_violation dominates capable-model failures while wrong_file dominates low-capability failures." I.e. capability-tier failures are *structured and predictable by tier*, not uniformly rare-and-known-in-advance. The paper's title is itself a rebuke to the course's "it's the harness" thesis.
- **Conclusion:** the *qualitative* direction (harness faults are common) is defensible, but the specific Low/High/Rising magnitudes and the 80/20 ratio are course rhetoric, not literature numbers — and 2605.26731 contradicts the "capability = Low" cell specifically.

---

## 4. Design exercise (internal consistency)

- **Scenario A (→ class 7) drifts from the map.** Class 7's map row is "Evaluation — constraint checks (M12), Instruction layer (M6) | Governance — approval gates (M15)." The answer prescribes **M4/M5 map-reduce** ("summarize *per section* (map-reduce over the document)") — layers that are **not** in class 7's map row. The M15 leg ("a human approval gate on anything that will be signed from. Caught = a coverage flag surfaces") also silently relies on M12's *coverage flag* for detection, since the M15 gate itself cannot see an omission (see §2, class 7).
- **Scenario B (→ class 2) mislabels the invariance test as M12.** The answer prescribes "Evaluation (M12) — an *invariance* test: same diff under confident / neutral / hostile author framing." M12's criteria contain **no invariance criterion**; invariance tests are M6's ("Invariance tests. The same request, phrased differently … This is M2's brittleness, tested."). The "invariance eval" the map and answer point to does not exist in M12.
- **Scenario C (→ class 4 + 5) fixes with class 8's owner.** The answer's "real fix" is "Tool interfaces (M8) — make the refund tool itself enforce the $50 ceiling … the policy becomes a capability boundary." But class 4's map row is M6/M7/M10, and **M8 is class 8's owner**; M4 (the answer's secondary "stable prefix") is class 5's owner. The answer is a defensible engineering fix but is *not* what the map routes class 4/5 to.
- **Stretch Tahoe (→ class 8 + 9) adds M14, which is the environment row.** The answer prescribes "Guardrails / injection defense (M14)." Class 8's map row is M8/M9(+M13); class 9's is M15/M10(+M12); neither names M14. M14 is the *attribution table's environment row* ("Environment … Harden the layer (M14)"), not a class 8/9 owner.
- **Cross-cutting circularity — CONFIRMED.** All four answers attribute the structural cause to **harness design** (Scenario A/B/C literally "Attribution: harness design"; the Stretch: "harness design, triggered by environment"). Every scenario is constructed so the model demonstrably *can* do the task (escalates in short sessions; finds the bug when neutral; summarizes fine), which *by construction* rules out model capability. The answer key therefore cannot generate evidence for the "High — the overwhelming majority" / 80% harness thesis — it only ever re-asserts it. The design exercises are circular with respect to the attribution table.

---

## 5. Opening scene (mechanism claim)

- The mechanism claim — "the model followed the most salient instruction in its context … a customer message … allowed to outrank the standing policy … no mechanism to know which text … was policy and which was data" — is **VERIFIED** against primary sources.
- **Wallace et al., "The Instruction Hierarchy," arXiv 2404.13208** — https://arxiv.org/abs/2404.13208 — states the exact vulnerability: "LLMs often consider system prompts … to be the same priority as text from untrusted users and third parties," and proposes a hierarchy so models "selectively ignore lower-privileged instructions."
- **Greshake et al., "Not What You've Signed Up For," arXiv 2302.12173** — https://arxiv.org/abs/2302.12173 — states LLM-integrated apps "blur the line between data and instructions," enabling instructions injected into retrieved data to override developer controls.
- Only the *narrative* (the specific ordering agent, 40% discount) is hypothetical; the technical mechanism is well-established. Verdict: **verified**.

---

## 6. The meta-lesson line ("$76,000 Tahoe … tribunal ruling … $100 billion typo")

- **Chevrolet Tahoe "$76,000" — approximately right, but a value figure, not a loss.** The "$76,000" is the Tahoe's price/MSRP, not money lost — no transaction actually completed (the dealer did not honor the chatbot's "$1" agreement). The figure is within the reported $70K–$81K range (e.g. the "$76,000 Chevrolet Tahoe for $1" framing appears in coverage of the Bakke/Chevrolet incident — https://tech.yahoo.com/ai/chatgpt/articles/software-engineer-tricks-car-dealership-162737145.html). Verdict: **partially verified** — correct order of magnitude, but the meta-lesson groups it with two *realized* liabilities (a ruling and a market-value loss), implying a comparable loss that did not occur.
- **Google Bard "~$100B" — VERIFIED.** Alphabet market value erased ~$100B after the JWST demo error (README catalog cites BBC/CNN; confirmed by the prior source audit).
- **Air Canada tribunal ruling — VERIFIED.** Moffatt v. Air Canada (BC Civil Resolution Tribunal) held the airline liable and rejected the "separate legal entity" defense (README catalog cites Law360; confirmed by the prior source audit).

---

## Claims that need correction

1. **Taxonomy is not exhaustive and not mutually exclusive.** Add (or explicitly exclude-and-name) safety/jailbreak, privacy leakage, availability/latency, and cost/inefficiency classes — or, at minimum, add a sentence stating the nine are a *competence-only* subset and pointing to the trustworthiness dimensions (2305.11391 / TrustLLM 2401.05561) and the 41-mode interaction taxonomy (2607.28802) for the rest.
2. **Drop or re-flag "confabulation"** as a debated clinical borrowing, and reconcile class 1 with Huang et al.'s factuality/faithfulness split (2311.05232).
3. **Mark classes 3/4/5/6 as mechanisms**, not modes; re-scope class 5 "position bias" explicitly as a mechanism (the README already treats it that way in Scenario C).
4. **Repair the map (7 of 9 rows).** Fix class 3 (adversarial/invariance → M6), class 4 (re-grounding → M4, not M10), class 2 (M13 "review queues" and M6 sycophancy don't exist), class 7 (M15 gates actions, not content), class 8 (M13 has retries, no validation), class 9 (M10/M12 never name it; M15 says unsolved).
5. **Relabel the attribution "frequency" column as a course heuristic, not data.** Delete or annotate "Low / High / Rising" and the 80/20 line; 2605.26731 contradicts "capability = Low," and 2607.28802 assigns fault per-mode, not by global ratio.
6. **Fix the design-exercise answer key** to match the map (or fix the map to match the answers): Scenario A's M4/M5, Scenario B's "M12 invariance test" (it's M6), Scenario C's M8 fix (class 8's owner), and the Tahoe answer's M14 (environment row) all drift from the map rows they're supposed to illustrate.
7. **Acknowledge the answer key's circularity** with the 80%-harness thesis (every scenario is built to be a harness-design case).
8. **Qualify the Tahoe number** in the meta-lesson: "$76,000" is the vehicle price, and no loss was realized (unlike Bard's ~$100B and the Air Canada ruling).
