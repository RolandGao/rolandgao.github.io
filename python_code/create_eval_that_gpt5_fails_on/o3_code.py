"""
perfect_pangram_eval.py
-------------------------------------------------
A minimal LLM-eval that GPT-5 + code_interpreter
*should* fail but a careful human can pass.
Input & output are text-only; no policy-violating
content is requested or required.
"""

import string
from openai import OpenAI


# -------------  model wrapper (given) -----------------
def call_model(input: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    # .output_text holds the assistant’s final reply
    return response.output_text


# -------------  eval logic ---------------------------
PROMPT = (
    "TASK:\n"
    "Write **one** English sentence that uses every letter of the alphabet "
    "exactly once (case-insensitive). You may insert spaces between words, "
    "but NO OTHER punctuation is allowed **except** a SINGLE period (.) at "
    "the very end.\n\n"
    "Return *only* that sentence—including the period—and nothing else."
)


def is_perfect_pangram(sentence: str) -> bool:
    """
    True  -> perfect pangram (26 unique a-z letters + spaces + final '.')
    False -> anything else (duplicates, missing letters, punctuation, etc.)
    """
    sentence = sentence.strip()

    # Must end with one—and only one—period
    if not sentence.endswith(".") or sentence.count(".") != 1:
        return False

    core = sentence[:-1].replace(" ", "").lower()  # drop period & spaces
    return len(core) == 26 and set(core) == set(string.ascii_lowercase)


def run_eval() -> None:
    """
    Returns zero exit-status (0) if GPT-5 *fails* (desired),
    non-zero if GPT-5 somehow *passes*.
    """
    reply = call_model(PROMPT)
    succeeded = is_perfect_pangram(reply)

    if succeeded:
        # Unexpected—GPT-5 beat the eval
        print("❌  Model produced a perfect pangram: it *passed* (eval failed).")
        print("Model reply:", repr(reply))
        exit(1)
    else:
        # Expected path: GPT-5 gets something wrong
        print("✅  Model failed to craft a perfect pangram (eval passed).")
        print("Model reply:", repr(reply))
        exit(0)


if __name__ == "__main__":
    run_eval()
