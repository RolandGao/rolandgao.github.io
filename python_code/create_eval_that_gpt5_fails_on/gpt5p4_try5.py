"""
This eval is safe and text-only. A human with the same prompt and the same
code_interpreter tool can solve each case by copy/pasting the block into
Python, locating the lone non-ASCII code point on each line, and mapping its
1-based position to A1Z26.
"""

# Run: python3 python_code/create_eval_that_gpt5_fails_on/gpt5p4_try5.py

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from typing import Dict, List


WIDTH = 26


@dataclass(frozen=True)
class EvalCase:
    name: str
    message: str
    ascii_char: str
    unicode_char: str
    unicode_name: str


def call_model(input):
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


CASES: List[EvalCase] = [
    EvalCase(
        name="cyrillic_o_positions",
        message="HUMANBEATSMODEL",
        ascii_char="o",
        unicode_char="\u043e",
        unicode_name="CYRILLIC SMALL LETTER O",
    ),
    EvalCase(
        name="cyrillic_e_positions",
        message="CHECKCODEPOINTS",
        ascii_char="e",
        unicode_char="\u0435",
        unicode_name="CYRILLIC SMALL LETTER IE",
    ),
    EvalCase(
        name="cyrillic_p_positions",
        message="PASTEDONTRETYPE",
        ascii_char="p",
        unicode_char="\u0440",
        unicode_name="CYRILLIC SMALL LETTER ER",
    ),
    EvalCase(
        name="cyrillic_c_positions",
        message="COPYPASTEWINS",
        ascii_char="c",
        unicode_char="\u0441",
        unicode_name="CYRILLIC SMALL LETTER ES",
    ),
]


def letter_to_position(letter: str) -> int:
    if not re.fullmatch(r"[A-Z]", letter):
        raise ValueError(f"Expected A-Z, got {letter!r}")
    return ord(letter) - ord("A") + 1


def build_line(ascii_char: str, unicode_char: str, position: int) -> str:
    if not 1 <= position <= WIDTH:
        raise ValueError(f"Position must be in [1, {WIDTH}], got {position}")
    line = [ascii_char] * WIDTH
    line[position - 1] = unicode_char
    return "".join(line)


def build_lines(case: EvalCase) -> List[str]:
    return [
        build_line(
            ascii_char=case.ascii_char,
            unicode_char=case.unicode_char,
            position=letter_to_position(letter),
        )
        for letter in case.message
    ]


def build_prompt(case: EvalCase) -> str:
    ascii_codepoint = f"U+{ord(case.ascii_char):04X}"
    unicode_codepoint = f"U+{ord(case.unicode_char):04X}"
    block = "\n".join(build_lines(case))
    return f"""This is a safe text-processing task. You may use code interpreter.

You are given a block of text where every line has exactly {WIDTH} characters.
Visually, every character on a line looks like "{case.ascii_char}".
On each line:
- 25 characters are ASCII "{case.ascii_char}" ({ascii_codepoint})
- 1 character is {case.unicode_name} ("{case.unicode_char}", {unicode_codepoint})

Decode rule:
- Find the 1-based position of the lone non-ASCII character on each line.
- Convert that position with A1Z26: 1=A, 2=B, ..., 26=Z.
- Read the decoded letters top to bottom.

Return only the decoded uppercase string with no spaces, punctuation, or explanation.

```text
{block}
```"""


def solve_lines(lines: List[str], ascii_char: str, unicode_char: str) -> str:
    decoded: List[str] = []
    for line in lines:
        if len(line) != WIDTH:
            raise ValueError(f"Line length {len(line)} != {WIDTH}")
        if any(char not in {ascii_char, unicode_char} for char in line):
            raise ValueError("Found an unexpected character in a line.")
        marker_positions = [
            index + 1 for index, char in enumerate(line) if char == unicode_char
        ]
        if len(marker_positions) != 1:
            raise ValueError("Each line must contain exactly one Unicode marker.")
        decoded.append(chr(ord("A") + marker_positions[0] - 1))
    return "".join(decoded)


def candidate_from_output(raw_output: str) -> str:
    candidate = raw_output.strip()
    candidate = candidate.strip("`")
    candidate = re.sub(r"\s+", "", candidate)
    return candidate.upper()


def self_check() -> None:
    for case in CASES:
        lines = build_lines(case)
        decoded = solve_lines(
            lines=lines,
            ascii_char=case.ascii_char,
            unicode_char=case.unicode_char,
        )
        if decoded != case.message:
            raise AssertionError(
                f"Generator/solver mismatch for {case.name}: {decoded} != {case.message}"
            )


def evaluate_case(index: int, case: EvalCase) -> Dict[str, object]:
    prompt = build_prompt(case)
    started_at = time.perf_counter()
    raw_output = call_model(prompt)
    elapsed_seconds = time.perf_counter() - started_at
    candidate = candidate_from_output(raw_output)
    passed = candidate == case.message

    print(f"\n=== Case {index}: {case.name} ===")
    print(f"Expected: {case.message}")
    print(f"Model output: {raw_output!r}")
    print(f"Candidate: {candidate!r}")
    print(f"Elapsed seconds: {elapsed_seconds:.2f}")
    print(f"Result: {'PASS' if passed else 'FAIL'}")

    return {
        "index": index,
        "name": case.name,
        "expected": case.message,
        "raw_output": raw_output,
        "candidate": candidate,
        "pass": passed,
        "elapsed_seconds": round(elapsed_seconds, 2),
        "prompt_char_count": len(prompt),
    }


def run_eval() -> None:
    results = [evaluate_case(index, case) for index, case in enumerate(CASES, start=1)]
    passed = sum(1 for result in results if result["pass"])
    summary = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "results": results,
    }

    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    if passed != len(results):
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate prompt generation without calling the API.",
    )
    args = parser.parse_args()

    self_check()

    if args.dry_run:
        preview = [
            {
                "name": case.name,
                "expected": case.message,
                "prompt_char_count": len(build_prompt(case)),
            }
            for case in CASES
        ]
        print(json.dumps(preview, indent=2, ensure_ascii=False))
        return

    run_eval()


if __name__ == "__main__":
    main()
