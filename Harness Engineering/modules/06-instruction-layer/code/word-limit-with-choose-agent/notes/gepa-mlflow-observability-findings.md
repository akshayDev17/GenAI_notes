# GEPA + MLflow observability: measured findings

Companion to `run_gepa_word_limit.py` and `data/{trainset,valset,testset}.json` in this directory.
Everything below is either **measured** (a command was run and its output is quoted) or **inferred**
(read out of source, consistent with measurement, not itself tested). The two are labelled.

## 1. What `mlflow.dspy.autolog` actually records

Tutorial snippet used verbatim:

```python
mlflow.set_tracking_uri(...); mlflow.set_experiment(...)
mlflow.dspy.autolog(log_compiles=True, log_evals=True, log_traces=True)
```

- Compile run artifacts: `best_model.json`, `trainset.json`, `valset.json`.
  - `best_model.json` keys: `['demos', 'lm', 'metadata', 'signature', 'traces', 'train']`.
  - `signature.instructions` holds the final instruction text, so **the optimized prompt is stored**.
  - measured: `demos: []` and `train: []`, i.e. GEPA added **no** few-shot examples.
- Eval run artifacts: `model.json`, and `result_table.json` when the eval returns a `Prediction`.
  - `result_table.json` shape: `{"columns": [...], "data": [[...]]}` with columns
    `['score', 'example_request', 'example_next_action', 'pred_next_action']`.
  - It is **not** a list of row dicts; parsing it as one yields 0 rows and looks empty.
- Traces: 4 spans per example, `Predict.forward` (LLM), `ChatAdapter.format` (PARSER),
  `LM.__call__` (CHAT_MODEL), `ChatAdapter.parse` (PARSER).
  - `CHAT_MODEL` span attributes include `mlflow.spanInputs` (the full rendered `messages` array,
    system message included) and `mlflow.spanOutputs` (completion plus `reasoning_content`).
  - also recorded: `cache`, `max_tokens`, `model`, `model_type`, `temperature`.
- Everything the script itself `print()`s stays on stdout. Autolog records what DSPy's hooks fire
  on and nothing else, so derived lines (deltas, warnings, config block) live only in the terminal.
- Run **params** carry the prompt, which is how you audit a candidate without downloading artifacts:
  `Predict.signature.instructions`, `Predict.signature.fields.N.description` / `.prefix`, and
  `lm_params` (a JSON string holding `cache`, `max_tokens`, `model`, `model_type`, `temperature`).
  - **open item**: the logged `lm_params` reports `"cache": true` even though the script calls
    `dspy.configure_cache(enable_disk_cache=False, enable_memory_cache=False)`. Whether that recorded
    flag reflects effective behaviour or just the `dspy.LM` constructor default was never resolved.

## 2. Run naming: where the odd names come from

- `fearless-perch-822` (the compile run) is **MLflow's random `adjective-noun-NNN`**, assigned
  because the run is started with no name.
  - The compile run is created by MLflow's generic autolog wrapper:
    `safe_patch(..., manage_run=get_autologging_config(FLAVOR_NAME, "log_compiles"))` in
    `mlflow/dspy/autolog.py`, which wraps the patched `compile` in
    `with_managed_run(...)` (`mlflow/utils/autologging_utils/safety.py:134`).
  - There is **no `run_name` anywhere** in `mlflow/dspy/*` except the eval callback, so the managed
    run is always started unnamed. (`mlflow/dspy/save.py:405`'s `with mlflow.start_run():` is inside
    a docstring example for `log_model`, not the compile path.)
- `eval` / `eval_0` / `eval_full_N` come from `mlflow/dspy/callback.py:271,274`:

```python
mlflow.start_run(run_name=f"{key}_{step}", nested=True)   # when inside an optimizer
mlflow.start_run(run_name=key, nested=True)               # when outside one, and no active run
```

  - `key` defaults to `"eval"` and is overridden by `callback_metadata["metric_key"]`.
  - GEPA passes `metric_key="eval_full"` (`dspy/teleprompt/gepa/gepa_utils.py`, the
    `callback_metadata` assignment; the `{"metric_key": "eval_full"}` branch is line 252).
  - So plain `eval` = evaluations run **outside** any optimizer; `eval_0` = an optimizer-internal
    eval with no metric_key, step 0; `eval_full_N` = GEPA's full-valset evals, steps 0..N.
  - Consequence: three different evaluations of ours were all named `eval`, so a reader cannot tell
    baseline-test from trainset-diagnostic from final-test without opening each run.
- **Naming is controllable by the caller**, same rule for both cases:
  `with_managed_run` documents it at `safety.py:138-139`: *"An MLflow run is only created if there
  is no active run present when the patch function is executed"*, and `on_evaluate_start` has
  `elif mlflow.active_run() is None` (`callback.py:273`). So wrapping the call in
  `with mlflow.start_run(run_name="..."):` makes autolog log **into your run** instead of creating
  its own.
- measured, after adding that wrapper: runs are named `compile`, `eval-test-baseline`,
  `eval-trainset`, `eval-test-final`. GEPA's own `eval_0` / `eval_full_*` keep their names (the key
  comes from DSPy, not from us).

## 3. Chronology

- Chronology is `attributes.start_time` in epoch ms. **Not** the run name and **not** the run id
  (random UUIDs, no order).
- Where to confirm: the **Created at** column on Training runs / Evaluation runs, the run page's
  Created at field, or `search_runs(order_by=["attributes.start_time ASC"])`.
- measured, one run (8 examples trainset, 5 valset, budget 40):

```text
12:30:31.163  eval               ours, baseline TEST            0.0   4.5s
12:30:35.691  fearless-perch-822 compile, ends 12:32:01.004    0.0   85.3s
12:30:35.718  eval_0             nested under the compile       0.0   6.7s
12:30:59.221  eval_full_0        candidate                     40.0   7.3s
12:31:37.828  eval_full_1        candidate, the selected one    60.0   9.7s
12:31:58.307  eval_full_2        candidate                     40.0   2.6s
12:32:01.014  eval               ours, TRAINSET diagnostic      50.0   8.6s
12:32:09.672  eval               ours, final TEST               60.0   9.4s
```

- Note `eval_full_0/1/2` start and end **inside** the compile window yet carry no `parentRunId`.
- `eval_0` **does** carry `parentRunId=8c5209b8` (the compile run).

## 4. Trace ownership

- Traces link to a run through `request_metadata["mlflow.sourceRun"]` (not a top-level `run_id`
  field on `TraceInfo`).
- measured, 18 traces total, counted by that field:

```text
7b643ed8 -> 5   (ours, final TEST eval)
ccbdf600 -> 8   (ours, TRAINSET diagnostic)
e5d907f3 -> 5   (ours, baseline TEST eval)
```

  i.e. **only our three top-level `dspy.Evaluate` runs own traces**; the compile run, `eval_0` and
  every `eval_full_N` own none.
- **Inferred** (consistent with the `parentRunId` evidence, not proven): GEPA evaluates candidates
  in copied contexts (`copy_context()` in the batch evaluator), so MLflow's run context is empty
  there, `start_run(..., nested=True)` degrades to a top-level run, and traces created in that
  context have no run to attach to. Same family of cause as the assessment loss in section 6.

## 5. Datasets: two unrelated registries

- **Run-input datasets** via `mlflow.log_input(...)` land on the run as
  `run.inputs.dataset_inputs` and surface on the **run page's Datasets section**.
  - measured after wiring it up: `compile -> [trainset, valset]`, `eval-test-baseline -> [testset]`,
    `eval-trainset -> [trainset]`, `eval-test-final -> [testset]`; GEPA's own runs -> none.
  - each dataset's `source` is the absolute path to `data/<name>.json`, so it is reloadable.
- **Registered / evaluation datasets** are first-class entities created by
  `MlflowClient.create_dataset(name, experiment_id, tags)` or
  `mlflow.genai.datasets.create_dataset(...)`, and that registry is what
  `/#/experiments/<id>/datasets` lists.
  - measured: `search_datasets(experiment_ids=[eid]) -> count: 0`, which is why that tab is empty.
  - populating it: `ds = gd.create_dataset(name=..., experiment_id=...); ds.merge_records([...])`;
    `EvaluationDataset` also exposes `merge_records`, `delete_records`, `to_df`, `list_versions`,
    `has_records`.
- `log_input` does **not** create a registered dataset; the two are separate tables.
- The dspy autolog handles only `trainset` and `valset`, and only as **artifacts**
  (`mlflow/dspy/autolog.py:207-210`, `log_dspy_dataset(trainset, "trainset.json")`). There is **no
  `testset` handling anywhere** in the integration, and no `log_input` call at all.
- JSON -> `dspy.Example` still needs hydrating by hand; JSON does not carry DSPy's input/label split:

```python
[dspy.Example(**row).with_inputs("request") for row in json.loads(Path(p).read_text())]
```

  - measured: `dspy.Example(a=1).with_inputs("x")` sets `input_keys`; the positional-dict form
    `dspy.Example({...})` gives `input_keys=None`, so the split is lost.
  - `GEPA.compile` is typed `trainset: list[dspy.Example]`, so raw dicts are not a substitute.

## 6. Why the per-row metric is NULL for some rows

**The metric is not NULL.** Measured on both frozen-spec runs:

```text
columns: ['score', 'example_request', 'example_next_action', 'pred_next_action']
[1.0, 'I want my money back for order 456',      'refund_agent',  'refund_agent']
[1.0, 'Billing says I owe for a cancelled plan', 'billing_agent', 'billing_agent']
[1.0, 'Find the precedent in case SC-2023-777',  'case_agent',    'case_agent']
[1.0, 'Is it raining in Kolkata right now?',     'weather_agent', 'weather_agent']
[1.0, 'Translate this sentence into French',     'no_agent',      'no_agent']
```

and both runs report `eval: 100.0`. All five rows scored 1.0.

The count in the UI is a **separate** thing: the per-row metric column reads the trace's
**assessments**, logged by `_patch_metric` in `mlflow/dspy/autolog.py:236`:

```python
# NB: DSPy runs prediction and the metric call in the same thread, so we can retrieve
# the prediction trace ID using the last active trace ID.
pred_trace_id = mlflow.get_last_active_trace_id(thread_local=True)   # line 246
if not pred_trace_id:
    _logger.debug("Tracing during evaluation is enabled, but no prediction trace found.")
    return metric(*args, **kwargs)      # score returned, NOTHING logged -> NULL row
```

- The lookup is (`mlflow/tracing/fluent.py:70` and `:1476`):

```python
_LAST_ACTIVE_TRACE_ID_THREAD_LOCAL = ContextVar("last_active_trace_id", default=None)
...
return _LAST_ACTIVE_TRACE_ID_THREAD_LOCAL.get() if thread_local else _LAST_ACTIVE_TRACE_ID_GLOBAL
```

  It is a **`ContextVar` despite the name**, set by the tracing processor
  (`mlflow/tracing/processor/base_mlflow.py:272`).
- measured losses, assessments per trace (5 traces per eval):

```text
eval-test-baseline   [0, 0, 1, 0, 1]  -> 3 lost
eval-test-final      [1, 1, 0, 1, 1]  -> 1 lost
eval-numthreads-1    [0, 0, 0, 1, 0]  -> 4 lost   (probe)
eval-numthreads-4    [1, 1, 1, 0, 1]  -> 1 lost   (probe)
```

- **No trace ever carried two assessments**, so the results are **lost, not misattributed**.
- The loss is silent by design: debug-level log only, and the metric's return value is unaffected,
  so the run-level score and `result_table.json` stay correct while the row column is incomplete.
- **Refuted hypothesis**: thread count is not the driver. The probe gave 4 lost at
  `num_threads=1` versus 1 lost at `num_threads=4`.
  - caveat: that probe was **n=1 per arm**, so the correct reading is "not monotonic in thread
    count", not "single-threaded is worse".
- **Inferred, not measured**: that the `ContextVar` plus `copy_context()` is the operative failure
  mode. `dspy.Evaluate` runs items in copied contexts, and a `ContextVar.set()` inside a copied
  context does not propagate out. Verified **semantics only** (free, no LM calls):

```text
before:                     v.get() = None
inside the copied context:  v.get() = tr-abc123
after copy_context().run(): v.get() = None   <- set() did NOT propagate out
inside a fresh thread:      v.get() = tr-in-new-thread
back in main thread:        v.get() = None
```

- What would settle it: monkeypatch `mlflow.get_last_active_trace_id` to count how often it returns
  `None` during one `dspy.Evaluate`, and check whether that count equals the number of missing
  assessments. Not yet run.

## 7. Budget accounting (`--max-metric-calls`)

- The unit is the metric call, and two constants drive the rest: `reflection_minibatch_size = 3` and
  valset size = 5.
- 1 metric call = scoring one example once. So one full pass over the valset (5 examples) costs 5
  calls; over the trainset (8) costs 8.
- Every reflection round costs a minibatch of 3: GEPA scores the parent on 3 examples to decide what
  to fix.
- A round that produces a candidate costs another 3, to score that candidate on the same minibatch.
- A candidate that beats the parent then costs a full valset eval of 5 (this is the `eval_full_N`
  run).

So roughly:

```text
~3 calls   minibatch reflection
+ ~3       candidate minibatch score
+ ~5       full valset eval (only if the candidate is accepted)
≈ 11 per accepted iteration
≈ 6 per non-accepted iteration
≈ 3 per skipped iteration (subsample already perfect -> skip)
```

How 40 spends down, matching the run's progress bar:

```text
 5   base program's full valset eval (iteration 0)
+11   iteration 1: minibatch + candidate + full valset          -> ~16
+ 3   iteration 2: minibatch only (already perfect -> skipped)  -> ~19
+11   iteration 3: minibatch + candidate + full valset          -> ~30
+11   iteration 4: minibatch + candidate + full valset          -> ~41, capped at 40
```

So 40 is not "40 iterations"; it is 40 scorings, which buys the base eval plus roughly four
reflection rounds, because each accepted round burns ~11 calls. The progress bar denominator is
exactly `max_metric_calls`, and the run stops when it hits 40, which is why the last iteration lands
partially counted.
