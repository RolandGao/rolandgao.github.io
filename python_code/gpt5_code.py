#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LLM Eval: Long-Range Counting & Tiny Stack Machine (text-only)

Design goals (per user constraints):
1) Model under test (default: gpt-5) is likely to fail:
   - Tasks stress precise long-range state tracking and arithmetic.
   - Strict answer formatting; no partial credit; no reasoning text allowed.

2) At least one careful human can succeed under the same inputs/time/compute:
   - A human can do bracket checking and basic stack ops by hand.
   - Inputs sized so a diligent human could finish the default small batch.

3) Human must also comply with safety/content policies:
   - Prompts are harmless, no disallowed content, no jailbreak ploys.
   - We explicitly forbid chain-of-thought and request final answers only.

4) Input is text only (no images/audio). Output is a short, deterministic string.

Usage:
  python eval_llm_textonly.py --model gpt-5 --n 40 --seed 7 --max_tokens 64

Requires:
  pip install openai (>=1.0.0)

Environment:
  export OPENAI_API_KEY=sk-...
"""

import argparse
import random
import time
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional, Literal

try:
    # OpenAI python client v1+
    from openai import OpenAI
except Exception as e:
    print(
        "Missing or incompatible 'openai' package. Run: pip install openai",
        file=sys.stderr,
    )
    raise

# -----------------------------
# Problem Type A: Deep Brackets
# -----------------------------

BRACKETS = {
    "(": ")",
    "[": "]",
    "{": "}",
}
OPENERS = set(BRACKETS.keys())
CLOSERS = set(BRACKETS.values())


@dataclass
class BracketSample:
    text: str
    # If valid: ("OK", max_depth); else ("ERR", first_bad_index)
    solution_type: Literal["OK", "ERR"]
    solution_value: int


def _solve_brackets(s: str) -> Tuple[str, int]:
    """
    Returns:
      ("OK", max_depth) if balanced
      ("ERR", index) index is 1-based of first error
    """
    stack = []
    max_depth = 0
    for i, ch in enumerate(s, start=1):
        if ch in OPENERS:
            stack.append(ch)
            if len(stack) > max_depth:
                max_depth = len(stack)
        elif ch in CLOSERS:
            if not stack:
                return ("ERR", i)
            top = stack.pop()
            if BRACKETS[top] != ch:
                return ("ERR", i)
        else:
            # shouldn't happen
            return ("ERR", i)
    if stack:
        # first error is "end of string" where more closers needed;
        # define error as position len(s)+1
        return ("ERR", len(s) + 1)
    return ("OK", max_depth)


def _inject_error(s: str, rng: random.Random) -> str:
    """
    Introduce a single-character error to create a first-bad-index that
    is not trivially at the beginning or end.
    """
    idx = rng.randrange(len(s))
    ch = s[idx]
    # Flip bracket to a mismatched counterpart
    all_brackets = list(OPENERS | CLOSERS)
    choices = [c for c in all_brackets if c != ch]
    new_ch = rng.choice(choices)
    return s[:idx] + new_ch + s[idx + 1 :]


def generate_bracket_string(
    rng: random.Random, length: int, valid_prob: float = 0.5
) -> BracketSample:
    """
    Generate a bracket string of exact length with roughly half valid cases.
    Start from a valid-ish backbone, then optionally inject an error.
    """
    # Build a valid sequence by random pushing and sometimes closing:
    s = []
    stack = []
    while len(s) < length:
        # If stack is deep, close; otherwise random choice.
        if len(stack) > 0 and (len(s) > length * 0.6 or rng.random() < 0.45):
            # close
            opener = stack.pop()
            s.append(BRACKETS[opener])
        else:
            # open
            opener = rng.choice(list(OPENERS))
            s.append(opener)
            stack.append(opener)
    # Clean up: if still openings remain, close some (may push length over, so trim).
    while stack and len(s) < length:
        opener = stack.pop()
        s.append(BRACKETS[opener])
    s = s[:length]
    text = "".join(s)
    sol_type, sol_val = _solve_brackets(text)
    if sol_type == "OK" and rng.random() > valid_prob:
        # force a single error
        text = _inject_error(text, rng)
        sol_type, sol_val = _solve_brackets(text)
    elif sol_type == "ERR" and rng.random() < valid_prob:
        # try to regenerate until OK
        for _ in range(10):
            text2 = generate_bracket_string(rng, length, valid_prob=1.0).text
            sol_type2, sol_val2 = _solve_brackets(text2)
            if sol_type2 == "OK":
                text = text2
                sol_type, sol_val = sol_type2, sol_val2
                break
    return BracketSample(text=text, solution_type=sol_type, solution_value=sol_val)


# --------------------------------
# Problem Type B: Tiny Stack Machine
# --------------------------------


@dataclass
class StackSample:
    program: List[str]
    solution: List[int]  # final stack (bottom ... top)


STACK_OPS = ("PUSH", "POP", "DUP", "SWAP", "ROT", "ADD", "MUL", "MOD97")


def run_tiny_stack(prog: List[str]) -> List[int]:
    """
    Executes the tiny stack program deterministically.
    Stack bottom is at index 0; top is at the end.
    If an operation is invalid (e.g., POP on empty), the program is invalid:
    define result as the string 'ERROR' by raising ValueError.
    """
    st: List[int] = []
    for pc, line in enumerate(prog):
        parts = line.strip().split()
        if not parts:
            continue
        op = parts[0]
        if op == "PUSH":
            if len(parts) != 2:
                raise ValueError(f"Bad PUSH at line {pc}")
            try:
                x = int(parts[1])
            except:
                raise ValueError(f"Bad integer at line {pc}")
            st.append(x)
        elif op == "POP":
            if not st:
                raise ValueError(f"POP on empty at line {pc}")
            st.pop()
        elif op == "DUP":
            if not st:
                raise ValueError(f"DUP on empty at line {pc}")
            st.append(st[-1])
        elif op == "SWAP":
            if len(st) < 2:
                raise ValueError(f"SWAP needs 2 at line {pc}")
            st[-1], st[-2] = st[-2], st[-1]
        elif op == "ROT":
            # rotate top 3: (a b c) -> (b c a) where c is top
            if len(st) < 3:
                raise ValueError(f"ROT needs 3 at line {pc}")
            a = st[-3]
            b = st[-2]
            c = st[-1]
            st[-3], st[-2], st[-1] = b, c, a
        elif op == "ADD":
            if len(st) < 2:
                raise ValueError(f"ADD needs 2 at line {pc}")
            b = st.pop()
            a = st.pop()
            st.append(a + b)
        elif op == "MUL":
            if len(st) < 2:
                raise ValueError(f"MUL needs 2 at line {pc}")
            b = st.pop()
            a = st.pop()
            st.append(a * b)
        elif op == "MOD97":
            if not st:
                raise ValueError(f"MOD97 on empty at line {pc}")
            st[-1] = st[-1] % 97
        else:
            raise ValueError(f"Unknown op '{op}' at line {pc}")
    return st


def generate_stack_program(rng: random.Random, length: int) -> StackSample:
    """
    Create a valid program (no runtime errors), so the spec stays simple for humans.
    """
    prog: List[str] = []
    st_depth = 0

    def ensure_depth(n: int):
        nonlocal st_depth, prog
        while st_depth < n:
            prog.append(f"PUSH {rng.randint(0, 999)}")
            st_depth += 1

    for _ in range(length):
        op_choice = rng.random()
        if op_choice < 0.35:
            # PUSH more often to grow entropy
            val = rng.randint(0, 999)
            prog.append(f"PUSH {val}")
            st_depth += 1
        elif op_choice < 0.50:
            ensure_depth(1)
            prog.append("DUP")
            st_depth += 1
        elif op_choice < 0.60:
            ensure_depth(2)
            prog.append("SWAP")
        elif op_choice < 0.70:
            ensure_depth(3)
            prog.append("ROT")
        elif op_choice < 0.82:
            ensure_depth(2)
            prog.append("ADD")
            st_depth -= 1
        elif op_choice < 0.94:
            ensure_depth(2)
            prog.append("MUL")
            st_depth -= 1
        else:
            ensure_depth(1)
            prog.append("MOD97")

    # Guarantee not empty at the end
    if st_depth == 0:
        prog.append(f"PUSH {rng.randint(0, 999)}")
        st_depth += 1

    final_stack = run_tiny_stack(prog)
    return StackSample(program=prog, solution=final_stack)


# -------------------------
# Prompting for the LLM
# -------------------------

SYSTEM_PROMPT = """You are taking a strict text-only evaluation.
Follow the task instructions exactly.
Do NOT include any reasoning or explanations.
Output only the final answer in the exact format specified.
No additional text, punctuation, or commentary.
"""


def make_bracket_user_prompt(sample: BracketSample) -> str:
    return (
        "TASK: Deep Brackets\n"
        "You are given a string S of brackets consisting only of the characters ()[]{}.\n"
        "If S is perfectly balanced, print exactly: OK <max_depth>\n"
        "  where <max_depth> is the maximum nesting depth as a nonnegative integer.\n"
        "If S is NOT balanced, print exactly: ERR <index>\n"
        "  where <index> is the 1-based position of the first error.\n"
        "No extra words. No explanations. One line only.\n\n"
        f"S = {sample.text}\n"
        "Answer:"
    )


def make_stack_user_prompt(sample: StackSample) -> str:
    program_text = "\n".join(sample.program)
    return (
        "TASK: TinyStack\n"
        "We execute a tiny stack language with the following instructions.\n"
        "Stack bottom is on the left; top is on the right.\n"
        "Instructions (one per line):\n"
        "  - PUSH X   (push integer X onto the stack)\n"
        "  - POP      (remove top element)\n"
        "  - DUP      (duplicate top element)\n"
        "  - SWAP     (swap top two elements)\n"
        "  - ROT      (rotate top 3: (a b c) -> (b c a))\n"
        "  - ADD      (pop two, push their sum)\n"
        "  - MUL      (pop two, push their product)\n"
        "  - MOD97    (replace top with top % 97)\n"
        "All programs here are valid (no errors). Execute exactly.\n"
        "Output format: one line with the final stack values from bottom to top, separated by single spaces.\n"
        "No extra words. No explanations.\n\n"
        "Program:\n"
        f"{program_text}\n"
        "Answer:"
    )


# -------------------------
# OpenAI API wrapper
# -------------------------


def call_model(
    client: OpenAI,
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 32,
    timeout: float = 60.0,
) -> str:
    """
    Calls the chat.completions API with deterministic settings.
    """
    start = time.time()
    resp = client.chat.completions.create(
        model=model,
        temperature=0,
        top_p=1,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    dur = time.time() - start
    text = (resp.choices[0].message.content or "").strip()
    return text


# -------------------------
# Scoring
# -------------------------


def score_bracket_answer(sample: BracketSample, answer: str) -> bool:
    # Must be exactly "OK <int>" or "ERR <int>"
    parts = answer.strip().split()
    if len(parts) != 2:
        return False
    tag, val = parts[0], parts[1]
    if tag not in ("OK", "ERR"):
        return False
    try:
        ival = int(val)
    except:
        return False
    return (tag == sample.solution_type) and (ival == sample.solution_value)


def score_stack_answer(sample: StackSample, answer: str) -> bool:
    # Must be exactly space-separated integers, matching final stack
    parts = answer.strip().split()
    # Accept empty stack as blank line (but we always ensure non-empty)
    try:
        predicted = [int(p) for p in parts] if parts else []
    except:
        return False
    return predicted == sample.solution


# -------------------------
# Dataset generation
# -------------------------


@dataclass
class Item:
    kind: Literal["brackets", "stack"]
    prompt: str
    solution_text: str


def generate_dataset(n: int, rng: random.Random) -> List[Item]:
    items: List[Item] = []
    for i in range(n):
        if rng.random() < 0.5:
            # Brackets: length chosen to be challenging but still human-feasible
            # length = rng.randint(350, 650)  # characters
            length = rng.randint(4, 6)
            bs = generate_bracket_string(rng, length, valid_prob=0.5)
            prompt = make_bracket_user_prompt(bs)
            gold = f"{bs.solution_type} {bs.solution_value}"
            items.append(Item(kind="brackets", prompt=prompt, solution_text=gold))
        else:
            # TinyStack: 150–400 instructions
            prog_len = rng.randint(150, 400)
            ss = generate_stack_program(rng, prog_len)
            prompt = make_stack_user_prompt(ss)
            gold = " ".join(str(x) for x in ss.solution)
            items.append(Item(kind="stack", prompt=prompt, solution_text=gold))
    return items


# -------------------------
# Main harness
# -------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--model", type=str, default="gpt-5", help="OpenAI model name to evaluate"
    )
    ap.add_argument("--n", type=int, default=1, help="Number of items")
    ap.add_argument("--seed", type=int, default=12345, help="Random seed")
    ap.add_argument(
        "--max_tokens", type=int, default=64, help="Max tokens for model answer"
    )
    ap.add_argument(
        "--per_item_timeout",
        type=float,
        default=60.0,
        help="Timeout budget per item (seconds), for parity with a human reading/thinking window",
    )
    ap.add_argument(
        "--print_failures",
        action="store_true",
        help="Print failing cases for inspection",
    )
    args = ap.parse_args()

    rng = random.Random(args.seed)
    dataset = generate_dataset(args.n, rng)

    client = OpenAI()

    num_correct = 0
    num_total = len(dataset)

    print(f"Evaluating model={args.model} on {num_total} items...")
    print("-" * 60)

    for idx, item in enumerate(dataset, start=1):
        try:
            ans = call_model(
                client=client,
                model=args.model,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=item.prompt,
                max_tokens=args.max_tokens,
                timeout=args.per_item_timeout,
            )
        except Exception as e:
            ans = ""
            if args.print_failures:
                print(f"[{idx}] API error: {e}", file=sys.stderr)

        # Score
        ok = False
        if item.kind == "brackets":
            # Recompute gold to be safe
            # (already in item.solution_text)
            parts = item.solution_text.split()
            # sanity
            if len(parts) == 2 and parts[0] in ("OK", "ERR"):
                try:
                    ok = score_bracket_answer(
                        BracketSample(
                            text="",
                            solution_type=parts[0],  # type: ignore
                            solution_value=int(parts[1]),
                        ),
                        ans,
                    )
                except:
                    ok = False
        else:
            gold_list = (
                [int(x) for x in item.solution_text.split()]
                if item.solution_text.strip()
                else []
            )
            ok = score_stack_answer(StackSample(program=[], solution=gold_list), ans)

        num_correct += 1 if ok else 0

        status = "✓" if ok else "✗"
        print(
            f"[{idx:03d}] {item.kind:9s}  {status}  ->  model: {ans!r}   gold: {item.solution_text!r}"
        )
        if (not ok) and args.print_failures:
            print("---- PROMPT BEGIN ----")
            print(item.prompt)
            print("---- PROMPT END ----")

    acc = num_correct / max(1, num_total)
    print("-" * 60)
    print(f"Score: {num_correct}/{num_total} = {acc:.3f}")
    # Simple pass/fail threshold. A careful human can achieve ~1.0 on small N.
    # The bar is high to make it a meaningful eval.
    pass_threshold = 0.95
    if acc >= pass_threshold:
        print("RESULT: PASS")
    else:
        print("RESULT: FAIL")


if __name__ == "__main__":
    main()
