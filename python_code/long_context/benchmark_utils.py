from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple
from urllib.error import HTTPError

try:
    import tiktoken
except ImportError:  # pragma: no cover
    tiktoken = None

HF_DATASET_SERVER = "https://datasets-server.huggingface.co"
MRCR_DATASET_ID = "openai/mrcr"
DEFAULT_HTTP_TIMEOUT_SECONDS = int(os.getenv("MRCR_HTTP_TIMEOUT_SECONDS", "180"))
DEFAULT_HTTP_MAX_ATTEMPTS = int(os.getenv("MRCR_HTTP_MAX_ATTEMPTS", "8"))
MAX_DATASET_ROWS_PER_REQUEST = 100
DEFAULT_TOKENIZER_NAME = "o200k_base"


@dataclass
class MRCRSample:
    sample_id: int
    messages: List[Dict[str, Any]]
    answer: str
    random_string_to_prepend: str
    n_needles: int
    desired_msg_index: int
    total_messages: int
    n_chars: int
    date_added: str
    prompt_tokens: Optional[int] = None
    answer_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


def _request_json(
    path: str,
    query: Dict[str, Any],
    timeout_seconds: int = DEFAULT_HTTP_TIMEOUT_SECONDS,
    max_attempts: int = DEFAULT_HTTP_MAX_ATTEMPTS,
) -> Dict[str, Any]:
    url = f"{HF_DATASET_SERVER}/{path}?{urllib.parse.urlencode(query)}"
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:  # pragma: no cover
            last_error = exc
            if attempt == max_attempts:
                break
            backoff = min(6 * attempt, 60) if exc.code == 429 else min(2**attempt, 20)
            time.sleep(backoff)
        except Exception as exc:  # pragma: no cover
            last_error = exc
            if attempt == max_attempts:
                break
            time.sleep(min(2**attempt, 20))
    raise RuntimeError(f"Failed to fetch {url}") from last_error


def _num_rows(dataset: str) -> int:
    payload = _request_json("size", {"dataset": dataset})
    return int(payload["size"]["dataset"]["num_rows"])


def _iter_dataset_rows(dataset: str, *, offset: int = 0, batch_size: int = 10, max_rows: Optional[int] = None) -> Iterator[Tuple[int, Dict[str, Any]]]:
    total_rows = _num_rows(dataset)
    start = max(0, offset)
    end = total_rows if max_rows is None else min(total_rows, start + max_rows)
    safe_batch = max(1, min(batch_size, MAX_DATASET_ROWS_PER_REQUEST))
    cursor = start

    while cursor < end:
        length = min(safe_batch, end - cursor)
        payload = _request_json(
            "rows",
            {
                "dataset": dataset,
                "config": "default",
                "split": "train",
                "offset": cursor,
                "length": length,
            },
        )
        rows = payload.get("rows", [])
        if not rows:
            break
        for row_record in rows:
            yield int(row_record["row_idx"]), row_record["row"]
        cursor += len(rows)


def _row_to_sample(
    *,
    row_idx: int,
    row: Dict[str, Any],
    allowed_needles: Optional[Set[int]],
    max_prompt_chars: Optional[int],
    max_n_chars: Optional[int],
    min_total_tokens: Optional[int],
    max_total_tokens: Optional[int],
    tokenizer_name: str,
) -> Optional[MRCRSample]:
    n_needles = int(row["n_needles"])
    if allowed_needles is not None and n_needles not in allowed_needles:
        return None
    if max_prompt_chars is not None and len(row["prompt"]) > max_prompt_chars:
        return None
    if max_n_chars is not None and int(row["n_chars"]) > max_n_chars:
        return None

    try:
        messages = json.loads(row["prompt"])
    except json.JSONDecodeError:
        return None
    if not isinstance(messages, list):
        return None

    prompt_tokens: Optional[int] = None
    answer_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    if min_total_tokens is not None or max_total_tokens is not None:
        prompt_tokens = _count_message_tokens(messages, encoding_name=tokenizer_name)
        answer_tokens = _count_text_tokens(str(row["answer"]), encoding_name=tokenizer_name)
        total_tokens = prompt_tokens + answer_tokens
        if min_total_tokens is not None and total_tokens < min_total_tokens:
            return None
        if max_total_tokens is not None and total_tokens > max_total_tokens:
            return None

    return MRCRSample(
        sample_id=row_idx,
        messages=messages,
        answer=str(row["answer"]),
        random_string_to_prepend=str(row["random_string_to_prepend"]),
        n_needles=n_needles,
        desired_msg_index=int(row["desired_msg_index"]),
        total_messages=int(row["total_messages"]),
        n_chars=int(row["n_chars"]),
        date_added=str(row.get("date_added", "")),
        prompt_tokens=prompt_tokens,
        answer_tokens=answer_tokens,
        total_tokens=total_tokens,
    )


def _get_encoder(encoding_name: str = DEFAULT_TOKENIZER_NAME):
    if tiktoken is None:
        raise RuntimeError("tiktoken is required for token filters. Install with: pip install tiktoken")
    return tiktoken.get_encoding(encoding_name)


def _count_text_tokens(text: str, encoding_name: str = DEFAULT_TOKENIZER_NAME) -> int:
    return len(_get_encoder(encoding_name).encode(text))


def _count_message_tokens(messages: Sequence[Dict[str, Any]], encoding_name: str = DEFAULT_TOKENIZER_NAME) -> int:
    enc = _get_encoder(encoding_name)
    total = 0
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, str):
            total += len(enc.encode(content))
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        total += len(enc.encode(str(item.get("text", ""))))
                    else:
                        total += len(enc.encode(json.dumps(item, ensure_ascii=False)))
                else:
                    total += len(enc.encode(str(item)))
        else:
            total += len(enc.encode(str(content)))
    return total


def iter_mrcr_samples(
    *,
    offset: int = 0,
    max_rows: Optional[int] = None,
    limit: Optional[int] = None,
    n_needles_filter: Optional[Sequence[int]] = None,
    max_prompt_chars: Optional[int] = None,
    max_n_chars: Optional[int] = None,
    batch_size: int = 10,
    min_total_tokens: Optional[int] = None,
    max_total_tokens: Optional[int] = None,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME,
) -> Iterator[MRCRSample]:
    allowed_needles = set(int(x) for x in n_needles_filter) if n_needles_filter else None
    yielded = 0

    for row_idx, row in _iter_dataset_rows(MRCR_DATASET_ID, offset=offset, batch_size=batch_size, max_rows=max_rows):
        sample = _row_to_sample(
            row_idx=row_idx,
            row=row,
            allowed_needles=allowed_needles,
            max_prompt_chars=max_prompt_chars,
            max_n_chars=max_n_chars,
            min_total_tokens=min_total_tokens,
            max_total_tokens=max_total_tokens,
            tokenizer_name=tokenizer_name,
        )
        if sample is None:
            continue

        yield sample
        yielded += 1
        if limit is not None and yielded >= limit:
            break


def iter_mrcr_samples_by_ids(
    sample_ids: Sequence[int],
    *,
    n_needles_filter: Optional[Sequence[int]] = None,
    max_prompt_chars: Optional[int] = None,
    max_n_chars: Optional[int] = None,
    min_total_tokens: Optional[int] = None,
    max_total_tokens: Optional[int] = None,
    tokenizer_name: str = DEFAULT_TOKENIZER_NAME,
    batch_size: int = MAX_DATASET_ROWS_PER_REQUEST,
) -> Iterator[MRCRSample]:
    if not sample_ids:
        return

    ordered_ids: List[int] = []
    seen_ids: Set[int] = set()
    for raw in sample_ids:
        sid = int(raw)
        if sid in seen_ids:
            continue
        ordered_ids.append(sid)
        seen_ids.add(sid)

    if not ordered_ids:
        return

    allowed_needles = set(int(x) for x in n_needles_filter) if n_needles_filter else None
    sorted_ids = sorted(ordered_ids)
    safe_batch = max(1, min(int(batch_size), MAX_DATASET_ROWS_PER_REQUEST))

    ranges: List[Tuple[int, int]] = []
    start = sorted_ids[0]
    prev = sorted_ids[0]
    for sid in sorted_ids[1:]:
        contiguous = sid == prev + 1
        within_cap = (sid - start + 1) <= safe_batch
        if contiguous and within_cap:
            prev = sid
            continue
        ranges.append((start, prev - start + 1))
        start = sid
        prev = sid
    ranges.append((start, prev - start + 1))

    found: Dict[int, MRCRSample] = {}
    wanted = set(ordered_ids)
    for offset, length in ranges:
        for row_idx, row in _iter_dataset_rows(MRCR_DATASET_ID, offset=offset, batch_size=length, max_rows=length):
            if row_idx not in wanted:
                continue
            sample = _row_to_sample(
                row_idx=row_idx,
                row=row,
                allowed_needles=allowed_needles,
                max_prompt_chars=max_prompt_chars,
                max_n_chars=max_n_chars,
                min_total_tokens=min_total_tokens,
                max_total_tokens=max_total_tokens,
                tokenizer_name=tokenizer_name,
            )
            if sample is not None:
                found[row_idx] = sample

    for sid in ordered_ids:
        sample = found.get(sid)
        if sample is not None:
            yield sample


def grade_mrcr(response: str, answer: str, random_string_to_prepend: str) -> Dict[str, Any]:
    sampled = response or ""
    golden = answer or ""
    prefix_ok = sampled.startswith(random_string_to_prepend)
    if not prefix_ok:
        return {"score": 0.0, "prefix_ok": False, "sampled_text": sampled, "golden_text": golden}

    sampled_text = sampled.removeprefix(random_string_to_prepend)
    golden_text = golden.removeprefix(random_string_to_prepend)
    return {
        "score": float(SequenceMatcher(None, sampled_text, golden_text).ratio()),
        "prefix_ok": True,
        "sampled_text": sampled_text,
        "golden_text": golden_text,
    }


def messages_to_transcript(messages: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for item in messages:
        role = str(item.get("role", "unknown")).strip().capitalize()
        content = item.get("content", "")
        if isinstance(content, list):
            parts: List[str] = []
            for segment in content:
                if isinstance(segment, dict) and segment.get("type") == "text":
                    parts.append(str(segment.get("text", "")))
                else:
                    parts.append(str(segment))
            text = "".join(parts)
        else:
            text = str(content)
        lines.append(f"{role}: {text}")
    return "\n".join(lines)


def extract_last_user_message(messages: Sequence[Dict[str, Any]]) -> str:
    for item in reversed(messages):
        if str(item.get("role", "")).lower() == "user":
            return str(item.get("content", ""))
    return ""
