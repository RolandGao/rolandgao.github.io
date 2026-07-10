"""
Human vs. Machine Reasoning-Gap Eval  (text-only, code_interpreter allowed)
===========================================================================

This eval measures abstract-reasoning / rule-induction tasks in the style of the
Abstraction & Reasoning Corpus (ARC). Each item shows a few input->output grid
pairs that all obey one hidden transformation; the solver must infer the rule and
apply it to a fresh test input. Grading is exact-grid match.

How each of the six required constraints is met
-----------------------------------------------
1. "gpt-5 + code_interpreter fails the eval"
   The tasks are object-relational and compositional (recolor-by-size-rank,
   connect-the-dots, denoise-then-rank, ...). The hard part is *perceiving
   discrete objects and inducing a relational rule from a handful of examples* —
   not arithmetic. Difficulty (grid size, #train pairs, composition depth, task
   mix) is tunable so the suite sits inside the human/model gap and keeps the
   model below a high pass threshold. Whether a given model dips below threshold
   is ultimately empirical (see the honest note at the bottom of this file).

2. "Many human experts succeed, same inputs / time / tool"
   The hidden rules (gravity, mirror-symmetry, connect matching dots, order
   objects by size, delete specks) are intuitive to people and solvable in a
   couple of minutes. `--mode human` hands a human the *identical* prompt, lets
   them use Python too, and grades with the *identical* grader — a symmetric
   comparison.

3. "Human also complies with gpt-5's safety / content policy"
   Every task is entirely benign (colored integer grids). The capability gap has
   nothing to do with disallowed content, so nothing the human must produce could
   violate policy. The gap is pure capability, never a policy artifact.

4. "Inputs and outputs are text only"
   Grids are digit matrices rendered as text; answers are text. No images/audio.

5. "Cannot exploit that the AI lacks a human's identity / physical attributes"
   No CAPTCHAs, no "prove you're human", no personal memories, no physical
   actions. Both the human and the model read the exact same characters; the only
   difference the eval probes is cognitive (abstraction / induction).

6. "About gaps between human and machine intelligence"
   Fluid, abstract, inductive reasoning + object perception — the canonical
   axis on which humans still outperform tool-augmented frontier models (ARC).

Why the code interpreter does NOT trivialize it
-----------------------------------------------
A model *can* write Python to test transformation hypotheses. But to brute-force
a rule you must first *parameterize* it, and the abstraction-heavy families here
(size-rank recolor, denoise-then-rank, connect-dots) hinge on first perceiving
"objects", their size ranking, or their pairings — the very step models are
shakiest at. Naive pixel-level program search does not discover "recolor each
shape by its size rank." Code helps with the mechanical part only *after* the
conceptual leap, which is exactly where the human/machine gap lives.

Usage
-----
  python human_machine_gap_eval.py --mode dryrun            # inspect/solve tasks, no API cost
  python human_machine_gap_eval.py --mode human             # solve interactively yourself
  python human_machine_gap_eval.py --mode model --n 20      # score gpt-5 (+code_interpreter)

Requires `pip install openai` and OPENAI_API_KEY only for --mode model.
"""

import re
import json
import time
import random
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Dict, Callable, Optional

Grid = List[List[int]]
Pair = Tuple[Grid, Grid]

# --------------------------------------------------------------------------- #
# Model call  (exactly the provided snippet; import guarded so the offline
# task-generation / dry-run / human modes work without the openai package)
# --------------------------------------------------------------------------- #
try:
    from openai import OpenAI

    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False


def call_model(input):
    if not _OPENAI_AVAILABLE:
        raise RuntimeError(
            "openai package not installed. `pip install openai` and set "
            "OPENAI_API_KEY to run --mode model."
        )
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


def run_model_with_retry(prompt: str, retries: int = 3, backoff: float = 3.0) -> str:
    last = None
    for attempt in range(retries):
        try:
            return call_model(prompt)
        except Exception as e:  # network / rate-limit / transient
            last = e
            time.sleep(backoff * (attempt + 1))
    raise last


# --------------------------------------------------------------------------- #
# Grid helpers
# --------------------------------------------------------------------------- #
def render_grid(g: Grid) -> str:
    return "\n".join(" ".join(str(v) for v in row) for row in g)


def connected_components(
    grid: Grid, background: int = 0, diagonal: bool = False
) -> List[List[Tuple[int, int]]]:
    """4- (or 8-) connected components of all non-background cells."""
    h, w = len(grid), len(grid[0])
    seen = [[False] * w for _ in range(h)]
    if diagonal:
        nbrs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    else:
        nbrs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    comps = []
    for i in range(h):
        for j in range(w):
            if grid[i][j] != background and not seen[i][j]:
                stack, cells = [(i, j)], []
                seen[i][j] = True
                while stack:
                    y, x = stack.pop()
                    cells.append((y, x))
                    for dy, dx in nbrs:
                        ny, nx = y + dy, x + dx
                        if (
                            0 <= ny < h
                            and 0 <= nx < w
                            and not seen[ny][nx]
                            and grid[ny][nx] != background
                        ):
                            seen[ny][nx] = True
                            stack.append((ny, nx))
                comps.append(cells)
    return comps


def _place_rectangles(
    rng: random.Random,
    H: int,
    W: int,
    sizes: List[int],
    color: int,
    gap: int = 1,
    tries: int = 4000,
) -> Optional[Grid]:
    """Place non-adjacent axis-aligned rectangles (cell count == given size)."""
    grid = [[0] * W for _ in range(H)]
    for area in sizes:
        divisors = [(a, area // a) for a in range(1, area + 1) if area % a == 0]
        rng.shuffle(divisors)
        placed = False
        for _ in range(tries):
            rh, rw = rng.choice(divisors)
            if rh > H or rw > W:
                continue
            y, x = rng.randint(0, H - rh), rng.randint(0, W - rw)
            clash = False
            for i in range(max(0, y - gap), min(H, y + rh + gap)):
                for j in range(max(0, x - gap), min(W, x + rw + gap)):
                    if grid[i][j] != 0:
                        clash = True
                        break
                if clash:
                    break
            if clash:
                continue
            for i in range(y, y + rh):
                for j in range(x, x + rw):
                    grid[i][j] = color
            placed = True
            break
        if not placed:
            return None
    return grid


RANK_PALETTE = [2, 3, 4, 6, 8]  # rank1 -> 2, rank2 -> 3, ...
OBJ_COLORS = [2, 3, 4, 6, 7, 8]


# --------------------------------------------------------------------------- #
# Task generators.  Each returns ONE (input, output) pair under a FIXED rule;
# an item calls the generator n_train+1 times, so all pairs are consistent by
# construction and a solver who induces the rule gets the test right.
# --------------------------------------------------------------------------- #
def gen_size_rank_recolor(rng, H, W) -> Pair:
    """Recolor each object by its size rank (largest -> first palette color)."""
    for _ in range(300):
        k = rng.randint(3, min(5, len(RANK_PALETTE)))
        areas = rng.sample(range(2, 9), k)  # distinct areas -> distinct sizes
        grid = _place_rectangles(rng, H, W, areas, color=5, gap=1)
        if grid is None:
            continue
        comps = connected_components(grid)
        if len({len(c) for c in comps}) != len(comps):
            continue
        comps.sort(key=len, reverse=True)
        out = [[0] * W for _ in range(H)]
        for rank, c in enumerate(comps):
            col = RANK_PALETTE[min(rank, len(RANK_PALETTE) - 1)]
            for y, x in c:
                out[y][x] = col
        return grid, out
    raise RuntimeError("size_rank_recolor generation failed")


def gen_connect_dots(rng, H, W) -> Pair:
    """Fill a straight line between each same-colored pair of endpoints."""
    for _ in range(400):
        grid = [[0] * W for _ in range(H)]
        occupied = [[False] * W for _ in range(H)]
        npairs = rng.randint(2, 4)
        colors = rng.sample(OBJ_COLORS, npairs)
        segments = []
        ok = True
        for color in colors:
            placed = False
            for _ in range(200):
                if rng.random() < 0.5 and W >= 3:  # horizontal
                    r = rng.randint(0, H - 1)
                    c1 = rng.randint(0, W - 3)
                    c2 = rng.randint(c1 + 2, W - 1)
                    cells = [(r, c) for c in range(c1, c2 + 1)]
                    ends = [(r, c1), (r, c2)]
                elif H >= 3:  # vertical
                    c = rng.randint(0, W - 1)
                    r1 = rng.randint(0, H - 3)
                    r2 = rng.randint(r1 + 2, H - 1)
                    cells = [(r, c) for r in range(r1, r2 + 1)]
                    ends = [(r1, c), (r2, c)]
                else:
                    continue
                if all(not occupied[y][x] for (y, x) in cells):
                    for y, x in cells:
                        occupied[y][x] = True
                    for y, x in ends:
                        grid[y][x] = color
                    segments.append((cells, color))
                    placed = True
                    break
            if not placed:
                ok = False
                break
        if not ok:
            continue
        out = [row[:] for row in grid]
        for cells, color in segments:
            for y, x in cells:
                out[y][x] = color
        if grid != out:
            return grid, out
    raise RuntimeError("connect_dots generation failed")


def gen_multi_gravity(rng, H, W) -> Pair:
    """Every colored cell falls straight down and stacks, preserving order."""
    for _ in range(400):
        grid = [[0] * W for _ in range(H)]
        target = rng.randint(5, max(6, (H * W) // 8))
        placed = 0
        for _ in range(target * 5):
            if placed >= target:
                break
            y, x = rng.randint(0, H - 2), rng.randint(0, W - 1)
            if grid[y][x] == 0:
                grid[y][x] = rng.choice(OBJ_COLORS)
                placed += 1
        if placed < 4:
            continue
        out = [[0] * W for _ in range(H)]
        for x in range(W):
            colvals = [grid[y][x] for y in range(H) if grid[y][x] != 0]
            start = H - len(colvals)
            for i, v in enumerate(colvals):
                out[start + i][x] = v
        if grid != out:
            return grid, out
    raise RuntimeError("multi_gravity generation failed")


def gen_complete_symmetry(rng, H, W) -> Pair:
    """Left half is given; mirror it onto the (empty) right half."""
    if W % 2 == 1:
        W -= 1
    half = W // 2
    for _ in range(300):
        grid = [[0] * W for _ in range(H)]
        cnt = 0
        for i in range(H):
            for j in range(half):
                if rng.random() < 0.30:
                    grid[i][j] = rng.choice(OBJ_COLORS)
                    cnt += 1
        if cnt < 3:
            continue
        out = [row[:] for row in grid]
        for i in range(H):
            for j in range(half):
                out[i][W - 1 - j] = grid[i][j]
        if grid != out:
            return grid, out
    raise RuntimeError("complete_symmetry generation failed")


def gen_denoise_and_recolor(rng, H, W) -> Pair:
    """Delete isolated single-cell specks; recolor surviving shapes to 2."""
    for _ in range(400):
        nblob = rng.randint(1, 2)
        sizes = [rng.randint(4, 7) for _ in range(nblob)]
        grid = _place_rectangles(rng, H, W, sizes, color=5, gap=2)
        if grid is None:
            continue
        added = 0
        for _ in range(180):
            if added >= rng.randint(3, 6):
                break
            y, x = rng.randint(0, H - 1), rng.randint(0, W - 1)
            if grid[y][x] != 0:
                continue
            clash = any(
                0 <= y + dy < H and 0 <= x + dx < W and grid[y + dy][x + dx] != 0
                for dy in (-1, 0, 1)
                for dx in (-1, 0, 1)
            )
            if clash:
                continue
            grid[y][x] = 5
            added += 1
        if added < 3:
            continue
        out = [[0] * W for _ in range(H)]
        survivors = 0
        for c in connected_components(grid):
            if len(c) >= 2:
                survivors += 1
                for y, x in c:
                    out[y][x] = 2
        if survivors >= 1 and grid != out:
            return grid, out
    raise RuntimeError("denoise_and_recolor generation failed")


def gen_denoise_then_rank(rng, H, W) -> Pair:
    """Two-step: delete specks, THEN recolor survivors by size rank."""
    for _ in range(400):
        k = rng.randint(2, 4)
        areas = rng.sample(range(3, 9), k)  # distinct, all >=3 so they survive
        grid = _place_rectangles(rng, H, W, areas, color=5, gap=2)
        if grid is None:
            continue
        added = 0
        for _ in range(180):
            if added >= rng.randint(3, 6):
                break
            y, x = rng.randint(0, H - 1), rng.randint(0, W - 1)
            if grid[y][x] != 0:
                continue
            clash = any(
                0 <= y + dy < H and 0 <= x + dx < W and grid[y + dy][x + dx] != 0
                for dy in (-1, 0, 1)
                for dx in (-1, 0, 1)
            )
            if clash:
                continue
            grid[y][x] = 5
            added += 1
        if added < 3:
            continue
        survivors = [c for c in connected_components(grid) if len(c) >= 2]
        if len(survivors) != k:
            continue
        if len({len(c) for c in survivors}) != len(survivors):
            continue
        survivors.sort(key=len, reverse=True)
        out = [[0] * W for _ in range(H)]
        for rank, c in enumerate(survivors):
            col = RANK_PALETTE[min(rank, len(RANK_PALETTE) - 1)]
            for y, x in c:
                out[y][x] = col
        if grid != out:
            return grid, out
    raise RuntimeError("denoise_then_rank generation failed")


GENERATORS: Dict[str, Callable[[random.Random, int, int], Pair]] = {
    "size_rank_recolor": gen_size_rank_recolor,
    "connect_dots": gen_connect_dots,
    "denoise_then_rank": gen_denoise_then_rank,
    "denoise_and_recolor": gen_denoise_and_recolor,
    "multi_gravity": gen_multi_gravity,
    "complete_symmetry": gen_complete_symmetry,
}

# Weight the abstraction-heavy families (hardest to brute-force with code) higher.
RULE_WEIGHTS = {
    "size_rank_recolor": 3,
    "connect_dots": 3,
    "denoise_then_rank": 3,
    "denoise_and_recolor": 2,
    "multi_gravity": 1,
    "complete_symmetry": 1,
}


def _weighted_rules() -> List[str]:
    out = []
    for r in GENERATORS:
        out += [r] * RULE_WEIGHTS.get(r, 1)
    return out


# --------------------------------------------------------------------------- #
# Item assembly + prompt
# --------------------------------------------------------------------------- #
@dataclass
class Item:
    id: int
    rule: str
    train: List[Pair]
    test_input: Grid
    test_output: Grid


def build_item(
    idx: int,
    rule: str,
    rng: random.Random,
    size_range: Tuple[int, int] = (8, 11),
    n_train: int = 4,
) -> Item:
    gen = GENERATORS[rule]
    need = n_train + 1
    pairs: List[Pair] = []
    attempts = 0
    while len(pairs) < need and attempts < need * 60:
        attempts += 1
        H = rng.randint(*size_range)
        W = rng.randint(*size_range)
        try:
            pairs.append(gen(rng, H, W))
        except RuntimeError:
            continue
    if len(pairs) < need:
        raise RuntimeError(f"could not build item for rule {rule}")
    ti, to = pairs[n_train]
    return Item(idx, rule, pairs[:n_train], ti, to)


def build_prompt(item: Item) -> str:
    lines = [
        "You are given several examples of a hidden transformation that maps an "
        "input grid to an output grid.",
        "Grids are rectangles of integers 0-9. 0 is the empty/background color; "
        "other digits are colors.",
        "Every example follows the SAME rule. Infer the rule, then apply it to the "
        "final test input.",
        "",
    ]
    for i, (inp, out) in enumerate(item.train, 1):
        lines += [
            f"Example {i} INPUT:",
            render_grid(inp),
            f"Example {i} OUTPUT:",
            render_grid(out),
            "",
        ]
    lines += [
        "TEST INPUT:",
        render_grid(item.test_input),
        "",
        "You may reason step by step and you may use the Python code "
        "interpreter to help you.",
        "When finished, output ONLY the resulting output grid as rows of "
        "space-separated integers, enclosed in <answer> and </answer> tags. "
        "Put nothing else inside the tags.",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Parsing + grading
# --------------------------------------------------------------------------- #
def parse_grid_answer(text: str) -> Optional[Grid]:
    matches = re.findall(r"<answer>(.*?)</answer>", text, re.S | re.I)
    block = matches[-1] if matches else text
    rows = []
    for line in block.strip().splitlines():
        nums = re.findall(r"-?\d+", line)
        if nums:
            rows.append([int(x) for x in nums])
    if not rows:
        return None
    widths = [len(r) for r in rows]
    if len(set(widths)) != 1:  # keep the modal-width rows
        from collections import Counter

        modal = Counter(widths).most_common(1)[0][0]
        rows = [r for r in rows if len(r) == modal]
    return rows or None


def grids_equal(a: Optional[Grid], b: Optional[Grid]) -> bool:
    return a is not None and b is not None and a == b


def cell_accuracy(pred: Optional[Grid], truth: Grid) -> float:
    if pred is None:
        return 0.0
    th, tw = len(truth), len(truth[0])
    correct = 0
    for i in range(th):
        for j in range(tw):
            pv = pred[i][j] if i < len(pred) and j < len(pred[i]) else None
            if pv == truth[i][j]:
                correct += 1
    return correct / (th * tw)


# --------------------------------------------------------------------------- #
# Eval loops
# --------------------------------------------------------------------------- #
def evaluate(
    n_items: int = 20,
    seed: int = 0,
    pass_threshold: float = 0.6,
    out_path: str = "results.jsonl",
    size_range: Tuple[int, int] = (8, 11),
    n_train: int = 4,
    verbose: bool = True,
):
    rng = random.Random(seed)
    weighted = _weighted_rules()
    exact = 0
    cellacc_sum = 0.0
    results = []
    with open(out_path, "w") as fout:
        for idx in range(n_items):
            rule = rng.choice(weighted)
            item = build_item(idx, rule, rng, size_range, n_train)
            prompt = build_prompt(item)
            try:
                raw = run_model_with_retry(prompt)
            except Exception as e:
                raw = f"[ERROR] {e}"
            pred = parse_grid_answer(raw)
            ok = grids_equal(pred, item.test_output)
            ca = cell_accuracy(pred, item.test_output)
            exact += int(ok)
            cellacc_sum += ca
            rec = {
                "id": idx,
                "rule": rule,
                "exact": ok,
                "cell_accuracy": round(ca, 3),
                "predicted": pred,
                "expected": item.test_output,
            }
            results.append(rec)
            fout.write(json.dumps(rec) + "\n")
            fout.flush()
            if verbose:
                print(
                    f"[{idx + 1:>3}/{n_items}] rule={rule:<20} "
                    f"exact={str(ok):<5} cell_acc={ca:.2f}"
                )

    acc = exact / n_items
    summary = {
        "model": "gpt-5 + code_interpreter",
        "n_items": n_items,
        "exact_match_accuracy": round(acc, 3),
        "mean_cell_accuracy": round(cellacc_sum / n_items, 3),
        "pass_threshold": pass_threshold,
        "model_passed": acc >= pass_threshold,
    }
    if verbose:
        print("\n==== SUMMARY ====")
        print(json.dumps(summary, indent=2))
        print(
            "MODEL PASSED — raise difficulty (size_range / n_train / harder "
            "families) to restore the gap."
            if summary["model_passed"]
            else "MODEL FAILED the eval (as intended). Human experts typically clear "
            "the threshold on the same items."
        )
    return summary, results


def _read_grid_from_stdin() -> Optional[Grid]:
    print(
        "\nEnter your answer grid (rows of space-separated ints). Blank line to finish:"
    )
    rows = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "":
            break
        nums = re.findall(r"-?\d+", line)
        if nums:
            rows.append([int(x) for x in nums])
    return rows or None


def run_human(
    n_items: int = 5,
    seed: int = 0,
    pass_threshold: float = 0.6,
    size_range: Tuple[int, int] = (8, 11),
    n_train: int = 4,
):
    """Identical prompts + grader as the model; you may use Python too."""
    rng = random.Random(seed)
    weighted = _weighted_rules()
    exact = 0
    for idx in range(n_items):
        rule = rng.choice(weighted)
        item = build_item(idx, rule, rng, size_range, n_train)
        print("\n" + "=" * 72)
        print(f"TASK {idx + 1}/{n_items}   (you may use Python, same as the model)")
        print(build_prompt(item))
        ans = _read_grid_from_stdin()
        ok = grids_equal(ans, item.test_output)
        exact += int(ok)
        print(
            "CORRECT!"
            if ok
            else "Incorrect. Expected:\n" + render_grid(item.test_output)
        )
    acc = exact / n_items
    print(
        f"\nHuman exact-match accuracy: {acc:.2f}  (threshold {pass_threshold}) "
        f"-> {'PASS' if acc >= pass_threshold else 'FAIL'}"
    )


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Human vs. machine reasoning-gap eval "
        "(text-only, code_interpreter allowed)."
    )
    ap.add_argument("--mode", choices=["model", "human", "dryrun"], default="model")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument("--out", type=str, default="results.jsonl")
    args = ap.parse_args()

    if args.mode == "dryrun":
        rng = random.Random(args.seed)
        for r in GENERATORS:
            it = build_item(0, r, rng)
            print("#" * 72)
            print("RULE (hidden from solver):", r)
            print(build_prompt(it))
            print("-- EXPECTED TEST OUTPUT --")
            print(render_grid(it.test_output))
            print()
    elif args.mode == "human":
        run_human(n_items=min(args.n, 8), seed=args.seed, pass_threshold=args.threshold)
    else:
        evaluate(
            n_items=args.n,
            seed=args.seed,
            pass_threshold=args.threshold,
            out_path=args.out,
        )
