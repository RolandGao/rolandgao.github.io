from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional

from openai import OpenAI


def call_model(input: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )

    print("STATUS:", getattr(response, "status", None))
    print("INCOMPLETE:", getattr(response, "incomplete_details", None))
    print("ERROR:", getattr(response, "error", None))
    print("OUTPUT_TEXT:", repr(response.output_text))

    return response.output_text or ""


VM_SPEC = """
You are solving a deterministic text-only programming puzzle.

You are given a tiny virtual machine. Compute the final machine state exactly.

Machine state:
- Three unsigned 32-bit registers: A, B, C
- A stack of signed integers (initially empty)
- A program counter (starts at instruction 0)
- All arithmetic on registers is modulo 2^32 unless explicitly noted.

Instruction syntax:
- SET X n        ; set register X to integer n modulo 2^32, where X in {A,B,C}
- ADD X Y        ; X := (X + Y) mod 2^32, Y is either integer literal or register
- XOR X Y        ; X := X xor Y, Y is either integer literal or register
- ROL X n        ; rotate-left register X by n mod 32 bits
- PUSH Y         ; push integer Y onto stack, where Y is integer literal or register value interpreted as signed 32-bit
- POP X          ; pop top of stack into register X; if stack is empty, X := 0
- REV k          ; reverse the top k items of the stack; if stack has fewer than k items, reverse entire stack
- MIX            ; let t1 = pop() else 0, t2 = pop() else 0
                 ; A := (A + (t1 mod 2^32)) mod 2^32
                 ; B := B xor (t2 mod 2^32)
                 ; C := rol32(C xor ((t1 * 1103515245 + t2 * 12345) mod 2^32), 7)
- SWAP X Y       ; swap registers X and Y
- JNZ X off      ; if register X != 0, jump relative by off, else continue
                 ; off is a signed integer; jumping is relative to current PC
                 ; after a taken jump, do not add the normal +1
- DEC X          ; X := (X - 1) mod 2^32
- HALT           ; stop execution immediately

Additional rules:
- Execution stops on HALT or after max_steps instructions, whichever comes first.
- Signed 32-bit interpretation:
    to_signed32(v):
        v = v mod 2^32
        if v >= 2^31: v -= 2^32
        return v
- For PUSH of a register, push to_signed32(register_value).
- For ADD/XOR/PUSH operands, integer literals may be negative.
- For JNZ, the tested register value is its unsigned 32-bit stored value.
- There are no labels; jumps use numeric offsets.
- Program lines are indexed starting from 0.

Required output format:
Return exactly one line in this format and nothing else:
A=<unsigned_decimal> B=<unsigned_decimal> C=<unsigned_decimal> STACK_SHA256=<lowercase_hex>

where STACK_SHA256 is the SHA-256 of the final stack serialized as:
json.dumps(stack, separators=(",", ":"))

If you use code_interpreter, still return only that single final line.
Do not include explanations.
""".strip()


MASK32 = 0xFFFFFFFF


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


def stack_sha256(stack: List[int]) -> str:
    payload = json.dumps(stack, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_program(program_text: str, max_steps: int) -> Dict[str, object]:
    regs = {"A": 0, "B": 0, "C": 0}
    stack: List[int] = []
    lines = [ln.strip() for ln in program_text.strip().splitlines() if ln.strip()]
    pc = 0
    steps = 0

    while 0 <= pc < len(lines) and steps < max_steps:
        steps += 1
        parts = lines[pc].split()
        op = parts[0]

        if op == "SET":
            x, n = parts[1], int(parts[2])
            regs[x] = n & MASK32
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
            x, n = parts[1], int(parts[2])
            regs[x] = rol32(regs[x], n)
            pc += 1

        elif op == "PUSH":
            y = parts[1]
            if y in regs:
                stack.append(to_signed32(regs[y]))
            else:
                stack.append(int(y))
            pc += 1

        elif op == "POP":
            x = parts[1]
            regs[x] = (stack.pop() if stack else 0) & MASK32
            pc += 1

        elif op == "REV":
            k = int(parts[1])
            if len(stack) < k:
                stack.reverse()
            else:
                stack[-k:] = reversed(stack[-k:])
            pc += 1

        elif op == "MIX":
            t1 = stack.pop() if stack else 0
            t2 = stack.pop() if stack else 0
            regs["A"] = (regs["A"] + (t1 & MASK32)) & MASK32
            regs["B"] = (regs["B"] ^ (t2 & MASK32)) & MASK32
            mix_term = ((t1 * 1103515245) + (t2 * 12345)) & MASK32
            regs["C"] = rol32(regs["C"] ^ mix_term, 7)
            pc += 1

        elif op == "SWAP":
            x, y = parts[1], parts[2]
            regs[x], regs[y] = regs[y], regs[x]
            pc += 1

        elif op == "JNZ":
            x, off = parts[1], int(parts[2])
            if regs[x] != 0:
                pc = pc + off
            else:
                pc += 1

        elif op == "DEC":
            x = parts[1]
            regs[x] = (regs[x] - 1) & MASK32
            pc += 1

        elif op == "HALT":
            break

        else:
            raise ValueError(f"Unknown instruction: {op}")

    return {
        "A": regs["A"],
        "B": regs["B"],
        "C": regs["C"],
        "stack": stack,
        "stack_sha256": stack_sha256(stack),
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


REGS = ["A", "B", "C"]


def rand_lit(rng: random.Random) -> int:
    choices = [
        rng.randint(-10, 10),
        rng.randint(-1000, 1000),
        rng.randint(-(2**31), 2**31 - 1),
    ]
    return rng.choice(choices)


def rand_reg(rng: random.Random) -> str:
    return rng.choice(REGS)


def rand_reg_or_lit(rng: random.Random) -> str:
    if rng.random() < 0.45:
        return rand_reg(rng)
    return str(rand_lit(rng))


def generate_candidate_program(
    seed: int, target_len: int = 26
) -> Tuple[str, int, Dict[str, object]]:
    rng = random.Random(seed)
    lines: List[str] = []

    init_a = rng.randint(0, MASK32)
    init_b = rng.randint(0, MASK32)
    init_c = rng.randint(0, MASK32)
    loop1 = rng.randint(2, 6)
    loop2 = rng.randint(2, 5)

    lines.append(f"SET A {init_a}")
    lines.append(f"SET B {init_b}")
    lines.append(f"SET C {init_c}")
    lines.append(f"PUSH {rand_lit(rng)}")
    lines.append(f"PUSH {rand_lit(rng)}")
    lines.append("MIX")

    lines.append(f"SET A {loop1}")
    loop1_start = len(lines)
    lines.append(f"XOR B {rand_reg_or_lit(rng)}")
    lines.append(f"ROL C {rng.randint(1, 31)}")
    lines.append(f"PUSH {rand_reg_or_lit(rng)}")
    if rng.random() < 0.65:
        lines.append(f"PUSH {rand_reg_or_lit(rng)}")
        lines.append("MIX")
    if rng.random() < 0.5:
        lines.append(f"REV {rng.randint(2, 5)}")
    lines.append("DEC A")
    lines.append(f"JNZ A {loop1_start - len(lines)}")

    mid_ops = rng.randint(5, 10)
    for _ in range(mid_ops):
        op = rng.choice(["ADD", "XOR", "ROL", "PUSH", "POP", "SWAP", "REV", "MIX"])
        if op == "ADD":
            lines.append(f"ADD {rand_reg(rng)} {rand_reg_or_lit(rng)}")
        elif op == "XOR":
            lines.append(f"XOR {rand_reg(rng)} {rand_reg_or_lit(rng)}")
        elif op == "ROL":
            lines.append(f"ROL {rand_reg(rng)} {rng.randint(1, 31)}")
        elif op == "PUSH":
            lines.append(f"PUSH {rand_reg_or_lit(rng)}")
        elif op == "POP":
            lines.append(f"POP {rand_reg(rng)}")
        elif op == "SWAP":
            x, y = rng.sample(REGS, 2)
            lines.append(f"SWAP {x} {y}")
        elif op == "REV":
            lines.append(f"REV {rng.randint(2, 7)}")
        elif op == "MIX":
            lines.append("MIX")

    lines.append(f"SET B {loop2}")
    loop2_start = len(lines)
    lines.append(f"ADD C {rand_reg_or_lit(rng)}")
    lines.append(f"XOR A {rand_reg_or_lit(rng)}")
    if rng.random() < 0.7:
        lines.append(f"PUSH {rand_reg_or_lit(rng)}")
    if rng.random() < 0.7:
        lines.append("MIX")
    lines.append("DEC B")
    lines.append(f"JNZ B {loop2_start - len(lines)}")

    while len(lines) < target_len - 1:
        op = rng.choice(["ADD", "XOR", "ROL", "PUSH", "POP", "REV", "MIX", "SWAP"])
        if op == "ADD":
            lines.append(f"ADD {rand_reg(rng)} {rand_reg_or_lit(rng)}")
        elif op == "XOR":
            lines.append(f"XOR {rand_reg(rng)} {rand_reg_or_lit(rng)}")
        elif op == "ROL":
            lines.append(f"ROL {rand_reg(rng)} {rng.randint(1, 31)}")
        elif op == "PUSH":
            lines.append(f"PUSH {rand_reg_or_lit(rng)}")
        elif op == "POP":
            lines.append(f"POP {rand_reg(rng)}")
        elif op == "REV":
            lines.append(f"REV {rng.randint(2, 8)}")
        elif op == "MIX":
            lines.append("MIX")
        else:
            x, y = rng.sample(REGS, 2)
            lines.append(f"SWAP {x} {y}")

    lines.append("HALT")

    max_steps = rng.randint(80, 220)
    program = "\n".join(lines)

    meta = {
        "program_len": len(lines),
        "init_a": init_a,
        "init_b": init_b,
        "init_c": init_c,
        "loop1": loop1,
        "loop2": loop2,
    }
    return program, max_steps, meta


def answer_string(result: Dict[str, object]) -> str:
    return (
        f"A={result['A']} "
        f"B={result['B']} "
        f"C={result['C']} "
        f"STACK_SHA256={result['stack_sha256']}"
    )


def make_prompt(program: str, max_steps: int) -> str:
    return f"{VM_SPEC}\n\nmax_steps = {max_steps}\n\nProgram:\n{program}\n"


def generate_eval_item(seed: int) -> EvalItem:
    program, max_steps, meta = generate_candidate_program(seed)
    result = run_program(program, max_steps)
    ans = answer_string(result)

    difficulty = "medium"
    if meta["program_len"] >= 30 or (meta["loop1"] + meta["loop2"] >= 9):
        difficulty = "hard"

    item_id = hashlib.sha256(f"{seed}|{ans}".encode()).hexdigest()[:16]
    prompt = make_prompt(program, max_steps)

    return EvalItem(
        item_id=item_id,
        seed=seed,
        max_steps=max_steps,
        difficulty=difficulty,
        prompt=prompt,
        answer=ans,
        metadata={
            **meta,
            "reference_steps": result["steps"],
            "final_stack_len": len(result["stack"]),
        },
    )


ANSWER_RE = re.compile(
    r"A=(\d+)\s+B=(\d+)\s+C=(\d+)\s+STACK_SHA256=([0-9a-f]{64})",
    re.IGNORECASE,
)


def normalize_model_answer(text: str) -> Optional[str]:
    if not text:
        return None

    text = text.strip()
    m = ANSWER_RE.search(text)
    if not m:
        print("Could not parse model output:", repr(text))
        return None

    a, b, c, sha = m.groups()
    return f"A={int(a)} B={int(b)} C={int(c)} STACK_SHA256={sha.lower()}"


def score_prediction(gold: str, pred_text: str) -> Dict[str, object]:
    pred = normalize_model_answer(pred_text)
    correct = pred == gold
    return {
        "correct": correct,
        "gold": gold,
        "pred_normalized": pred,
        "raw_pred": pred_text,
    }


def run_single_model_item(item: EvalItem, sleep_s: float = 0.0) -> Dict[str, object]:
    if sleep_s > 0:
        time.sleep(sleep_s)

    raw = call_model(item.prompt)
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
    seed_start: int = 1000,
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

        checked = i
        if checked >= 20 and len(kept) == 0:
            print("Stopping early: no failed items found in first 20 candidates.")
            break

    return kept


def save_jsonl(path: str, rows: List[Dict[str, object]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_jsonl(path: str) -> List[Dict[str, object]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def save_eval(path: str, items: List[EvalItem]) -> None:
    rows = [asdict(x) for x in items]
    save_jsonl(path, rows)


def load_eval(path: str) -> List[EvalItem]:
    rows = load_jsonl(path)
    return [EvalItem(**row) for row in rows]


HUMAN_INSTRUCTIONS = """
Human protocol for this eval

Goal:
- Solve each item using the exact same text prompt given to the model.
- You may use code_interpreter.
- You must comply with the same safety/content policies as the model.
- Outputs must be exactly one line in the required format.

Why a human can succeed:
- The problem is deterministic and fully specified.
- A human can write a short interpreter in Python inside code_interpreter, paste in
  the program, and compute the exact answer.
- No external tools, images, audio, copyrighted text reproduction, or unsafe content
  are needed.

Suggested time budget:
- 5 to 10 minutes per item is reasonable for a careful human on first exposure.
- After writing the interpreter once, later items are much faster.

Suggested human solution method:
1. Paste the VM spec and one program into code_interpreter.
2. Implement the interpreter directly from the spec.
3. Print:
   A=<unsigned_decimal> B=<unsigned_decimal> C=<unsigned_decimal> STACK_SHA256=<lowercase_hex>

Compliance notes:
- The task contains no disallowed content.
- The human should not use outside assistance beyond the same allowed tool.
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

    correctness = []
    by_diff: Dict[str, List[int]] = {}

    for row in preds:
        item_id = row["item_id"]
        item = eval_items[item_id]
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
    p = argparse.ArgumentParser(description="Build and run a calibrated VM eval.")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser(
        "build", help="Build a calibrated eval gpt-5 currently fails."
    )
    p_build.add_argument("--num-candidates", type=int, default=40)
    p_build.add_argument("--keep", type=int, default=8)
    p_build.add_argument("--seed-start", type=int, default=1000)
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

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

# pip install openai
# export OPENAI_API_KEY="your_api_key_here"
# python gpt5p4.py build --num-candidates 20 --keep 5 --out calibrated_eval.jsonl
# python gpt5p4.py run-model --eval-file calibrated_eval.jsonl --pred-out model_preds.jsonl
# python gpt5p4.py score --eval-file calibrated_eval.jsonl --pred-file model_preds.jsonl
# python gpt5p4.py print-human-instructions
