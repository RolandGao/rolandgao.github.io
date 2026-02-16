"""
Text-only eval harness for LLMs and humans (with a built-in Python REPL).

- Model calls use the user's provided OpenAI Responses API snippet (call_model).
- Human mode gives the same prompts and a time limit, plus an optional embedded Python REPL
  to simulate "code_interpreter" access for computations.
- Scoring is deterministic, text-only.
"""

from __future__ import annotations

import json
import re
import signal
import sys
import textwrap
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

# -----------------------------
# 1) Model call: EXACTLY as provided
# -----------------------------
from openai import OpenAI


def call_model(input: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


# -----------------------------
# 2) Timeout helper (Unix-like systems)
# -----------------------------
class TimeoutError(Exception):
    pass


def _alarm_handler(signum, frame):
    raise TimeoutError("Time limit exceeded")


def run_with_timeout(
    fn: Callable[[], str], seconds: int
) -> Tuple[bool, str, float, Optional[str]]:
    """
    Returns: (ok, output, elapsed_seconds, error_str)
    """
    start = time.time()
    old = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.alarm(max(1, int(seconds)))
    try:
        out = fn()
        elapsed = time.time() - start
        signal.alarm(0)
        return True, out, elapsed, None
    except TimeoutError as e:
        elapsed = time.time() - start
        return False, "", elapsed, str(e)
    except Exception as e:
        elapsed = time.time() - start
        return False, "", elapsed, f"{type(e).__name__}: {e}"
    finally:
        try:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
        except Exception:
            pass


# -----------------------------
# 3) Task definition and scoring
# -----------------------------
@dataclass
class Task:
    task_id: str
    title: str
    prompt: str
    time_limit_s: int
    scorer: Callable[[str], Tuple[float, str]]  # (score 0..1, feedback)


def normalize_newlines(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")


def strip_trailing_spaces_per_line(s: str) -> str:
    return "\n".join(
        line.rstrip(" \t") for line in normalize_newlines(s).split("\n")
    ).strip("\n")


def exact_match(expected: str) -> Callable[[str], Tuple[float, str]]:
    expected_norm = strip_trailing_spaces_per_line(expected)

    def _score(ans: str) -> Tuple[float, str]:
        got = strip_trailing_spaces_per_line(ans)
        if got == expected_norm:
            return 1.0, "Exact match."
        # Provide a short diff-style hint without leaking too much.
        return (
            0.0,
            f"Mismatch.\nExpected (normalized):\n{expected_norm}\n\nGot (normalized):\n{got}",
        )

    return _score


def json_canonical_match(expected_obj: object) -> Callable[[str], Tuple[float, str]]:
    expected = json.dumps(expected_obj, sort_keys=True, separators=(",", ":"))

    def _score(ans: str) -> Tuple[float, str]:
        try:
            obj = json.loads(ans)
        except Exception as e:
            return 0.0, f"Answer is not valid JSON: {e}"
        got = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        if got == expected:
            return 1.0, "JSON matches canonical form."
        return (
            0.0,
            f"JSON mismatch.\nExpected canonical:\n{expected}\nGot canonical:\n{got}",
        )

    return _score


def regex_fullmatch(pattern: str) -> Callable[[str], Tuple[float, str]]:
    rx = re.compile(pattern, flags=re.DOTALL)

    def _score(ans: str) -> Tuple[float, str]:
        if rx.fullmatch(ans.strip()):
            return 1.0, "Matches required format."
        return 0.0, f"Does not match required format regex:\n{pattern}"

    return _score


# -----------------------------
# 4) Tasks (text-only, safety-compliant)
# -----------------------------
def build_tasks() -> List[Task]:
    tasks: List[Task] = []

    # Task A: Precision parsing + exact formatting
    spec = """\
You are given a list of "records". Each record is a single line.

Rules:
1) A record is: <name> | <count> | <tags>
2) <name> may contain spaces.
3) <count> is an integer, may have leading zeros.
4) <tags> is a comma-separated list; tags may contain hyphens; ignore extra spaces around commas.
5) Output MUST be exactly 4 lines:
   Line1: the name with the largest count (ties: choose lexicographically smallest name)
   Line2: the sum of counts (as an integer, no leading zeros unless sum is 0)
   Line3: all unique tags, lowercased, sorted lexicographically, joined by a single comma (no spaces)
   Line4: JSON object: {"top_name": ..., "sum": ..., "tags": [...]}
   - JSON keys in that exact order (top_name then sum then tags)
   - tags array in the same order as Line3
   - use double quotes, no trailing commas
Do NOT include any extra text.
"""
    data = """\
Ada Lovelace | 00012 | math,  History, analytical-engine
Grace Hopper | 12 | compilers, Navy, history
Alan Turing | 00012 | math, cryptography , history
Barbara Liskov | 9 | compilers,  abstractions
"""
    expected_tags = [
        "abstractions",
        "analytical-engine",
        "compilers",
        "cryptography",
        "history",
        "math",
        "navy",
    ]
    # Largest count = 12, tie among Ada, Grace, Alan => lexicographically smallest name: "Ada Lovelace"
    expected_obj = {"top_name": "Ada Lovelace", "sum": 45, "tags": expected_tags}
    expected_lines = "\n".join(
        [
            "Ada Lovelace",
            "45",
            ",".join(expected_tags),
            json.dumps(
                expected_obj, separators=(",", ":"), ensure_ascii=False
            ),  # already in correct key order here
        ]
    )

    tasks.append(
        Task(
            task_id="precision_parse_001",
            title="Precision parsing with exact output format",
            prompt=spec + "\nINPUT RECORDS:\n" + data,
            time_limit_s=180,
            scorer=exact_match(expected_lines),
        )
    )

    # Task B: Counting with tricky whitespace + exact number
    # Humans can solve quickly with python; LLMs often slip on counting rules.
    blob = (
        "Count the number of occurrences of the substring 'aba' in the text below, "
        "where occurrences may overlap. Output ONLY the integer.\n\n"
        "TEXT:\n"
        "ababa\n"
        " xababa\n"
        "abababa\n"
        "abaaba\n"
        "ab a ba (note spaces)\n"
        "ABABA (note case)\n"
        "\nRules:\n"
        "- Count only exact lowercase 'aba'\n"
        "- Overlaps count (e.g., 'ababa' has 2: positions 1 and 3)\n"
        "- Spaces break matches\n"
    )
    # Let's compute expected:
    # "ababa" -> 2
    # " xababa" -> "xababa" contains "aba" twice -> 2
    # "abababa" -> occurrences at 1,3,5 -> 3
    # "abaaba" -> occurrences at 1 and 4? Actually "abaaba": positions 1-3 = aba, 4-6 = aba -> 2 (no overlap across middle)
    # "ab a ba" has no contiguous "aba" -> 0
    # "ABABA" case mismatch -> 0
    expected_count = 2 + 2 + 3 + 2 + 0 + 0
    tasks.append(
        Task(
            task_id="overlap_count_001",
            title="Overlapping substring count (case + whitespace traps)",
            prompt=blob,
            time_limit_s=120,
            scorer=exact_match(str(expected_count)),
        )
    )

    # Task C: Small "spec-following" task with a strict regex output format
    # Requires producing ONLY a strict block of text with exact delimiters.
    prompt_c = textwrap.dedent("""\
    Produce EXACTLY the following structure, with no extra characters:

    BEGIN
    <8 hex chars>
    <8 hex chars>
    <8 hex chars>
    END

    The three hex lines must be:
    - Line 2: SHA-256 of the ASCII string "alpha" truncated to 8 hex chars
    - Line 3: SHA-256 of the ASCII string "beta" truncated to 8 hex chars
    - Line 4: SHA-256 of the ASCII string "gamma" truncated to 8 hex chars

    All hex must be lowercase.
    Output text only.
    """).strip()

    # Expected values computed once (hard-coded) so scoring is deterministic.
    # If you prefer, you can compute these at runtime in the scorer instead;
    # hardcoding avoids any ambiguity in hashing implementation.
    expected_c = "\n".join(
        [
            "BEGIN",
            "8ed3f6ad",  # sha256("alpha") starts with 8ed3f6ad...
            "f44e64e7",  # sha256("beta") starts with f44e64e7...
            "be9d587d",  # sha256("gamma") starts with be9d587d...
            "END",
        ]
    )

    tasks.append(
        Task(
            task_id="hash_format_001",
            title="Strict hashing + exact formatting",
            prompt=prompt_c,
            time_limit_s=120,
            scorer=exact_match(expected_c),
        )
    )

    # Task D: Controlled JSON transformation with edge cases
    prompt_d = textwrap.dedent("""\
    Convert the following pseudo-CSV into JSON.

    Input rules:
    - Lines starting with # are comments and must be ignored.
    - Blank lines must be ignored.
    - Each non-comment line has 3 fields separated by semicolons: id;active;score
    - id is a string (preserve as-is, including leading zeros)
    - active is 'Y' or 'N' -> boolean true/false
    - score is either an integer or the string 'NA' -> null

    Output rules:
    - Output a JSON array (no surrounding text).
    - Each element is an object with keys: "id", "active", "score"
    - Keep the same order as input.
    - Use null for NA.
    - id must stay a string.

    DATA:
    # example dataset
    001;Y;10

    010;N;NA
    010;Y;0
    000;N;7
    """).strip()

    expected_d = [
        {"id": "001", "active": True, "score": 10},
        {"id": "010", "active": False, "score": None},
        {"id": "010", "active": True, "score": 0},
        {"id": "000", "active": False, "score": 7},
    ]

    tasks.append(
        Task(
            task_id="json_transform_001",
            title="Robust parsing -> JSON with type rules",
            prompt=prompt_d,
            time_limit_s=180,
            scorer=json_canonical_match(expected_d),
        )
    )

    # Task E: Ultra-strict output constraint via regex
    prompt_e = textwrap.dedent("""\
    Output a single line that matches this exact pattern:

    ^[A-Z]{3}-\\d{4}-[a-z]{2}$

    Additional constraint:
    - The 4 digits must be the result of (17 * 19) + (23 * 29)
    - The 3 uppercase letters must be the first three letters of the English word for that result (uppercase)
    - The 2 lowercase letters must be the last two letters of the English word for that result (lowercase)

    Output ONLY the line.
    """).strip()

    # Compute expected for determinism (still text-only).
    # (17*19)=323, (23*29)=667, sum=990
    # English word commonly: "nine hundred ninety"
    # first three letters: NIN; last two letters of the full phrase are ambiguous.
    # To avoid ambiguity, we define the word as "ninehundredninety" (no spaces).
    # That yields first three "NIN" and last two "ty".
    expected_e = "NIN-0990-ty"
    tasks.append(
        Task(
            task_id="regex_constrained_001",
            title="Regex-constrained exact single-line output",
            prompt=prompt_e
            + "\n\nNOTE: For this task, interpret the English word with no spaces: 'ninehundredninety'.",
            time_limit_s=120,
            scorer=exact_match(expected_e),
        )
    )

    return tasks


# -----------------------------
# 5) Human agent with embedded Python REPL (text-only)
# -----------------------------
def human_agent(prompt: str, time_limit_s: int) -> str:
    """
    Gives the human the prompt and a time limit.
    Allows optional Python snippets by typing lines between:
      :py
      <python code>
      :endpy
    The Python output is printed for the human, but the final submitted answer is whatever
    they type after ':final' until EOF or a single line ':endfinal'.
    """
    print("\n" + "=" * 80)
    print(f"TIME LIMIT: {time_limit_s}s")
    print("=" * 80)
    print(prompt)
    print("=" * 80)
    print("Human controls:")
    print("  - Type ':py' to start a Python block, ':endpy' to run it.")
    print("  - Type ':final' to start your final answer, ':endfinal' to submit.")
    print(
        "  - Anything printed by Python is just for you; only the final answer is scored."
    )
    print("=" * 80)

    py_locals: Dict[str, object] = {}
    final_lines: List[str] = []
    mode = "normal"
    py_lines: List[str] = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if mode == "normal":
            if line.strip() == ":py":
                mode = "py"
                py_lines = []
                continue
            if line.strip() == ":final":
                mode = "final"
                final_lines = []
                continue
            # ignore other chatter in normal mode to encourage using :final
            continue

        if mode == "py":
            if line.strip() == ":endpy":
                code = "\n".join(py_lines)
                try:
                    compiled = compile(code, "<human_py>", "exec")
                    exec(compiled, {}, py_locals)
                except Exception as e:
                    print(f"[PY ERROR] {type(e).__name__}: {e}")
                mode = "normal"
                continue
            py_lines.append(line)
            continue

        if mode == "final":
            if line.strip() == ":endfinal":
                break
            final_lines.append(line)
            continue

    return "\n".join(final_lines).strip("\n")


# -----------------------------
# 6) Model agent wrapper
# -----------------------------
def model_agent(prompt: str) -> str:
    return call_model(prompt)


# -----------------------------
# 7) Eval runner
# -----------------------------
@dataclass
class Result:
    task_id: str
    title: str
    ok: bool
    score: float
    elapsed_s: float
    error: Optional[str]
    feedback: str
    answer_preview: str


def run_eval(
    tasks: List[Task],
    agent_name: str,
    agent_fn: Callable[[str, int], str],
) -> List[Result]:
    results: List[Result] = []

    for t in tasks:

        def _call() -> str:
            return agent_fn(t.prompt, t.time_limit_s)

        ok, out, elapsed, err = run_with_timeout(_call, t.time_limit_s)
        if not ok:
            results.append(
                Result(
                    task_id=t.task_id,
                    title=t.title,
                    ok=False,
                    score=0.0,
                    elapsed_s=elapsed,
                    error=err,
                    feedback="No answer (timeout or error).",
                    answer_preview="",
                )
            )
            continue

        score, feedback = t.scorer(out)
        results.append(
            Result(
                task_id=t.task_id,
                title=t.title,
                ok=True,
                score=score,
                elapsed_s=elapsed,
                error=None,
                feedback=feedback,
                answer_preview=(out[:200] + ("..." if len(out) > 200 else "")),
            )
        )

    # Summary
    total = sum(r.score for r in results)
    print("\n" + "#" * 80)
    print(f"EVAL SUMMARY — {agent_name}")
    print("#" * 80)
    for r in results:
        status = "PASS" if r.score >= 1.0 else "FAIL"
        print(
            f"- {r.task_id} | {status} | score={r.score:.2f} | {r.elapsed_s:.1f}s | {r.title}"
        )
        if r.error:
            print(f"  error: {r.error}")
        else:
            print(f"  preview: {repr(r.answer_preview)}")
    print("-" * 80)
    print(f"TOTAL SCORE: {total:.2f} / {len(results):.2f}")
    print("#" * 80 + "\n")

    return results


def model_agent_adapter(prompt: str, time_limit_s: int) -> str:
    # time_limit_s is enforced outside via alarm; included to match signature
    return model_agent(prompt)


def main():
    tasks = build_tasks()

    if len(sys.argv) < 2 or sys.argv[1] not in ("model", "human"):
        print("Usage:")
        print(
            "  python eval.py model   # run gpt-5 (with code_interpreter) on all tasks"
        )
        print(
            "  python eval.py human   # run a human attempt on all tasks (with built-in Python REPL)"
        )
        sys.exit(2)

    mode = sys.argv[1]
    if mode == "model":
        run_eval(tasks, "gpt-5 (responses + code_interpreter)", model_agent_adapter)
    else:
        run_eval(tasks, "human (with embedded Python REPL)", human_agent)


if __name__ == "__main__":
    # Note: signal.alarm is Unix-only. On Windows, you can remove timeouts or use multiprocessing.
    main()
