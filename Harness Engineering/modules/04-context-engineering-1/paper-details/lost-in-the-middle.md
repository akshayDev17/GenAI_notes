# Paper details — *Lost in the Middle: How Language Models Use Long Contexts*

**Citation:** Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang. *Transactions of the Association for Computational Linguistics (TACL)*, 2023. [arXiv:2307.03172](https://arxiv.org/pdf/2307.03172)

---

## Sections that support "performance is highest at the beginning and end"

| Section | What it says |
|---|---|
| **Abstract** | "performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts." |
| **§1 (Figure 1 caption)** | names the two biases explicitly: "better at using relevant information that occurs at the very beginning (**primacy bias**) or end… (**recency bias**), and performance degrades significantly… in the middle." |
| **§2.3 Results and Discussion** | the subsection titled *"Model performance is highest when relevant information occurs at the beginning or end of its input context"* — the primary evidence, Figure 5. |
| **§3.2** | the same U-shape reproduced on the key-value retrieval task (Figure 7). |
| **§4.3 / Appendix E** | primacy/recency as a function of model scale: 7B is recency-only, 13B and 70B show both. |

---

## What "performance" means, and how it is computed

**Metric:** *accuracy* — the paper states it directly: "judging whether any of the correct answers… appear in the predicted output" (§2.1 for QA; §3.1 for key-value).

### The two tasks

1. **Multi-document QA** (§2): NaturalQuestions. `k` documents in context; exactly **one** contains the answer, the other `k−1` are distractors retrieved by Contriever (MS-MARCO-tuned). `k` ∈ {10, 20, 30}, and the answer document's *position* is varied.
2. **Key-value retrieval** (§3): a serialized JSON object of `k` key-value pairs (all 128-bit UUIDs) plus one query key; return the matching value. `k` ∈ {75, 140, 300}, position varied.

### Python, as the paper's scoring works

```python
def contains_any(predicted: str, gold_answers: list[str]) -> bool:
    return any(g in predicted for g in gold_answers)

def accuracy(examples: list) -> float:
    correct = sum(contains_any(ex["prediction"], ex["gold"]) for ex in examples)
    return correct / len(examples)
```

That is the entire metric — substring presence. No F1, no exact-match normalization.

### Terms involved

- **closed-book** — no documents in the prompt (the model's parametric memory alone)
- **oracle** — only the answer document, no distractors
- **`k` total documents** — answer doc + `k−1` distractors
- **distractor** — a retrieved non-answer document
- **relevant-information position** — where in the context the answer-bearing doc/pair sits
- **U-shaped curve** — accuracy vs. position

---

## Examples of 100% and low scores

- **100%** — Claude-1.3 and Claude-1.3(100K) "do nearly perfectly on all evaluated input context lengths" on key-value retrieval (§3.2). With query-aware contextualization, "GPT-3.5-Turbo (16K)… achieves **perfect performance** when evaluated with 300 key-value pairs" (§4.2).
- **Below the model's own closed-book score** — in multi-doc QA, "in the worst case, performance in 20- and 30-document settings is **lower than… closed-book performance (56.1%)**" for GPT-3.5-Turbo (§2.3). Giving the model the answer can score *worse* than giving it nothing.
- **Concrete key-value number** — GPT-3.5-Turbo(16K), 300 pairs, without contextualization: **45.6%** worst case (§4.2).

---

## Why the module cites it

Liu is the source of the **behavioral** claim: *placed at the ends, a fact is used more reliably.* It measures accuracy, not attention. The attention-level claim (U-shaped attention weights) is a different paper — see `found-in-the-middle.md`.
