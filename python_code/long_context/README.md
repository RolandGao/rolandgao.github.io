# Long Context MRCR Eval (Minimal)

This directory is now organized for one primary workflow:

- `mrcr_agent_compare_minimal.py`: the main script to compare 3 methods on MRCR (8-needle, 4K-8K).
- `benchmark_utils.py`: dataset loading + grading helpers.

## What The Main Script Runs

`mrcr_agent_compare_minimal.py` compares:
- `base_direct`: one OpenAI API call with full prompt visibility.
- `custom_windowed`: one-page-at-a-time visibility (default page = 1K tokens) with file-based notes.
- `codex_cli_single`: one `codex exec` call that returns the final answer.

## Code Map (Where To Extend)

- `evaluate_sample(...)`: one-sample orchestration.
- `evaluate_base_direct(...)`: base model baseline.
- `run_custom_windowed_loop(...)`: custom agent logic (`append_note`, `rewrite_note`, `flip_to_page`, `answer`).
- `evaluate_codex_single(...)`: Codex CLI baseline.
- `iter_mrcr_samples(...)` in `benchmark_utils.py`: dataset filtering and loading.

## Defaults

- model for all 3 methods: `gpt-5-nano`
- codex reasoning effort override: `medium` (`--codex-reasoning-effort`)
- codex baseline auth: uses a temporary isolated `CODEX_HOME` with API-key auth (does not modify your normal Codex login mode)
- benchmark slice: MRCR only, `n_needles=8`, total tokens in `4K-8K`
- custom windowed page size: `--page-tokens 1000`
- custom windowed payload cap: `--payload-limit-tokens 2000`
- custom windowed reasoning effort: `none`
- base reasoning effort: `medium`
- custom max steps: `max(--max-steps, 10 * number_of_pages)`

## Quick Start

Set API key:

```bash
export OPENAI_API_KEY=...
```

Run 1 sample (fast sanity check):

```bash
./.venv/bin/python python_code/long_context/mrcr_agent_compare_minimal.py --max-samples 1
```

Run 10 samples:

```bash
./.venv/bin/python python_code/long_context/mrcr_agent_compare_minimal.py --max-samples 10
```

If your key is in a file:

```bash
./.venv/bin/python python_code/long_context/mrcr_agent_compare_minimal.py \
  --openai-api-key-file ~/.openai_api_key \
  --max-samples 10
```

## Output

Each run is written under:

- `python_code/long_context/results/<run_name>/config.json`
- `python_code/long_context/results/<run_name>/per_sample.jsonl`
- `python_code/long_context/results/<run_name>/summary.json`

Per sample, the script may also write:

- `sample_<id>/custom_notes.txt`
- `sample_<id>/codex/` (Codex workspace files)
