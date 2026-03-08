# Long Context MRCR Eval

This directory now uses one primary runner:

- `mrcr_eval.py`: unified MRCR evaluator for method comparison and bucketed sampling.
- `benchmark_utils.py`: dataset loading and grading helpers shared by the runner.

## Methods

`mrcr_eval.py` can run any subset of:

- `base_direct`: one OpenAI API call with full prompt visibility.
- `custom_windowed`: one-page-at-a-time visibility with file-based notes.
- `codex_cli_single`: one `codex exec` call that returns the final answer.

Use `--methods` to choose, for example:

```bash
--methods base_direct,custom_windowed,codex_cli_single
```

## Defaults

- default methods: `base_direct,custom_windowed`
- default buckets: `4096-8192,8192-16384`
- default max samples: `--max-samples-per-bucket 10`
- default model(s): `gpt-5-nano`
- custom window page size: `--page-tokens 1000`
- custom window payload cap: `--payload-limit-tokens 2000`
- custom window notes cap: `--notes-limit-tokens 800`

## Quick Start

Set API key:

```bash
export OPENAI_API_KEY=...
```

Fast sanity check (single bucket, 1 sample, default methods):

```bash
./.venv/bin/python python_code/long_context/mrcr_eval.py \
  --bucket-spec 4096-8192 \
  --max-samples-per-bucket 1
```

Run all three methods:

```bash
./.venv/bin/python python_code/long_context/mrcr_eval.py \
  --methods base_direct,custom_windowed,codex_cli_single \
  --bucket-spec 4096-8192 \
  --max-samples-per-bucket 1
```

If your key is in a file:

```bash
./.venv/bin/python python_code/long_context/mrcr_eval.py \
  --openai-api-key-file ~/.openai_api_key \
  --max-samples-per-bucket 10
```

## Reuse Selected Samples

To rerun on previously selected IDs:

```bash
./.venv/bin/python python_code/long_context/mrcr_eval.py \
  --selected-samples-jsonl python_code/long_context/results/<old_run>/selected_samples.jsonl
```

## Output

Each run is written under:

- `python_code/long_context/results/<run_name>/config.json`
- `python_code/long_context/results/<run_name>/selection_summary.json`
- `python_code/long_context/results/<run_name>/selected_samples.jsonl`
- `python_code/long_context/results/<run_name>/per_sample.jsonl`
- `python_code/long_context/results/<run_name>/summary.json`

Per sample, the runner may also write:

- `sample_<id>/custom_notes.txt`
- `sample_<id>/codex/`
