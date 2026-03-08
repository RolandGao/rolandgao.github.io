from __future__ import annotations

import argparse
import json
import os
import subprocess
import statistics
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import tiktoken
from openai import OpenAI

try:
    from .benchmark_utils import extract_last_user_message, grade_mrcr
except ImportError:
    from benchmark_utils import extract_last_user_message, grade_mrcr  # type: ignore

HF_DATASET_SERVER = "https://datasets-server.huggingface.co"
ENC = tiktoken.get_encoding("o200k_base")


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": int(self.input_tokens or 0),
            "output_tokens": int(self.output_tokens or 0),
        }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fast single-bucket MRCR base-direct eval (8 needles).")
    p.add_argument("--model", default="gpt-5-nano")
    p.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh", "none"], default="medium")
    p.add_argument("--openai-api-key-file", default=None)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--scan-rows", type=int, default=2400)
    p.add_argument("--batch-size", type=int, default=20)
    p.add_argument("--bucket-min", type=int, required=True)
    p.add_argument("--bucket-max", type=int, required=True)
    p.add_argument("--max-samples", type=int, default=10)
    p.add_argument("--http-timeout-seconds", type=int, default=20)
    p.add_argument("--http-max-attempts", type=int, default=3)
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


def bucket_label(lo: int, hi: int) -> str:
    return f"{lo // 1024}K-{hi // 1024}K"


def count_message_tokens(messages: Sequence[Dict[str, Any]]) -> int:
    total = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total += len(ENC.encode(content))
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        total += len(ENC.encode(str(item.get("text", ""))))
                    else:
                        total += len(ENC.encode(json.dumps(item, ensure_ascii=False)))
                else:
                    total += len(ENC.encode(str(item)))
        else:
            total += len(ENC.encode(str(content)))
    return total


def request_rows(*, offset: int, length: int, timeout_seconds: int, max_attempts: int) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode(
        {
            "dataset": "openai/mrcr",
            "config": "default",
            "split": "train",
            "offset": offset,
            "length": length,
        }
    )
    url = f"{HF_DATASET_SERVER}/rows?{query}"
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            proc = subprocess.run(
                ["curl", "-sS", "--max-time", str(timeout_seconds), url],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr.strip() or "curl failed")
            payload = json.loads(proc.stdout)
            return list(payload.get("rows", []))
        except Exception as exc:  # pragma: no cover
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(min(2**attempt, 8))

    raise RuntimeError(f"Failed to fetch rows at offset={offset} length={length}") from last_error


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


def summarize_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
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

    scores = [float(r["base_direct"]["score"]) for r in rows]
    latencies = [float(r["base_direct"]["latency_seconds"]) for r in rows]
    input_tokens = [int(r["base_direct"]["usage"]["input_tokens"]) for r in rows]
    output_tokens = [int(r["base_direct"]["usage"]["output_tokens"]) for r in rows]
    prefix_oks = [bool(r["base_direct"]["prefix_ok"]) for r in rows]
    errors = [r["base_direct"]["error"] for r in rows]

    return {
        "samples": len(rows),
        "mean_score": float(statistics.mean(scores)),
        "median_score": float(statistics.median(scores)),
        "p10_score": percentile(scores, 0.10),
        "p90_score": percentile(scores, 0.90),
        "min_score": float(min(scores)),
        "max_score": float(max(scores)),
        "prefix_ok_rate": float(sum(1 for x in prefix_oks if x) / len(prefix_oks)),
        "error_count": sum(1 for e in errors if e),
        "mean_latency_seconds": float(statistics.mean(latencies)),
        "median_latency_seconds": float(statistics.median(latencies)),
        "total_usage": {
            "input_tokens": int(sum(input_tokens)),
            "output_tokens": int(sum(output_tokens)),
        },
        "mean_input_tokens": float(statistics.mean(input_tokens)),
        "mean_output_tokens": float(statistics.mean(output_tokens)),
    }


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.reasoning_effort = normalize_effort(args.reasoning_effort)

    maybe_set_api_key(args.openai_api_key_file)
    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    if args.bucket_max <= args.bucket_min:
        raise SystemExit("--bucket-max must be greater than --bucket-min")

    run_name = args.run_name or datetime.now().strftime("mrcr_base_direct_single_bucket_%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    label = bucket_label(args.bucket_min, args.bucket_max)
    config = {
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "offset": args.offset,
        "scan_rows": args.scan_rows,
        "batch_size": args.batch_size,
        "bucket": {
            "label": label,
            "min_total_tokens": args.bucket_min,
            "max_total_tokens": args.bucket_max,
        },
        "max_samples": args.max_samples,
        "http_timeout_seconds": args.http_timeout_seconds,
        "http_max_attempts": args.http_max_attempts,
        "dry_run": args.dry_run,
        "started_at": datetime.now().isoformat(),
        "methods": ["base_direct"],
    }
    write_json(run_dir / "config.json", config)

    selected: List[Dict[str, Any]] = []
    scanned_matches = 0

    end = args.offset + args.scan_rows
    for off in range(args.offset, end, args.batch_size):
        length = min(args.batch_size, end - off)
        if length <= 0:
            break

        rows = request_rows(
            offset=off,
            length=length,
            timeout_seconds=args.http_timeout_seconds,
            max_attempts=args.http_max_attempts,
        )
        if not rows:
            break

        for record in rows:
            row = record.get("row", {})
            if int(row.get("n_needles", 0)) != 8:
                continue

            try:
                messages = json.loads(str(row.get("prompt", "")))
            except json.JSONDecodeError:
                continue
            if not isinstance(messages, list):
                continue

            prompt_tokens = count_message_tokens(messages)
            answer_text = str(row.get("answer", ""))
            answer_tokens = len(ENC.encode(answer_text))
            total_tokens = prompt_tokens + answer_tokens

            if args.bucket_min <= total_tokens < args.bucket_max:
                scanned_matches += 1
                if len(selected) < args.max_samples:
                    selected.append(
                        {
                            "sample_id": int(record.get("row_idx", -1)),
                            "messages": messages,
                            "answer": answer_text,
                            "random_string_to_prepend": str(row.get("random_string_to_prepend", "")),
                            "n_needles": int(row.get("n_needles", 0)),
                            "desired_msg_index": int(row.get("desired_msg_index", -1)),
                            "total_messages": int(row.get("total_messages", 0)),
                            "n_chars": int(row.get("n_chars", 0)),
                            "date_added": str(row.get("date_added", "")),
                            "prompt_tokens": prompt_tokens,
                            "answer_tokens": answer_tokens,
                            "total_tokens": total_tokens,
                        }
                    )
                if len(selected) >= args.max_samples:
                    break
        if len(selected) >= args.max_samples:
            break

    selection_summary = {
        "bucket": label,
        "scanned_matches": scanned_matches,
        "selected": len(selected),
    }
    write_json(run_dir / "selection_summary.json", selection_summary)

    if not selected:
        raise SystemExit("No samples selected for the bucket.")

    with (run_dir / "selected_samples.jsonl").open("w", encoding="utf-8") as sel_out:
        for sample in selected:
            sel_out.write(
                json.dumps(
                    {
                        "sample_id": sample["sample_id"],
                        "bucket": label,
                        "n_needles": sample["n_needles"],
                        "desired_msg_index": sample["desired_msg_index"],
                        "total_messages": sample["total_messages"],
                        "n_chars": sample["n_chars"],
                        "date_added": sample["date_added"],
                        "prompt_tokens": sample["prompt_tokens"],
                        "answer_tokens": sample["answer_tokens"],
                        "total_tokens": sample["total_tokens"],
                        "question_preview": extract_last_user_message(sample["messages"])[:600],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    client = None if args.dry_run else OpenAI()
    rows_out: List[Dict[str, Any]] = []

    with (run_dir / "per_sample.jsonl").open("w", encoding="utf-8") as out, (run_dir / "events.jsonl").open("w", encoding="utf-8") as events:
        total = len(selected)
        for idx, sample in enumerate(selected, start=1):
            start = time.perf_counter()
            if args.dry_run:
                sampled_answer = sample["answer"]
                usage = Usage()
                error: Optional[str] = None
            else:
                try:
                    assert client is not None
                    sampled_answer, usage = call_openai(client, args.model, sample["messages"], args.reasoning_effort)
                    error = None
                except Exception as exc:  # pragma: no cover
                    sampled_answer = ""
                    usage = Usage()
                    error = str(exc)

            latency = time.perf_counter() - start
            g = grade_mrcr(sampled_answer, sample["answer"], sample["random_string_to_prepend"])
            row = {
                "sample_id": sample["sample_id"],
                "bucket": label,
                "n_needles": sample["n_needles"],
                "desired_msg_index": sample["desired_msg_index"],
                "total_messages": sample["total_messages"],
                "n_chars": sample["n_chars"],
                "date_added": sample["date_added"],
                "prompt_tokens": sample["prompt_tokens"],
                "answer_tokens": sample["answer_tokens"],
                "total_tokens": sample["total_tokens"],
                "question_preview": extract_last_user_message(sample["messages"])[:600],
                "base_direct": {
                    "score": g["score"],
                    "prefix_ok": g["prefix_ok"],
                    "latency_seconds": latency,
                    "usage": usage.to_dict(),
                    "error": error,
                    "answer_preview": (sampled_answer or "")[:2000],
                    "answer_chars": len(sampled_answer or ""),
                },
            }
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            rows_out.append(row)

            event = {
                "ts": datetime.now().isoformat(),
                "index": idx,
                "total": total,
                "sample_id": sample["sample_id"],
                "bucket": label,
                "score": g["score"],
                "prefix_ok": g["prefix_ok"],
                "error": error,
                "latency_seconds": latency,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
            }
            events.write(json.dumps(event, ensure_ascii=False) + "\n")
            events.flush()
            print(f"[{idx}/{total}] sample={sample['sample_id']} bucket={label} score={g['score']:.4f} prefix_ok={g['prefix_ok']} err={'yes' if error else 'no'}")

    summary = {
        "samples": len(rows_out),
        "selection_summary": selection_summary,
        "overall": summarize_rows(rows_out),
        "per_bucket": {label: summarize_rows(rows_out)},
        "note": "Scoring uses MRCR prefix gate + SequenceMatcher ratio over suffix text.",
        "completed_at": datetime.now().isoformat(),
    }
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    print(f"Saved to {run_dir}")


if __name__ == "__main__":
    main()
