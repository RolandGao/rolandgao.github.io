#!/usr/bin/env python3
"""Run this file to evaluate GPT-5 with Code Interpreter. No CLI arguments.

Setup once:
    python -m pip install openai
    Set the OPENAI_API_KEY environment variable to your API key.

Run:
    python sequence_transfer_eval.py

The default run makes six model calls and scores 36 individual answers. It
prints per-problem scores and final RIGHT / WRONG / UNSCORED totals. API errors,
timeouts, and incomplete API responses are unscored; malformed final answers
count as wrong and are identified separately. No additional files are needed
or written. Adjust the constants below only if you want a different run size.
Each problem is an independent request containing only its own prompt text.
Previous responses, reasoning items, and Code Interpreter records are never
replayed as API input. API errors include the server's diagnostic message.

The benchmark tests compositional rule discovery and transfer. Every answer
is checked for agreement across all rules consistent with the examples.
A fixed seed keeps the problems reproducible, but model outputs may vary.
This measures GPT-5 performance; it does not establish that experts do better
or guarantee that GPT-5 fails. That would require actual human/model trials.

API reference:
    https://developers.openai.com/api/docs/guides/tools-code-interpreter
    https://developers.openai.com/api/docs/guides/conversation-state
"""

from __future__ import annotations

import itertools
import json
import multiprocessing as mp
import os
import random
import re
import sys
import time
from collections import Counter
from functools import lru_cache
from unittest.mock import patch

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


# Configuration lives here; running the file does not require arguments.
RANDOM_SEED = "sequence-transfer-v1"
CONFIG = {
    "problems": 6,
    "queries": 6,
    "seconds_per_problem": 900,
    "max_program_length": 4,
}


# The requested model function, with its request unchanged.
def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


RULES = [
    ("reverse", "Reverse the entire sequence."),
    ("left", "Move the first symbol to the end; empty stays empty."),
    ("right", "Move the last symbol to the front; empty stays empty."),
    ("odd", "Keep positions 1, 3, 5, ... (positions start at 1)."),
    ("even", "Keep positions 2, 4, 6, ... (positions start at 1)."),
    ("first", "Keep only the first occurrence of each distinct symbol, in order."),
    ("last", "Keep only the last occurrence of each distinct symbol, in order."),
    ("squeeze", "Replace each maximal consecutive run of equal symbols by one symbol."),
    ("repeated", "Keep every occurrence of symbols whose total count is at least two."),
    ("single", "Keep only symbols whose total count is exactly one."),
    (
        "frequency",
        "Group all equal symbols together, most frequent group first; "
        "tie-break groups by their first appearance in the input to this operation.",
    ),
    ("pairs", "Swap positions 1 and 2, 3 and 4, ...; an unpaired last symbol stays."),
    (
        "cancel",
        "Scan left to right with an initially empty stack. If the next symbol "
        "equals the stack top, pop; otherwise push. Output the final stack bottom to top.",
    ),
    (
        "longest",
        "Keep only the longest maximal consecutive run of equal symbols; "
        "choose the first run on ties. Empty stays empty.",
    ),
    (
        "ends",
        "Read alternately from the left and right ends: first, last, second, "
        "next-to-last, ... until every position has been used once.",
    ),
    ("double", "Replace every symbol by two consecutive copies of itself."),
]


def transform(op: int, s: str) -> str:
    if op == 0:
        return s[::-1]
    if op == 1:
        return s[1:] + s[:1]
    if op == 2:
        return s[-1:] + s[:-1]
    if op == 3:
        return s[::2]
    if op == 4:
        return s[1::2]
    if op == 5:
        return "".join(dict.fromkeys(s))
    if op == 6:
        return "".join(dict.fromkeys(s[::-1]))[::-1]
    if op == 7:
        return "".join(k for k, _ in itertools.groupby(s))
    if op in (8, 9, 10):
        counts = Counter(s)
        if op == 8:
            return "".join(c for c in s if counts[c] >= 2)
        if op == 9:
            return "".join(c for c in s if counts[c] == 1)
        return "".join(
            c * counts[c] for c in sorted(dict.fromkeys(s), key=lambda c: -counts[c])
        )
    if op == 11:
        return "".join(s[i : i + 2][::-1] for i in range(0, len(s), 2))
    if op == 12:
        stack = []
        for c in s:
            if stack and stack[-1] == c:
                stack.pop()
            else:
                stack.append(c)
        return "".join(stack)
    if op == 13:
        runs = ["".join(g) for _, g in itertools.groupby(s)]
        return max(runs, key=len, default="")
    if op == 14:
        out, lo, hi = [], 0, len(s) - 1
        while lo <= hi:
            out.append(s[lo])
            if lo < hi:
                out.append(s[hi])
            lo, hi = lo + 1, hi - 1
        return "".join(out)
    if op == 15:
        return "".join(c * 2 for c in s)
    raise ValueError("Unknown operation")


def execute(program, s):
    for op in program:
        s = transform(op, s)
    return s


@lru_cache(maxsize=2)
def programs(depth):
    return tuple(
        p
        for n in range(depth + 1)
        for p in itertools.product(range(len(RULES)), repeat=n)
    )


def canonical(s):
    mapping = {}
    return tuple(mapping.setdefault(c, len(mapping)) for c in s)


def random_sequence(rng, low, high):
    # Both independent symbols and clustered repeats are represented.
    out = ""
    for _ in range(rng.randint(low, high)):
        out += out[-1] if out and rng.random() < 0.30 else rng.choice("ABCD")
    return out


def make_problem(rng, number, config):
    depth, n_queries = config["max_program_length"], config["queries"]
    for _attempt in range(300):
        secret = tuple(rng.randrange(len(RULES)) for _ in range(depth))
        examples, seen = [], set()
        while len(examples) < 10:
            s = random_sequence(rng, 4, 9)
            if canonical(s) not in seen:
                seen.add(canonical(s))
                examples.append([s, execute(secret, s)])
        ys = [y for _, y in examples]
        if len(set(ys)) < 5 or sum(len(set(y)) >= 2 for y in ys) < 5:
            continue
        if max(map(len, ys)) > 40:
            continue
        survivors = [
            p for p in programs(depth) if all(execute(p, x) == y for x, y in examples)
        ]
        # Reject accidental simplifications: the demonstrations actually require
        # composition of the advertised maximum number of primitive operations.
        if any(len(p) < depth for p in survivors):
            continue
        queries, answers = [], []
        for _ in range(400):
            x = random_sequence(rng, 10, 15)
            if canonical(x) in seen:
                continue
            y = execute(secret, x)
            if not 2 <= len(y) <= 40 or len(set(y)) < 2 or y in answers:
                continue
            if not all(execute(p, x) == y for p in survivors):
                continue
            seen.add(canonical(x))
            queries.append(x)
            answers.append(y)
            if len(queries) == n_queries:
                break
        if len(queries) != n_queries:
            continue
        # Rename all query symbols bijectively. No primitive depends on spelling.
        renamed = rng.sample(list("WXYZ"), 4)
        table = str.maketrans(dict(zip("ABCD", renamed)))
        problem = {
            "id": f"T{number:02d}",
            "examples": examples,
            "queries": [s.translate(table) for s in queries],
            "answers": [s.translate(table) for s in answers],
            "program": list(secret),
            "consistent_programs": len(survivors),
        }
        problem["prompt"] = make_prompt(problem, config)
        return problem
    raise RuntimeError(
        "Could not generate an unambiguous problem; no model calls were made."
    )


def make_prompt(problem, config):
    definitions = "\n".join(f"- {name}: {meaning}" for name, meaning in RULES)
    return f"""SEQUENCE TRANSFER / {problem["id"]}
You have {config["seconds_per_problem"]} seconds for this problem, including
reading, reasoning, code execution, and submitting the final answer.
Your only external tool is OpenAI Code Interpreter, using an auto container.
Use it to check your reasoning. Submit self-contained Python when using code.
Do not browse, use other models, obtain help, or inspect benchmark source or keys.
Comply with the applicable GPT-5 safety and content policies. Work only in text:
no images, plots, audio, or generated files as answers. These are abstract symbols.

An unknown machine applies a fixed sequence of ZERO to
{config["max_program_length"]} operations from the list below. An operation may
repeat. Apply operations in sequence; each sees the previous operation's output.
Every string consists of individual symbols, so ABB means A, then B, then B.
An empty string is written "". Symbol spellings carry no meaning or ordering.
There are NO other operations, parameters, lookups, branches, or exceptions.

OPERATIONS
{definitions}

All examples are exact. For every query, ALL machines in this specified rule
language that fit ALL examples give the SAME answer. You do not need to identify
one unique machine or explain it. You may use any reasoning or code strategy.
The query symbols are renamed and the queries are longer; the same rules apply.

EXAMPLES (JSON pairs [input, output])
{json.dumps(problem["examples"], indent=2)}

QUERIES, IN ORDER
{json.dumps(problem["queries"])}

Return one JSON object with an "answers" array containing exactly
{config["queries"]} output strings, in query order. Put your final answer last.
Whitespace and letter case within answers are ignored. Each correct sequence
earns one point. Every prediction is scored separately.
Do not return operation names in place of output sequences.
"""


def parse_answers(text, count):
    """Accept the last suitable JSON object/array; never execute model text."""
    decoder, candidates = json.JSONDecoder(), []
    for match in re.finditer(r"[\[{]", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except (ValueError, RecursionError):
            continue
        if isinstance(value, dict):
            value = value.get("answers")
        if not isinstance(value, list) or len(value) != count:
            continue
        if not all(isinstance(v, str) for v in value):
            continue
        normalized = [re.sub(r"\s+", "", v).upper() for v in value]
        if all(re.fullmatch(r"[A-Z]*", v) for v in normalized):
            candidates.append(normalized)
    return candidates[-1] if candidates else None


def capture_call(prompt):
    """Observe SDK metadata without changing call_model or its model request."""
    if not isinstance(prompt, str):
        raise TypeError(
            "Each evaluation request must contain one problem's prompt text."
        )
    from openai.resources.responses import Responses

    observed = []
    original = Responses.create

    def tapped(resource, *args, **kwargs):
        response = original(resource, *args, **kwargs)
        observed.append(response)
        return response

    with patch.object(Responses, "create", tapped):
        answer = call_model(prompt)
    if len(observed) != 1:
        raise RuntimeError("Expected exactly one Responses.create call.")
    response = observed[0]
    data = response.model_dump(mode="json")
    return {
        "answer": answer,
        "response_status": data.get("status"),
        "response_id": data.get("id"),
        "resolved_model": data.get("model"),
        "usage": data.get("usage"),
        "incomplete_details": data.get("incomplete_details"),
    }


def error_details(exc):
    """Keep useful API diagnostics without printing credentials or headers."""
    body = getattr(exc, "body", None)
    if isinstance(body, dict) and isinstance(body.get("error"), dict):
        body = body["error"]
    message = body.get("message") if isinstance(body, dict) else None
    message = str(message or getattr(exc, "message", None) or str(exc))
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        message = message.replace(key, "[REDACTED]")
    message = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", message)
    return {
        "status": "api_error",
        "error_type": type(exc).__name__,
        "status_code": getattr(exc, "status_code", None),
        "error_message": message[:2000],
        "request_id": getattr(exc, "request_id", None),
    }


def api_worker(connection, prompt):
    try:
        result = capture_call(prompt)
        result["status"] = (
            "completed"
            if result["response_status"] == "completed"
            else "incomplete_response"
        )
        connection.send(result)
    except Exception as exc:
        connection.send(error_details(exc))
    finally:
        connection.close()


def timed_model(prompt, seconds):
    started = time.monotonic()
    context = mp.get_context("spawn")
    receiving, sending = context.Pipe(duplex=False)
    process = context.Process(target=api_worker, args=(sending, prompt))
    process.start()
    sending.close()
    try:
        remaining = max(0, seconds - (time.monotonic() - started))
        if receiving.poll(remaining):
            try:
                result = receiving.recv()
            except EOFError:
                result = {"status": "worker_error"}
        else:
            # Stopping the local waiter may not stop server computation/billing.
            result = {"status": "timeout"}
        result["elapsed_seconds"] = time.monotonic() - started
        if result["elapsed_seconds"] > seconds:
            result["status"] = "timeout"
        return result
    finally:
        receiving.close()
        process.join(timeout=0.2)
        if process.is_alive():
            process.terminate()
            process.join(timeout=2)
        if process.is_alive():
            process.kill()
            process.join()


def require_api():
    if OpenAI is None:
        raise RuntimeError("Install the dependency with: python -m pip install openai")
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY before running this file.")


def score_response(record, problem):
    """Score model output; transport failures never count as wrong answers."""
    count = len(problem["answers"])
    if record.get("status") != "completed":
        return {"right": 0, "wrong": 0, "unscored": count, "format_errors": 0}
    predicted = parse_answers(record.get("answer", ""), count)
    if predicted is None:
        return {"right": 0, "wrong": count, "unscored": 0, "format_errors": count}
    right = sum(
        actual == expected for actual, expected in zip(predicted, problem["answers"])
    )
    return {"right": right, "wrong": count - right, "unscored": 0, "format_errors": 0}


def main():
    require_api()
    print("GPT-5 + Code Interpreter evaluation", flush=True)
    print(
        f"{CONFIG['problems']} problems, {CONFIG['queries']} answers each "
        f"({CONFIG['problems'] * CONFIG['queries']} answers total).",
        flush=True,
    )
    print(f"Seed: {RANDOM_SEED}", flush=True)

    # Freeze every problem before making calls. Only prompts go to the model;
    # hidden programs, correct answers, and grading results stay local.
    rng = random.Random(RANDOM_SEED)
    problems = []
    for number in range(1, CONFIG["problems"] + 1):
        print(f"Preparing problem {number}/{CONFIG['problems']}...", flush=True)
        problems.append(make_problem(rng, number, CONFIG))

    totals = {"right": 0, "wrong": 0, "unscored": 0, "format_errors": 0}
    started = time.monotonic()
    for index, problem in enumerate(problems, 1):
        print(f"\nProblem {index}/{len(problems)}: waiting for GPT-5...", flush=True)
        # Each case uses the original text-only request shape. Native tool
        # records from an earlier case are not inputs to the next case.
        try:
            record = timed_model(problem["prompt"], CONFIG["seconds_per_problem"])
        except KeyboardInterrupt:
            totals["unscored"] += sum(len(p["answers"]) for p in problems[index - 1 :])
            print("Interrupted. Remaining answers are unscored.", flush=True)
            break
        grade = score_response(record, problem)
        for key in totals:
            totals[key] += grade[key]
        if record["status"] == "completed":
            print(f"Right: {grade['right']} | Wrong: {grade['wrong']}", flush=True)
            if grade["format_errors"]:
                print("The response did not contain a valid answers array.", flush=True)
        else:
            detail = record.get("error_type") or record["status"]
            if record.get("status_code"):
                detail += f" (HTTP {record['status_code']})"
            print(f"Unscored: {grade['unscored']} ({detail})", flush=True)
            if record.get("error_message"):
                print(f"API message: {record['error_message']}", flush=True)
            if record.get("request_id"):
                print(f"Request ID: {record['request_id']}", flush=True)
            if record.get("incomplete_details"):
                print(
                    f"Incomplete response: {record['incomplete_details']}", flush=True
                )
            # A rejected credential or access error cannot be fixed by sending
            # the same configured request for each remaining problem.
            if record.get("error_type") in {
                "AuthenticationError",
                "PermissionDeniedError",
            }:
                totals["unscored"] += sum(len(p["answers"]) for p in problems[index:])
                print("Stopping because API access failed.", flush=True)
                break

    scored = totals["right"] + totals["wrong"]
    print("\nFINAL RESULTS", flush=True)
    print(f"Right:    {totals['right']}")
    print(f"Wrong:    {totals['wrong']}")
    print(f"Unscored: {totals['unscored']}")
    print(f"Total:    {scored + totals['unscored']}")
    if totals["unscored"]:
        print(
            f"INCOMPLETE RUN: only {scored}/{scored + totals['unscored']} answers were scored."
        )
    if scored:
        print(f"Accuracy: {totals['right'] / scored:.1%} on {scored} scored answers")
    else:
        print("Accuracy: unavailable; no answers were scored")
    if totals["format_errors"]:
        print(
            f"Wrong answers due to invalid response format: {totals['format_errors']}"
        )
    print(f"Evaluation time: {time.monotonic() - started:.1f} seconds")
    return totals


if __name__ == "__main__":
    mp.freeze_support()
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("Interrupted before evaluation completed.", file=sys.stderr)
        sys.exit(130)
