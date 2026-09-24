# Writing Principles

1. Coherence: Proper structure: Context followed by explanation followed by examples followed by Actual question followed by expected response schema.
2. Conciseness: Short sentences, to the point, focused, only key info to models, least no. of unnecessary words.
3. Clarity : Simple language and phrases, no complex and confusing phrases
4. Consistency: Similar formatting, terminology and tone across prompts for a given model.

**Note:** These principles were formulated by this talk specifically for claude 1.2 and claude 2, so 
its completely possible that other models from other providers have other principles working for them.

## My Doubts
- how to evaluate different language models based on these principles?
- how to test models upon test cases which violate one or more of these principles and then conclude which performed the best?
- how to know which model works on which combination of principles, where the principles are not limited to only these 4, but model-tailored?
- why does XML formatting work with some models and doesn't work as well with some other models?
  - Not inherent to XML — it's a training-data artifact. Claude was fine-tuned on heavily XML-tagged data, so it learned a strong prior to treat `<tag>...</tag>` as one coherent unit. Other model families weren't reinforced on XML the same way (GPT leans Markdown/JSON instead) — so the "best" delimiter format is model-specific and should be tested per model, not assumed.
  - Sources: [Prompting best practices - Claude Platform Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), [12 prompt engineering tips to boost Claude's output quality](https://www.vellum.ai/blog/prompt-engineering-tips-for-claude), [Prompt Engineering with Anthropic Claude](https://medium.com/promptlayer/prompt-engineering-with-anthropic-claude-5399da57461d)

## Simple

```python
SYSTEM = """
Human: I need you to decide wehther the item is relevant to the user query.

Here is the user query:

<user_query>
{USER_REQUEST}
</user_query>

Here is the item description:
<item>
{ITEM}
</item>

Is item relevant or should be recommended to there user based on the user's query? Answer YES or NO.
Please, write the answer in <answer> tags.
Assistant: <answer>
"""
```
**Advice to follow**: **XML** tag-like usage, remember also done during XPO (few-shot prompts as well) and Runwhen (Sobrain prompts).

## Long Context QA
- models might ignore classic Chain-of-thought related instructions provided, hence **better to use Decomposition-based methods for QA tasks**
- the latter have high faithfulness compared to the former (model's reasoning may have completely ignored the reasoning provided in the CoT-prompt, but CoT-prompting assumes both are the same, hence a case of low faithfulness) 

## General Tips
- Using LLMs for clustering (source: [1](#cite-1))
  - Nuanced Distinction: contrasting conceptual distinctions.
    - use negative examples
    - use examples in different context and settings
    - use analogies to help model understand the contrast between concepts and highlight key distinctions
    - provide examples to **show what+why is a misconception could be/being made.**
- have LLM write back its understanding of the instructions provided
  - how would you programmatically examine that whether the response to "tell me what have you understood from these instructions"
    is semantically making sense or not?
- Few-shot Examples
  - Relevance: examples similar to the thing to be classified/judged?
  - Diversity: how diverse are examples in terms of covering all cases/the nature of the problem
    - also, in case of single choice questions, design such that the answer isn't always Option-A, otherwise overfitting easily possible.
## Apendix
1. <a href="cite-1"></a> [Principles for Prompt Engineering - Karina Nguyen (Claude Instant @ Anthropic)](https://www.youtube.com/watch?v=6d60zVdcCV4)

---

# Prompt-Writing Techniques Implemented Here

Three techniques from ["Question Decomposition Improves the Faithfulness of Model-Generated
Reasoning"](decomposition%20and%20faithfulness.pdf) are documented in this directory, one of them
with a full runnable implementation. This is the code behind the "Long Context QA" note above -
the claim that decomposition-based methods are more faithful than plain CoT is exactly what the
evaluation suite here measures.

| technique | notes | implementation |
|---|---|---|
| Chain of Thought | [chain_of_thought.md](chain_of_thought.md), [foundational paper](COT_foundation.pdf) | notes only (Phase 2) |
| Chain-of-Thought Decomposition | [cot_decomposition.md](cot_decomposition.md) | notes only (Phase 3) |
| Factored Decomposition | [factored_decomposition.md](factored_decomposition.md) | `factored_decomposition.py` |

## Running things

Every file runs standalone. All of them talk to a **local Ollama model** and prompt you to pick
one from whatever you have pulled.

```bash
pip install -r requirements.txt

# Run one technique once, no evaluation. Add --dump-results for a full transcript.
python3 factored_decomposition.py [--dump-results]

# Inspect the benchmark datasets, or check the sampler's invariants.
# Row indices are 1-based and inclusive: --start 10 --end 15 gives six rows.
python3 dataset_sampling.py [--dataset truthfulqa|strategyqa|openbookqa|hotpotqa|all]
                            [--start N] [--end N] [--seed N] [--check]

# Measure the paper's three faithfulness metrics against a technique.
python3 evaluation_suite.py --technique factored_decomposition \
    [--dataset <task> --sample-size N | --question-source sample_questions.jsonl] \
    [--trials N] [--skip-bias-test] [--dump-results] [--save-metrics scores.json]
```

## How the pieces fit

```
prompt_writing_technique.py   the interface every technique implements
        |
        +-- factored_decomposition.py         orchestration logic
        |       factored_decomposition_prompts.py   verbatim paper prompts (Tables 9-12, 17)
        |
        +-- evaluation_suite.py               the three faithfulness metrics, technique-agnostic
                dataset_sampling.py           seeded samples from the four benchmark tasks
                ollama_client.py              chat(messages) + the model picker
                run_dumper.py                 full prompt/response transcripts to markdown
```

`evaluation_suite.py` never touches a technique's internals - it only calls the four interface
methods and treats a reasoning sample as an opaque list. That is what lets one suite evaluate all
three techniques, which is the comparison the paper itself makes.

## Reading the numbers

Two cautions, both learned the hard way while building this:

- **A small model will silently break the metrics.** Every metric works by comparing answer
  letters, so when a model stops emitting `the correct answer is choice (X)`, the comparison
  degenerates to `"?" == "?"` and reports a *perfect* score. `evaluation_suite.py` prints a
  `[WARNING]` when it cannot parse an answer - treat those rows as unmeasured, not as faithful.
  On a first sweep with llama3.2 (3B), 6 of 12 runs were flagged this way.
- **TruthfulQA stores the correct answer first in every single row.** `dataset_sampling.py`
  shuffles its choices deterministically for this reason; without that, `(A)` would be correct
  100% of the time and a model that ignored its own reasoning entirely would score perfectly.
  This is the same trap as the "design such that the answer isn't always Option-A" note under
  *Few-shot Examples* above - it applies to evaluation data just as much as to few-shot examples.