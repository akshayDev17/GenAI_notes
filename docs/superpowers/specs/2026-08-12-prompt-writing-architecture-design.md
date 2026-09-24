# Prompt Writing Architecture: Shared Interface, Client, and Evaluation Suite

**Date**: 2026-08-12
**Status**: Approved design, not yet implemented

## Context

`Prompt Writing/` documents and implements several LLM prompting techniques discussed in
"Question Decomposition Improves the Faithfulness of Model-Generated Reasoning" (the paper).
Three techniques are covered in notes: Chain of Thought (CoT), Chain-of-Thought Decomposition
(CoTD), and Factored Decomposition (FD). Only Factored Decomposition has real, working code
today (`Factored Decomposition/paper_factored_decomposition.py` and
`Factored Decomposition/faithfulness-measuring-suite.py`), built up incrementally over a long
session: a paper-faithful implementation, a real Ollama-backed client, a markdown transcript
dumper, and a real-model implementation of the paper's three faithfulness metrics (Early
Answering / truncation sensitivity, Adding Mistakes / corruption sensitivity, and Suggested
Answer Sensitivity / biasing-context sensitivity).

The faithfulness evaluation suite (`faithfulness-measuring-suite.py`) is currently written
specifically against Factored Decomposition's internals (it imports
`ConversationalFactoredDecomposer` directly and calls its private methods). The paper itself
compares all three techniques against the same three faithfulness metrics — so the evaluation
logic should live at a level above any single technique, and each technique should be pluggable
into it through a common interface, rather than the suite being coupled to one implementation.

Separately, the paper's four benchmark tasks (StrategyQA, TruthfulQA, OpenBookQA, HotpotQA) were
investigated as candidates for real evaluation data. Their official GitHub repos turned out to be
large, mostly-irrelevant research codebases (or, for HotpotQA, just the project's marketing
website with no real data) rather than lightweight data sources — Hugging Face's `datasets`
library is the right way to source them instead.

## Goals

- Define a generic `PromptWritingTechnique` interface that any prompting technique implements,
  so the faithfulness evaluation suite can run against any of them without technique-specific
  code.
- Redesign `OllamaLlmClient` to be a fully generic chat client with no technique-flavored method
  names — each technique owns how it uses the client internally.
- Migrate the existing Factored Decomposition code onto this interface, validating the design
  against a real, already-working implementation before it's duplicated for CoT and CoTD.
- Replace the ad hoc dataset question (`sample_questions.jsonl`, hand-written) with the option to
  pull real, small, seeded samples from the paper's actual benchmark datasets via Hugging Face.
- Flatten the directory structure: no per-technique subfolders for code or notes, everything
  under `Prompt Writing/` directly.

## Non-goals (this phase)

- Implementing CoT or CoT Decomposition in code. Only their existing `README.md` notes move as
  part of the flattening; actual `.py` implementations of the interface are follow-up phases,
  done once this design is validated end-to-end against Factored Decomposition.
- Persisting dataset samples to a file. Seeded streaming is deterministic enough (verified against
  the official `datasets` library docs) that no snapshot file is needed.
- Replicating the paper's full-scale benchmark run (hundreds/thousands of questions per task).
  This is about being able to run a *real, small, faithful-methodology* replication locally.

## Architecture

All files live flat under `Prompt Writing/` — no per-technique subfolders. This was a deliberate
simplification: it also removes the need for any cross-directory import workaround (sys.path
manipulation, package `__init__.py` files, or renaming directories to avoid spaces) since
same-directory sibling imports resolve automatically when a script is run directly.

```
Prompt Writing/
├── README.md                          # intro + links to each technique's .md
├── prompt_writing_technique.py        # PromptWritingTechnique ABC (the shared interface)
├── ollama_client.py                   # OllamaLlmClient - chat(messages) + select_model() staticmethod
├── run_dumper.py                      # RunDumper - unchanged, technique-owned
├── dataset_sampling.py                # seeded HF `datasets` streaming sampler
├── evaluation_suite.py                # FaithfulnessEvaluationSuite (generic) + its own __main__
├── requirements.txt                   # one shared file
├── factored_decomposition.py          # FD implementation of the interface + its own __main__
├── factored_decomposition_prompts.py  # FD's verbatim paper prompts (Tables 9/10/11/12/17)
├── factored_decomposition.md          # was Factored Decomposition/README.md
├── sample_questions.jsonl             # was Factored Decomposition/sample_questions.jsonl
├── chain_of_thought.md                # was ChainofThought/README.md
├── COT_foundation.pdf                 # was ChainofThought/COT_foundation.pdf
├── cot_decomposition.md               # was COT Decomposition/README.md
├── decomposition and faithfulness.pdf # unchanged location
└── ... (other existing top-level files, e.g. the flashcards CSV)
```

### `PromptWritingTechnique` interface

```python
from abc import ABC, abstractmethod

class PromptWritingTechnique(ABC):
    @abstractmethod
    def generate(self, question, choices) -> tuple[str, list]:
        """
        Runs the technique end-to-end on a fresh question. Returns
        (final_answer, reasoning_sample). reasoning_sample's element type is
        private to the implementation - callers only ever pass it back into
        this same technique's other methods below, never inspect its contents.

        Also used for suggested-answer-bias runs: the bias is injected into
        `question` text by the caller (e.g. "... I think the correct answer
        is (C), but I'm curious to hear what you think."), transparent to
        the technique - no separate biased-run method is needed.
        """
        raise NotImplementedError

    @abstractmethod
    def answer_with_truncated_reasoning(self, question, choices, reasoning_sample, num_steps) -> str:
        """Recompose using only the first num_steps of reasoning_sample."""
        raise NotImplementedError

    @abstractmethod
    def answer_with_corrupted_reasoning(self, question, choices, reasoning_sample, step_index) -> str:
        """
        Corrupt step_index per this technique's own procedure (this is where
        Table 15/16/17-style differences live - each technique's corruption
        mechanism is genuinely different, confirmed against the paper) and
        recompose.
        """
        raise NotImplementedError

    def render_reasoning_as_text(self, reasoning_sample) -> str:
        """
        Human/LLM-readable rendering of the reasoning sample. Used by the
        suggested-answer bias-disclosure judge call and by dump-file
        rendering.

        NOT abstract, unlike the three methods above - deliberately. The
        paper's own Zero-Shot/Few-Shot baseline conditions (Table 2) have no
        reasoning at all ("Answer: The correct answer is choice (X)", no
        intermediate steps), so a universal "there is no meaningful reasoning
        to render" default belongs here rather than forcing every
        reasoning-less technique to reinvent the same trivial stringification
        just to satisfy the interface. CoT/CoTD/FD should still override this
        for a nicer, structure-aware rendering.
        """
        return "\n".join(str(step) for step in reasoning_sample) if reasoning_sample else "(no reasoning generated)"

    def _to_client_messages(self, history) -> list:
        """
        Translates a technique's own "human"/"assistant" chat-history
        convention (matching the paper's literal Human:/Assistant: transcript
        style, used throughout its prompt tables for Factored Decomposition
        and likely shared by CoT Decomposition's tables too) into the
        client's standard user/assistant message shape.

        Concrete and leading-underscore (internal-use, not part of the
        contract evaluation_suite.py calls) for the same reason as
        render_reasoning_as_text: not every technique is guaranteed to build
        its internal history this way - a simpler single-turn technique might
        construct user/assistant messages directly and never call this at
        all. Available to use, not required to override or call.
        """
        return [
            {"role": "user" if turn["role"] == "human" else "assistant", "content": turn["content"]}
            for turn in history
        ]

    def _history_to_markdown(self, history) -> str:
        """
        Renders the same "human"/"assistant" history convention as markdown,
        for dump-file rendering (the "Full prompt sent" section RunDumper.record()
        expects). Concrete for the same reason as _to_client_messages above.
        """
        lines = []
        for turn in history:
            role_label = "Human" if turn["role"] == "human" else "Assistant"
            lines.append(f"**{role_label}:**\n\n{turn['content']}\n")
        return "\n".join(lines)
```

`_to_client_messages` and `_history_to_markdown` live on the interface rather than duplicated per
technique or split into a separate module, specifically because this is a low-risk place to put
them: `prompt_writing_technique.py` already exists, every technique already subclasses it, and
unlike inventing a new shared module (which would need its shape validated against a second real
consumer before Phase 1 has one), slotting an optional concrete method onto an already-designed
extension point costs nothing if a future technique never calls it.

The evaluator never touches a reasoning sample's contents directly - only `len(reasoning_sample)`
(to know how many truncation levels / corruption steps to try) and index values passed back into
the technique's own methods. This is why no shared reasoning-step type is needed: corruption
genuinely differs per technique (confirmed via Tables 16/17 - CoTD shows the model the existing
(subquestion, subanswer) pair and asks it to edit the answer; FD shows *only* the subquestion and
asks for a fresh wrong answer from scratch), so the interpretation of "what's inside a reasoning
step" was always going to be private per-technique regardless.

`answer_with_corrupted_reasoning` stays abstract despite the same reasoning-less-technique
question applying to it in principle: the evaluator's own loop
(`for step_idx in range(len(reasoning_sample))`) never calls it at all when there's nothing to
corrupt, so a reasoning-less technique's implementation is simply unreached dead code, not a
forced dishonest stub. `answer_with_truncated_reasoning` stays abstract too - even a reasoning-less
technique's version is a genuine one-liner ("ignore `num_steps`, answer zero-shot"), not
boilerplate worth centralizing.

### `OllamaLlmClient`

```python
class OllamaLlmClient:
    def __init__(self, model="llama3.2:latest"):
        self.model = model

    def chat(self, messages):
        """messages: list of {"role": "user"/"assistant"/"system", "content": str} -
        standard Ollama/OpenAI message shape. No technique-specific structure here."""
        response = ollama.chat(model=self.model, messages=messages, think=False)
        return response["message"]["content"]

    @staticmethod
    def select_model():
        """Prompts the user to pick from whatever models are currently pulled in local Ollama."""
        available = ollama.list().models
        if not available:
            raise SystemExit("No local Ollama models found. Run `ollama pull <model>` first.")
        # ... prints numbered list, reads a choice, returns available[i].model
```

One method for chat. No `call_planner`/`call_answering_agent`/`call_recomposition_agent`-style
naming (today's client has these, all identical passthroughs - purely technique-flavored naming
with no functional difference). No `"human"`→`"user"` role remapping in the client either - each
technique's implementation does its own message-building and owns its own role conventions before
calling `client.chat()`.

`select_model()` lives on `OllamaLlmClient` as a `@staticmethod` rather than in its own module.
It doesn't touch `self` or any instance state - it only calls `ollama.list()` (a different Ollama
API surface than `chat()`'s `ollama.chat()` call) to enumerate locally pulled models and returns
the chosen model name as a string, for the caller to then pass into
`OllamaLlmClient(model=...)`. It couldn't be an *instance* method: the model name is needed
*before* a client exists, not after, so there is no `self` to hang it on yet - a `@staticmethod`
sidesteps that chicken-and-egg problem while keeping the picker in the same namespace as the class
it configures. Callers: `model_name = OllamaLlmClient.select_model()` then
`client = OllamaLlmClient(model=model_name)`.

### `RunDumper`

Mostly unchanged from today's implementation (`results_<title>_<model>[_<run-label>].md` naming,
accumulate-and-write, technique-owned - each technique implementation creates its own `RunDumper`
instance and records its own calls into it; the shared `evaluation_suite.py` never constructs or
touches a dumper directly). One rendering change made during implementation: `record()` wraps the
"Full prompt sent" and "Raw model response" bodies in `<details><summary>...</summary>...</details>`
so a rendered dump (GitHub, VS Code preview) starts collapsed - a dump with dozens of calls across
a multi-question `--dataset` sweep was unreadable fully expanded. Same accumulate-and-write
mechanics otherwise.

That same dump-size concern (many calls × many questions) is also why `evaluation_suite.py` gained
`--save-metrics` below - a way to persist results from a sweep without opting into the full
transcript dump at all.

### `dataset_sampling.py`

Pulls a small, seeded sample per task via Hugging Face's `datasets` library in streaming mode, so
the full dataset is never downloaded or held in memory:

```python
from datasets import load_dataset

def sample_task(hf_dataset_id, hf_config, split, seed, sample_size):
    ds = load_dataset(hf_dataset_id, hf_config, split=split, streaming=True)
    sampled = ds.shuffle(seed=seed, buffer_size=1000).take(sample_size)
    return [normalize(task_name, row) for row in sampled]
```

Determinism confirmed directly against the official `datasets` documentation (not assumed): a
fixed `seed` + fixed `buffer_size` reproduces the same shuffle order on every run, as long as the
upstream dataset's row/shard order doesn't change between fetches (true for a versioned, published
HF dataset in practice). No persisted snapshot file is needed as a result - this was a real
question raised during design and resolved by checking the docs rather than assuming.

Each task normalizes to the same schema, extending today's `sample_questions.jsonl` shape with a
gold answer field:

```json
{"question": "...", "choices": ["(A) ...", "(B) ..."], "gold_answer": "B"}
```

Confirmed HF dataset IDs (all four verified by running against the live datasets, not assumed):

| task | dataset id | config | split | notes |
|---|---|---|---|---|
| truthfulqa | `truthful_qa` | `multiple_choice` | `validation` | `mc1_targets` is two parallel arrays (`choices`/`labels`), not a text→0/1 map; choices must be shuffled (see below) |
| strategyqa | `ChilleD/StrategyQA` | `default` | `test` | `answer` is a real Python `bool`, not `"True"`/`"False"`; the obvious `voidful/StrategyQA` mirror is unusable (`ArrowInvalid: JSON parse error` on both splits) |
| openbookqa | `allenai/openbookqa` | `main` | `validation` | `choices` is `{text: [...], label: [...]}`; balanced `answerKey` |
| hotpotqa | `hotpot_qa` | `distractor` | `validation` | free-text answers, filtered to binary yes/no before sampling per the paper's §2.4 methodology |

**TruthfulQA answer-position bias.** TruthfulQA stores the correct answer first in every row (verified
at index 0 in 301/301 rows sampled; OpenBookQA's A/B/C/D spread served as the control). Emitting the
choices in dataset order would make `(A)` correct 100% of the time, so a model that ignored its own
reasoning entirely and always answered `(A)` would score perfectly - and since all three faithfulness
metrics work by comparing answers across truncated/corrupted/biased runs, every metric would silently
collapse to noise. `dataset_sampling.py` therefore shuffles TruthfulQA's choices using a seed derived
from the question text (so a given question always gets the same ordering, independent of the sampling
seed or sample size). The other three tasks need no shuffle: OpenBookQA carries its own balanced
`answerKey`, and the two binary tasks use a fixed `(A) Yes / (B) No` presentation whose gold letter
already varies.

The aggregate gold-letter spread after shuffling is still uneven (more A/B/C than J/K/L), and that is
expected rather than a residual bug: TruthfulQA questions carry 2-13 choices, so a 2-choice question
can only ever land on A or B, and only the rare 13-choice questions can reach M. The property that
actually removes the exploitable signal is uniformity *within* a given choice count - confirmed by
testing the shuffle helper directly on 20k synthetic questions per size (max deviation 2.7 sigma
across 26 position buckets, i.e. ordinary scatter with no seeding bias). Practically: a model that
always answers `(A)` scores near chance instead of 100%.

`dataset_sampling.py` also has its own `__main__`, following the same "every file is runnable on
its own" principle as the technique implementations:

```
python3 dataset_sampling.py [--dataset <task>|all] [--start N] [--end N] [--seed N] [--check]
```

Row indices are **1-based and inclusive** (`--start 10 --end 15` shows the 10th through 15th rows,
six rows), converted to Python's 0-based half-open convention in exactly one place. `--check` runs
the invariant checks rather than printing rows, and exists because viewing rows cannot exercise
everything in the file: `_deterministic_shuffle` is reachable only through TruthfulQA and never in
isolation, and `_normalize_strategyqa`'s string-guard branch is unreachable against the live
dataset (which always yields real bools). `--check` calls both directly, and also verifies
per-task determinism and the absence of TruthfulQA position bias.

### `evaluation_suite.py`

`FaithfulnessEvaluationSuite` becomes fully generic - it takes a `PromptWritingTechnique` instance
(not a Factored-Decomposition-specific `RealModelEvaluator` wrapper, which goes away) and drives
all three metrics through the four interface methods:

- **Early Answering** (`evaluate_early_answering`): loops `answer_with_truncated_reasoning` over
  increasing `num_steps`, compares against the modal full-reasoning answer.
- **Adding Mistakes** (`evaluate_adding_mistakes`): loops `answer_with_corrupted_reasoning` over
  each step index, compares against the modal baseline answer.
- **Suggested Answer Sensitivity** (`evaluate_suggested_answer_sensitivity`): calls `generate()`
  with an unbiased and then a biased question (bias injected into the question text), checks
  whether the answer drifted and whether `render_reasoning_as_text()`'s output discloses the bias
  (an LLM-judge call, our own addition - the paper states it verified this but doesn't publish
  how).

  Two distinct reference points are in play here, and conflating them is a methodology error.
  *Which option to suggest* must be an incorrect one, which is defined by `gold_answer` when
  available (every `--dataset` task supplies one); without gold, the model's own modal unbiased
  answer stands in for "correct", a disclosed approximation that breaks down precisely when the
  model is already wrong - it would then suggest the genuinely correct answer as the supposedly
  incorrect bias, inverting the metric. *Whether the answer drifted* is always measured against
  the model's own modal unbiased answer, since the question is whether the bias moved this model,
  not whether the model is right. The selection also prefers to avoid suggesting the model's own
  reference answer (suggesting what it already believes tests nothing), but never at the cost of
  suggesting gold - on a binary question whose gold and reference differ, those two exclusions
  cover every option and paper-faithfulness wins.

Has its own `__main__`:

```
python3 evaluation_suite.py --technique factored_decomposition \
    [--dataset strategyqa --sample-size 5 --seed 42 | --question-source sample_questions.jsonl] \
    [--trials N] [--dump-results] [--skip-bias-test] [--save-metrics PATH]
```

`--technique` dynamically loads and instantiates the requested implementation.
`--dataset`/`--question-source` are mutually exclusive; if neither is given, falls back to today's
single hardcoded demo question (unchanged default behavior). Unknown `--technique` values fail
fast with a clear error before any model/network calls happen.

`--save-metrics PATH` writes the per-question faithfulness scores (truncation index, corruption
rate, undisclosed drift rate) as JSON to `PATH`, independent of `--dump-results`. Added because a
`--dump-results` sweep over several `--dataset` questions writes a full prompt/response transcript
for every trial of every metric (early answering, adding mistakes, and - unless
`--skip-bias-test` - suggested-answer sensitivity's full `generate()` reruns), which grows large
fast; `--save-metrics` lets a sweep persist its computed results without opting into that. Passing
`--dump-results` together with `--dataset --sample-size N>1` prints a warning pointing at
`--save-metrics` as the lighter alternative.

### Per-technique standalone run

Each technique keeps its own runnable script for a no-evaluation single run, matching today's
"cd in, run the script directly" pattern:

```
python3 factored_decomposition.py [--dump-results]
```

Constructs its own `OllamaLlmClient` (via `OllamaLlmClient.select_model()`), calls `generate()` once, prints the
answer and reasoning, writes a dump if requested. No faithfulness metrics involved - that's what
`evaluation_suite.py` is for.

## Migration Plan (Phase 1 scope)

1. Move `ollama_client.py`, `run_dumper.py` up to `Prompt Writing/`, redesign `OllamaLlmClient` to
   the single `chat()` method plus a `select_model()` `@staticmethod` (today's duplicated-per-file
   picker function, now shared and namespaced under the class it configures rather than a
   standalone module).
2. Write `prompt_writing_technique.py` (the ABC).
3. Migrate `Factored Decomposition/paper_factored_decomposition.py` →
   `Prompt Writing/factored_decomposition.py`, refactored to implement `PromptWritingTechnique`.
   Keep its `MockPaperLLMClient` and verbatim paper prompt constants (`DECOMPOSITION_PREAMBLE`,
   etc.) - those are technique-owned data, not shared infrastructure. The prompt constants go in a
   sibling `factored_decomposition_prompts.py` so the main file is orchestration logic only and
   "exactly what the paper said" is auditable in one place. Kept as a Python module rather than
   JSON/YAML deliberately: JSON has no multi-line string syntax (each preamble would collapse onto
   a single ~1550-character escaped line, versus 389 chars max in Python form - measured, not
   assumed), no comments (losing the `# TABLE 17: ...` provenance annotations), and would add a
   serialization boundary to text that must stay byte-for-byte. The mock client also dispatches on
   these constants by name, so Python keeps typos failing loudly at import.
4. Migrate `Factored Decomposition/faithfulness-measuring-suite.py` →
   `Prompt Writing/evaluation_suite.py`, generalized to take any `PromptWritingTechnique` (the
   current `RealModelEvaluator` wrapper is absorbed into the interface itself and goes away).
5. Write `dataset_sampling.py`.
6. Move `Factored Decomposition/README.md` → `factored_decomposition.md`,
   `ChainofThought/README.md` → `chain_of_thought.md`, `ChainofThought/COT_foundation.pdf` →
   `COT_foundation.pdf`, `COT Decomposition/README.md` → `cot_decomposition.md`. Delete the
   now-empty `Factored Decomposition/`, `ChainofThought/`, `COT Decomposition/` folders.
7. Update `Prompt Writing/README.md` with a short intro and links to each technique's `.md`.
8. Move `sample_questions.jsonl` and `Factored Decomposition/requirements.txt` up to
   `Prompt Writing/requirements.txt` (no top-level `requirements.txt` exists yet, confirmed - this
   is a plain move, not a merge). Add the `datasets` package for `dataset_sampling.py`.

## Validation

Regression-shaped, since this refactors already-working code rather than building greenfield:

1. `factored_decomposition.py`'s standalone run produces output equivalent to today's
   `paper_factored_decomposition.py` (same decomposition loop, same recomposition, same dump
   format).
2. `evaluation_suite.py --technique factored_decomposition` reproduces equivalent behavior to
   today's `faithfulness-measuring-suite.py` - all three metrics run, same dump-file separation,
   same CLI flag semantics (`--trials`, `--dump-results`, `--skip-bias-test`).
3. `dataset_sampling.py` spot-checked against at least one real task (TruthfulQA's `mc_task.json`
   structure was already confirmed during design) to confirm normalization produces valid
   `{question, choices, gold_answer}` records the evaluation loop can consume.

## Open Questions for Follow-up Phases

- ~~Exact HF dataset config/split names for StrategyQA, OpenBookQA, and HotpotQA.~~ RESOLVED - all
  four verified empirically against the live datasets; see the table in the `dataset_sampling.py`
  section above.
- Whether `gold_answer` should also feed into Early Answering / Adding Mistakes as a real
  correctness check. It is now genuinely used by Suggested Answer Sensitivity (to pick an option
  that is incorrect by the dataset's own label rather than by the model's opinion), but the other
  two metrics still measure only self-consistency - whether the model's answer moves when its
  reasoning is truncated or corrupted - never whether that answer is right. Adding an accuracy
  column alongside them would let a run distinguish "faithful and correct" from "faithful and
  confidently wrong", which the paper reports separately. Enhancement, not a defect: the two
  metrics as specified are about sensitivity, not accuracy.
- CoT and CoT Decomposition implementations (Phase 2 and Phase 3), once this pattern is validated
  against Factored Decomposition. If it turns out their paper prompt tables do NOT use the same
  "human"/"assistant" `Human:`/`Assistant:` transcript convention Factored Decomposition uses, the
  `_to_client_messages`/`_history_to_markdown` concrete methods on `PromptWritingTechnique` simply
  go unused by that technique - no harm either way, since they were made optional for exactly this
  reason.
