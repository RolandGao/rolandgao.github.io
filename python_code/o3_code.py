"""
Character-Position Eval
-----------------------
Evaluates whether a model can give the exact 1-indexed position of an
uppercase 'X' hidden in a long ASCII noise string.

Humans can solve instantly with a simple text‐search; LLMs typically fail
at least one item due to brittle long-range counting.

Usage:
  export OPENAI_API_KEY=sk-...
  python o3_code.py --model gpt-5 --n 1 --seed 42

A run passes only if *every* sample is answered correctly.
"""

import os, re, random, argparse, sys, json, time
import openai
from openai import OpenAI
from typing import Tuple

#######################################################################
# 1. Dataset generation                                               #
#######################################################################


def make_item(min_len: int = 2000, max_len: int = 5000) -> Tuple[str, int]:
    """
    Returns:
        prompt (str): the text sent to the model
        answer (int): ground-truth 1-indexed position of 'X'
    """
    length = random.randint(min_len, max_len)
    pos = random.randint(1, length)  # ground-truth index
    chars = [random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(length)]
    chars[pos - 1] = "X"
    noise = "".join(chars)

    prompt = (
        "You will be given a single-line ASCII string containing **exactly one** "
        "uppercase letter 'X'. All other characters are lowercase letters.\n\n"
        "Return **only** the 1-indexed character position where 'X' occurs. "
        "For example, if the string were 'abXc', you would reply `3`.\n\n"
        f"STRING:\n{noise}\n\nYour answer:"
    )
    return prompt, pos


#######################################################################
# 2. Helper utilities                                                 #
#######################################################################

_int_re = re.compile(r"-?\d+")


def first_int(text: str) -> int | None:
    """Extracts the first integer in `text`, if any."""
    m = _int_re.search(text)
    return int(m.group()) if m else None


#######################################################################
# 3. Core evaluation loop                                             #
#######################################################################


def eval_model(
    model: str,
    n_samples: int = 25,
    temperature: float = 0.0,
    seed: int | None = None,
    max_retries: int = 3,
    sleep_s: float = 1.0,
) -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if seed is not None:
        random.seed(seed)

    passed = 0
    for i in range(1, n_samples + 1):
        prompt, truth = make_item()
        # ---------- call the model ----------
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model,
                    temperature=temperature,
                    max_tokens=8,
                    messages=[{"role": "user", "content": prompt}],
                )
                output = response.choices[0].message.content.strip()
                break
            except openai.OpenAIError as e:
                if attempt == max_retries - 1:
                    print(
                        f"[{i}] API error after {max_retries} tries: {e}",
                        file=sys.stderr,
                    )
                    output = ""
                else:
                    time.sleep(sleep_s)

        guess = first_int(output)
        ok = guess == truth
        passed += ok
        print(
            f"[{i}/{n_samples}] expected={truth:<5} got={guess} {'✅' if ok else '❌'}"
        )

    accuracy = passed / n_samples
    print("\n==========  RESULTS  ==========")
    print(f"model     : {model}")
    print(f"samples   : {n_samples}")
    print(f"accuracy  : {accuracy:.2%}")
    print("STATUS    : " + ("PASS ✅" if accuracy == 1.0 else "FAIL ❌"))


#######################################################################
# 4. CLI entry-point                                                  #
#######################################################################


def main() -> None:
    ap = argparse.ArgumentParser(description="Character-Position Eval harness")
    ap.add_argument("--model", default="gpt-5", help="OpenAI model name")
    ap.add_argument("--n", type=int, default=25, help="number of samples")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, help="set random seed for reproducibility")
    args = ap.parse_args()

    eval_model(
        model=args.model,
        n_samples=args.n,
        temperature=args.temperature,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
