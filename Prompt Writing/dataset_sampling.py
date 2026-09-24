"""
Dataset Sampling
================
Pulls a small, seeded sample of real questions from the paper's four
benchmark tasks (StrategyQA, TruthfulQA, OpenBookQA, HotpotQA) via Hugging
Face's `datasets` library, in streaming mode - the full dataset is never
downloaded or held in memory. A fixed seed reproduces the same sample, in
the same order, on every run (verified empirically, not just via the
library docs) as long as the upstream dataset's row order doesn't change -
so no snapshot file is persisted.

Each task normalizes to the same schema used by --question-source JSONL
files: (question: str, choices: list[str], gold_answer: str).
"""

import argparse
import hashlib
import random
from collections import Counter

from datasets import load_dataset


def _deterministic_shuffle(texts, correct_idx, question):
    """
    Shuffles answer choices with a seed derived from the question text, and
    returns (shuffled_texts, new_correct_idx).

    Seeded off the question rather than off sample_task()'s seed so a given
    question always gets the same choice ordering, independent of which seed
    or sample_size pulled it - two runs that both include a question compare
    like-for-like.
    """
    seed = int.from_bytes(hashlib.sha256(question.encode("utf-8")).digest()[:8], "big")
    order = list(range(len(texts)))
    random.Random(seed).shuffle(order)
    return [texts[i] for i in order], order.index(correct_idx)


def _normalize_truthfulqa(row):
    # mc1_targets is {"choices": [...], "labels": [...]} - two PARALLEL arrays,
    # not a {choice_text: 0/1} mapping. Checked against the FULL 817-row
    # validation split: every row has exactly one label==1, arrays are always
    # the same length, and the largest question has 13 choices - so positional
    # A-Z lettering tops out at 'M' and never runs past 'Z'.
    #
    # The choices MUST be shuffled. TruthfulQA stores the correct answer first
    # in every single row (index 0 in 301/301 rows sampled, versus OpenBookQA's
    # healthy A/B/C/D spread as a control). Presenting them in dataset order
    # would make "(A)" correct 100% of the time, so a model that ignores its
    # reasoning entirely and always answers (A) would score perfectly - and
    # every faithfulness metric here is built on comparing answers, so they
    # would all measure nothing.
    #
    # Note the aggregate gold-letter spread is still uneven (more A/B/C than
    # J/K/L) and that is correct, not a residual bug: questions have 2-13
    # choices, so a 2-choice question can only ever land on A or B. What
    # matters is that gold is uniform WITHIN a given choice count, which is
    # what removes the exploitable signal - a model that always answers (A)
    # now scores near chance instead of 100%.
    targets = row["mc1_targets"]
    texts, correct_idx = _deterministic_shuffle(
        targets["choices"], targets["labels"].index(1), row["question"]
    )
    letters = [chr(ord("A") + i) for i in range(len(texts))]
    choices = [f"({letter}) {text}" for letter, text in zip(letters, texts)]
    return row["question"], choices, letters[correct_idx]


def _normalize_strategyqa(row):
    # ChilleD/StrategyQA stores `answer` as a real Python bool, NOT the string
    # "True"/"False". The string branch is a deliberate guard rather than dead
    # code: if a mirror ever switched to strings, a bare `if row["answer"]`
    # would read "False" as truthy and silently flip every negative label.
    answer = row["answer"]
    if isinstance(answer, str):
        is_yes = answer.strip().lower() == "true"
    else:
        is_yes = bool(answer)
    return row["question"], ["(A) Yes", "(B) No"], "A" if is_yes else "B"


def _normalize_openbookqa(row):
    texts = row["choices"]["text"]
    labels = row["choices"]["label"]
    choices = [f"({label}) {text}" for label, text in zip(labels, texts)]
    return row["question_stem"], choices, row["answerKey"]


def _normalize_hotpotqa(row):
    choices = ["(A) Yes", "(B) No"]
    gold = "A" if row["answer"].strip().lower() == "yes" else "B"
    return row["question"], choices, gold


def _hotpotqa_is_yes_no(row):
    return row["answer"].strip().lower() in ("yes", "no")


# Each entry: (hf_dataset_id, hf_config, split, normalize_fn, filter_fn or None)
TASK_CONFIGS = {
    "truthfulqa": ("truthful_qa", "multiple_choice", "validation", _normalize_truthfulqa, None),
    "strategyqa": ("ChilleD/StrategyQA", "default", "test", _normalize_strategyqa, None),
    "openbookqa": ("allenai/openbookqa", "main", "validation", _normalize_openbookqa, None),
    # HotpotQA's answers are mostly free-text; the paper (§2.4) filters to
    # only binary yes/no questions "since the remaining questions would not
    # be easily amenable to a [multiple-choice format]" - replicated here.
    "hotpotqa": ("hotpot_qa", "distractor", "validation", _normalize_hotpotqa, _hotpotqa_is_yes_no),
}


def sample_task(task_name, seed=42, sample_size=5):
    """
    Pulls sample_size questions from task_name via seeded streaming.
    Returns a list of (question, choices, gold_answer) tuples.
    """
    if task_name not in TASK_CONFIGS:
        raise ValueError(f"Unknown task {task_name!r}. Available: {', '.join(TASK_CONFIGS)}")

    hf_dataset_id, hf_config, split, normalize_fn, filter_fn = TASK_CONFIGS[task_name]
    ds = load_dataset(hf_dataset_id, hf_config, split=split, streaming=True)
    if filter_fn:
        ds = ds.filter(filter_fn)
    sampled_rows = ds.shuffle(seed=seed, buffer_size=1000).take(sample_size)
    return [normalize_fn(row) for row in sampled_rows]


# ==========================================================================
# CLI - inspect samples, or run the invariant checks.
#
# Everything below exists only for running this file directly. Nothing here
# is imported by evaluation_suite.py, which uses sample_task() alone.
# ==========================================================================

# HotpotQA is the slow one, by a wide margin. Its rows are filtered to yes/no
# before shuffling, and the shuffle buffer wants 1000 rows - but yes/no rows
# are a minority of the split, so filling that buffer means streaming many
# times more rows than the other three tasks ever touch. Expect a wait.
_SLOW_TASK_NOTE = "hotpotqa takes a while - its yes/no filter has to stream a lot to fill the shuffle buffer"


def _view(task_name, first, last, seed):
    """
    Prints rows `first`..`last` of task_name. Both bounds are 1-BASED and
    INCLUSIVE, matching how the CLI flags read - `--start 10 --end 15` shows
    the 10th through 15th rows, six rows in total.

    This is the single place that translates to Python's 0-based half-open
    convention, so the rest of the module stays 0-based throughout:
        1-based inclusive [first, last]  ==  0-based half-open [first-1, last)

    Streaming can only ever hand back a prefix, so the window is taken by
    requesting `last` rows and slicing off the first `first-1`. The seeded
    order is stable, so that window is reproducible run to run.
    """
    # Printed BEFORE the pull, not after, so a slow task shows which one is
    # being fetched rather than sitting on a blank screen.
    print(f"=== {task_name}  |  rows {first}-{last} (1-based, inclusive)  |  seed={seed} ===")
    if task_name == "hotpotqa":
        print(f"    [fetching - {_SLOW_TASK_NOTE}]")

    rows = sample_task(task_name, seed=seed, sample_size=last)
    window = rows[first - 1:last]

    if len(rows) < last:
        print(f"    [note] only {len(rows)} row(s) available upstream, so this window is short")
    if not window:
        print("    (no rows in this range)")
        print()
        return

    for offset, (question, choices, gold) in enumerate(window):
        print(f"  [{first + offset}] {question}")
        for choice in choices:
            print(f"        {choice}{'   <-- gold' if choice[1] == gold else ''}")
    print()


def _run_checks():
    """
    Exercises the properties that simply looking at rows cannot show, and
    reaches the two code paths no amount of viewing will hit:
    _deterministic_shuffle (only reachable via TruthfulQA, never in
    isolation) and _normalize_strategyqa's string branch (dead against the
    live dataset, which always yields real bools).
    """
    print("=== 1. _deterministic_shuffle puts gold in every position, uniformly ===")
    for n in (2, 4, 13):
        trials = 6000
        texts = [f"choice{i}" for i in range(n)]
        positions = Counter(
            _deterministic_shuffle(texts, 0, f"synthetic question {q}?")[1]
            for q in range(trials)
        )
        expected = trials / n
        sd = (trials * (1 / n) * (1 - 1 / n)) ** 0.5
        worst = max(abs(positions.get(i, 0) - expected) / sd for i in range(n))
        assert len(positions) == n, f"n={n}: gold never landed in some positions: {positions}"
        assert worst < 4, f"n={n}: position {worst:.1f} sigma off uniform - seeding may be biased"
        print(f"    n={n:2d}: all {n} positions hit, worst deviation {worst:.2f} sigma  OK")

    print()
    print("=== 2. _normalize_strategyqa handles bool AND the string guard ===")
    # The live dataset only ever yields bools, so the isinstance(str) branch is
    # unreachable through the CLI. Call it directly - the branch exists because
    # bool("False") is True, which would silently invert every negative label.
    for raw, expected in [(True, "A"), (False, "B"), ("True", "A"), ("False", "B"), ("true", "A")]:
        _, _, gold = _normalize_strategyqa({"question": "synthetic?", "answer": raw})
        assert gold == expected, f"answer={raw!r} gave gold={gold!r}, expected {expected!r}"
        print(f"    answer={raw!r:>8} ({type(raw).__name__:>4}) -> gold={gold}  OK")

    print()
    print("=== 3. same seed reproduces the same sample, per task ===")
    print(f"    (two live pulls per task; {_SLOW_TASK_NOTE})")
    for task in TASK_CONFIGS:
        print(f"    {task}: ", end="", flush=True)
        assert sample_task(task, seed=7, sample_size=3) == sample_task(task, seed=7, sample_size=3), \
            f"{task}: same seed produced different samples"
        print("deterministic  OK")

    print()
    print("=== 4. TruthfulQA answer-position bias is gone ===")
    # Unshuffled, TruthfulQA's correct answer sits at index 0 in every row, so
    # gold would be "(A)" 100% of the time and every faithfulness metric here
    # (all of which compare answers) would quietly collapse to noise.
    letters = Counter(gold for _, _, gold in sample_task("truthfulqa", seed=42, sample_size=40))
    assert len(letters) > 1, f"gold is still always the same letter: {letters}"
    print(f"    gold-letter spread over 40 questions: {dict(sorted(letters.items()))}")
    print("    (uneven by design - questions carry 2-13 choices, so a 2-choice")
    print("     question can only ever land on A or B; check 1 is what proves uniformity)")

    print()
    print("All checks passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Inspect seeded samples from the paper's four benchmark tasks, or run the "
            "invariant checks. With no arguments it walks all four tasks, which exercises "
            "every normalizer in this file."
        ),
    )
    parser.add_argument(
        "--dataset", default="all", choices=sorted(TASK_CONFIGS) + ["all"],
        help="Which task to pull from. 'all' (the default) walks every task in turn.",
    )
    parser.add_argument(
        "--start", type=int, default=1, metavar="N",
        help="First row to show. 1-BASED and inclusive, so 1 is the first row (default: 1).",
    )
    parser.add_argument(
        "--end", type=int, default=5, metavar="N",
        help="Last row to show. 1-BASED and INCLUSIVE, so '--start 10 --end 15' shows the "
             "10th through 15th rows - six rows in total (default: 5).",
    )
    parser.add_argument(
        "--seed", type=int, default=42, metavar="N",
        help="Sampling seed. The same seed always reproduces the same rows (default: 42).",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Run the invariant checks instead of printing rows: shuffle uniformity, the "
             "StrategyQA bool/string guard, per-task determinism, and absence of TruthfulQA "
             "answer-position bias. These cover what viewing rows cannot, and reach the two "
             "code paths viewing can never hit.",
    )
    args = parser.parse_args()

    if args.check:
        _run_checks()
    else:
        if args.start < 1:
            raise SystemExit(f"--start is 1-based, so it must be at least 1 (got {args.start}).")
        if args.end < args.start:
            raise SystemExit(f"--end ({args.end}) must be greater than or equal to --start ({args.start}).")

        tasks = sorted(TASK_CONFIGS) if args.dataset == "all" else [args.dataset]
        for task in tasks:
            _view(task, args.start, args.end, args.seed)
