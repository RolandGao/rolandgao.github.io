from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from openai import OpenAI

try:
    from .benchmark_utils import MRCRSample, extract_last_user_message, grade_mrcr, iter_mrcr_samples
except ImportError:
    from benchmark_utils import MRCRSample, extract_last_user_message, grade_mrcr, iter_mrcr_samples  # type: ignore


DEFAULT_BUCKETS = "4096-8192,8192-16384,16384-32768,32768-65536"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, other: "Usage") -> None:
        self.input_tokens += int(other.input_tokens or 0)
        self.output_tokens += int(other.output_tokens or 0)

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MRCR base_direct eval by context length bucket (8 needles, up to 64K).")
    p.add_argument("--model", default="gpt-5-nano")
    p.add_argument("--reasoning-effort", choices=["minimal", "low", "medium", "high", "xhigh", "none"], default="medium")
    p.add_argument("--openai-api-key-file", default=None)
    p.add_argument("--output-dir", default="python_code/long_context/results")
    p.add_argument("--run-name", default=None)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--scan-rows", type=int, default=2400)
    p.add_argument("--batch-size", type=int, default=100)
    p.add_argument(
        "--bucket-spec",
        default=DEFAULT_BUCKETS,
        help="Comma-separated inclusive-exclusive token ranges, e.g. 4096-8192,8192-16384",
    )
    p.add_argument(
        "--max-samples-per-bucket",
        type=int,
        default=10,
        help="0 means all matched samples in each bucket.",
    )
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


def parse_bucket_spec(text: str) -> List[Tuple[int, int]]:
    buckets: List[Tuple[int, int]] = []
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        if "-" not in raw:
            raise ValueError(f"Invalid bucket '{raw}'. Expected format min-max.")
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


def usage_from_response(resp: Any) -> Usage:
    u = getattr(resp, "usage", None)
    if u is None:
        return Usage()
    return Usage(int(getattr(u, "input_tokens", 0) or 0), int(getattr(u, "output_tokens", 0) or 0))


def call_openai(client: OpenAI, model: str, input_payload: Any, reasoning_effort: Optional[str]) -> Tuple[str, Usage]:
    kwargs: Dict[str, Any] = {
        "model": model,
        "input": input_payload,
    }
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    resp = client.responses.create(**kwargs)
    return resp.output_text or "", usage_from_response(resp)


def evaluate_base_direct(sample: MRCRSample, model: str, reasoning_effort: Optional[str], client: Optional[OpenAI], dry_run: bool) -> Dict[str, Any]:
    start = time.perf_counter()
    if dry_run:
        answer = sample.answer
        usage = Usage()
        error = None
    else:
        try:
            assert client is not None
            answer, usage = call_openai(client, model, list(sample.messages), reasoning_effort)
            error = None
        except Exception as exc:
            answer = ""
            usage = Usage()
            error = str(exc)

    latency_seconds = time.perf_counter() - start
    g = grade_mrcr(answer, sample.answer, sample.random_string_to_prepend)

    return {
        "score": g["score"],
        "prefix_ok": g["prefix_ok"],
        "latency_seconds": latency_seconds,
        "usage": usage.to_dict(),
        "error": error,
        "answer_preview": (answer or "")[:2000],
        "answer_chars": len(answer or ""),
    }


def assign_bucket(total_tokens: Optional[int], buckets: Sequence[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    if total_tokens is None:
        return None
    for lo, hi in buckets:
        if lo <= total_tokens < hi:
            return (lo, hi)
    return None


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


def all_bucket_limits_reached(selected_count: Dict[str, int], limit: int) -> bool:
    if limit <= 0:
        return False
    return all(v >= limit for v in selected_count.values())


def make_selection(
    *,
    buckets: Sequence[Tuple[int, int]],
    offset: int,
    scan_rows: Optional[int],
    batch_size: int,
    max_samples_per_bucket: int,
) -> Tuple[List[MRCRSample], Dict[str, Any]]:
    labels = [bucket_label(lo, hi) for lo, hi in buckets]
    selected: List[MRCRSample] = []
    selected_count: Dict[str, int] = {label: 0 for label in labels}
    scanned_count: Dict[str, int] = {label: 0 for label in labels}

    min_total = min(lo for lo, _ in buckets)
    max_total = max(hi for _, hi in buckets)

    for sample in iter_mrcr_samples(
        offset=offset,
        max_rows=scan_rows,
        limit=None,
        n_needles_filter=[8],
        min_total_tokens=min_total,
        max_total_tokens=max_total,
        batch_size=batch_size,
    ):
        bucket = assign_bucket(sample.total_tokens, buckets)
        if bucket is None:
            continue

        label = bucket_label(*bucket)
        scanned_count[label] += 1

        if max_samples_per_bucket > 0 and selected_count[label] >= max_samples_per_bucket:
            if all_bucket_limits_reached(selected_count, max_samples_per_bucket):
                break
            continue

        selected.append(sample)
        selected_count[label] += 1

        if all_bucket_limits_reached(selected_count, max_samples_per_bucket):
            break

    selection_meta = {
        "scanned_matches_per_bucket": scanned_count,
        "selected_per_bucket": selected_count,
        "selected_total": len(selected),
    }
    return selected, selection_meta


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_event(path: Path, event: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


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


def main() -> None:
    args = parse_args()
    args.reasoning_effort = normalize_effort(args.reasoning_effort)

    maybe_set_api_key(args.openai_api_key_file)
    if not args.dry_run and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set.")

    buckets = parse_bucket_spec(args.bucket_spec)
    run_name = args.run_name or datetime.now().strftime("mrcr_base_direct_by_context_%Y%m%d_%H%M%S")
    run_dir = Path(args.output_dir) / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    config = {
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "offset": args.offset,
        "scan_rows": args.scan_rows,
        "batch_size": args.batch_size,
        "bucket_spec": args.bucket_spec,
        "buckets": [{"label": bucket_label(lo, hi), "min_total_tokens": lo, "max_total_tokens": hi} for lo, hi in buckets],
        "max_samples_per_bucket": args.max_samples_per_bucket,
        "dry_run": args.dry_run,
        "started_at": datetime.now().isoformat(),
        "methods": ["base_direct"],
    }
    write_json(run_dir / "config.json", config)

    samples, selection_meta = make_selection(
        buckets=buckets,
        offset=args.offset,
        scan_rows=args.scan_rows,
        batch_size=args.batch_size,
        max_samples_per_bucket=args.max_samples_per_bucket,
    )
    write_json(run_dir / "selection_summary.json", selection_meta)

    if not samples:
        raise SystemExit("No MRCR rows matched filters.")

    # Evaluate shorter-context buckets first so a cross-bucket view appears earlier in long runs.
    samples.sort(
        key=lambda s: (
            (assign_bucket(s.total_tokens, buckets) or (10**9, 10**9))[0],
            int(s.total_tokens or 10**9),
            s.sample_id,
        )
    )

    event_path = run_dir / "events.jsonl"
    rows: List[Dict[str, Any]] = []
    client = None if args.dry_run else OpenAI()

    with (run_dir / "selected_samples.jsonl").open("w", encoding="utf-8") as selected_out:
        for sample in samples:
            bucket = assign_bucket(sample.total_tokens, buckets)
            assert bucket is not None
            selected_out.write(json.dumps(sample_metadata(sample, bucket), ensure_ascii=False) + "\n")

    with (run_dir / "per_sample.jsonl").open("w", encoding="utf-8") as out:
        total = len(samples)
        for idx, sample in enumerate(samples, start=1):
            bucket = assign_bucket(sample.total_tokens, buckets)
            assert bucket is not None
            label = bucket_label(*bucket)

            t0 = time.perf_counter()
            result = evaluate_base_direct(sample, args.model, args.reasoning_effort, client, args.dry_run)
            elapsed = time.perf_counter() - t0

            row = sample_metadata(sample, bucket)
            row["base_direct"] = result
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            out.flush()
            rows.append(row)

            event = {
                "ts": datetime.now().isoformat(),
                "index": idx,
                "total": total,
                "sample_id": sample.sample_id,
                "bucket": label,
                "score": result["score"],
                "prefix_ok": result["prefix_ok"],
                "error": result["error"],
                "latency_seconds": result["latency_seconds"],
                "input_tokens": result["usage"]["input_tokens"],
                "output_tokens": result["usage"]["output_tokens"],
                "wall_seconds_for_sample": elapsed,
            }
            write_event(event_path, event)
            print(f"[{idx}/{total}] sample={sample.sample_id} bucket={label} score={result['score']:.4f} prefix_ok={result['prefix_ok']} err={'yes' if result['error'] else 'no'}")

    rows_by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        rows_by_bucket.setdefault(str(row["bucket"]), []).append(row)

    per_bucket: Dict[str, Any] = {}
    for lo, hi in buckets:
        label = bucket_label(lo, hi)
        per_bucket[label] = summarize_rows(rows_by_bucket.get(label, []))

    overall = summarize_rows(rows)
    summary = {
        "samples": len(rows),
        "selection_summary": selection_meta,
        "overall": overall,
        "per_bucket": per_bucket,
        "note": "Scoring uses MRCR prefix gate + SequenceMatcher ratio over suffix text.",
        "completed_at": datetime.now().isoformat(),
    }

    write_json(run_dir / "bucket_summary.json", per_bucket)
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2))
    print(f"Saved to {run_dir}")


if __name__ == "__main__":
    main()
