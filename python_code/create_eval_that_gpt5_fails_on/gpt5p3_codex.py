#!/usr/bin/env python3
"""Build a text-only eval where gpt-5 + code_interpreter is calibrated to fail.

Run:
python3 python_code/create_eval_that_gpt5_fails_on/gpt5p3_codex.py build --num-candidates 8 --keep 1 --out python_code/create_eval_that_gpt5_fails_on/gpt5p3_codex_eval.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI


def call_model(input: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


@dataclass
class Candidate:
    id: str
    prompt: str
    expected_answer: str
    data_block: str


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def has_exactly_three_distinct_prime_factors(n: int) -> bool:
    if n < 2:
        return False
    distinct = 0
    x = n
    p = 2
    while p * p <= x:
        if x % p == 0:
            distinct += 1
            while x % p == 0:
                x //= p
            if distinct > 3:
                return False
        p = 3 if p == 2 else p + 2
    if x > 1:
        distinct += 1
    return distinct == 3


def to_base36_upper(n: int) -> str:
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if n == 0:
        return "0"
    out = []
    x = n
    while x > 0:
        x, rem = divmod(x, 36)
        out.append(chars[rem])
    return "".join(reversed(out))


def compute_expected_answer(data_block: str) -> str:
    kept = []
    for ch in data_block:
        if ch == "\n":
            continue
        code = ord(ch)
        if is_prime(code) or has_exactly_three_distinct_prime_factors(code):
            kept.append(to_base36_upper(code))
    t = ":".join(kept)
    digest = hashlib.blake2s(t.encode("utf-8")).hexdigest()
    return digest[8:40][::-1]


def extract_answer(model_output: str) -> Optional[str]:
    if not model_output:
        return None
    # Prefer exact 32-hex spans; take the last one to tolerate explanations.
    matches = re.findall(r"(?i)\b[0-9a-f]{32}\b", model_output)
    if not matches:
        return None
    return matches[-1].lower()


def make_data_block(rng: random.Random, lines: int = 12, width: int = 42) -> str:
    single_chars = list(
        "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz0123456789"
    ) + [
        "Ω",
        "Ж",
        "λ",
        "ß",
        "é",
        "İ",
        "ı",
        "ø",
        "你",
        "好",
        "中",
        "文",
        "０",
        "５",
        "９",
        "·",
        "—",
        " ",
        "\u200b",
        "\u200c",
        "\u200d",
        "\ufeff",
    ]
    literal_sequences = [r"\u200d", r"\n", r"\t", r"\\", r"\x41", r"\u03A9"]

    all_tokens = single_chars + literal_sequences

    out_lines = []
    for _ in range(lines):
        line_tokens = []
        current_len = 0
        while current_len < width:
            tok = rng.choice(all_tokens)
            line_tokens.append(tok)
            current_len += len(tok)
        line = "".join(line_tokens)[:width]
        out_lines.append(line)
    return "\n".join(out_lines)


def make_prompt(data_block: str) -> str:
    return (
        "Use Python in the code interpreter.\\n"
        "\\n"
        "Compute the answer exactly from this DATA block.\\n"
        "\\n"
        "Rules (must be followed exactly):\\n"
        "1) DATA is the exact text between BEGIN_DATA and END_DATA, including newline characters between lines.\\n"
        "2) Do not unicode-normalize anything.\\n"
        "3) Treat backslash sequences literally (example: \\\\u200d is six characters).\\n"
        "4) Build list C of every character in DATA except newline.\\n"
        "5) Keep c in C iff ord(c) is prime OR ord(c) has exactly 3 distinct prime factors.\\n"
        "6) Convert each kept ord(c) to base-36 uppercase (digits 0-9 then A-Z).\\n"
        "7) Join these tokens using ':' to form string T.\\n"
        "8) Compute blake2s hex digest of UTF-8 bytes of T.\\n"
        "9) Output only digest[8:40] reversed, lowercase hex, exactly 32 chars.\\n"
        "\\n"
        "Return only the 32-character answer.\\n"
        "BEGIN_DATA\\n"
        f"{data_block}\\n"
        "END_DATA"
    )


def generate_candidate(rng: random.Random, idx: int) -> Candidate:
    data_block = make_data_block(rng)
    expected = compute_expected_answer(data_block)
    prompt = make_prompt(data_block)
    return Candidate(
        id=f"cand_{idx:04d}",
        prompt=prompt,
        expected_answer=expected,
        data_block=data_block,
    )


def build_eval(args: argparse.Namespace) -> None:
    rng = random.Random(args.seed)

    records = []
    failures = []

    for i in range(args.num_candidates):
        cand = generate_candidate(rng, i)
        model_output = call_model(cand.prompt)
        extracted = extract_answer(model_output)
        passed = extracted == cand.expected_answer

        record = {
            "id": cand.id,
            "prompt": cand.prompt,
            "expected_answer": cand.expected_answer,
            "model_output": model_output,
            "model_extracted_answer": extracted,
            "model_passed": passed,
            "human_feasibility_note": (
                "A human can solve this within the time limit by copying DATA into Python, "
                "implementing the rules directly, and printing the 32-char result."
            ),
        }
        records.append(record)
        if not passed:
            failures.append(record)

    if len(failures) < args.keep:
        raise RuntimeError(
            f"Only found {len(failures)} failures out of {args.num_candidates} candidates; "
            "increase --num-candidates or change --seed."
        )

    kept = failures[: args.keep]
    payload = {
        "name": "gpt5p3_codex_text_only_calibrated_eval",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model_under_test": "gpt-5 with code_interpreter(auto)",
        "constraints": [
            "gpt-5 with code_interpreter fails at least one kept item",
            "text-only input/output",
            "human-solvable with the same tool and constraints",
            "no policy-violating content",
        ],
        "time_limit_minutes": args.time_limit_minutes,
        "build": {
            "seed": args.seed,
            "num_candidates": args.num_candidates,
            "keep": args.keep,
            "total_failures_found": len(failures),
        },
        "items": kept,
        "all_candidate_results": records,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote eval to {out_path}")
    print(f"Candidates tested: {len(records)}")
    print(f"Failures found: {len(failures)}")
    print(f"Kept: {len(kept)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a calibrated text-only eval where gpt-5+code_interpreter fails."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Generate and calibrate eval items")
    b.add_argument("--num-candidates", type=int, default=8)
    b.add_argument("--keep", type=int, default=1)
    b.add_argument("--seed", type=int, default=7)
    b.add_argument("--time-limit-minutes", type=int, default=20)
    b.add_argument(
        "--out",
        type=str,
        default="python_code/create_eval_that_gpt5_fails_on/gpt5p3_codex_eval.json",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "build":
        build_eval(args)
        return
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
