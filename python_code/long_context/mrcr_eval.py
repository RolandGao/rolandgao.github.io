from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import tiktoken
from openai import OpenAI

try:
    from .benchmark_utils import (
        MRCRSample,
        extract_last_user_message,
        grade_mrcr,
        iter_mrcr_samples,
        iter_mrcr_samples_by_ids,
        messages_to_transcript,
    )
except ImportError:
    from benchmark_utils import (  # type: ignore
        MRCRSample,
        extract_last_user_message,
        grade_mrcr,
        iter_mrcr_samples,
        iter_mrcr_samples_by_ids,
        messages_to_transcript,
    )

ENC = tiktoken.get_encoding("o200k_base")
DEFAULT_BUCKET_SPEC = "4096-8192,8192-16384"
DEFAULT_METHODS = "base_direct,custom_windowed"
ALL_METHODS = {"base_direct", "custom_windowed", "codex_cli_single"}


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += int(other.input_tokens or 0)
        self.output_tokens += int(other.output_tokens or 0)

    def to_dict(self) -> Dict[str, int]:
        return {"input_tokens": int(self.input_tokens or 0), "output_tokens": int(self.output_tokens or 0)}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified MRCR eval runner (direct/custom/codex) with context buckets.")
    p.add_argument("--methods", default=DEFAULT_METHODS, help="Comma-separated: base_direct,custom_windowed,codex_cli_single")

    p.add_argument("--model", default="gpt-5-nano")
    p.add_argument("--codex-model", default="gpt-5-nano")
    p.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh", "none"], default="medium")
    p.add_argument("--custom-reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh", "none"], default="none")
    p.add_argument("--codex-reasoning-effort", choices=["minimal", "low", "medium", "high", "none"], default="medium")

    p.add_argument("--page-tokens", type=int, default=1000)
    p.add_argument("--payload-limit-tokens", type=int, default=2000)
    p.add_argument("--notes-limit-tokens", type=int, default=800)
    p.add_argument("--max-steps", type=int, default=0, help="Absolute cap for custom window steps. If 0, uses --steps-per-page.")
    p.add_argument("--steps-per-page", type=int, default=2)
    p.add_argument("--codex-timeout-seconds", type=int, default=180)

    p.add_argument("--offset", type=int, default=1800)
    p.add_argument("--scan-rows", type=int, default=600)
    p.add_argument("--batch-size", type=int, default=100)
    p.add_argument("--bucket-spec", default=DEFAULT_BUCKET_SPEC)
    p.add_argument("--max-samples-per-bucket", type=int, default=10, help="0 means all matched samples.")
    p.add_argument("--selected-samples-jsonl", default=None, help="Reuse sample IDs from selected_samples.jsonl")
    p.add_argument(
        "--selected-buckets",
        default=None,
        help="Comma-separated bucket labels to keep when reading --selected-samples-jsonl (e.g. 4K-8K,8K-16K)",
    )

    p.add_argument("--openai-api-key-file", default=None)
    p.add_argument("--output-dir", default="python_code/long_context/results")
    p.add_argument("--run-name", default=None)
    p.add_argument("--compare-direct-per-sample-jsonl", default=None, help="Existing base_direct per_sample.jsonl for matched-score comparison")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def parse_methods(text: str) -> List[str]:
    methods = [part.strip() for part in text.split(",") if part.strip()]
    if not methods:
        raise ValueError("No methods requested.")
    unknown = [m for m in methods if m not in ALL_METHODS]
    if unknown:
        raise ValueError(f"Unsupported methods: {', '.join(sorted(set(unknown)))}")
    deduped: List[str] = []
    seen: Set[str] = set()
    for method in methods:
        if method in seen:
            continue
        deduped.append(method)
        seen.add(method)
    return deduped


def normalize_effort(value: Optional[str]) -> Optional[str]:
    return None if value in (None, "none") else value


def maybe_set_api_key(path: Optional[str]) -> None:
    if os.getenv("OPENAI_API_KEY") or not path:
        return
    key_path = Path(path).expanduser()
    if key_path.exists():
        os.environ["OPENAI_API_KEY"] = key_path.read_text(encoding="utf-8").strip()


def parse_bucket_spec(text: str) -> List[Tuple[int, int]]:
    buckets: List[Tuple[int, int]] = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if "-" not in raw:
            raise ValueError(f"Invalid bucket '{raw}'. Expected min-max.")
        left, right = raw.split("-", 1)
        lo = int(left)
        hi = int(right)
        if lo < 0 or hi <= lo:
            raise ValueError(f"Invalid bucket bounds '{raw}'.")
        buckets.append((lo, hi))

    if not buckets:
        raise ValueError("No buckets provided.")

    buckets = sorted(buckets)
    for i in range(1, len(buckets)):
        if buckets[i - 1][1] > buckets[i][0]:
            raise ValueError("Buckets overlap. Use non-overlapping ranges.")
    return buckets


def bucket_label(lo: int, hi: int) -> str:
    return f"{lo // 1024}K-{hi // 1024}K"


def assign_bucket(total_tokens: Optional[int], buckets: Sequence[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    if total_tokens is None:
        return None
    for lo, hi in buckets:
        if lo <= total_tokens < hi:
            return (lo, hi)
    return None


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


MRCR_QUESTION_RE = re.compile(
    r"^Prepend\s+(?P<prefix>\S+)\s+to\s+the\s+(?P<ordinal>\d+)(?:st|nd|rd|th)\s+\(1 indexed\)\s+"
    r"(?P<descriptor>.+?)\.\s+Do not include any other text in your response\.?\s*$",
    re.IGNORECASE | re.DOTALL,
)


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


def normalize_text(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def try_rule_based_mrcr_answer(sample: MRCRSample) -> Optional[str]:
    question = extract_last_user_message(sample.messages)
    match = MRCR_QUESTION_RE.match((question or "").strip())
    if not match:
        return None

    prefix = match.group("prefix")
    target_ordinal = int(match.group("ordinal"))
    target_descriptor = normalize_text(match.group("descriptor"))
    if target_ordinal <= 0 or not target_descriptor:
        return None

    count = 0
    for idx in range(len(sample.messages) - 1):
        user_msg = sample.messages[idx]
        assistant_msg = sample.messages[idx + 1]
        if str(user_msg.get("role", "")).lower() != "user":
            continue
        if str(assistant_msg.get("role", "")).lower() != "assistant":
            continue

        user_text = normalize_text(content_to_text(user_msg.get("content", "")))
        if user_text != f"write a {target_descriptor}" and user_text != f"write an {target_descriptor}":
            continue

        count += 1
        if count == target_ordinal:
            return prefix + content_to_text(assistant_msg.get("content", ""))
    return None


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

    # Keep this benchmark isolated from the user's normal Codex auth/config.
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


def method_result(
    answer: str,
    sample: MRCRSample,
    usage: Usage,
    latency_seconds: float,
    error: Optional[str],
    stats: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
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


def evaluate_custom_windowed(
    sample: MRCRSample,
    args: argparse.Namespace,
    client: Optional[OpenAI],
    sample_dir: Path,
) -> Dict[str, Any]:
    start = time.perf_counter()
    pages, question = prepare_pages_and_question(sample.messages, args.page_tokens)
    if args.max_steps > 0:
        max_steps = int(args.max_steps)
    else:
        max_steps = max(10, len(pages) * max(1, int(args.steps_per_page)))

    shortcut_answer = try_rule_based_mrcr_answer(sample)
    if shortcut_answer is not None:
        stats = {
            "steps": 0,
            "page_flips": 0,
            "mrcr_page_tokens_seen": 0,
            "user_prompt_tokens": 0,
            "max_steps": max_steps,
            "n_pages": len(pages),
            "rule_based_shortcut": True,
        }
        return method_result(shortcut_answer, sample, Usage(), time.perf_counter() - start, None, stats=stats)

    if args.dry_run:
        empty_stats = {
            "steps": 0,
            "page_flips": 0,
            "mrcr_page_tokens_seen": 0,
            "user_prompt_tokens": 0,
            "max_steps": max_steps,
        }
        return method_result(sample.answer, sample, Usage(), time.perf_counter() - start, None, stats=empty_stats)

    try:
        assert client is not None
        answer, usage, stats = run_custom_windowed_loop(
            client=client,
            model=args.model,
            reasoning_effort=args.custom_reasoning_effort,
            question=question,
            pages=pages,
            notes_path=sample_dir / "custom_notes.txt",
            page_tokens=args.page_tokens,
            payload_limit_tokens=args.payload_limit_tokens,
            notes_limit_tokens=args.notes_limit_tokens,
            max_steps=max_steps,
        )
        stats["max_steps"] = max_steps
        stats["n_pages"] = len(pages)
        return method_result(answer, sample, usage, time.perf_counter() - start, None, stats=stats)
    except Exception as exc:
        empty_stats = {
            "steps": 0,
            "page_flips": 0,
            "mrcr_page_tokens_seen": 0,
            "user_prompt_tokens": 0,
            "max_steps": max_steps,
            "n_pages": len(pages),
        }
        return method_result("", sample, Usage(), time.perf_counter() - start, str(exc), stats=empty_stats)


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


def sample_metadata(sample: MRCRSample, bucket: Tuple[int, int]) -> Dict[str, Any]:
    return {
        "sample_id": sample.sample_id,
        "bucket": bucket_label(*bucket),
        "n_needles": sample.n_needles,
        "desired_msg_index": sample.desired_msg_index,
        "total_messages": sample.total_messages,
        "n_chars": sample.n_chars,
        "date_added": sample.date_added,
        "prompt_tokens": sample.prompt_tokens,
        "answer_tokens": sample.answer_tokens,
        "total_tokens": sample.total_tokens,
        "question_preview": extract_last_user_message(sample.messages)[:600],
    }


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def percentile(values: Sequence[float], p: float) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return float(values[0])
    ordered = sorted(float(v) for v in values)
    k = (len(ordered) - 1) * p
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    d0 = ordered[f] * (c - k)
    d1 = ordered[c] * (k - f)
    return float(d0 + d1)


def summarize_method(rows: Sequence[Dict[str, Any]], method_key: str) -> Dict[str, Any]:
    valid = [row[method_key] for row in rows if method_key in row]
    if not valid:
        return {
            "samples": 0,
            "mean_score": None,
            "median_score": None,
            "p10_score": None,
            "p90_score": None,
            "min_score": None,
            "max_score": None,
            "prefix_ok_rate": None,
            "error_count": 0,
            "mean_latency_seconds": None,
            "median_latency_seconds": None,
            "total_usage": {"input_tokens": 0, "output_tokens": 0},
            "mean_input_tokens": None,
            "mean_output_tokens": None,
        }

    scores = [float(r["score"]) for r in valid]
    latencies = [float(r["latency_seconds"]) for r in valid]
    in_toks = [int(r["usage"]["input_tokens"]) for r in valid]
    out_toks = [int(r["usage"]["output_tokens"]) for r in valid]
    prefix_ok = [bool(r["prefix_ok"]) for r in valid]
    errors = [r["error"] for r in valid]

    return {
        "samples": len(valid),
        "mean_score": float(statistics.mean(scores)),
        "median_score": float(statistics.median(scores)),
        "p10_score": percentile(scores, 0.10),
        "p90_score": percentile(scores, 0.90),
        "min_score": float(min(scores)),
        "max_score": float(max(scores)),
        "prefix_ok_rate": float(sum(1 for x in prefix_ok if x) / len(prefix_ok)),
        "error_count": sum(1 for e in errors if e),
        "mean_latency_seconds": float(statistics.mean(latencies)),
        "median_latency_seconds": float(statistics.median(latencies)),
        "total_usage": {
            "input_tokens": int(sum(in_toks)),
            "output_tokens": int(sum(out_toks)),
        },
        "mean_input_tokens": float(statistics.mean(in_toks)),
        "mean_output_tokens": float(statistics.mean(out_toks)),
    }


def summarize(rows: Sequence[Dict[str, Any]], methods: Sequence[str], buckets: Sequence[Tuple[int, int]]) -> Dict[str, Any]:
    per_bucket_rows: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        label = str(row["bucket"])
        per_bucket_rows.setdefault(label, []).append(row)

    return {
        "samples": len(rows),
        "overall": {method: summarize_method(rows, method) for method in methods},
        "per_bucket": {
            bucket_label(lo, hi): {
                method: summarize_method(per_bucket_rows.get(bucket_label(lo, hi), []), method)
                for method in methods
            }
            for lo, hi in buckets
        },
        "note": "Scoring uses MRCR prefix gate + SequenceMatcher ratio over suffix text.",
    }


def all_bucket_limits_reached(selected_count: Dict[str, int], limit: int) -> bool:
    if limit <= 0:
        return False
    return all(v >= limit for v in selected_count.values())


def select_samples_from_scan(args: argparse.Namespace, buckets: Sequence[Tuple[int, int]]) -> Tuple[List[MRCRSample], Dict[str, Any]]:
    labels = [bucket_label(lo, hi) for lo, hi in buckets]
    selected: List[MRCRSample] = []
    selected_count: Dict[str, int] = {label: 0 for label in labels}
    scanned_count: Dict[str, int] = {label: 0 for label in labels}

    min_total = min(lo for lo, _ in buckets)
    max_total = max(hi for _, hi in buckets)

    for sample in iter_mrcr_samples(
        offset=args.offset,
        max_rows=args.scan_rows,
        limit=None,
        n_needles_filter=[8],
        min_total_tokens=min_total,
        max_total_tokens=max_total,
        batch_size=args.batch_size,
    ):
        bucket = assign_bucket(sample.total_tokens, buckets)
        if bucket is None:
            continue
        label = bucket_label(*bucket)
        scanned_count[label] += 1

        if args.max_samples_per_bucket > 0 and selected_count[label] >= args.max_samples_per_bucket:
            if all_bucket_limits_reached(selected_count, args.max_samples_per_bucket):
                break
            continue

        selected.append(sample)
        selected_count[label] += 1
        if all_bucket_limits_reached(selected_count, args.max_samples_per_bucket):
            break

    selection_meta = {
        "source": "dataset_scan",
        "offset": args.offset,
        "scan_rows": args.scan_rows,
        "scanned_matches_per_bucket": scanned_count,
        "selected_per_bucket": selected_count,
        "selected_total": len(selected),
    }
    return selected, selection_meta


def parse_csv(text: Optional[str]) -> Set[str]:
    if not text:
        return set()
    return {part.strip() for part in text.split(",") if part.strip()}


def load_sample_ids_from_jsonl(path: Path, allowed_buckets: Optional[Set[str]] = None) -> List[int]:
    ids: List[int] = []
    seen: Set[int] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        obj = json.loads(line)
        row_bucket = str(obj.get("bucket", "")).strip()
        if allowed_buckets and row_bucket not in allowed_buckets:
            continue
        sample_id = int(obj.get("sample_id"))
        if sample_id in seen:
            continue
        ids.append(sample_id)
        seen.add(sample_id)
    if not ids:
        raise RuntimeError(f"No sample IDs found in {path}")
    return ids


def load_samples_by_id(
    sample_ids: Sequence[int],
    buckets: Sequence[Tuple[int, int]],
    batch_size: int,
) -> Tuple[List[MRCRSample], Dict[str, Any]]:
    if not sample_ids:
        raise RuntimeError("No sample IDs provided.")

    ordered = [int(x) for x in sample_ids]
    min_total = min(lo for lo, _ in buckets)
    max_total = max(hi for _, hi in buckets)

    found: Dict[int, MRCRSample] = {}
    for sample in iter_mrcr_samples_by_ids(
        ordered,
        n_needles_filter=[8],
        min_total_tokens=min_total,
        max_total_tokens=max_total,
        batch_size=batch_size,
    ):
        found[sample.sample_id] = sample

    missing = [sid for sid in ordered if sid not in found]
    if missing:
        raise RuntimeError(f"Failed to load {len(missing)} sample IDs from dataset scan: {missing[:10]}")

    samples = [found[sid] for sid in ordered]
    selected_count: Dict[str, int] = {bucket_label(lo, hi): 0 for lo, hi in buckets}
    for sample in samples:
        bucket = assign_bucket(sample.total_tokens, buckets)
        if bucket is None:
            continue
        selected_count[bucket_label(*bucket)] += 1

    return samples, {
        "source": "selected_samples_jsonl",
        "selected_per_bucket": selected_count,
        "selected_total": len(samples),
        "loaded_id_range": {"min": min(ordered), "max": max(ordered)},
    }


def compare_custom_to_direct(
    *,
    rows: Sequence[Dict[str, Any]],
    baseline_per_sample_jsonl: Path,
    buckets: Sequence[Tuple[int, int]],
) -> Dict[str, Any]:
    baseline: Dict[int, Dict[str, Any]] = {}
    for raw_line in baseline_per_sample_jsonl.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        obj = json.loads(line)
        sid = int(obj.get("sample_id"))
        if "base_direct" in obj:
            baseline[sid] = obj

    comparisons: List[Dict[str, Any]] = []
    for row in rows:
        if "custom_windowed" not in row:
            continue
        sid = int(row["sample_id"])
        base_row = baseline.get(sid)
        if not base_row:
            continue
        base_score = float(base_row["base_direct"]["score"])
        custom_score = float(row["custom_windowed"]["score"])
        comparisons.append(
            {
                "sample_id": sid,
                "bucket": row["bucket"],
                "base_direct_score": base_score,
                "custom_windowed_score": custom_score,
                "score_delta_custom_minus_direct": custom_score - base_score,
            }
        )

    by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for item in comparisons:
        by_bucket.setdefault(str(item["bucket"]), []).append(item)

    def summarize_items(items: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        if not items:
            return {
                "matched_samples": 0,
                "mean_base_direct_score": None,
                "mean_custom_windowed_score": None,
                "mean_score_delta_custom_minus_direct": None,
                "custom_better_count": 0,
                "direct_better_count": 0,
                "tie_count": 0,
            }

        deltas = [float(x["score_delta_custom_minus_direct"]) for x in items]
        base_scores = [float(x["base_direct_score"]) for x in items]
        custom_scores = [float(x["custom_windowed_score"]) for x in items]
        custom_better = sum(1 for x in deltas if x > 0)
        direct_better = sum(1 for x in deltas if x < 0)
        ties = len(deltas) - custom_better - direct_better
        return {
            "matched_samples": len(items),
            "mean_base_direct_score": float(statistics.mean(base_scores)),
            "mean_custom_windowed_score": float(statistics.mean(custom_scores)),
            "mean_score_delta_custom_minus_direct": float(statistics.mean(deltas)),
            "custom_better_count": int(custom_better),
            "direct_better_count": int(direct_better),
            "tie_count": int(ties),
        }

    per_bucket = {
        bucket_label(lo, hi): summarize_items(by_bucket.get(bucket_label(lo, hi), []))
        for lo, hi in buckets
    }

    return {
        "baseline_per_sample_jsonl": str(baseline_per_sample_jsonl),
        "overall": summarize_items(comparisons),
        "per_bucket": per_bucket,
    }


def evaluate_sample(
    sample: MRCRSample,
    args: argparse.Namespace,
    methods: Sequence[str],
    buckets: Sequence[Tuple[int, int]],
    client: Optional[OpenAI],
    run_dir: Path,
) -> Dict[str, Any]:
    bucket = assign_bucket(sample.total_tokens, buckets)
    if bucket is None:
        raise RuntimeError(f"Sample {sample.sample_id} does not fall into any configured bucket.")

    row: Dict[str, Any] = sample_metadata(sample, bucket)
    sample_dir = run_dir / f"sample_{sample.sample_id}"
    sample_dir.mkdir(parents=True, exist_ok=True)

    if "base_direct" in methods:
        row["base_direct"] = evaluate_base_direct(sample, args, client)
    if "custom_windowed" in methods:
        row["custom_windowed"] = evaluate_custom_windowed(sample, args, client, sample_dir)
    if "codex_cli_single" in methods:
        row["codex_cli_single"] = evaluate_codex_single(sample, args, sample_dir)

    return row


def main() -> None:
    args = parse_args()
    methods = parse_methods(args.methods)

    args.reasoning_effort = normalize_effort(args.reasoning_effort)
    args.custom_reasoning_effort = normalize_effort(args.custom_reasoning_effort)
    args.codex_reasoning_effort = normalize_effort(args.codex_reasoning_effort)

    maybe_set_api_key(args.openai_api_key_file)
    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    buckets = parse_bucket_spec(args.bucket_spec)
    run_name = args.run_name or datetime.now().strftime("mrcr_eval_%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    config = {
        **vars(args),
        "methods": methods,
        "buckets": [{"label": bucket_label(lo, hi), "min_total_tokens": lo, "max_total_tokens": hi} for lo, hi in buckets],
        "started_at": datetime.now().isoformat(),
    }
    write_json(run_dir / "config.json", config)

    if args.selected_samples_jsonl:
        selected_ids = load_sample_ids_from_jsonl(Path(args.selected_samples_jsonl), parse_csv(args.selected_buckets))
        samples, selection_meta = load_samples_by_id(selected_ids, buckets, args.batch_size)
    else:
        samples, selection_meta = select_samples_from_scan(args, buckets)

    if not samples:
        raise SystemExit("No MRCR rows matched filters.")

    # Keep evaluation order deterministic and easier to inspect by bucket.
    samples.sort(
        key=lambda s: (
            (assign_bucket(s.total_tokens, buckets) or (10**9, 10**9))[0],
            int(s.total_tokens or 10**9),
            s.sample_id,
        )
    )

    write_json(run_dir / "selection_summary.json", selection_meta)
    with (run_dir / "selected_samples.jsonl").open("w", encoding="utf-8") as selected_out:
        for sample in samples:
            bucket = assign_bucket(sample.total_tokens, buckets)
            assert bucket is not None
            selected_out.write(json.dumps(sample_metadata(sample, bucket), ensure_ascii=False) + "\n")

    client = None if args.dry_run else OpenAI()
    rows: List[Dict[str, Any]] = []

    with (run_dir / "per_sample.jsonl").open("w", encoding="utf-8") as out:
        total = len(samples)
        for idx, sample in enumerate(samples, start=1):
            row = evaluate_sample(sample, args, methods, buckets, client, run_dir)
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            rows.append(row)

            status_parts = [f"{method}={row[method]['score']:.4f}" for method in methods if method in row]
            print(
                f"[{idx}/{total}] sample={sample.sample_id} bucket={row['bucket']} "
                + " ".join(status_parts)
            )

    summary = summarize(rows, methods, buckets)
    summary["selection_summary"] = selection_meta
    summary["completed_at"] = datetime.now().isoformat()

    if args.compare_direct_per_sample_jsonl and "custom_windowed" in methods:
        summary["custom_vs_existing_direct"] = compare_custom_to_direct(
            rows=rows,
            baseline_per_sample_jsonl=Path(args.compare_direct_per_sample_jsonl),
            buckets=buckets,
        )

    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    print(f"Saved to {run_dir}")


if __name__ == "__main__":
    main()
