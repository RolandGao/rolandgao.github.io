#!/usr/bin/env python3
"""
TextARC-AF: an adversarially filtered, text-only abstraction eval.
python gpt5p6.py mine --out-dir eval_run

Purpose
-------
Construct a benchmark that demonstrates a human-machine gap without relying on
identity, embodiment, private information, images, audio, unsafe content, or
model-policy differences.

The benchmark uses small digit grids rendered as plain text. Each task contains
training input/output pairs and two held-out inputs. A hidden transformation must
be inferred and applied. Candidate tasks are generated deterministically and
exact-graded. The constructor searches for tasks that GPT-5 + Code Interpreter
gets wrong, then exports those exact prompts for a time-matched human study.

A benchmark is declared VALID only after:
  1. GPT-5 + Code Interpreter has zero correct answers on every selected task
     across the configured confirmation attempts; and
  2. enough human experts complete the same text prompts under the same per-task
     time limit using only an offline Python environment; and
  3. the configured human-success thresholds are met.

This is deliberately a two-stage evaluation. No code can honestly guarantee in
advance that an evolving, nondeterministic model will fail or that many humans
will succeed. This program makes those claims empirical and auditable.

Examples
--------
  export OPENAI_API_KEY=...

  # Mine six tasks that GPT-5 fails in all three attempts.
  python human_machine_gap_eval.py mine --out-dir eval_run

  # Give each expert the public packet. Their result contains no answer key.
  python human_machine_gap_eval.py human \
      --public eval_run/public.json \
      --participant expert_01 \
      --output eval_run/humans/expert_01.json

  # Validate after collecting at least eight human submissions.
  python human_machine_gap_eval.py validate \
      --public eval_run/public.json \
      --key eval_run/private_key.json \
      --submissions 'eval_run/humans/*.json'

  # Optional: run fresh post-selection model trials on the frozen suite.
  python human_machine_gap_eval.py rerun-model \
      --public eval_run/public.json \
      --key eval_run/private_key.json \
      --attempts 3
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import glob
import hashlib
import json
import multiprocessing as mp
import os
import queue
import random
import re
import statistics
import sys
import time
import traceback
from collections import deque
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence

from openai import OpenAI


# ---------------------------------------------------------------------------
# Required model call. Kept exactly in the form requested by the user.
# ---------------------------------------------------------------------------


def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1
DEFAULT_MASTER_SEED = 20260709
DEFAULT_TARGET_TASKS = 6
DEFAULT_CONFIRMATION_ATTEMPTS = 3
DEFAULT_MAX_CANDIDATES_PER_FAMILY = 40
DEFAULT_TIME_LIMIT_SECONDS = 8 * 60
DEFAULT_TRAIN_EXAMPLES = 4
DEFAULT_TEST_EXAMPLES = 2

# Validation defaults. "Many" is operationalized as at least eight independent
# experts, at least 75% of them solving each task, and a median expert score of
# at least 80% across the suite.
DEFAULT_MIN_HUMANS = 8
DEFAULT_MIN_HUMAN_TASK_RATE = 0.75
DEFAULT_MIN_MEDIAN_HUMAN_SCORE = 0.80

Grid = list[list[int]]


@dataclasses.dataclass
class Example:
    input: Grid
    output: Grid


@dataclasses.dataclass
class Task:
    task_id: str
    family: str
    seed: int
    train: list[Example]
    tests: list[Grid]
    expected: list[Grid]
    post_transform: str

    def prompt(self) -> str:
        return render_prompt(self)


# ---------------------------------------------------------------------------
# Grid utilities
# ---------------------------------------------------------------------------


def new_grid(height: int, width: int, fill: int = 0) -> Grid:
    return [[fill for _ in range(width)] for _ in range(height)]


def clone_grid(grid: Grid) -> Grid:
    return [row[:] for row in grid]


def grid_to_rows(grid: Grid) -> list[str]:
    return ["".join(str(cell) for cell in row) for row in grid]


def rows_to_grid(rows: Sequence[str]) -> Grid:
    cleaned = [re.sub(r"\s+", "", row) for row in rows]
    if not cleaned or any(not row for row in cleaned):
        raise ValueError("A grid must contain at least one nonempty row")
    width = len(cleaned[0])
    if any(len(row) != width for row in cleaned):
        raise ValueError("Grid rows have inconsistent widths")
    if any(not row.isdigit() for row in cleaned):
        raise ValueError("Grid rows may contain only digits")
    return [[int(ch) for ch in row] for row in cleaned]


def normalize_grid_value(value: Any) -> Grid:
    """Accept common JSON encodings while retaining exact grid semantics."""
    if not isinstance(value, list) or not value:
        raise ValueError("Grid must be a nonempty JSON list")
    if all(isinstance(row, str) for row in value):
        return rows_to_grid(value)
    if all(isinstance(row, list) for row in value):
        grid: Grid = []
        width: Optional[int] = None
        for row in value:
            if not row:
                raise ValueError("Grid rows may not be empty")
            normalized_row: list[int] = []
            for cell in row:
                if isinstance(cell, bool):
                    raise ValueError("Boolean cells are invalid")
                if isinstance(cell, int) and 0 <= cell <= 9:
                    normalized_row.append(cell)
                elif (
                    isinstance(cell, str)
                    and len(cell.strip()) == 1
                    and cell.strip().isdigit()
                ):
                    normalized_row.append(int(cell.strip()))
                else:
                    raise ValueError(f"Invalid cell: {cell!r}")
            width = width if width is not None else len(normalized_row)
            if len(normalized_row) != width:
                raise ValueError("Grid rows have inconsistent widths")
            grid.append(normalized_row)
        return grid
    raise ValueError("Grid must be a list of digit strings or a 2D list of digits")


def trim(grid: Grid) -> Grid:
    cells = [
        (r, c)
        for r, row in enumerate(grid)
        for c, value in enumerate(row)
        if value != 0
    ]
    if not cells:
        return [[0]]
    r0 = min(r for r, _ in cells)
    r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    c1 = max(c for _, c in cells)
    return [row[c0 : c1 + 1] for row in grid[r0 : r1 + 1]]


def rot90(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid[::-1])]


def rot180(grid: Grid) -> Grid:
    return rot90(rot90(grid))


def rot270(grid: Grid) -> Grid:
    return rot90(rot180(grid))


def flip_lr(grid: Grid) -> Grid:
    return [row[::-1] for row in grid]


def flip_ud(grid: Grid) -> Grid:
    return grid[::-1]


def transpose(grid: Grid) -> Grid:
    return [list(row) for row in zip(*grid)]


POST_TRANSFORMS: dict[str, Callable[[Grid], Grid]] = {
    "identity": clone_grid,
    "rotate_90_clockwise": rot90,
    "rotate_180": rot180,
    "mirror_left_right": flip_lr,
    "mirror_top_bottom": flip_ud,
    "transpose": transpose,
}


def apply_post(grid: Grid, name: str) -> Grid:
    return POST_TRANSFORMS[name](grid)


def connected_components(
    grid: Grid, color: Optional[int] = None
) -> list[list[tuple[int, int]]]:
    height, width = len(grid), len(grid[0])
    seen: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for r in range(height):
        for c in range(width):
            if (r, c) in seen or grid[r][c] == 0:
                continue
            if color is not None and grid[r][c] != color:
                continue
            target = grid[r][c]
            stack = [(r, c)]
            seen.add((r, c))
            comp: list[tuple[int, int]] = []
            while stack:
                rr, cc = stack.pop()
                comp.append((rr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = rr + dr, cc + dc
                    if not (0 <= nr < height and 0 <= nc < width):
                        continue
                    if (nr, nc) in seen or grid[nr][nc] != target:
                        continue
                    seen.add((nr, nc))
                    stack.append((nr, nc))
            components.append(comp)
    return components


def component_to_grid(component: Sequence[tuple[int, int]], color: int) -> Grid:
    r0 = min(r for r, _ in component)
    r1 = max(r for r, _ in component)
    c0 = min(c for _, c in component)
    c1 = max(c for _, c in component)
    out = new_grid(r1 - r0 + 1, c1 - c0 + 1)
    for r, c in component:
        out[r - r0][c - c0] = color
    return out


def place_shape(
    grid: Grid, shape: Grid, top: int, left: int, overwrite_zero_only: bool = True
) -> bool:
    height, width = len(grid), len(grid[0])
    for r, row in enumerate(shape):
        for c, value in enumerate(row):
            if value == 0:
                continue
            rr, cc = top + r, left + c
            if not (0 <= rr < height and 0 <= cc < width):
                return False
            if overwrite_zero_only and grid[rr][cc] != 0:
                return False
    for r, row in enumerate(shape):
        for c, value in enumerate(row):
            if value != 0:
                grid[top + r][left + c] = value
    return True


def random_polyomino(rng: random.Random, size: int, color: int) -> Grid:
    cells = {(0, 0)}
    while len(cells) < size:
        r, c = rng.choice(tuple(cells))
        dr, dc = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        cells.add((r + dr, c + dc))
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    shifted = {(r - min_r, c - min_c) for r, c in cells}
    height = max(r for r, _ in shifted) + 1
    width = max(c for _, c in shifted) + 1
    out = new_grid(height, width)
    for r, c in shifted:
        out[r][c] = color
    return out


def shape_canonical(grid: Grid) -> tuple[str, ...]:
    variants: list[tuple[str, ...]] = []
    current = trim(grid)
    for _ in range(4):
        variants.append(tuple(grid_to_rows(trim(current))))
        variants.append(tuple(grid_to_rows(trim(flip_lr(current)))))
        current = rot90(current)
    return min(variants)


def random_dihedral(grid: Grid, rng: random.Random) -> Grid:
    out = clone_grid(grid)
    for _ in range(rng.randrange(4)):
        out = rot90(out)
    if rng.random() < 0.5:
        out = flip_lr(out)
    return out


def place_non_touching(
    grid: Grid,
    shape: Grid,
    rng: random.Random,
    margin: int = 1,
    attempts: int = 200,
) -> tuple[int, int]:
    height, width = len(grid), len(grid[0])
    sh, sw = len(shape), len(shape[0])
    for _ in range(attempts):
        top = rng.randrange(margin, height - sh - margin + 1)
        left = rng.randrange(margin, width - sw - margin + 1)
        ok = True
        for r, row in enumerate(shape):
            for c, value in enumerate(row):
                if value == 0:
                    continue
                rr, cc = top + r, left + c
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        nr, nc = rr + dr, cc + dc
                        if 0 <= nr < height and 0 <= nc < width and grid[nr][nc] != 0:
                            ok = False
        if ok and place_shape(grid, shape, top, left):
            return top, left
    raise RuntimeError("Could not place shape without touching another component")


def choose_distinct_colors(
    rng: random.Random, count: int, excluded: Iterable[int] = ()
) -> list[int]:
    pool = [x for x in range(1, 10) if x not in set(excluded)]
    return rng.sample(pool, count)


# ---------------------------------------------------------------------------
# Task families
# ---------------------------------------------------------------------------


def make_unique_component_example(rng: random.Random, obj_color: int) -> Example:
    grid = new_grid(13, 13)
    while True:
        base = random_polyomino(rng, rng.choice((4, 5, 6)), obj_color)
        odd = random_polyomino(rng, rng.choice((4, 5, 6)), obj_color)
        if shape_canonical(base) != shape_canonical(odd):
            break
    copies = [
        random_dihedral(base, rng),
        random_dihedral(base, rng),
        random_dihedral(odd, rng),
    ]
    rng.shuffle(copies)
    odd_canon = shape_canonical(odd)
    odd_placed: Optional[Grid] = None
    for shape in copies:
        place_non_touching(grid, shape, rng)
        if shape_canonical(shape) == odd_canon:
            odd_placed = trim(shape)
    assert odd_placed is not None
    return Example(grid, odd_placed)


def make_marker_rotation_example(
    rng: random.Random, object_color: int, marker_color: int
) -> Example:
    while True:
        shape = random_polyomino(rng, rng.choice((5, 6, 7)), object_color)
        if len(shape) >= 2 and len(shape[0]) >= 2 and len(shape_canonical(shape)) >= 2:
            break
    shape = random_dihedral(shape, rng)
    grid = new_grid(11, 11)
    sh, sw = len(shape), len(shape[0])
    top = rng.randrange(2, 11 - sh - 1)
    left = rng.randrange(2, 11 - sw - 1)
    place_shape(grid, shape, top, left)
    corner = rng.choice(("TL", "TR", "BR", "BL"))
    marker_positions = {
        "TL": (top - 1, left - 1),
        "TR": (top - 1, left + sw),
        "BR": (top + sh, left + sw),
        "BL": (top + sh, left - 1),
    }
    mr, mc = marker_positions[corner]
    grid[mr][mc] = marker_color
    rotations = {"TL": 0, "TR": 3, "BR": 2, "BL": 1}
    out = trim(shape)
    for _ in range(rotations[corner]):
        out = rot90(out)
    return Example(grid, out)


def make_symmetry_example(
    rng: random.Random, object_color: int, axis_color: int
) -> Example:
    vertical = rng.random() < 0.5
    size = rng.choice((9, 11))
    grid = new_grid(size, size)
    axis = size // 2
    if vertical:
        for r in range(size):
            grid[r][axis] = axis_color
        count = rng.randint(5, 10)
        cells: set[tuple[int, int]] = set()
        while len(cells) < count:
            cells.add((rng.randrange(1, size - 1), rng.randrange(1, axis - 1)))
        for r, c in cells:
            grid[r][c] = object_color
        out = clone_grid(grid)
        for r, c in cells:
            out[r][2 * axis - c] = object_color
    else:
        for c in range(size):
            grid[axis][c] = axis_color
        count = rng.randint(5, 10)
        cells = set()
        while len(cells) < count:
            cells.add((rng.randrange(1, axis - 1), rng.randrange(1, size - 1)))
        for r, c in cells:
            grid[r][c] = object_color
        out = clone_grid(grid)
        for r, c in cells:
            out[2 * axis - r][c] = object_color
    return Example(grid, out)


def fill_enclosed_regions(grid: Grid, fill_color: int) -> Grid:
    out = clone_grid(grid)
    height, width = len(out), len(out[0])
    reachable: set[tuple[int, int]] = set()
    q: deque[tuple[int, int]] = deque()
    for r in range(height):
        for c in (0, width - 1):
            if out[r][c] == 0 and (r, c) not in reachable:
                reachable.add((r, c))
                q.append((r, c))
    for c in range(width):
        for r in (0, height - 1):
            if out[r][c] == 0 and (r, c) not in reachable:
                reachable.add((r, c))
                q.append((r, c))
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if (
                0 <= nr < height
                and 0 <= nc < width
                and out[nr][nc] == 0
                and (nr, nc) not in reachable
            ):
                reachable.add((nr, nc))
                q.append((nr, nc))
    for r in range(height):
        for c in range(width):
            if out[r][c] == 0 and (r, c) not in reachable:
                out[r][c] = fill_color
    return out


def draw_rectangle_outline(
    grid: Grid, top: int, left: int, height: int, width: int, color: int
) -> None:
    for c in range(left, left + width):
        grid[top][c] = color
        grid[top + height - 1][c] = color
    for r in range(top, top + height):
        grid[r][left] = color
        grid[r][left + width - 1] = color


def make_enclosure_example(
    rng: random.Random, outline_color: int, fill_color: int
) -> Example:
    grid = new_grid(12, 14)
    # One guaranteed closed rectangle.
    h1 = rng.randint(4, 6)
    w1 = rng.randint(4, 6)
    t1 = rng.randint(1, 4)
    l1 = rng.randint(1, 4)
    draw_rectangle_outline(grid, t1, l1, h1, w1, outline_color)

    # A deliberately open decoy far to the right or bottom.
    h2 = rng.randint(3, 5)
    w2 = rng.randint(3, 5)
    t2 = rng.randint(1, 12 - h2 - 1)
    l2 = rng.randint(8, 14 - w2 - 1) if 14 - w2 - 1 >= 8 else 8
    draw_rectangle_outline(grid, t2, l2, h2, w2, outline_color)
    # Remove one edge cell so the decoy is not enclosed.
    if rng.random() < 0.5:
        grid[t2][l2 + w2 // 2] = 0
    else:
        grid[t2 + h2 // 2][l2] = 0

    # Add a harmless open polyline if it does not collide.
    for _ in range(20):
        r = rng.randrange(1, 10)
        c = rng.randrange(1, 12)
        if all(grid[rr][cc] == 0 for rr, cc in ((r, c), (r + 1, c), (r + 1, c + 1))):
            grid[r][c] = outline_color
            grid[r + 1][c] = outline_color
            grid[r + 1][c + 1] = outline_color
            break
    return Example(grid, fill_enclosed_regions(grid, fill_color))


def make_size_rank_example(
    rng: random.Random,
    object_color: int,
    smallest_color: int,
    largest_color: int,
) -> Example:
    grid = new_grid(14, 14)
    sizes = rng.sample(range(2, 8), 4)
    for size in sizes:
        shape = random_polyomino(rng, size, object_color)
        place_non_touching(grid, shape, rng)
    out = clone_grid(grid)
    comps = connected_components(grid, object_color)
    smallest = min(comps, key=len)
    largest = max(comps, key=len)
    for r, c in smallest:
        out[r][c] = smallest_color
    for r, c in largest:
        out[r][c] = largest_color
    return Example(grid, out)


def make_gravity_example(
    rng: random.Random, wall_color: int, block_colors: Sequence[int]
) -> Example:
    height, width = 11, 11
    grid = new_grid(height, width)
    walls = (0, 5, 10)
    for c in walls:
        for r in range(height):
            grid[r][c] = wall_color
    for c in range(width):
        grid[height - 1][c] = wall_color
    for c in [x for x in range(1, width - 1) if x not in walls]:
        count = rng.randint(1, 4)
        rows = rng.sample(range(0, height - 2), count)
        for r in rows:
            grid[r][c] = rng.choice(block_colors)
    out = clone_grid(grid)
    for c in range(1, width - 1):
        if c in walls:
            continue
        values = [
            grid[r][c] for r in range(height - 1) if grid[r][c] not in (0, wall_color)
        ]
        for r in range(height - 1):
            out[r][c] = 0
        start = height - 1 - len(values)
        for i, value in enumerate(values):
            out[start + i][c] = value
    return Example(grid, out)


def make_repeat_example(
    rng: random.Random, count_color: int, motif_color: int, separator_color: int
) -> Example:
    height, left_width, right_width = 9, 5, 6
    sep_col = left_width
    grid = new_grid(height, left_width + 1 + right_width)
    for r in range(height):
        grid[r][sep_col] = separator_color

    n = rng.randint(2, 5)
    positions = [(r, c) for r in range(1, height - 1) for c in range(1, left_width - 1)]
    rng.shuffle(positions)
    chosen: list[tuple[int, int]] = []
    for r, c in positions:
        if all(abs(r - rr) + abs(c - cc) > 1 for rr, cc in chosen):
            chosen.append((r, c))
            if len(chosen) == n:
                break
    if len(chosen) < n:
        raise RuntimeError("Could not place count tokens")
    for r, c in chosen:
        grid[r][c] = count_color

    motif = random_polyomino(rng, rng.choice((3, 4, 5)), motif_color)
    motif = trim(random_dihedral(motif, rng))
    mh, mw = len(motif), len(motif[0])
    top = rng.randrange(1, height - mh)
    left = sep_col + 1 + rng.randrange(0, right_width - mw + 1)
    place_shape(grid, motif, top, left)

    out_width = n * mw + (n - 1)
    out = new_grid(mh, out_width)
    for i in range(n):
        place_shape(out, motif, 0, i * (mw + 1), overwrite_zero_only=False)
    return Example(grid, out)


def binary_panel(rng: random.Random, size: int, density: float) -> list[list[bool]]:
    panel = [[rng.random() < density for _ in range(size)] for _ in range(size)]
    if not any(any(row) for row in panel):
        panel[rng.randrange(size)][rng.randrange(size)] = True
    return panel


def overlay_operation(a: bool, b: bool, op: str) -> bool:
    if op == "xor":
        return a != b
    if op == "union":
        return a or b
    if op == "intersection":
        return a and b
    if op == "left_minus_right":
        return a and not b
    raise ValueError(op)


def make_overlay_example(
    rng: random.Random,
    left_color: int,
    right_color: int,
    separator_color: int,
    output_color: int,
    op: str,
) -> Example:
    size = 7
    for _ in range(200):
        a = binary_panel(rng, size, rng.uniform(0.18, 0.42))
        b = binary_panel(rng, size, rng.uniform(0.18, 0.42))
        result = [
            [overlay_operation(a[r][c], b[r][c], op) for c in range(size)]
            for r in range(size)
        ]
        if any(any(row) for row in result):
            break
    else:
        raise RuntimeError("Could not create nonempty overlay result")
    grid = new_grid(size, size * 2 + 1)
    for r in range(size):
        grid[r][size] = separator_color
        for c in range(size):
            if a[r][c]:
                grid[r][c] = left_color
            if b[r][c]:
                grid[r][size + 1 + c] = right_color
    out = new_grid(size, size)
    for r in range(size):
        for c in range(size):
            if result[r][c]:
                out[r][c] = output_color
    return Example(grid, out)


FamilyBuilder = Callable[[random.Random, int, int, str], Task]


def build_task_from_examples(
    family: str,
    seed: int,
    examples: list[Example],
    post_transform: str,
    train_count: int,
    test_count: int,
) -> Task:
    transformed = [
        Example(ex.input, apply_post(ex.output, post_transform)) for ex in examples
    ]
    train = transformed[:train_count]
    tests = [ex.input for ex in transformed[train_count : train_count + test_count]]
    expected = [ex.output for ex in transformed[train_count : train_count + test_count]]
    digest_source = json.dumps(
        {
            "family": family,
            "seed": seed,
            "train": [
                {"input": grid_to_rows(ex.input), "output": grid_to_rows(ex.output)}
                for ex in train
            ],
            "tests": [grid_to_rows(g) for g in tests],
        },
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(digest_source).hexdigest()[:12]
    return Task(
        task_id=f"textarc-{digest}",
        family=family,
        seed=seed,
        train=train,
        tests=tests,
        expected=expected,
        post_transform=post_transform,
    )


def choose_post_transform(rng: random.Random) -> str:
    # Identity remains common, while occasional composition makes the task less
    # reducible to memorized one-step patterns.
    choices = [
        "identity",
        "identity",
        "identity",
        "rotate_90_clockwise",
        "rotate_180",
        "mirror_left_right",
        "mirror_top_bottom",
        "transpose",
    ]
    return rng.choice(choices)


def build_unique_component_task(
    rng: random.Random, seed: int, total: int, post: str
) -> Task:
    (obj_color,) = choose_distinct_colors(rng, 1)
    examples = [make_unique_component_example(rng, obj_color) for _ in range(total)]
    return build_task_from_examples(
        "unique_component", seed, examples, post, total - 2, 2
    )


def build_marker_rotation_task(
    rng: random.Random, seed: int, total: int, post: str
) -> Task:
    obj, marker = choose_distinct_colors(rng, 2)
    examples = [make_marker_rotation_example(rng, obj, marker) for _ in range(total)]
    return build_task_from_examples(
        "marker_guided_rotation", seed, examples, post, total - 2, 2
    )


def build_symmetry_task(rng: random.Random, seed: int, total: int, post: str) -> Task:
    obj, axis = choose_distinct_colors(rng, 2)
    examples = [make_symmetry_example(rng, obj, axis) for _ in range(total)]
    return build_task_from_examples(
        "complete_reflection", seed, examples, post, total - 2, 2
    )


def build_enclosure_task(rng: random.Random, seed: int, total: int, post: str) -> Task:
    outline, fill = choose_distinct_colors(rng, 2)
    examples = [make_enclosure_example(rng, outline, fill) for _ in range(total)]
    return build_task_from_examples(
        "fill_enclosed_regions", seed, examples, post, total - 2, 2
    )


def build_size_rank_task(rng: random.Random, seed: int, total: int, post: str) -> Task:
    obj, small, large = choose_distinct_colors(rng, 3)
    examples = [make_size_rank_example(rng, obj, small, large) for _ in range(total)]
    return build_task_from_examples(
        "recolor_size_extremes", seed, examples, post, total - 2, 2
    )


def build_gravity_task(rng: random.Random, seed: int, total: int, post: str) -> Task:
    colors = choose_distinct_colors(rng, 5)
    wall, blocks = colors[0], colors[1:]
    examples = [make_gravity_example(rng, wall, blocks) for _ in range(total)]
    return build_task_from_examples(
        "gravity_in_chambers", seed, examples, post, total - 2, 2
    )


def build_repeat_task(rng: random.Random, seed: int, total: int, post: str) -> Task:
    count_color, motif_color, separator = choose_distinct_colors(rng, 3)
    examples = [
        make_repeat_example(rng, count_color, motif_color, separator)
        for _ in range(total)
    ]
    return build_task_from_examples(
        "count_then_repeat", seed, examples, post, total - 2, 2
    )


def build_overlay_task(rng: random.Random, seed: int, total: int, post: str) -> Task:
    left, right, separator, output = choose_distinct_colors(rng, 4)
    op = rng.choice(("xor", "union", "intersection", "left_minus_right"))
    examples = [
        make_overlay_example(rng, left, right, separator, output, op)
        for _ in range(total)
    ]
    return build_task_from_examples(f"overlay_{op}", seed, examples, post, total - 2, 2)


FAMILY_BUILDERS: dict[str, FamilyBuilder] = {
    "unique_component": build_unique_component_task,
    "marker_guided_rotation": build_marker_rotation_task,
    "complete_reflection": build_symmetry_task,
    "fill_enclosed_regions": build_enclosure_task,
    "recolor_size_extremes": build_size_rank_task,
    "gravity_in_chambers": build_gravity_task,
    "count_then_repeat": build_repeat_task,
    "overlay": build_overlay_task,
}


def generate_task(family: str, seed: int, train_count: int, test_count: int) -> Task:
    if family not in FAMILY_BUILDERS:
        raise KeyError(f"Unknown family: {family}")
    rng = random.Random(seed)
    post = choose_post_transform(rng)
    total = train_count + test_count
    # Builders use the final two examples as tests. The public defaults use two
    # tests; keeping this explicit prevents accidental silent mismatch.
    if test_count != 2:
        raise ValueError(
            "This reference implementation currently requires exactly two tests per task"
        )
    return FAMILY_BUILDERS[family](rng, seed, total, post)


# ---------------------------------------------------------------------------
# Prompting, parsing, and exact grading
# ---------------------------------------------------------------------------


def render_grid(grid: Grid) -> str:
    return "\n".join(grid_to_rows(grid))


def render_prompt(task: Task) -> str:
    parts = [
        "You are taking a text-only abstract-reasoning evaluation.",
        "Each grid is made only of digits. 0 is blank; other digits are distinct tokens.",
        "Infer one simple deterministic transformation that explains every training pair,",
        "then apply the same transformation to both test inputs.",
        "You may and should use the python tool to check your reasoning.",
        "Return exactly one JSON object with this schema:",
        '{"answers": [["ROW", "ROW", ...], ["ROW", "ROW", ...]]}',
        "There must be exactly two answer grids. Use digit strings for rows. Give no explanation.",
        "",
    ]
    for i, example in enumerate(task.train, start=1):
        parts.extend(
            [
                f"TRAIN {i} INPUT",
                render_grid(example.input),
                f"TRAIN {i} OUTPUT",
                render_grid(example.output),
                "",
            ]
        )
    for i, test in enumerate(task.tests, start=1):
        parts.extend([f"TEST {i} INPUT", render_grid(test), ""])
    return "\n".join(parts).rstrip() + "\n"


def json_objects_in_text(text: str) -> Iterable[Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        yield value


def parse_answers(text: str, expected_count: int = 2) -> list[Grid]:
    errors: list[str] = []
    for value in json_objects_in_text(text):
        try:
            if isinstance(value, dict):
                raw = value.get("answers")
                if raw is None and expected_count == 1:
                    raw = value.get("answer")
            else:
                raw = value
            if not isinstance(raw, list) or len(raw) != expected_count:
                raise ValueError(f"Expected exactly {expected_count} answer grids")
            return [normalize_grid_value(grid) for grid in raw]
        except (ValueError, TypeError) as exc:
            errors.append(str(exc))
    raise ValueError(
        "Could not parse valid answer JSON"
        + (f": {'; '.join(errors[-3:])}" if errors else "")
    )


def exact_grade(
    expected: Sequence[Grid], output_text: str
) -> tuple[bool, Optional[list[Grid]], Optional[str]]:
    try:
        parsed = parse_answers(output_text, expected_count=len(expected))
    except ValueError as exc:
        return False, None, str(exc)
    return list(expected) == parsed, parsed, None


# ---------------------------------------------------------------------------
# Time-limited model execution
# ---------------------------------------------------------------------------


def _model_worker(prompt: str, result_queue: mp.Queue) -> None:
    try:
        result_queue.put({"status": "ok", "output": call_model(prompt)})
    except BaseException as exc:  # Child must report API/SDK failures cleanly.
        result_queue.put(
            {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(limit=20),
            }
        )


def call_model_with_timeout(prompt: str, timeout_seconds: int) -> dict[str, Any]:
    context = mp.get_context("spawn")
    result_queue: mp.Queue = context.Queue(maxsize=1)
    process = context.Process(target=_model_worker, args=(prompt, result_queue))
    started = time.time()
    process.start()
    process.join(timeout_seconds)
    elapsed = time.time() - started
    if process.is_alive():
        process.terminate()
        process.join(10)
        return {"status": "timeout", "elapsed_seconds": elapsed}
    try:
        result = result_queue.get_nowait()
    except queue.Empty:
        return {
            "status": "error",
            "error": f"Worker exited with code {process.exitcode} without returning a result",
            "elapsed_seconds": elapsed,
        }
    result["elapsed_seconds"] = elapsed
    return result


def evaluate_model_once(task: Task, timeout_seconds: int) -> dict[str, Any]:
    run = call_model_with_timeout(task.prompt(), timeout_seconds)
    if run["status"] == "ok":
        correct, parsed, parse_error = exact_grade(task.expected, run.get("output", ""))
        run["correct"] = correct
        run["parsed_answers"] = (
            [grid_to_rows(g) for g in parsed] if parsed is not None else None
        )
        run["parse_error"] = parse_error
    else:
        # A timeout is a valid failure under the shared time limit. Infrastructure
        # errors are not accepted as evidence of an intelligence failure.
        run["correct"] = False
        run["parsed_answers"] = None
        run["parse_error"] = None
    return run


def run_is_usable_evidence(run: dict[str, Any]) -> bool:
    return run.get("status") in {"ok", "timeout"}


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def task_public_record(task: Task, time_limit_seconds: int) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "time_limit_seconds": time_limit_seconds,
        "prompt": task.prompt(),
    }


def task_private_record(
    task: Task, model_runs: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "family": task.family,
        "seed": task.seed,
        "post_transform": task.post_transform,
        "expected": [grid_to_rows(grid) for grid in task.expected],
        "model_runs": list(model_runs),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def task_from_records(
    public_record: dict[str, Any], private_record: dict[str, Any]
) -> Task:
    # Only prompt and expected answers are needed for reruns. Preserve an empty
    # structural task and override prompt through a tiny shim object instead.
    expected = [rows_to_grid(rows) for rows in private_record["expected"]]
    prompt_text = public_record["prompt"]

    class FrozenTask(Task):
        def prompt(self) -> str:  # type: ignore[override]
            return prompt_text

    return FrozenTask(
        task_id=public_record["task_id"],
        family=private_record.get("family", "frozen"),
        seed=int(private_record.get("seed", 0)),
        train=[],
        tests=[],
        expected=expected,
        post_transform=private_record.get("post_transform", "unknown"),
    )


# ---------------------------------------------------------------------------
# Mining
# ---------------------------------------------------------------------------


def mine_command(args: argparse.Namespace) -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    public_path = out_dir / "public.json"
    key_path = out_dir / "private_key.json"
    if (public_path.exists() or key_path.exists()) and not args.overwrite:
        print(
            f"Refusing to overwrite existing files in {out_dir}; pass --overwrite",
            file=sys.stderr,
        )
        return 2

    family_names = list(FAMILY_BUILDERS)
    master_rng = random.Random(args.master_seed)
    master_rng.shuffle(family_names)
    selected: list[tuple[Task, list[dict[str, Any]]]] = []

    print(
        f"Mining up to {args.target_tasks} tasks; "
        f"{args.confirmation_attempts} failed GPT-5 attempts required per task."
    )

    # Search round-robin so the final suite covers different abstractions.
    for family in family_names:
        if len(selected) >= args.target_tasks:
            break
        print(f"\nFamily: {family}")
        accepted_for_family = False
        for candidate_index in range(args.max_candidates_per_family):
            seed = master_rng.randrange(1, 2**31 - 1)
            try:
                task = generate_task(
                    family, seed, args.train_examples, args.test_examples
                )
            except Exception as exc:
                print(f"  generator retry ({type(exc).__name__}: {exc})")
                continue

            # One screening run. Correct candidates are discarded immediately.
            first = evaluate_model_once(task, args.time_limit_seconds)
            if not run_is_usable_evidence(first):
                print(
                    f"  candidate {candidate_index + 1}: API/worker error; not evidence"
                )
                continue
            if first["correct"]:
                print(f"  candidate {candidate_index + 1}: solved")
                continue

            runs = [first]
            print(f"  candidate {candidate_index + 1}: failed screening; confirming")
            evidence_ok = True
            for _ in range(args.confirmation_attempts - 1):
                run = evaluate_model_once(task, args.time_limit_seconds)
                runs.append(run)
                if not run_is_usable_evidence(run):
                    evidence_ok = False
                    break
                if run["correct"]:
                    break

            if (
                evidence_ok
                and len(runs) == args.confirmation_attempts
                and not any(r["correct"] for r in runs)
            ):
                selected.append((task, runs))
                accepted_for_family = True
                print(
                    f"  ACCEPTED {task.task_id}: 0/{args.confirmation_attempts} correct"
                )
                break
            print("  rejected during confirmation")

        if not accepted_for_family:
            print(f"  no robust failure found for {family}")

    if len(selected) < args.target_tasks:
        print(
            f"\nCould find only {len(selected)} robust failures, fewer than target {args.target_tasks}.\n"
            "No benchmark was declared successful. Increase --max-candidates-per-family, "
            "lower --target-tasks, or add independently human-solvable families.",
            file=sys.stderr,
        )
        return 1

    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    public = {
        "schema_version": SCHEMA_VERSION,
        "name": "TextARC-AF",
        "created_utc": now,
        "modality": "text-only",
        "tool": "offline Python / OpenAI code_interpreter",
        "time_limit_seconds_per_task": args.time_limit_seconds,
        "pass_rule": "All task answer grids must be exactly correct in one complete suite attempt.",
        "tasks": [
            task_public_record(task, args.time_limit_seconds) for task, _ in selected
        ],
    }
    private = {
        "schema_version": SCHEMA_VERSION,
        "name": "TextARC-AF private key",
        "created_utc": now,
        "master_seed": args.master_seed,
        "constructor": {
            "model": "gpt-5",
            "tool": {"type": "code_interpreter", "container": {"type": "auto"}},
            "confirmation_attempts": args.confirmation_attempts,
            "time_limit_seconds_per_task": args.time_limit_seconds,
            "train_examples": args.train_examples,
            "test_examples": args.test_examples,
        },
        "tasks": [task_private_record(task, runs) for task, runs in selected],
    }
    write_json(public_path, public)
    write_json(key_path, private)
    print(f"\nWrote public packet: {public_path}")
    print(f"Wrote private key/audit log: {key_path}")
    print(
        "The suite is only a model-failure candidate until the human validation command passes."
    )
    return 0


# ---------------------------------------------------------------------------
# Human study runner
# ---------------------------------------------------------------------------


def human_command(args: argparse.Namespace) -> int:
    public = read_json(Path(args.public))
    tasks = public.get("tasks", [])
    if not tasks:
        print("Public packet contains no tasks", file=sys.stderr)
        return 2

    print("TextARC-AF human evaluation")
    print(
        "Use only the displayed text and an offline Python 3 environment (standard library)."
    )
    print(
        "Do not use internet search, another person, an LLM, or the private answer key."
    )
    print(
        "The clock starts when each task is displayed. Late answers are recorded as timeouts."
    )
    print(
        "Paste one JSON object on a single line using the schema requested in the prompt.\n"
    )

    submissions: list[dict[str, Any]] = []
    for index, task in enumerate(tasks, start=1):
        limit = int(
            task.get("time_limit_seconds", public["time_limit_seconds_per_task"])
        )
        print("=" * 80)
        print(
            f"TASK {index}/{len(tasks)} | ID {task['task_id']} | LIMIT {limit} seconds"
        )
        print("=" * 80)
        print(task["prompt"])
        started_monotonic = time.monotonic()
        started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            raw = input("ANSWER JSON> ")
        except EOFError:
            raw = ""
        elapsed = time.monotonic() - started_monotonic
        timed_out = elapsed > limit
        parse_error: Optional[str] = None
        normalized: Optional[list[list[str]]] = None
        try:
            parsed = parse_answers(raw, expected_count=2)
            normalized = [grid_to_rows(grid) for grid in parsed]
        except ValueError as exc:
            parse_error = str(exc)
        submissions.append(
            {
                "task_id": task["task_id"],
                "started_utc": started_utc,
                "elapsed_seconds": elapsed,
                "timed_out": timed_out,
                "raw_answer": raw,
                "normalized_answers": normalized,
                "parse_error": parse_error,
            }
        )
        print(
            f"Recorded in {elapsed:.1f}s" + (" (TIMEOUT)" if timed_out else "") + "\n"
        )

    result = {
        "schema_version": SCHEMA_VERSION,
        "benchmark_name": public.get("name", "TextARC-AF"),
        "participant": args.participant,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "declared_conditions": {
            "text_only": True,
            "offline_python_standard_library_only": True,
            "no_llm": True,
            "no_internet": True,
            "no_other_person": True,
        },
        "submissions": submissions,
    }
    write_json(Path(args.output), result)
    print(f"Saved submission: {args.output}")
    return 0


# ---------------------------------------------------------------------------
# Fresh model reruns
# ---------------------------------------------------------------------------


def rerun_model_command(args: argparse.Namespace) -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set", file=sys.stderr)
        return 2
    public_path, key_path = Path(args.public), Path(args.key)
    public, private = read_json(public_path), read_json(key_path)
    public_by_id = {task["task_id"]: task for task in public["tasks"]}
    fresh_batch = {
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "attempts": args.attempts,
        "runs": [],
    }
    for private_task in private["tasks"]:
        task_id = private_task["task_id"]
        task = task_from_records(public_by_id[task_id], private_task)
        print(f"Rerunning {task_id}")
        runs = [
            evaluate_model_once(task, args.time_limit_seconds)
            for _ in range(args.attempts)
        ]
        fresh_batch["runs"].append({"task_id": task_id, "model_runs": runs})
        print(f"  correct: {sum(bool(run.get('correct')) for run in runs)}/{len(runs)}")
    private.setdefault("fresh_model_batches", []).append(fresh_batch)
    write_json(key_path, private)
    print(f"Appended fresh model audit batch to {key_path}")
    return 0


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_command(args: argparse.Namespace) -> int:
    public = read_json(Path(args.public))
    private = read_json(Path(args.key))
    task_ids = [task["task_id"] for task in public["tasks"]]
    private_by_id = {task["task_id"]: task for task in private["tasks"]}
    if set(task_ids) != set(private_by_id):
        print("Public/private task IDs do not match", file=sys.stderr)
        return 2

    paths: list[str] = []
    for pattern in args.submissions:
        paths.extend(glob.glob(pattern))
    paths = sorted(set(paths))
    if not paths:
        print("No human submission files matched", file=sys.stderr)
        return 2

    human_records: list[dict[str, Any]] = []
    duplicate_participants: set[str] = set()
    seen_participants: set[str] = set()
    for path in paths:
        record = read_json(Path(path))
        participant = str(record.get("participant", Path(path).stem))
        if participant in seen_participants:
            duplicate_participants.add(participant)
            continue
        seen_participants.add(participant)
        by_id = {entry["task_id"]: entry for entry in record.get("submissions", [])}
        scores: dict[str, bool] = {}
        for task_id in task_ids:
            entry = by_id.get(task_id)
            expected = [
                rows_to_grid(rows) for rows in private_by_id[task_id]["expected"]
            ]
            correct = False
            if entry and not entry.get("timed_out", False):
                normalized = entry.get("normalized_answers")
                if normalized is not None:
                    try:
                        parsed = [rows_to_grid(rows) for rows in normalized]
                        correct = parsed == expected
                    except (ValueError, TypeError):
                        correct = False
                elif entry.get("raw_answer"):
                    correct, _, _ = exact_grade(expected, entry["raw_answer"])
            scores[task_id] = correct
        human_records.append(
            {"participant": participant, "scores": scores, "path": path}
        )

    if duplicate_participants:
        print(f"Ignored duplicate participant IDs: {sorted(duplicate_participants)}")

    # Constructor evidence: API/worker errors are excluded. A timeout is a valid
    # failure under the shared time limit.
    model_task_ok: dict[str, bool] = {}
    model_attempt_counts: dict[str, tuple[int, int]] = {}
    for task_id in task_ids:
        runs = private_by_id[task_id].get("model_runs", [])
        usable = [run for run in runs if run_is_usable_evidence(run)]
        correct_count = sum(bool(run.get("correct")) for run in usable)
        model_attempt_counts[task_id] = (correct_count, len(usable))
        model_task_ok[task_id] = bool(usable) and correct_count == 0

    human_rates: dict[str, float] = {}
    for task_id in task_ids:
        human_rates[task_id] = (
            sum(record["scores"][task_id] for record in human_records)
            / len(human_records)
            if human_records
            else 0.0
        )
    human_scores = [
        sum(record["scores"].values()) / len(task_ids) for record in human_records
    ]
    median_human_score = statistics.median(human_scores) if human_scores else 0.0

    enough_humans = len(human_records) >= args.min_humans
    model_failed_robustly = all(model_task_ok.values())
    humans_solve_each_task = all(
        rate >= args.min_human_task_rate for rate in human_rates.values()
    )
    humans_solve_suite = median_human_score >= args.min_median_human_score
    valid = (
        enough_humans
        and model_failed_robustly
        and humans_solve_each_task
        and humans_solve_suite
    )

    print("\nVALIDATION REPORT")
    print("=" * 80)
    print(f"Human participants: {len(human_records)} (minimum {args.min_humans})")
    print(
        f"Median human accuracy: {median_human_score:.3f} (minimum {args.min_median_human_score:.3f})"
    )
    print("\nPer-task results:")
    for task_id in task_ids:
        mc, mn = model_attempt_counts[task_id]
        print(
            f"  {task_id}: model {mc}/{mn} correct; "
            f"humans {human_rates[task_id]:.3f} correct"
        )
    print("\nConstraint checks:")
    print(
        f"  GPT-5 + Code Interpreter robustly failed selected tasks: {model_failed_robustly}"
    )
    print(f"  Enough human experts participated: {enough_humans}")
    print(f"  Human per-task threshold met: {humans_solve_each_task}")
    print(f"  Human median-suite threshold met: {humans_solve_suite}")
    print(
        "  Text-only, benign abstract reasoning, no identity/physical attributes: True by construction"
    )
    print("=" * 80)
    print(
        "VALID HUMAN-MACHINE GAP EVAL"
        if valid
        else "NOT YET A VALIDATED HUMAN-MACHINE GAP EVAL"
    )

    report = {
        "validated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "valid": valid,
        "human_count": len(human_records),
        "median_human_score": median_human_score,
        "human_task_rates": human_rates,
        "model_attempt_counts": {
            task_id: {"correct": counts[0], "usable_attempts": counts[1]}
            for task_id, counts in model_attempt_counts.items()
        },
        "thresholds": {
            "min_humans": args.min_humans,
            "min_human_task_rate": args.min_human_task_rate,
            "min_median_human_score": args.min_median_human_score,
        },
        "participants": [
            {
                "participant": record["participant"],
                "accuracy": sum(record["scores"].values()) / len(task_ids),
            }
            for record in human_records
        ],
    }
    report_path = Path(args.report)
    write_json(report_path, report)
    print(f"Wrote validation report: {report_path}")
    return 0 if valid else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Construct and validate a text-only human-vs-GPT-5 abstraction eval."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    mine = subparsers.add_parser("mine", help="Adversarially mine GPT-5 failures")
    mine.add_argument("--out-dir", default="textarc_af_run")
    mine.add_argument("--master-seed", type=int, default=DEFAULT_MASTER_SEED)
    mine.add_argument("--target-tasks", type=int, default=DEFAULT_TARGET_TASKS)
    mine.add_argument(
        "--confirmation-attempts", type=int, default=DEFAULT_CONFIRMATION_ATTEMPTS
    )
    mine.add_argument(
        "--max-candidates-per-family",
        type=int,
        default=DEFAULT_MAX_CANDIDATES_PER_FAMILY,
    )
    mine.add_argument(
        "--time-limit-seconds", type=int, default=DEFAULT_TIME_LIMIT_SECONDS
    )
    mine.add_argument("--train-examples", type=int, default=DEFAULT_TRAIN_EXAMPLES)
    mine.add_argument("--test-examples", type=int, default=DEFAULT_TEST_EXAMPLES)
    mine.add_argument("--overwrite", action="store_true")
    mine.set_defaults(func=mine_command)

    human = subparsers.add_parser(
        "human", help="Run the frozen public packet for one human"
    )
    human.add_argument("--public", required=True)
    human.add_argument(
        "--participant",
        required=True,
        help="Opaque participant ID; do not use personal data",
    )
    human.add_argument("--output", required=True)
    human.set_defaults(func=human_command)

    rerun = subparsers.add_parser(
        "rerun-model", help="Run fresh model trials on the frozen suite"
    )
    rerun.add_argument("--public", required=True)
    rerun.add_argument("--key", required=True)
    rerun.add_argument("--attempts", type=int, default=3)
    rerun.add_argument(
        "--time-limit-seconds", type=int, default=DEFAULT_TIME_LIMIT_SECONDS
    )
    rerun.set_defaults(func=rerun_model_command)

    validate = subparsers.add_parser("validate", help="Validate the machine-human gap")
    validate.add_argument("--public", required=True)
    validate.add_argument("--key", required=True)
    validate.add_argument(
        "--submissions", nargs="+", required=True, help="One or more glob patterns"
    )
    validate.add_argument("--report", default="validation_report.json")
    validate.add_argument("--min-humans", type=int, default=DEFAULT_MIN_HUMANS)
    validate.add_argument(
        "--min-human-task-rate", type=float, default=DEFAULT_MIN_HUMAN_TASK_RATE
    )
    validate.add_argument(
        "--min-median-human-score", type=float, default=DEFAULT_MIN_MEDIAN_HUMAN_SCORE
    )
    validate.set_defaults(func=validate_command)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "confirmation_attempts", 1) < 1:
        parser.error("--confirmation-attempts must be at least 1")
    if getattr(args, "target_tasks", 1) < 1:
        parser.error("--target-tasks must be at least 1")
    if getattr(args, "time_limit_seconds", 1) < 1:
        parser.error("--time-limit-seconds must be positive")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
