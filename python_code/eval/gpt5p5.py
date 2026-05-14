from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


Grid = list[list[int]]
Marker = tuple[int, int, int]
TaskSpec = tuple[int, int, Grid, int, list[Marker]]


def call_model(prompt: str) -> str:
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    key_file = Path.home() / ".openai_api_key"
    if api_key is None and key_file.exists():
        api_key = key_file.read_text(encoding="utf-8").strip()

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=prompt,
    )
    return response.output_text


def rotate_clockwise(pattern: Grid) -> Grid:
    return [list(row) for row in zip(*pattern[::-1])]


def rotate_counterclockwise(pattern: Grid) -> Grid:
    return [list(row) for row in zip(*pattern)][::-1]


def flip_left_right(pattern: Grid) -> Grid:
    return [list(reversed(row)) for row in pattern]


TRANSFORMS = {
    5: rotate_clockwise,
    6: rotate_counterclockwise,
    7: flip_left_right,
}


TRAIN_EXAMPLES: tuple[TaskSpec, ...] = (
    (
        12,
        12,
        [[1, 1, 0], [0, 1, 0], [0, 1, 1]],
        2,
        [(1, 5, 5), (5, 1, 6), (5, 6, 7)],
    ),
    (
        12,
        12,
        [[0, 1, 0], [1, 1, 1], [1, 0, 0]],
        3,
        [(2, 6, 5), (6, 2, 6), (6, 7, 7)],
    ),
    (
        12,
        12,
        [[1, 0, 0], [1, 1, 0], [0, 1, 1]],
        4,
        [(1, 7, 5), (6, 1, 6), (6, 6, 7)],
    ),
)


TEST_CASES: dict[str, TaskSpec] = {
    "T1": (
        16,
        16,
        [[0, 1, 1], [1, 1, 0], [0, 1, 0]],
        8,
        [
            (2, 6, 5),
            (2, 11, 6),
            (6, 1, 7),
            (6, 6, 5),
            (6, 11, 6),
            (10, 1, 7),
            (10, 6, 5),
            (10, 11, 6),
        ],
    ),
    "T2": (
        16,
        16,
        [[1, 0, 1], [1, 1, 0], [0, 1, 1]],
        8,
        [
            (2, 6, 7),
            (2, 11, 5),
            (6, 1, 6),
            (6, 6, 7),
            (6, 11, 5),
            (10, 1, 6),
            (10, 6, 7),
            (10, 11, 5),
        ],
    ),
    "T3": (
        16,
        16,
        [[1, 1, 1], [0, 1, 0], [1, 0, 0]],
        8,
        [
            (2, 6, 6),
            (2, 11, 7),
            (6, 1, 5),
            (6, 6, 6),
            (6, 11, 7),
            (10, 1, 5),
            (10, 6, 6),
            (10, 11, 7),
        ],
    ),
}


def make_task(height: int, width: int, pattern: Grid, color: int, markers: list[Marker]) -> tuple[Grid, Grid]:
    input_grid = [[0 for _ in range(width)] for _ in range(height)]
    for row_idx, row in enumerate(pattern):
        for col_idx, value in enumerate(row):
            if value:
                input_grid[row_idx][col_idx] = color

    for row_idx, col_idx, marker_color in markers:
        input_grid[row_idx][col_idx] = marker_color

    output_grid = [row[:] for row in input_grid]
    for row_idx, col_idx, marker_color in markers:
        output_grid[row_idx][col_idx] = 0
        transformed = TRANSFORMS[marker_color](pattern)
        for dr, row in enumerate(transformed):
            for dc, value in enumerate(row):
                if value:
                    output_grid[row_idx + dr][col_idx + dc] = marker_color

    return input_grid, output_grid


def compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


def build_prompt() -> str:
    parts = [
        "You are solving abstract grid reasoning tasks.",
        "Infer the single transformation rule from the training examples, then apply it to every test input.",
        'Return exactly one JSON object: {"outputs":{"T1":[[...]],"T2":[[...]],"T3":[[...]]}}.',
        "Colors are integers. 0 is background.",
    ]

    for idx, spec in enumerate(TRAIN_EXAMPLES, start=1):
        input_grid, output_grid = make_task(*spec)
        parts.extend(
            [
                f"Example {idx} input:",
                compact_json(input_grid),
                f"Example {idx} output:",
                compact_json(output_grid),
            ]
        )

    for case_id, spec in TEST_CASES.items():
        input_grid, _ = make_task(*spec)
        parts.extend([f"{case_id} input:", compact_json(input_grid)])

    return "\n".join(parts)


PROMPT = build_prompt()
EXPECTED_OUTPUTS = {
    case_id: make_task(*spec)[1] for case_id, spec in TEST_CASES.items()
}


def extract_json(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def is_grid(value: Any) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(row, list) for row in value)
        and all(isinstance(cell, int) for row in value for cell in row)
    )


def grid_cell_score(submitted: Any, expected: Grid) -> tuple[int, int]:
    total = sum(len(row) for row in expected)
    if not is_grid(submitted):
        return 0, total

    correct = 0
    for row_idx, row in enumerate(expected):
        for col_idx, expected_cell in enumerate(row):
            if (
                row_idx < len(submitted)
                and isinstance(submitted[row_idx], list)
                and col_idx < len(submitted[row_idx])
                and submitted[row_idx][col_idx] == expected_cell
            ):
                correct += 1
    return correct, total


def grade_response(text: str) -> dict[str, Any]:
    parsed = extract_json(text)
    submitted_outputs = parsed.get("outputs", {}) if parsed else {}
    if not isinstance(submitted_outputs, dict):
        submitted_outputs = {}

    per_case: dict[str, dict[str, Any]] = {}
    correct_cells = 0
    total_cells = 0
    all_exact = parsed is not None

    for case_id, expected in EXPECTED_OUTPUTS.items():
        submitted = submitted_outputs.get(case_id)
        case_correct, case_total = grid_cell_score(submitted, expected)
        exact = submitted == expected
        all_exact = all_exact and exact
        correct_cells += case_correct
        total_cells += case_total
        per_case[case_id] = {
            "exact": exact,
            "correct_cells": case_correct,
            "total_cells": case_total,
            "cell_accuracy": case_correct / case_total,
        }

    return {
        "official_score": int(all_exact),
        "cell_accuracy": correct_cells / total_cells,
        "correct_cells": correct_cells,
        "total_cells": total_cells,
        "per_case": per_case,
        "parse_error": parsed is None,
        "expected_outputs": EXPECTED_OUTPUTS,
        "submitted_outputs": submitted_outputs,
    }


def run_eval() -> dict[str, Any]:
    response_text = call_model(PROMPT)
    grade = grade_response(response_text)
    return {
        "prompt": PROMPT,
        "response": response_text,
        "grade": grade,
    }


if __name__ == "__main__":
    result = run_eval()
    print(json.dumps(result["grade"], indent=2, sort_keys=True))
