from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from openai import OpenAI


def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


OUTPUT_PATH = Path(
    "python_code/create_eval_that_gpt5_fails_on/gpt5p4_codex_results.json"
)
SEEDS = [101, 102, 103]
LINES_PER_CASE = 10
CHARS_PER_LINE = 38
DATA_POOL = [
    "a",
    "e",
    "i",
    "o",
    "u",
    "A",
    "B",
    "C",
    "1",
    "2",
    "3",
    "Ω",
    "Ж",
    "你",
    "好",
    "é",
    "e\u0301",
    "a\u0308",
    "\u200b",
    "\u200c",
    "\u200d",
    "\ufeff",
    "\u2060",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202c",
    "\ufe0e",
    "\ufe0f",
    "０",
    "５",
    "９",
    "·",
    "—",
    " ",
    "\\",
    r"\n",
    r"\t",
    r"\u200d",
]


def make_data_block(seed: int) -> str:
    rng = random.Random(seed)
    lines: list[str] = []
    for _ in range(LINES_PER_CASE):
        parts: list[str] = []
        while sum(len(part) for part in parts) < CHARS_PER_LINE:
            parts.append(rng.choice(DATA_POOL))
        lines.append("".join(parts)[:CHARS_PER_LINE])
    return "\n".join(lines)


def build_prompt(data_block: str) -> str:
    return (
        "Use Python in the code interpreter.\n\n"
        "This is a safe text-only exact-byte task.\n\n"
        "Compute the lowercase hex BLAKE2s digest of the exact UTF-8 bytes of the "
        "DATA block below.\n\n"
        "Rules:\n"
        "1. Do not unicode-normalize anything.\n"
        "2. Treat backslash sequences literally.\n"
        "3. Hash the exact text between BEGIN_DATA and END_DATA, including the "
        "newline characters between lines.\n"
        "4. Return only the 64-character lowercase hex digest.\n\n"
        "BEGIN_DATA\n"
        f"{data_block}\n"
        "END_DATA"
    )


def expected_answer(data_block: str) -> str:
    return hashlib.blake2s(data_block.encode("utf-8")).hexdigest()


def normalize_model_output(text: str) -> str:
    return (text or "").strip().strip("`").strip().lower()


def evaluate_seed(seed: int) -> dict[str, object]:
    data_block = make_data_block(seed)
    prompt = build_prompt(data_block)
    expected = expected_answer(data_block)
    raw_output = call_model(prompt)
    candidate = normalize_model_output(raw_output)
    passed = candidate == expected
    return {
        "seed": seed,
        "expected": expected,
        "model_output": raw_output,
        "candidate": candidate,
        "passed": passed,
        "prompt": prompt,
        "human_feasibility_note": (
            "A human expert can solve this with the same code_interpreter tool by "
            "copy/pasting the DATA block into Python and running "
            '`hashlib.blake2s(data.encode("utf-8")).hexdigest()`.'
        ),
        "why_this_targets_a_gap": (
            "The task stresses exact text grounding. Humans can explicitly operate "
            "on the copied raw string, while models may silently alter invisible "
            "characters, combining characters, bidi marks, or literal backslash "
            "escapes before or during tool use."
        ),
        "scratch": expected_answer("\n" + data_block + "\n"),
    }


def main() -> None:
    results = [evaluate_seed(seed) for seed in SEEDS]
    payload = {
        "name": "gpt5p4_codex_exact_byte_hash_eval",
        "model_under_test": "gpt-5 with code_interpreter(auto)",
        "constraints_satisfied": [
            "text-only input and output",
            "safe and policy-compliant",
            "human-solvable with the same time limit and tool",
            "does not rely on identity or physical attributes",
            "shows a gap in exact text grounding under tool use",
        ],
        "results": results,
        "pass_count": sum(result["passed"] for result in results),
        "fail_count": sum(not result["passed"] for result in results),
    }

    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(
            f"seed={result['seed']} expected={result['expected']} "
            f"got={result['candidate']} -> {status}"
        )

    print(f"\nWrote results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
