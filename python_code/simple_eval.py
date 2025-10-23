from typing import Callable, List, Dict, Tuple
import re
import textwrap


# ---- Provided by you ----
def call_model(input_text: str) -> str:
    """Send the prompt to gpt-5 and return the raw text output."""
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        input=input_text,
    )
    return response.output_text


# -------------------------


def only_short_words(text: str, max_len: int = 5) -> bool:
    # consider words as sequences of A-Za-z letters
    words = re.findall(r"[A-Za-z]+", text)
    return all(len(w) <= max_len for w in words)


def normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def run_test(name: str, prompt: str, validator: Callable[[str], Tuple[bool, str]]):
    print(f"\n=== {name} ===")
    print(f"Prompt:\n{prompt}\n")
    out = call_model(prompt)
    ok, why = validator(out)
    print(
        "Model output:\n"
        + textwrap.shorten(normalize(out), width=800, placeholder=" ...")
    )
    print(f"\nResult: {'PASS' if ok else 'FAIL'} — {why}")


def contains_hd_84937_only(answer: str) -> Tuple[bool, str]:
    """
    Accept a correct F-type subdwarf by name.
    We require 'HD 84937' (well-documented sdF / metal-poor F-type).
    Reject common wrong responses like Groombridge 1830 (G8 VI).
    """
    a = normalize(answer).upper()
    if "GROOMBRIDGE 1830" in a:
        return (False, "Returned Groombridge 1830 (G8 VI), not F-type.")
    if re.search(r"\bHD[-\s]?84937\b", a):
        return (True, "Named HD 84937 (accepted F-type subdwarf).")
    return (
        False,
        "Did not name a clearly correct F-type subdwarf (expected: HD 84937).",
    )


def validator_short_words(answer: str) -> Tuple[bool, str]:
    return (
        only_short_words(answer, max_len=5),
        "All words are ≤ 5 letters"
        if only_short_words(answer, 5)
        else "Found words longer than 5 letters.",
    )


def validator_min_words(answer: str, min_words: int = 950) -> Tuple[bool, str]:
    n = len(re.findall(r"\b\w+\b", answer))
    return (n >= min_words, f"Word count = {n} (expected ≥ {min_words})")


def main():
    tests: List[Dict] = [
        {
            "name": "F-type subdwarf: factual correctness",
            "prompt": "Name a real F-type subdwarf star (luminosity class VI). "
            "Answer with just the star's common designation (e.g., 'HD 84937') and nothing else.",
            "validator": contains_hd_84937_only,
        },
        {
            "name": "Macbeth summary with 5-letter constraint",
            "prompt": "Summarize the plot of Macbeth in words of five letters or fewer. Keep it under 120 words.",
            "validator": validator_short_words,
        },
        {
            "name": "No truncation at 1000 words",
            "prompt": "Write a 1000-word blog post about the benefits of container gardening for urban dwellers.",
            "validator": lambda out: validator_min_words(out, 950),
        },
    ]

    for t in tests:
        run_test(t["name"], t["prompt"], t["validator"])


if __name__ == "__main__":
    main()
