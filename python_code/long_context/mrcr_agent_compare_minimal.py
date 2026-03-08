from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import tiktoken
from openai import OpenAI

try:
    from .benchmark_utils import (
        MRCRSample,
        extract_last_user_message,
        grade_mrcr,
        iter_mrcr_samples,
        messages_to_transcript,
    )
except ImportError:
    from benchmark_utils import (  # type: ignore
        MRCRSample,
        extract_last_user_message,
        grade_mrcr,
        iter_mrcr_samples,
        messages_to_transcript,
    )

ENC = tiktoken.get_encoding("o200k_base")


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += int(other.input_tokens or 0)
        self.output_tokens += int(other.output_tokens or 0)

    def to_dict(self) -> Dict[str, int]:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MRCR 8-needle 4K-8K compare: base_direct vs custom_windowed vs codex_cli_single")
    p.add_argument("--model", default="gpt-5-nano")
    p.add_argument("--codex-model", default="gpt-5-nano")
    p.add_argument(
        "--codex-reasoning-effort",
        choices=["minimal", "low", "medium", "high", "none"],
        default="medium",
    )
    p.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh", "none"], default="medium")
    p.add_argument("--custom-reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh", "none"], default="none")
    p.add_argument("--page-tokens", type=int, default=1000)
    p.add_argument("--payload-limit-tokens", type=int, default=2000)
    p.add_argument("--notes-limit-tokens", type=int, default=800)
    p.add_argument("--max-steps", type=int, default=0)
    p.add_argument("--codex-timeout-seconds", type=int, default=180)
    p.add_argument("--offset", type=int, default=2000)
    p.add_argument("--scan-rows", type=int, default=400)
    p.add_argument("--max-samples", type=int, default=1)
    p.add_argument("--openai-api-key-file", default=None)
    p.add_argument("--output-dir", default="python_code/long_context/results")
    p.add_argument("--run-name", default=None)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def normalize_effort(value: Optional[str]) -> Optional[str]:
    return None if value in (None, "none") else value


def maybe_set_api_key(path: Optional[str]) -> None:
    if os.getenv("OPENAI_API_KEY") or not path:
        return
    key_path = Path(path).expanduser()
    if key_path.exists():
        os.environ["OPENAI_API_KEY"] = key_path.read_text(encoding="utf-8").strip()


def tok_len(text: str) -> int:
    return len(ENC.encode(text))


def truncate_tokens(text: str, limit: int) -> str:
    if limit <= 0:
        return ""
    toks = ENC.encode(text)
    return text if len(toks) <= limit else ENC.decode(toks[:limit])


def split_pages(text: str, page_tokens: int) -> List[str]:
    if page_tokens <= 0:
        return [text]
    toks = ENC.encode(text)
    if not toks:
        return [""]
    return [ENC.decode(toks[i : i + page_tokens]) for i in range(0, len(toks), page_tokens)]


def first_json_object(text: str) -> Optional[Dict[str, Any]]:
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            return obj
    return None


def usage_from_response(resp: Any) -> Usage:
    u = getattr(resp, "usage", None)
    if u is None:
        return Usage()
    return Usage(int(getattr(u, "input_tokens", 0) or 0), int(getattr(u, "output_tokens", 0) or 0))


def call_openai(client: OpenAI, model: str, input_payload: Any, reasoning_effort: Optional[str]) -> Tuple[str, Usage]:
    kwargs: Dict[str, Any] = {"model": model, "input": input_payload}
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    resp = client.responses.create(**kwargs)
    return resp.output_text or "", usage_from_response(resp)


def prepare_pages_and_question(messages: Sequence[Dict[str, Any]], page_tokens: int) -> Tuple[List[str], str]:
    question = extract_last_user_message(messages)
    prompt_messages = list(messages)
    if prompt_messages and str(prompt_messages[-1].get("role", "")).lower() == "user":
        prompt_messages = prompt_messages[:-1]
    transcript = messages_to_transcript(prompt_messages)
    return split_pages(transcript, page_tokens), question


def method_result(answer: str, sample: MRCRSample, usage: Usage, latency_seconds: float, error: Optional[str], stats: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    g = grade_mrcr(answer, sample.answer, sample.random_string_to_prepend)
    out: Dict[str, Any] = {
        "score": g["score"],
        "prefix_ok": g["prefix_ok"],
        "latency_seconds": latency_seconds,
        "usage": usage.to_dict(),
        "answer": (answer or "")[:2000],
        "error": error,
    }
    if stats is not None:
        out["stats"] = stats
    return out


def evaluate_base_direct(sample: MRCRSample, args: argparse.Namespace, client: Optional[OpenAI]) -> Dict[str, Any]:
    start = time.perf_counter()
    if args.dry_run:
        return method_result(sample.answer, sample, Usage(), time.perf_counter() - start, None)

    try:
        assert client is not None
        answer, usage = call_openai(client, args.model, list(sample.messages), args.reasoning_effort)
        return method_result(answer, sample, usage, time.perf_counter() - start, None)
    except Exception as exc:
        return method_result("", sample, Usage(), time.perf_counter() - start, str(exc))


def custom_prompt(question: str, page_idx: int, n_pages: int, page_text: str, notes: str) -> str:
    return (
        "You are solving an MRCR retrieval task using paged context.\n"
        f"Question:\n{question}\n\n"
        f"Current page {page_idx + 1}/{n_pages} (this is the only MRCR page visible now):\n"
        f"{page_text}\n\n"
        "Current notes:\n"
        f"{notes}\n\n"
        "Reply with JSON only. Valid actions:\n"
        '{"action":"append_note","text":"short factual note"}\n'
        '{"action":"rewrite_note","text":"replace all notes with this text"}\n'
        '{"action":"flip_to_page","page":3}\n'
        '{"action":"answer","text":"final answer"}'
    )


def run_custom_windowed_loop(
    *,
    client: OpenAI,
    model: str,
    reasoning_effort: Optional[str],
    question: str,
    pages: Sequence[str],
    notes_path: Path,
    page_tokens: int,
    payload_limit_tokens: int,
    notes_limit_tokens: int,
    max_steps: int,
) -> Tuple[str, Usage, Dict[str, int]]:
    notes_path.write_text("", encoding="utf-8")
    usage = Usage()
    stats = {"steps": 0, "page_flips": 0, "mrcr_page_tokens_seen": 0, "user_prompt_tokens": 0}
    page_idx = 0

    for _ in range(max_steps):
        page_text = pages[page_idx]
        notes = truncate_tokens(notes_path.read_text(encoding="utf-8"), notes_limit_tokens)
        prompt = custom_prompt(question, page_idx, len(pages), page_text, notes)
        prompt = truncate_tokens(prompt, payload_limit_tokens + 2000)

        step_answer, step_usage = call_openai(client, model, [{"role": "user", "content": prompt}], reasoning_effort)
        usage.add(step_usage)
        stats["steps"] += 1
        stats["mrcr_page_tokens_seen"] += min(page_tokens, tok_len(page_text))
        stats["user_prompt_tokens"] += tok_len(prompt)

        cmd = first_json_object(step_answer)
        if cmd is None:
            if step_answer.strip():
                return step_answer, usage, stats
            continue

        action = str(cmd.get("action", "")).lower()
        if action == "append_note":
            text = str(cmd.get("text", "")).strip()
            if text:
                with notes_path.open("a", encoding="utf-8") as fh:
                    fh.write(text + "\n")
            continue

        if action == "rewrite_note":
            text = str(cmd.get("text", "")).strip()
            notes_path.write_text((text + "\n") if text else "", encoding="utf-8")
            continue

        if action == "flip_to_page":
            try:
                target = int(cmd.get("page", page_idx + 1)) - 1
            except Exception:
                target = page_idx
            target = max(0, min(len(pages) - 1, target))
            if target != page_idx:
                page_idx = target
                stats["page_flips"] += 1
            continue

        if action == "answer":
            return str(cmd.get("text", "")), usage, stats

    notes = truncate_tokens(notes_path.read_text(encoding="utf-8"), notes_limit_tokens)
    fallback_prompt = (
        "You ran out of steps. Use these notes and answer exactly the MRCR question.\n"
        f"Question:\n{question}\n\n"
        f"Notes:\n{notes}"
    )
    fallback_answer, fallback_usage = call_openai(
        client,
        model,
        [{"role": "user", "content": fallback_prompt}],
        reasoning_effort,
    )
    usage.add(fallback_usage)
    return fallback_answer, usage, stats


def evaluate_custom_windowed(
    sample: MRCRSample,
    args: argparse.Namespace,
    client: Optional[OpenAI],
    question: str,
    pages: Sequence[str],
    notes_path: Path,
    max_steps: int,
) -> Dict[str, Any]:
    start = time.perf_counter()
    if args.dry_run:
        empty_stats = {"steps": 0, "page_flips": 0, "mrcr_page_tokens_seen": 0, "user_prompt_tokens": 0}
        return method_result(sample.answer, sample, Usage(), time.perf_counter() - start, None, stats=empty_stats)

    try:
        assert client is not None
        answer, usage, stats = run_custom_windowed_loop(
            client=client,
            model=args.model,
            reasoning_effort=args.custom_reasoning_effort,
            question=question,
            pages=pages,
            notes_path=notes_path,
            page_tokens=args.page_tokens,
            payload_limit_tokens=args.payload_limit_tokens,
            notes_limit_tokens=args.notes_limit_tokens,
            max_steps=max_steps,
        )
        return method_result(answer, sample, usage, time.perf_counter() - start, None, stats=stats)
    except Exception as exc:
        empty_stats = {"steps": 0, "page_flips": 0, "mrcr_page_tokens_seen": 0, "user_prompt_tokens": 0}
        return method_result("", sample, Usage(), time.perf_counter() - start, str(exc), stats=empty_stats)


def run_codex_single(
    codex_model: str,
    messages: Sequence[Dict[str, Any]],
    timeout_seconds: int,
    work_dir: Path,
    codex_reasoning_effort: Optional[str],
) -> Tuple[str, Usage]:
    work_dir.mkdir(parents=True, exist_ok=True)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for codex_cli_single.")

    prompt = (
        "You are solving an MRCR task. Below is the full conversation transcript.\n"
        "Return exactly the final answer to the user's last request.\n"
        "Output only the answer text.\n\n"
        f"{messages_to_transcript(messages)}"
    )
    cmd = [
        "codex",
        "exec",
        "-C",
        str(work_dir),
        "--skip-git-repo-check",
        "--sandbox",
        "workspace-write",
        "--json",
        "-m",
        codex_model,
        "-c",
        f'model_reasoning_effort="{codex_reasoning_effort or "medium"}"',
        prompt,
    ]
    # Use an isolated CODEX_HOME so this eval can use API-key auth without changing the user's normal Codex auth mode.
    with tempfile.TemporaryDirectory(prefix="codex_eval_") as codex_home:
        auth_path = Path(codex_home) / "auth.json"
        auth_path.write_text(json.dumps({"OPENAI_API_KEY": api_key, "auth_mode": "apikey"}), encoding="utf-8")

        config_path = Path(codex_home) / "config.toml"
        config_path.write_text(
            f'model_reasoning_effort = "{codex_reasoning_effort or "medium"}"\n'
            'personality = "pragmatic"\n',
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["CODEX_HOME"] = codex_home
        env["OPENAI_API_KEY"] = api_key
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
            env=env,
        )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "codex exec failed")

    usage = Usage()
    answer = ""
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "item.completed":
            item = obj.get("item", {})
            if item.get("type") == "agent_message":
                answer = str(item.get("text", ""))
        if obj.get("type") == "turn.completed":
            u = obj.get("usage", {}) or {}
            usage.add(Usage(u.get("input_tokens", 0), u.get("output_tokens", 0)))
    return answer, usage


def evaluate_codex_single(sample: MRCRSample, args: argparse.Namespace, sample_dir: Path) -> Dict[str, Any]:
    start = time.perf_counter()
    if args.dry_run:
        return method_result(sample.answer, sample, Usage(), time.perf_counter() - start, None)

    try:
        answer, usage = run_codex_single(
            codex_model=args.codex_model,
            messages=sample.messages,
            timeout_seconds=args.codex_timeout_seconds,
            work_dir=sample_dir / "codex",
            codex_reasoning_effort=args.codex_reasoning_effort,
        )
        return method_result(answer, sample, usage, time.perf_counter() - start, None)
    except Exception as exc:
        return method_result("", sample, Usage(), time.perf_counter() - start, str(exc))


def evaluate_sample(sample: MRCRSample, args: argparse.Namespace, client: Optional[OpenAI], run_dir: Path) -> Dict[str, Any]:
    pages, question = prepare_pages_and_question(sample.messages, args.page_tokens)
    sample_dir = run_dir / f"sample_{sample.sample_id}"
    sample_dir.mkdir(parents=True, exist_ok=True)

    row: Dict[str, Any] = {
        "sample_id": sample.sample_id,
        "n_needles": sample.n_needles,
        "prompt_tokens": sample.prompt_tokens,
        "answer_tokens": sample.answer_tokens,
        "total_tokens": sample.total_tokens,
        "n_pages": len(pages),
        "page_tokens_limit": args.page_tokens,
    }
    max_steps = max(int(args.max_steps), len(pages) * 10)
    row["custom_max_steps"] = max_steps
    row["base_direct"] = evaluate_base_direct(sample, args, client)
    row["custom_windowed"] = evaluate_custom_windowed(
        sample,
        args,
        client,
        question,
        pages,
        sample_dir / "custom_notes.txt",
        max_steps,
    )
    row["codex_cli_single"] = evaluate_codex_single(sample, args, sample_dir)
    return row


def summarize(results: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    def avg(values: Sequence[float]) -> Optional[float]:
        return None if not values else float(sum(values) / len(values))

    def usage_sum(method_key: str) -> Dict[str, int]:
        return {
            "input_tokens": sum(r[method_key]["usage"]["input_tokens"] for r in results),
            "output_tokens": sum(r[method_key]["usage"]["output_tokens"] for r in results),
        }

    return {
        "samples": len(results),
        "base_direct_mean_score": avg([r["base_direct"]["score"] for r in results]),
        "custom_windowed_mean_score": avg([r["custom_windowed"]["score"] for r in results]),
        "codex_cli_single_mean_score": avg([r["codex_cli_single"]["score"] for r in results]),
        "base_direct_total_usage": usage_sum("base_direct"),
        "custom_windowed_total_usage": usage_sum("custom_windowed"),
        "codex_cli_single_total_usage": usage_sum("codex_cli_single"),
        "note": (
            "custom_windowed exposes one MRCR page at a time; totals still include all tokens "
            "(instructions, reasoning, outputs, and framework overhead)."
        ),
    }


def main() -> None:
    args = parse_args()
    args.reasoning_effort = normalize_effort(args.reasoning_effort)
    args.custom_reasoning_effort = normalize_effort(args.custom_reasoning_effort)
    args.codex_reasoning_effort = normalize_effort(args.codex_reasoning_effort)

    maybe_set_api_key(args.openai_api_key_file)
    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    run_name = args.run_name or datetime.now().strftime("mrcr_compare_%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(vars(args), indent=2), encoding="utf-8")

    samples = list(
        iter_mrcr_samples(
            offset=args.offset,
            max_rows=args.scan_rows,
            limit=args.max_samples,
            n_needles_filter=[8],
            min_total_tokens=4096,
            max_total_tokens=8192,
            batch_size=100,
        )
    )
    if not samples:
        raise SystemExit("No MRCR rows matched filters.")

    client = None if args.dry_run else OpenAI()
    results: List[Dict[str, Any]] = []

    with (run_dir / "per_sample.jsonl").open("w", encoding="utf-8") as out:
        for i, sample in enumerate(samples, start=1):
            print(f"[{i}/{len(samples)}] sample {sample.sample_id}")
            row = evaluate_sample(sample, args, client, run_dir)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            results.append(row)

    summary = summarize(results)
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Saved to {run_dir}")


if __name__ == "__main__":
    main()
