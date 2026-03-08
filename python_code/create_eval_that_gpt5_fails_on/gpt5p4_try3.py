from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from collections import deque
from dataclasses import asdict, dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from openai import OpenAI


def call_model(input: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


CANVAS_SPEC = """
You are solving a deterministic text-only ASCII canvas puzzle.

State:
- A grid of H rows and W columns.
- Each cell contains exactly one character from this alphabet:
  . # @ o + *
- Coordinates are zero-indexed as (x, y), with x = column and y = row.
- The top-left cell is (0, 0).

Patterns for STAMP:
- Pattern 0:
  .#.
  ###
  .#.
- Pattern 1:
  ###
  #..
  ###
- Pattern 2:
  #.#
  .#.
  #.#

Commands:
- PAINT x y ch
  Set cell (x, y) to ch.

- RECT x y w h ch
  Fill the rectangle with top-left (x, y), width w, height h, using ch.

- SHIFTROW y k
  Cyclically shift row y to the right by k positions.
  Negative k shifts left.

- SHIFTCOL x k
  Cyclically shift column x downward by k positions.
  Negative k shifts upward.

- MIRRORX x y w h
  Reflect the rectangle left-to-right in place.

- MIRRORY x y w h
  Reflect the rectangle top-to-bottom in place.

- ROT x y s
  Rotate the s x s square with top-left (x, y) clockwise by 90 degrees.

- FLOOD x y ch
  Let src be the original character at (x, y) before this command.
  Replace the entire 4-neighbor connected component of src containing (x, y) with ch.
  If src == ch, do nothing.

- STAMP x y ch p
  Overlay the 3 x 3 pattern p with top-left anchor (x, y).
  For every # in the pattern, paint that cell with ch.
  For every . in the pattern, leave that cell unchanged.
  If a stamped cell would fall outside the grid, ignore that cell.

- SWAP a b
  Swap all occurrences of symbols a and b across the entire grid.

Additional rules:
- All commands are valid.
- Characters are always from the given alphabet.
- Commands are applied in order.
- Rows in the input grid are listed top to bottom.

Required output format:
Return exactly one line in this format and nothing else:
NONDOT=<int> COMPONENTS=<int> LARGEST=<int> GRID_SHA256=<lowercase_hex>

Definitions:
- NONDOT is the number of cells that are not '.' in the final grid.
- COMPONENTS is the number of 4-neighbor connected components of non-dot cells,
  ignoring symbol identity.
- LARGEST is the size of the largest such component, or 0 if there are none.
- GRID_SHA256 is the SHA-256 of the final grid serialized as:
  json.dumps(rows, separators=(",", ":"))
  where rows is the final list of row strings.

If you use code_interpreter, still return only that single final line.
Do not include explanations.
""".strip()


ALPHABET = [".", "#", "@", "o", "+", "*"]
NON_DOT = [ch for ch in ALPHABET if ch != "."]
STAMP_PATTERNS: Dict[int, Sequence[str]] = {
    0: (".#.", "###", ".#."),
    1: ("###", "#..", "###"),
    2: ("#.#", ".#.", "#.#"),
}
ANSWER_RE = re.compile(
    r"NONDOT=(\d+)\s+COMPONENTS=(\d+)\s+LARGEST=(\d+)\s+GRID_SHA256=([0-9a-f]{64})",
    re.IGNORECASE,
)


@dataclass
class CanvasItem:
    item_id: str
    seed: int
    difficulty: str
    prompt: str
    answer: str
    metadata: Dict[str, object]


def choose_symbol(rng: random.Random, allow_dot: bool = True) -> str:
    pool = ALPHABET if allow_dot else NON_DOT
    return rng.choice(pool)


def make_random_grid(rng: random.Random, height: int, width: int) -> List[List[str]]:
    weights = [0.58, 0.10, 0.08, 0.08, 0.08, 0.08]
    flat = rng.choices(ALPHABET, weights=weights, k=height * width)
    return [flat[i * width : (i + 1) * width] for i in range(height)]


def grid_rows(grid: Sequence[Sequence[str]]) -> List[str]:
    return ["".join(row) for row in grid]


def grid_sha256(grid: Sequence[Sequence[str]]) -> str:
    payload = json.dumps(grid_rows(grid), separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def count_components(grid: Sequence[Sequence[str]]) -> Tuple[int, int, int]:
    height = len(grid)
    width = len(grid[0])
    seen = [[False] * width for _ in range(height)]
    components = 0
    largest = 0
    nondot = 0

    for y in range(height):
        for x in range(width):
            if grid[y][x] != ".":
                nondot += 1

    for y in range(height):
        for x in range(width):
            if seen[y][x] or grid[y][x] == ".":
                continue
            components += 1
            q = deque([(x, y)])
            seen[y][x] = True
            size = 0
            while q:
                cx, cy = q.popleft()
                size += 1
                for nx, ny in (
                    (cx + 1, cy),
                    (cx - 1, cy),
                    (cx, cy + 1),
                    (cx, cy - 1),
                ):
                    if 0 <= nx < width and 0 <= ny < height:
                        if not seen[ny][nx] and grid[ny][nx] != ".":
                            seen[ny][nx] = True
                            q.append((nx, ny))
            largest = max(largest, size)

    return nondot, components, largest


def paint(grid: List[List[str]], x: int, y: int, ch: str) -> None:
    grid[y][x] = ch


def fill_rect(grid: List[List[str]], x: int, y: int, w: int, h: int, ch: str) -> None:
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            grid[yy][xx] = ch


def shift_row(grid: List[List[str]], y: int, k: int) -> None:
    width = len(grid[0])
    k %= width
    if k:
        grid[y] = grid[y][-k:] + grid[y][:-k]


def shift_col(grid: List[List[str]], x: int, k: int) -> None:
    height = len(grid)
    k %= height
    if not k:
        return
    col = [grid[y][x] for y in range(height)]
    col = col[-k:] + col[:-k]
    for y in range(height):
        grid[y][x] = col[y]


def mirror_x(grid: List[List[str]], x: int, y: int, w: int, h: int) -> None:
    for yy in range(y, y + h):
        segment = grid[yy][x : x + w]
        grid[yy][x : x + w] = list(reversed(segment))


def mirror_y(grid: List[List[str]], x: int, y: int, w: int, h: int) -> None:
    rows = [grid[yy][x : x + w] for yy in range(y, y + h)]
    rows.reverse()
    for offset, row in enumerate(rows):
        grid[y + offset][x : x + w] = row


def rotate_square(grid: List[List[str]], x: int, y: int, s: int) -> None:
    block = [grid[yy][x : x + s] for yy in range(y, y + s)]
    rotated = [[block[s - 1 - xx][yy] for xx in range(s)] for yy in range(s)]
    for yy in range(s):
        for xx in range(s):
            grid[y + yy][x + xx] = rotated[yy][xx]


def flood_fill(grid: List[List[str]], x: int, y: int, ch: str) -> None:
    src = grid[y][x]
    if src == ch:
        return
    height = len(grid)
    width = len(grid[0])
    q = deque([(x, y)])
    grid[y][x] = ch
    while q:
        cx, cy = q.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < width and 0 <= ny < height and grid[ny][nx] == src:
                grid[ny][nx] = ch
                q.append((nx, ny))


def stamp(grid: List[List[str]], x: int, y: int, ch: str, pattern_id: int) -> None:
    pattern = STAMP_PATTERNS[pattern_id]
    height = len(grid)
    width = len(grid[0])
    for dy, row in enumerate(pattern):
        for dx, token in enumerate(row):
            if token != "#":
                continue
            xx = x + dx
            yy = y + dy
            if 0 <= xx < width and 0 <= yy < height:
                grid[yy][xx] = ch


def swap_symbols(grid: List[List[str]], a: str, b: str) -> None:
    height = len(grid)
    width = len(grid[0])
    for y in range(height):
        for x in range(width):
            if grid[y][x] == a:
                grid[y][x] = b
            elif grid[y][x] == b:
                grid[y][x] = a


def apply_command(grid: List[List[str]], command: str) -> None:
    parts = command.split()
    op = parts[0]

    if op == "PAINT":
        paint(grid, int(parts[1]), int(parts[2]), parts[3])
    elif op == "RECT":
        fill_rect(
            grid,
            int(parts[1]),
            int(parts[2]),
            int(parts[3]),
            int(parts[4]),
            parts[5],
        )
    elif op == "SHIFTROW":
        shift_row(grid, int(parts[1]), int(parts[2]))
    elif op == "SHIFTCOL":
        shift_col(grid, int(parts[1]), int(parts[2]))
    elif op == "MIRRORX":
        mirror_x(grid, int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
    elif op == "MIRRORY":
        mirror_y(grid, int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4]))
    elif op == "ROT":
        rotate_square(grid, int(parts[1]), int(parts[2]), int(parts[3]))
    elif op == "FLOOD":
        flood_fill(grid, int(parts[1]), int(parts[2]), parts[3])
    elif op == "STAMP":
        stamp(grid, int(parts[1]), int(parts[2]), parts[3], int(parts[4]))
    elif op == "SWAP":
        swap_symbols(grid, parts[1], parts[2])
    else:
        raise ValueError(f"Unknown command: {command}")


def execute_program(
    initial_grid: Sequence[Sequence[str]], commands: Iterable[str]
) -> List[List[str]]:
    grid = [list(row) for row in initial_grid]
    for command in commands:
        apply_command(grid, command)
    return grid


def render_prompt(
    height: int,
    width: int,
    initial_grid: Sequence[Sequence[str]],
    commands: Sequence[str],
) -> str:
    return (
        f"{CANVAS_SPEC}\n\n"
        f"H = {height}\n"
        f"W = {width}\n\n"
        f"Initial grid:\n"
        f"{chr(10).join(grid_rows(initial_grid))}\n\n"
        f"Commands:\n"
        f"{chr(10).join(commands)}\n"
    )


def answer_from_grid(grid: Sequence[Sequence[str]]) -> str:
    nondot, components, largest = count_components(grid)
    return (
        f"NONDOT={nondot} "
        f"COMPONENTS={components} "
        f"LARGEST={largest} "
        f"GRID_SHA256={grid_sha256(grid)}"
    )


def random_rect(
    rng: random.Random, width: int, height: int, min_side: int = 1
) -> Tuple[int, int, int, int]:
    w = rng.randint(min_side, min(5, width))
    h = rng.randint(min_side, min(5, height))
    x = rng.randint(0, width - w)
    y = rng.randint(0, height - h)
    return x, y, w, h


def random_square(rng: random.Random, width: int, height: int) -> Tuple[int, int, int]:
    s = rng.randint(2, min(5, width, height))
    x = rng.randint(0, width - s)
    y = rng.randint(0, height - s)
    return x, y, s


def generate_commands(
    rng: random.Random, width: int, height: int, count: int
) -> List[str]:
    commands: List[str] = []
    for _ in range(count):
        op = rng.choices(
            [
                "PAINT",
                "RECT",
                "SHIFTROW",
                "SHIFTCOL",
                "MIRRORX",
                "MIRRORY",
                "ROT",
                "FLOOD",
                "STAMP",
                "SWAP",
            ],
            weights=[6, 7, 4, 4, 3, 3, 4, 5, 4, 2],
            k=1,
        )[0]

        if op == "PAINT":
            commands.append(
                f"PAINT {rng.randrange(width)} {rng.randrange(height)} {choose_symbol(rng)}"
            )
        elif op == "RECT":
            x, y, w, h = random_rect(rng, width, height)
            commands.append(f"RECT {x} {y} {w} {h} {choose_symbol(rng)}")
        elif op == "SHIFTROW":
            commands.append(f"SHIFTROW {rng.randrange(height)} {rng.randint(-11, 11)}")
        elif op == "SHIFTCOL":
            commands.append(f"SHIFTCOL {rng.randrange(width)} {rng.randint(-11, 11)}")
        elif op == "MIRRORX":
            x, y, w, h = random_rect(rng, width, height, min_side=2)
            commands.append(f"MIRRORX {x} {y} {w} {h}")
        elif op == "MIRRORY":
            x, y, w, h = random_rect(rng, width, height, min_side=2)
            commands.append(f"MIRRORY {x} {y} {w} {h}")
        elif op == "ROT":
            x, y, s = random_square(rng, width, height)
            commands.append(f"ROT {x} {y} {s}")
        elif op == "FLOOD":
            commands.append(
                f"FLOOD {rng.randrange(width)} {rng.randrange(height)} {choose_symbol(rng)}"
            )
        elif op == "STAMP":
            commands.append(
                f"STAMP {rng.randint(-1, width - 1)} {rng.randint(-1, height - 1)} "
                f"{choose_symbol(rng, allow_dot=False)} {rng.randrange(len(STAMP_PATTERNS))}"
            )
        else:
            a, b = rng.sample(ALPHABET, 2)
            commands.append(f"SWAP {a} {b}")
    return commands


def classify_difficulty(width: int, height: int, commands: Sequence[str]) -> str:
    hard_ops = sum(
        cmd.startswith(("FLOOD", "STAMP", "ROT", "MIRROR", "SWAP")) for cmd in commands
    )
    if width * height >= 100 or len(commands) >= 28 or hard_ops >= 11:
        return "hard"
    return "medium"


def make_item(seed: int) -> CanvasItem:
    rng = random.Random(seed)
    height = rng.randint(8, 12)
    width = rng.randint(8, 12)
    initial_grid = make_random_grid(rng, height, width)
    command_count = rng.randint(20, 32)
    commands = generate_commands(rng, width, height, command_count)
    final_grid = execute_program(initial_grid, commands)
    answer = answer_from_grid(final_grid)
    prompt = render_prompt(height, width, initial_grid, commands)
    difficulty = classify_difficulty(width, height, commands)
    item_id = hashlib.sha256(f"{seed}|{answer}".encode("utf-8")).hexdigest()[:16]
    metadata = {
        "height": height,
        "width": width,
        "command_count": len(commands),
        "hard_op_count": sum(
            cmd.startswith(("FLOOD", "STAMP", "ROT", "MIRROR", "SWAP"))
            for cmd in commands
        ),
    }
    return CanvasItem(
        item_id=item_id,
        seed=seed,
        difficulty=difficulty,
        prompt=prompt,
        answer=answer,
        metadata=metadata,
    )


def normalize_prediction(text: str) -> Optional[str]:
    if not text:
        return None
    match = ANSWER_RE.search(text.strip())
    if not match:
        return None
    nondot, components, largest, sha = match.groups()
    return (
        f"NONDOT={int(nondot)} "
        f"COMPONENTS={int(components)} "
        f"LARGEST={int(largest)} "
        f"GRID_SHA256={sha.lower()}"
    )


def score_item(item: CanvasItem, raw_text: str) -> Dict[str, object]:
    pred = normalize_prediction(raw_text)
    return {
        "item_id": item.item_id,
        "seed": item.seed,
        "difficulty": item.difficulty,
        "correct": pred == item.answer,
        "gold": item.answer,
        "pred_normalized": pred,
        "raw_pred": raw_text,
    }


def run_model_on_item(item: CanvasItem, sleep_s: float = 0.0) -> Dict[str, object]:
    if sleep_s > 0:
        time.sleep(sleep_s)
    raw = call_model(item.prompt) or ""
    return score_item(item, raw)


def save_jsonl(path: str, rows: Sequence[Dict[str, object]]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: str) -> List[Dict[str, object]]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def save_items(path: str, items: Sequence[CanvasItem]) -> None:
    save_jsonl(path, [asdict(item) for item in items])


def load_items(path: str) -> List[CanvasItem]:
    return [CanvasItem(**row) for row in load_jsonl(path)]


def calibrate_failed_set(
    keep: int,
    candidates: int,
    seed_start: int,
    sleep_s: float,
) -> List[CanvasItem]:
    failures: List[CanvasItem] = []
    for offset in range(candidates):
        seed = seed_start + offset
        item = make_item(seed)
        scored = run_model_on_item(item, sleep_s=sleep_s)
        if scored["correct"]:
            print(f"[pass-model] seed={seed} item_id={item.item_id}")
        else:
            failures.append(item)
            print(
                f"[keep {len(failures):>2}/{keep}] seed={seed} item_id={item.item_id}"
            )
        if len(failures) >= keep:
            break
    return failures


def print_human_protocol() -> None:
    print(
        """
Human protocol for this eval

Goal:
- Solve each item using the exact same prompt given to the model.
- You may use code_interpreter.
- You must comply with the same safety and content policies as the model.
- Return exactly one line in the required format.

Why a human can succeed:
- The task is fully specified and deterministic.
- A human can write a short Python simulator for the grid operations.
- The task uses only text inputs and text outputs.
- No external data, unsafe content, images, or audio are needed.

Reasonable time budget:
- 5 to 10 minutes for a first item.
- Later items are faster once the simulator exists.
        """.strip()
    )


def cmd_build(args: argparse.Namespace) -> None:
    items = calibrate_failed_set(
        keep=args.keep,
        candidates=args.num_candidates,
        seed_start=args.seed_start,
        sleep_s=args.sleep_s,
    )
    save_items(args.out, items)
    print(f"Saved {len(items)} calibrated items to {args.out}")


def cmd_run(args: argparse.Namespace) -> None:
    items = load_items(args.eval_file)
    preds: List[Dict[str, object]] = []
    for idx, item in enumerate(items, start=1):
        print(f"[{idx}/{len(items)}] item_id={item.item_id}")
        scored = run_model_on_item(item, sleep_s=args.sleep_s)
        preds.append(scored)
        print(f"  correct={scored['correct']} pred={scored['pred_normalized']!r}")
    save_jsonl(args.pred_out, preds)
    print(f"Saved predictions to {args.pred_out}")


def cmd_score(args: argparse.Namespace) -> None:
    items = {item.item_id: item for item in load_items(args.eval_file)}
    preds = load_jsonl(args.pred_file)
    if not preds:
        print("No predictions found.")
        return

    total = len(preds)
    correct = 0
    by_diff: Dict[str, List[int]] = {}
    for row in preds:
        is_correct = int(bool(row["correct"]))
        correct += is_correct
        diff = items[row["item_id"]].difficulty
        by_diff.setdefault(diff, []).append(is_correct)

    print(f"Accuracy: {correct / total:.3f} ({correct}/{total})")
    for diff, values in sorted(by_diff.items()):
        print(
            f"  {diff}: {sum(values)}/{len(values)} = {sum(values) / len(values):.3f}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ASCII canvas eval calibrated on gpt-5 failures."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build", help="Generate a failed-item eval set.")
    p_build.add_argument("--num-candidates", type=int, default=40)
    p_build.add_argument("--keep", type=int, default=8)
    p_build.add_argument("--seed-start", type=int, default=3000)
    p_build.add_argument("--sleep-s", type=float, default=0.0)
    p_build.add_argument("--out", required=True)
    p_build.set_defaults(func=cmd_build)

    p_run = sub.add_parser("run-model", help="Run gpt-5 on an eval file.")
    p_run.add_argument("--eval-file", required=True)
    p_run.add_argument("--pred-out", required=True)
    p_run.add_argument("--sleep-s", type=float, default=0.0)
    p_run.set_defaults(func=cmd_run)

    p_score = sub.add_parser("score", help="Score predictions.")
    p_score.add_argument("--eval-file", required=True)
    p_score.add_argument("--pred-file", required=True)
    p_score.set_defaults(func=cmd_score)

    p_human = sub.add_parser(
        "print-human-instructions", help="Print the human protocol."
    )
    p_human.set_defaults(func=lambda args: print_human_protocol())

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
# python3 python_code/create_eval_that_gpt5_fails_on/gpt5p4_try3.py build --num-candidates 5 --keep 1 --out python_code/create_eval_that_gpt5_fails_on/calibrated_eval_try2.json
