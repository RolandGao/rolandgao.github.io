from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

from openai import OpenAI


def call_model(input: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


TAPE_SPEC = """
You are solving a deterministic text-only tape-machine puzzle.

You are given a tiny virtual machine. Compute the final machine state exactly.

Machine state:
- Four unsigned 32-bit registers: A, B, C, D
- A circular tape of signed 32-bit integers of length N
- A pointer P into the tape, 0-indexed
- A program counter (starts at instruction 0)
- Registers start at 0 unless changed by the program.
- All register arithmetic is modulo 2^32 unless explicitly noted.
- Tape cells are always stored as signed 32-bit integers.

Helper functions:
- to_signed32(v):
    v = v mod 2^32
    if v >= 2^31: v -= 2^32
    return v
- tape_u32(i) means tape[i] interpreted modulo 2^32
- rol32(x, n) rotates x left by n mod 32 bits

Instruction syntax:
- SET X n         ; set register X to integer n modulo 2^32, where X in {A,B,C,D}
- ADD X Y         ; X := (X + Y) mod 2^32, Y is either integer literal or register
- XOR X Y         ; X := X xor Y, Y is either integer literal or register
- ROL X n         ; rotate-left register X by n mod 32 bits
- MOV n           ; P := (P + n) mod N, where n is a signed integer
- LOAD X          ; X := tape_u32(P)
- STORE Y         ; tape[P] := to_signed32(value(Y)), where Y is integer literal or register
- ADDT X off      ; X := (X + tape_u32((P + off) mod N)) mod 2^32
- XORT X off      ; X := X xor tape_u32((P + off) mod N)
- MIX off         ; let i = P and j = (P + off) mod N
                  ; let x = tape[i] and y = tape[j], using the original tape values
                  ; A := (A + tape_u32(i)) mod 2^32
                  ; B := rol32(B xor tape_u32(j), 3)
                  ; C := (C + ((tape_u32(i) * 2654435761 + tape_u32(j) * 97531) mod 2^32)) mod 2^32
                  ; tape[i] := to_signed32(x + to_signed32(B))
                  ; tape[j] := to_signed32(y - to_signed32(A))
                  ; P := j
- SWAP X Y        ; swap registers X and Y
- DEC X           ; X := (X - 1) mod 2^32
- JNZ X off       ; if register X != 0, jump relative by off, else continue
                  ; off is a signed integer; jumping is relative to current PC
                  ; after a taken jump, do not add the normal +1
- HALT            ; stop execution immediately

Additional rules:
- Execution stops on HALT or after max_steps instructions, whichever comes first.
- For ADD/XOR/STORE operands, integer literals may be negative.
- For JNZ, the tested register value is its stored unsigned 32-bit value.
- There are no labels; jumps use numeric offsets.
- Program lines are indexed starting from 0.

Required output format:
Return exactly one line in this format and nothing else:
A=<unsigned_decimal> B=<unsigned_decimal> C=<unsigned_decimal> P=<unsigned_decimal> TAPE_SHA256=<lowercase_hex>

where TAPE_SHA256 is the SHA-256 of the final tape serialized as:
json.dumps(tape, separators=(",", ":"))

If you use code_interpreter, still return only that single final line.
Do not include explanations.
""".strip()


MASK32 = 0xFFFFFFFF
REGS = ["A", "B", "C", "D"]
WORK_REGS = ["A", "B", "C"]


def rol32(x: int, n: int) -> int:
    n %= 32
    x &= MASK32
    return ((x << n) | (x >> (32 - n))) & MASK32


def to_signed32(v: int) -> int:
    v &= MASK32
    if v >= 2**31:
        v -= 2**32
    return v


def parse_reg_or_int(tok: str, regs: Dict[str, int]) -> int:
    if tok in regs:
        return regs[tok]
    return int(tok)


def tape_sha256(tape: List[int]) -> str:
    payload = json.dumps(tape, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_program(
    program_text: str,
    tape_init: List[int],
    pointer_init: int,
    max_steps: int,
) -> Dict[str, object]:
    regs = {name: 0 for name in REGS}
    tape = [to_signed32(x) for x in tape_init]
    n = len(tape)
    pointer = pointer_init % n
    lines = [ln.strip() for ln in program_text.strip().splitlines() if ln.strip()]
    pc = 0
    steps = 0

    while 0 <= pc < len(lines) and steps < max_steps:
        steps += 1
        parts = lines[pc].split()
        op = parts[0]

        if op == "SET":
            x, value = parts[1], int(parts[2])
            regs[x] = value & MASK32
            pc += 1

        elif op == "ADD":
            x, y = parts[1], parse_reg_or_int(parts[2], regs)
            regs[x] = (regs[x] + y) & MASK32
            pc += 1

        elif op == "XOR":
            x, y = parts[1], parse_reg_or_int(parts[2], regs)
            regs[x] = (regs[x] ^ (y & MASK32)) & MASK32
            pc += 1

        elif op == "ROL":
            x, amount = parts[1], int(parts[2])
            regs[x] = rol32(regs[x], amount)
            pc += 1

        elif op == "MOV":
            amount = int(parts[1])
            pointer = (pointer + amount) % n
            pc += 1

        elif op == "LOAD":
            x = parts[1]
            regs[x] = tape[pointer] & MASK32
            pc += 1

        elif op == "STORE":
            value = parse_reg_or_int(parts[1], regs)
            tape[pointer] = to_signed32(value)
            pc += 1

        elif op == "ADDT":
            x, off = parts[1], int(parts[2])
            regs[x] = (regs[x] + (tape[(pointer + off) % n] & MASK32)) & MASK32
            pc += 1

        elif op == "XORT":
            x, off = parts[1], int(parts[2])
            regs[x] = (regs[x] ^ (tape[(pointer + off) % n] & MASK32)) & MASK32
            pc += 1

        elif op == "MIX":
            off = int(parts[1])
            i = pointer
            j = (pointer + off) % n
            x = tape[i]
            y = tape[j]
            regs["A"] = (regs["A"] + (x & MASK32)) & MASK32
            regs["B"] = rol32(regs["B"] ^ (y & MASK32), 3)
            mix_term = (((x & MASK32) * 2654435761) + ((y & MASK32) * 97531)) & MASK32
            regs["C"] = (regs["C"] + mix_term) & MASK32
            tape[i] = to_signed32(x + to_signed32(regs["B"]))
            tape[j] = to_signed32(y - to_signed32(regs["A"]))
            pointer = j
            pc += 1

        elif op == "SWAP":
            x, y = parts[1], parts[2]
            regs[x], regs[y] = regs[y], regs[x]
            pc += 1

        elif op == "DEC":
            x = parts[1]
            regs[x] = (regs[x] - 1) & MASK32
            pc += 1

        elif op == "JNZ":
            x, off = parts[1], int(parts[2])
            if regs[x] != 0:
                pc = pc + off
            else:
                pc += 1

        elif op == "HALT":
            break

        else:
            raise ValueError(f"Unknown instruction: {op}")

    return {
        "A": regs["A"],
        "B": regs["B"],
        "C": regs["C"],
        "D": regs["D"],
        "P": pointer,
        "tape": tape,
        "tape_sha256": tape_sha256(tape),
        "steps": steps,
        "halted": (0 <= pc < len(lines) and lines[pc].startswith("HALT")),
    }


@dataclass
class EvalItem:
    item_id: str
    seed: int
    max_steps: int
    difficulty: str
    prompt: str
    answer: str
    metadata: Dict[str, object]


def rand_lit(rng: random.Random) -> int:
    choices = [
        rng.randint(-9, 9),
        rng.randint(-999, 999),
        rng.randint(-(2**31), 2**31 - 1),
    ]
    return rng.choice(choices)


def rand_work_reg(rng: random.Random) -> str:
    return rng.choice(WORK_REGS)


def rand_reg_or_lit(rng: random.Random) -> str:
    if rng.random() < 0.45:
        return rand_work_reg(rng)
    return str(rand_lit(rng))


def rand_off(rng: random.Random, tape_len: int, nonzero: bool = False) -> int:
    width = min(4, tape_len - 1) if tape_len > 1 else 0
    if width <= 0:
        return 0
    choices = list(range(-width, width + 1))
    if nonzero:
        choices = [x for x in choices if x != 0]
    return rng.choice(choices)


def append_random_data_op(lines: List[str], rng: random.Random, tape_len: int) -> None:
    op = rng.choice(
        ["ADD", "XOR", "ROL", "MOV", "LOAD", "STORE", "ADDT", "XORT", "MIX", "SWAP"]
    )
    if op == "ADD":
        lines.append(f"ADD {rand_work_reg(rng)} {rand_reg_or_lit(rng)}")
    elif op == "XOR":
        lines.append(f"XOR {rand_work_reg(rng)} {rand_reg_or_lit(rng)}")
    elif op == "ROL":
        lines.append(f"ROL {rand_work_reg(rng)} {rng.randint(1, 31)}")
    elif op == "MOV":
        lines.append(f"MOV {rand_off(rng, tape_len)}")
    elif op == "LOAD":
        lines.append(f"LOAD {rand_work_reg(rng)}")
    elif op == "STORE":
        lines.append(f"STORE {rand_reg_or_lit(rng)}")
    elif op == "ADDT":
        lines.append(f"ADDT {rand_work_reg(rng)} {rand_off(rng, tape_len)}")
    elif op == "XORT":
        lines.append(f"XORT {rand_work_reg(rng)} {rand_off(rng, tape_len)}")
    elif op == "MIX":
        lines.append(f"MIX {rand_off(rng, tape_len, nonzero=True)}")
    else:
        x, y = rng.sample(WORK_REGS, 2)
        lines.append(f"SWAP {x} {y}")


def generate_candidate_program(
    seed: int,
    target_len: int = 30,
) -> Tuple[str, List[int], int, int, Dict[str, object]]:
    rng = random.Random(seed)
    tape_len = rng.randint(9, 15)
    tape_init = [rand_lit(rng) for _ in range(tape_len)]
    pointer_init = rng.randrange(tape_len)

    init_a = rng.randint(0, MASK32)
    init_b = rng.randint(0, MASK32)
    init_c = rng.randint(0, MASK32)
    loop1 = rng.randint(3, 6)
    loop2 = rng.randint(2, 5)

    lines: List[str] = []
    lines.append(f"SET A {init_a}")
    lines.append(f"SET B {init_b}")
    lines.append(f"SET C {init_c}")

    lines.append(f"SET D {loop1}")
    loop1_start = len(lines)
    for _ in range(rng.randint(4, 6)):
        append_random_data_op(lines, rng, tape_len)
    lines.append("DEC D")
    lines.append(f"JNZ D {loop1_start - len(lines)}")

    for _ in range(rng.randint(5, 8)):
        append_random_data_op(lines, rng, tape_len)

    lines.append(f"SET D {loop2}")
    loop2_start = len(lines)
    for _ in range(rng.randint(3, 5)):
        append_random_data_op(lines, rng, tape_len)
    lines.append("DEC D")
    lines.append(f"JNZ D {loop2_start - len(lines)}")

    while len(lines) < target_len - 1:
        append_random_data_op(lines, rng, tape_len)

    lines.append("HALT")
    program = "\n".join(lines)

    reference = run_program(program, tape_init, pointer_init, max_steps=5000)
    max_steps = reference["steps"] + rng.randint(6, 40)

    meta = {
        "program_len": len(lines),
        "tape_len": tape_len,
        "pointer_init": pointer_init,
        "init_a": init_a,
        "init_b": init_b,
        "init_c": init_c,
        "loop1": loop1,
        "loop2": loop2,
    }
    return program, tape_init, pointer_init, max_steps, meta


def answer_string(result: Dict[str, object]) -> str:
    return (
        f"A={result['A']} "
        f"B={result['B']} "
        f"C={result['C']} "
        f"P={result['P']} "
        f"TAPE_SHA256={result['tape_sha256']}"
    )


def make_prompt(
    program: str,
    tape_init: List[int],
    pointer_init: int,
    max_steps: int,
) -> str:
    tape_json = json.dumps(tape_init, separators=(",", ":"))
    return (
        f"{TAPE_SPEC}\n\n"
        f"N = {len(tape_init)}\n"
        f"initial_pointer = {pointer_init}\n"
        f"initial_tape = {tape_json}\n"
        f"max_steps = {max_steps}\n\n"
        f"Program:\n{program}\n"
    )


def generate_eval_item(seed: int) -> EvalItem:
    target_len = 28 + (seed % 5)
    program, tape_init, pointer_init, max_steps, meta = generate_candidate_program(
        seed=seed,
        target_len=target_len,
    )
    result = run_program(program, tape_init, pointer_init, max_steps=max_steps)
    answer = answer_string(result)

    difficulty = "medium"
    if meta["program_len"] >= 31 or (meta["loop1"] + meta["loop2"] >= 9):
        difficulty = "hard"

    item_id = hashlib.sha256(f"{seed}|{answer}".encode("utf-8")).hexdigest()[:16]
    prompt = make_prompt(program, tape_init, pointer_init, max_steps)

    return EvalItem(
        item_id=item_id,
        seed=seed,
        max_steps=max_steps,
        difficulty=difficulty,
        prompt=prompt,
        answer=answer,
        metadata={
            **meta,
            "reference_steps": result["steps"],
            "final_pointer": result["P"],
            "final_tape_len": len(result["tape"]),
        },
    )


ANSWER_RE = re.compile(
    r"A=(\d+)\s+B=(\d+)\s+C=(\d+)\s+P=(\d+)\s+TAPE_SHA256=([0-9a-f]{64})",
    re.IGNORECASE,
)


def normalize_model_answer(text: str) -> Optional[str]:
    if not text:
        return None

    match = ANSWER_RE.search(text.strip())
    if not match:
        return None

    a, b, c, p, sha = match.groups()
    return f"A={int(a)} B={int(b)} C={int(c)} P={int(p)} TAPE_SHA256={sha.lower()}"


def score_prediction(gold: str, pred_text: str) -> Dict[str, object]:
    pred = normalize_model_answer(pred_text)
    return {
        "correct": pred == gold,
        "gold": gold,
        "pred_normalized": pred,
        "raw_pred": pred_text,
    }


def run_single_model_item(item: EvalItem, sleep_s: float = 0.0) -> Dict[str, object]:
    if sleep_s > 0:
        time.sleep(sleep_s)

    raw = call_model(item.prompt) or ""
    scored = score_prediction(item.answer, raw)
    return {
        "item_id": item.item_id,
        "seed": item.seed,
        "difficulty": item.difficulty,
        **scored,
    }


def build_calibrated_eval(
    num_candidates: int,
    keep: int,
    seed_start: int = 2000,
    sleep_s: float = 0.0,
) -> List[EvalItem]:
    kept: List[EvalItem] = []

    for i, seed in enumerate(range(seed_start, seed_start + num_candidates), start=1):
        item = generate_eval_item(seed)
        result = run_single_model_item(item, sleep_s=sleep_s)

        if not result["correct"]:
            kept.append(item)
            print(f"[keep {len(kept):>2}/{keep}] seed={seed} item_id={item.item_id}")
        else:
            print(f"[pass-model] seed={seed} item_id={item.item_id}")

        if len(kept) >= keep:
            break

        if i >= 20 and not kept:
            print("Stopping early: no failed items found in first 20 candidates.")
            break

    return kept


def save_jsonl(path: str, rows: List[Dict[str, object]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def save_eval(path: str, items: List[EvalItem]) -> None:
    save_jsonl(path, [asdict(x) for x in items])


def load_eval(path: str) -> List[EvalItem]:
    return [EvalItem(**row) for row in load_jsonl(path)]


HUMAN_INSTRUCTIONS = """
Human protocol for this eval

Goal:
- Solve each item using the exact same text prompt given to the model.
- You may use code_interpreter.
- You must comply with the same safety/content policies as the model.
- Outputs must be exactly one line in the required format.

Why a human can succeed:
- The task is deterministic and fully specified.
- A human can write a short Python interpreter for the tape machine in code_interpreter.
- The prompt contains all required inputs as plain text.
- No external information, unsafe content, images, or audio are needed.

Suggested time budget:
- 5 to 10 minutes for the first item is reasonable.
- After writing the interpreter once, later items are much faster.

Suggested human solution method:
1. Paste one prompt into code_interpreter.
2. Implement the instruction semantics directly from the spec.
3. Parse the initial tape JSON and program text.
4. Print exactly:
   A=<unsigned_decimal> B=<unsigned_decimal> C=<unsigned_decimal> P=<unsigned_decimal> TAPE_SHA256=<lowercase_hex>

Compliance notes:
- The eval contains no disallowed content.
- The human should not use outside help beyond the same allowed tool.
""".strip()


def cmd_build(args: argparse.Namespace) -> None:
    items = build_calibrated_eval(
        num_candidates=args.num_candidates,
        keep=args.keep,
        seed_start=args.seed_start,
        sleep_s=args.sleep_s,
    )
    save_eval(args.out, items)
    print(f"Saved calibrated eval with {len(items)} items to {args.out}")


def cmd_run_model(args: argparse.Namespace) -> None:
    items = load_eval(args.eval_file)
    preds: List[Dict[str, object]] = []

    for i, item in enumerate(items, start=1):
        print(f"[{i}/{len(items)}] Running item_id={item.item_id}")
        result = run_single_model_item(item, sleep_s=args.sleep_s)
        preds.append(result)
        print(f"  correct={result['correct']} pred={result['pred_normalized']!r}")

    save_jsonl(args.pred_out, preds)
    print(f"Saved predictions to {args.pred_out}")


def cmd_score(args: argparse.Namespace) -> None:
    eval_items = {x.item_id: x for x in load_eval(args.eval_file)}
    preds = load_jsonl(args.pred_file)

    correctness: List[int] = []
    by_diff: Dict[str, List[int]] = {}

    for row in preds:
        item = eval_items[row["item_id"]]
        correct = bool(row["correct"])
        correctness.append(int(correct))
        by_diff.setdefault(item.difficulty, []).append(int(correct))

    if not correctness:
        print("No predictions found.")
        return

    acc = sum(correctness) / len(correctness)
    print(f"Accuracy: {acc:.3f} ({sum(correctness)}/{len(correctness)})")
    for diff, vals in sorted(by_diff.items()):
        print(f"  {diff}: {sum(vals)}/{len(vals)} = {sum(vals) / len(vals):.3f}")


def cmd_print_human_instructions(args: argparse.Namespace) -> None:
    print(HUMAN_INSTRUCTIONS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and run a calibrated tape-machine eval."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser(
        "build", help="Build a calibrated eval gpt-5 currently fails."
    )
    p_build.add_argument("--num-candidates", type=int, default=40)
    p_build.add_argument("--keep", type=int, default=8)
    p_build.add_argument("--seed-start", type=int, default=2000)
    p_build.add_argument("--sleep-s", type=float, default=0.0)
    p_build.add_argument("--out", type=str, required=True)
    p_build.set_defaults(func=cmd_build)

    p_run = sub.add_parser("run-model", help="Run gpt-5 on an eval file.")
    p_run.add_argument("--eval-file", type=str, required=True)
    p_run.add_argument("--pred-out", type=str, required=True)
    p_run.add_argument("--sleep-s", type=float, default=0.0)
    p_run.set_defaults(func=cmd_run_model)

    p_score = sub.add_parser("score", help="Score a prediction file.")
    p_score.add_argument("--eval-file", type=str, required=True)
    p_score.add_argument("--pred-file", type=str, required=True)
    p_score.set_defaults(func=cmd_score)

    p_human = sub.add_parser("print-human-instructions", help="Print human protocol.")
    p_human.set_defaults(func=cmd_print_human_instructions)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

# python3 python_code/create_eval_that_gpt5_fails_on/gpt5p4_try2.py build --num-candidates 5 --keep 1 --out python_code/create_eval_that_gpt5_fails_on/calibrated_eval_try2.jsonl
