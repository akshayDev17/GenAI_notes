"""
Run a REAL GEPA optimization with the docs' `WordLimitProposer` plugged in as
`instruction_proposer=`, then count the words of every instruction GEPA produced.

This is the docs' "Usage" block, not a standalone call to the ProposalFn:

    gepa = dspy.GEPA(
        metric=my_metric,
        reflection_lm=dspy.LM(...),
        instruction_proposer=WordLimitProposer(max_words=700),
        auto="medium",
    )
    optimized = gepa.compile(student=program, trainset=trainset)

Apart from `--max-words`, a real GEPA run needs (all supplied here):
  - a STUDENT PROGRAM whose docstring is the instruction GEPA rewrites
  - a METRIC in GEPA's 5-argument form. Its return type must branch on `pred_name`: a float at
    program level (dspy.Evaluate aggregates with sum()) and a dspy.Prediction(score=, feedback=)
    at predictor level. The feedback must name the expected answer, otherwise the reflection LM
    never sees your labels and invents plausible ones instead.
  - a TRAINSET that teaches
  - a VALSET that GEPA uses to choose the program it returns. Omit it and GEPA reuses the
    trainset as its own valset and warns that it will overfit.
  - a TESTSET it never sees, evaluated afterwards with dspy.Evaluate (the tutorial's pattern)
  - a REFLECTION_LM (GEPA asserts one is required, or a custom proposer)
  - a BUDGET: exactly one of auto / max_full_evals / max_metric_calls
  - optionally num_threads; use_merge is forced off here so merging never re-invokes the
    custom proposer with multiple parents.

`--no-proposer` runs the identical configuration with GEPA's DEFAULT proposer, so you can see
the length difference the word-limited proposer actually makes.

MLflow tracking (--mlflow) follows the tutorial's four steps verbatim:
https://dspy.ai/current/tutorials/gepa_facilitysupportanalyzer/#mlflow-dspy-integration
  1. %pip install mlflow>=3.0.0
  2. mlflow ui --port 5000 --backend-store-uri sqlite:///mlruns.db     (in a separate terminal)
  3. import mlflow / mlflow.set_tracking_uri("http://localhost:5000") / mlflow.set_experiment("DSPy")
  4. mlflow.dspy.autolog(log_compiles=True, log_evals=True, log_traces=True)
The URI and experiment name are exposed as --mlflow-uri and --mlflow-experiment. Autologging
records what DSPy's hooks fire on, so this script's own print() output still goes to stdout only.

Two layers, deliberately separated:

  SPEC (frozen, hand-written)  the agent roster and each agent's remit, in the output field's
                               `desc`. GEPA rewrites the docstring only, never `desc`, so the
                               roster cannot be dropped or re-worded by the proposal loop.
  POLICY (searched)            the signature docstring, which starts as a one-liner and is the
                               only thing the proposer rewrites.

That split is the point of the experiment. The script evaluates the test set before and after
compiling, so one run yields both arms:

  arm B = "TEST SET before optimization"  a competent seed WITH the spec, unaided
  arm C = "TEST SET after optimization"   the same seed plus GEPA's policy search
  (arm A, the one-liner with the roster nowhere in the prompt, measured 0% in earlier runs)

B is the number that decides whether you need an optimizer at all; C - B is what the optimizer
actually adds. Quoting A -> C, as earlier runs did, conflates the two.

Docs: https://dspy.ai/current/api/optimizers/GEPA/GEPA_Advanced/#basic-example-word-limit-proposer

Run (--max-words and --max-metric-calls are REQUIRED; live API calls; reads DEEPSEEK_API_KEY
from tmp/code/.env):
  .../python run_gepa_word_limit.py --max-words 100 --max-metric-calls 40
  .../python run_gepa_word_limit.py --max-words 100 --max-metric-calls 40 --no-proposer
  .../python run_gepa_word_limit.py --help

Budget: one full pass over the trainset costs len(TRAINSET) metric calls, and the base-program
score consumes the first pass. Aim for about 5x the trainset size, which is 40 for the 8 examples
below. Below 3x you usually get zero proposals and the run measures nothing.
"""

import argparse
import json
import os
import re
import sys
import time
from contextlib import nullcontext
from pathlib import Path

import dspy
import pandas as pd
from dotenv import load_dotenv
from gepa.core.adapter import ProposalFn

from dspy.teleprompt.gepa.gepa_utils import ReflectiveExample

try:
    import mlflow  # optional: only needed for --mlflow
except ImportError:
    mlflow = None

load_dotenv(Path(__file__).with_name(".env"))  # tmp/code/.env, independent of the CWD


# --- verbatim from the docs example -------------------------------------------------
class GenerateWordLimitedInstruction(dspy.Signature):
    """Given a current instruction and feedback examples, generate an improved instruction with word limit constraints."""

    current_instruction = dspy.InputField(desc="The current instruction that needs improvement")
    feedback_summary = dspy.InputField(desc="Feedback from examples that might include both positive and negative cases")
    max_words = dspy.InputField(desc="Maximum number of words allowed in the new instruction")

    improved_instruction = dspy.OutputField(
        desc="A new instruction that fixes the issues while staying under the max_words limit"
    )


class WordLimitProposer(ProposalFn):
    def __init__(self, max_words: int = 1000):
        self.max_words = max_words
        self.instruction_improver = dspy.ChainOfThought(GenerateWordLimitedInstruction)
        self.calls = 0  # how many proposals this proposer actually produced

    def __call__(
        self,
        candidate: dict[str, str],
        reflective_dataset: dict[str, list[ReflectiveExample]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        updated_components = {}

        for component_name in components_to_update:
            if component_name not in candidate or component_name not in reflective_dataset:
                continue

            current_instruction = candidate[component_name]
            component_examples = reflective_dataset[component_name]

            feedback_text = "\n".join(
                [
                    f"Example {i + 1}: {ex.get('Feedback', 'No feedback')}"
                    for i, ex in enumerate(component_examples)
                ]
            )

            result = self.instruction_improver(
                current_instruction=current_instruction, feedback_summary=feedback_text, max_words=self.max_words
            )

            updated_components[component_name] = result.improved_instruction
            self.calls += 1

        return updated_components


# -----------------------------------------------------------------------------------


# The agent roster is the SPEC: domain knowledge we own, so it is frozen into the output field's
# `desc`. GEPA rewrites the signature DOCSTRING only and never touches field names, `desc` or
# `prefix` (DSPy docs, "Signatures in depth" section 9), so the roster cannot be dropped,
# renamed or re-worded by the proposal loop. The docstring below is the POLICY layer, and that
# alone is what gets searched.
ROSTER = (
    "Exactly one valid agent identifier, copied verbatim:\n"
    "- refund_agent: refunds, charge reversals, money-back requests\n"
    "- billing_agent: invoices, payments, charges, plan or subscription billing\n"
    "- weather_agent: weather and forecast questions\n"
    "- case_agent: case lookup, case briefs, precedents, legal case handling\n"
    "- outage_agent: service outages, downtime, service unavailable\n"
    "- no_agent: none of the above matches, the request is out of scope, or it must be declined"
)


class Route(dspy.Signature):
    """Decide which assistant should handle the request."""

    request: str = dspy.InputField()
    next_action: str = dspy.OutputField(desc=ROSTER)


# The three disjoint splits live as JSON in data/ and are hydrated back into dspy.Example here.
# TRAINSET teaches, VALSET selects the program GEPA returns, TESTSET reports. No example appears
# in more than one split. Each record is {"request": ..., "next_action": ...}, and the input
# field is re-marked on load because JSON does not carry DSPy's input/label split.
DATA_DIR = Path(__file__).with_name("data")


def load_split(name: str):
    """Read data/<name>.json back into dspy.Example objects, re-marking the input field."""
    return [
        dspy.Example(**row).with_inputs("request")
        for row in json.loads((DATA_DIR / f"{name}.json").read_text())
    ]


TRAINSET = load_split("trainset")
VALSET = load_split("valset")
TESTSET = load_split("testset")


STRICT_MATCH = False  # set by --strict-match


def _label_present(label: str, text: str) -> bool:
    """Whole-identifier containment. Verified against these actual cases:

        "case_agent"                  -> True
        "use case_agent here"         -> True
        "case_agent_summarizer"       -> False   a longer wrong label is no longer credited
        "technical_case_agent"        -> False
        "not no_agent"                -> True    LIMITATION: a negated mention still matches
        "i will not use refund_agent" -> True    LIMITATION

    So this fixes the longer-label false positive but not negation. With negative samples in the
    trainset that gap is reachable: an output saying "no_agent is wrong, use refund_agent" still
    contains the required token and scores a pass. Use --strict-match when the output has to BE
    the label rather than merely mention it.
    """
    pattern = r"(?<![a-z0-9_])" + re.escape(label.lower()) + r"(?![a-z0-9_])"
    return re.search(pattern, text) is not None


def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    """GEPA's 5-argument metric, in the form the official tutorial uses.

    The return type MUST branch on `pred_name`:
      - `pred_name is None`  -> program-level scoring. GEPA's internal dspy.Evaluate aggregates
        these with sum(), so a dict or a Prediction here raises
        `TypeError: unsupported operand type(s) for +: 'int' and 'dict'`. Return a float.
      - `pred_name` is set   -> predictor-level feedback for the reflection LM. Return
        `dspy.Prediction(score=..., feedback=...)`. The feedback must name the gold label,
        otherwise the reflection LM never sees it and invents its own answer names.

    Negative samples (gold `no_agent`) need no special casing: the same function scores them.
    What does need care is the matcher. The default is containment, which credits an output that
    names the right label anywhere inside a longer string. --strict-match requires equality.
    """
    got = (getattr(pred, "next_action", "") or "").strip().lower()
    if STRICT_MATCH:
        hit = got == gold.next_action.lower().strip()
    else:
        hit = _label_present(gold.next_action, got)
    score = 1.0 if hit else 0.0

    if pred_name is None:
        return score

    return dspy.Prediction(
        score=score,
        feedback=f"Expected next_action to be {gold.next_action!r}; the program produced {got!r}.",
    )


def positive_int(s: str) -> int:
    value = int(s)
    if value <= 0:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return value


def report(optimized, max_words: int, seed_instruction: str, proposer_calls: int | None) -> None:
    print("\n=== optimized instructions ===")
    over = 0
    total = 0
    unchanged = 0
    for name, predictor in optimized.named_predictors():
        text = predictor.signature.instructions
        wc = len(text.split())
        total += 1
        flag = "OVER the limit" if wc > max_words else "within limit"
        if wc > max_words:
            over += 1
        if text.strip() == seed_instruction.strip():
            unchanged += 1
            flag = "UNCHANGED from the seed"
        print(f"\n--- {name}: {wc} words ({flag}) ---")
        print(text)
    print("\n=== summary ===")
    print(f"instructions: {total}   over the {max_words}-word limit: {over}/{total}")
    if proposer_calls is None:
        print("instruction_proposer: not used (--no-proposer); GEPA's default proposer ran instead.")
    elif proposer_calls == 0:
        print(
            "!!! instruction_proposer was NEVER INVOKED, so this run measured nothing.\n"
            f"    One full evaluation of the trainset costs {len(TRAINSET)} metric calls, and the\n"
            "    base-program score consumed the whole budget before any reflection round.\n"
            "    Raise --max-metric-calls (a useful floor is about 3x the trainset size)."
        )
    else:
        print(
            f"instruction_proposer produced {proposer_calls} proposal(s), so the {max_words}-word\n"
            f"limit was tested on {proposer_calls} sample(s)."
        )
    if unchanged:
        print(f"note: {unchanged}/{total} instruction(s) came back byte-identical to the seed.")
    print("A custom proposer is a request to the reflection LM; nothing in GEPA validates it.")


def evaluate_split(program, split, name: str, num_threads: int) -> float:
    """Run dspy.Evaluate over one split and print its per-example breakdown.

    This is the tutorial's pattern. dspy.Evaluate calls the metric with three positional
    arguments, so `pred_name` stays None, the metric takes its program-level branch and returns
    a float, and Evaluate can aggregate with sum().
    """
    evaluator = dspy.Evaluate(
        devset=split,
        metric=metric,
        num_threads=num_threads,
        display_progress=False,
        return_all_scores=True,
    )
    res = evaluator(program)

    print(f"\n=== {name}: {len(split)} examples, score {res.score:.1f}% ===")
    fails = 0
    for i, (ex, pred, score) in enumerate(res.results):
        got = (getattr(pred, "next_action", "") or "").strip().lower()
        ok = score == 1.0
        if not ok:
            fails += 1
        print(
            f"  [{i}] {'PASS' if ok else 'FAIL'}  gold={ex.next_action:15} "
            f"got={got[:36]!r}  request={ex.request[:38]!r}"
        )
    print(f"  {fails} failure(s) out of {len(split)}")
    return res.score


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a real GEPA optimization with the docs' WordLimitProposer as instruction_proposer."
    )
    parser.add_argument("--max-words", type=positive_int, required=True, help="word limit passed to the proposer")
    parser.add_argument(
        "--max-metric-calls", type=positive_int, required=True, help="GEPA budget: total metric calls allowed"
    )
    parser.add_argument("--model", default="deepseek/deepseek-v4-flash", help="LM used as both task and reflection LM")
    parser.add_argument("--num-threads", type=positive_int, default=4, help="GEPA evaluation concurrency")
    parser.add_argument(
        "--strict-match",
        action="store_true",
        help="require the output to BE the gold label instead of merely containing it",
    )
    parser.add_argument(
        "--no-proposer",
        action="store_true",
        help="skip instruction_proposer and use GEPA's default proposer, for comparison",
    )
    parser.add_argument(
        "--mlflow",
        action="store_true",
        help="enable mlflow.dspy.autolog (needs mlflow>=3.0.0 and a reachable tracking URI)",
    )
    parser.add_argument(
        "--mlflow-uri",
        default="http://localhost:5000",
        help="tracking URI, as the tutorial sets it",
    )
    parser.add_argument(
        "--mlflow-experiment",
        default="DSPy",
        help="experiment name, as the tutorial sets it",
    )

    try:
        args = parser.parse_args()
    except SystemExit as exc:
        if exc.code != 0:
            parser.print_help(sys.stderr)
        raise

    global STRICT_MATCH
    STRICT_MATCH = args.strict_match

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("ABORTED: DEEPSEEK_API_KEY not set (expected in tmp/code/.env)")
        return

    if args.mlflow:
        if mlflow is None:
            print("ABORTED: --mlflow requested but mlflow is not installed.")
            print("         install it with: pip install 'mlflow>=3.0.0'")
            return
        # Tutorial steps 3 and 4, verbatim.
        mlflow.set_tracking_uri(args.mlflow_uri)
        mlflow.set_experiment(args.mlflow_experiment)
        mlflow.dspy.autolog(
            # Log the optimization progress
            log_compiles=True,
            # Log the evaluation results
            log_evals=True,
            # Log traces from module executions
            log_traces=True,
        )

    dspy.configure_cache(enable_disk_cache=False, enable_memory_cache=False)
    lm = dspy.LM(args.model, api_key=api_key, max_tokens=3000)
    dspy.configure(lm=lm)

    program = dspy.Predict(Route)

    def nneg(split):
        return sum(1 for e in split if e.next_action == "no_agent")

    print("=== config ===")
    print("student          :", type(program).__name__, "over", Route.__name__)
    print("seed instruction :", repr(program.signature.instructions))
    print("frozen spec      : agent roster in next_action.desc (GEPA cannot rewrite desc)")
    print("trainset         :", len(TRAINSET), f"examples ({nneg(TRAINSET)} negatives) -> teaches")
    print("valset           :", len(VALSET), f"examples ({nneg(VALSET)} negatives) -> GEPA picks the returned program on this")
    print("testset          :", len(TESTSET), f"examples ({nneg(TESTSET)} negatives) -> held out, only dspy.Evaluate sees it")
    print("match mode       :", "strict (equality)" if args.strict_match else "containment (whole identifier)")
    print("reflection_lm    :", args.model)
    print(
        "budget           : max_metric_calls =",
        args.max_metric_calls,
        f"(~{args.max_metric_calls / len(TRAINSET):.2f} full evals of the {len(TRAINSET)}-example trainset)",
    )
    print("instruction_proposer :", "NONE (GEPA default)" if args.no_proposer else f"WordLimitProposer(max_words={args.max_words})")
    print(
        "mlflow           :",
        f"ON -> {args.mlflow_uri} (experiment {args.mlflow_experiment!r})" if args.mlflow else "off",
    )
    print()

    gepa_kwargs = {
        "metric": metric,
        "max_metric_calls": args.max_metric_calls,
        "reflection_lm": lm,
        "num_threads": args.num_threads,
        "use_merge": False,  # keep the custom proposer out of merge rounds
    }
    proposer = None
    if not args.no_proposer:
        proposer = WordLimitProposer(max_words=args.max_words)
        gepa_kwargs["instruction_proposer"] = proposer

    def named_run(name):
        return mlflow.start_run(run_name=name) if args.mlflow else nullcontext()

    def log_split_dataset(name: str, split, context: str) -> None:
        if not args.mlflow:
            return
        df = pd.DataFrame([ex.toDict() for ex in split])
        dataset = mlflow.data.from_pandas(df, source=str(DATA_DIR / f"{name}.json"), name=name)
        mlflow.log_input(dataset, context=context)

    with named_run("eval-test-baseline"):
        log_split_dataset("testset", TESTSET, "test")
        baseline = evaluate_split(program, TESTSET, "TEST SET before optimization (seed instruction)", args.num_threads)

    print("\n=== compiling ===")
    t0 = time.time()
    with named_run("compile"):
        log_split_dataset("trainset", TRAINSET, "train")
        log_split_dataset("valset", VALSET, "validation")
        optimized = dspy.GEPA(**gepa_kwargs).compile(student=program, trainset=TRAINSET, valset=VALSET)
    print(f"compile finished in {time.time() - t0:.1f}s")

    report(optimized, args.max_words, program.signature.instructions, None if proposer is None else proposer.calls)

    with named_run("eval-trainset"):
        log_split_dataset("trainset", TRAINSET, "train")
        evaluate_split(
            optimized, TRAINSET, "TRAINSET after optimization (diagnostic: did it overfit here?)", args.num_threads
        )
    with named_run("eval-test-final"):
        log_split_dataset("testset", TESTSET, "test")
        after = evaluate_split(optimized, TESTSET, "TEST SET after optimization (held out)", args.num_threads)

    print("\n=== held-out result ===")
    print(f"test-set score: {baseline:.1f}% -> {after:.1f}%  ({after - baseline:+.1f} points)")


if __name__ == "__main__":
    main()
