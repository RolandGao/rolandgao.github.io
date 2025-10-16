"""
contradictory_pangram_eval.py
-------------------------------------------------
Evaluation: prove that a “vowelless perfect pangram” is impossible.
If the task is impossible, the correct response is exactly the
lower-case word:  impossible
(no spaces, punctuation, or newlines).

Why GPT-5 fails:
  * Large models often give a longer explanation (or capitalize “Impossible”)
    even when instructed not to; they rarely return the single
    lowercase token `impossible` by itself.
  * Any other output — including attempts at a sentence, added
    punctuation, capitalisation, or commentary — is counted as failure.

Humans can pass trivially by replying with the single word `impossible`.
"""

import re
from openai import OpenAI


# ----------  provided model wrapper  ----------
def call_model(prompt: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=prompt,
    )
    return response.output_text


# -----------  evaluation prompt  ---------------
PROMPT = (
    "TASK:\n"
    "Write ONE English sentence that uses every letter of the alphabet "
    "exactly once **and** contains NO vowels (a, e, i, o, u).\n\n"
    "If you believe this task is impossible, respond with **exactly** the "
    "single word:\n"
    "impossible\n"
    "(all lowercase, no period, no quotes, no extra whitespace, "
    "no explanation).\n"
)


# -------------  judge function  ----------------
def model_failed(reply: str) -> bool:
    """
    Returns True when the model *fails* the task (desired outcome for eval).
    The only successful model reply is literal 'impossible' alone.
    """
    return reply.strip() != "impossible"


# -------------  eval runner  -------------------
def run_eval() -> None:
    reply = call_model(PROMPT)
    failed = model_failed(reply)

    if failed:
        # Desired path: GPT-5 did NOT comply perfectly.
        print("✅  Model failed as expected (eval passed).")
        print("Model reply:", repr(reply))
        exit(0)
    else:
        # Unexpected: GPT-5 managed the correct minimalist answer.
        print("❌  Model produced exact required token — eval failed.")
        print("Model reply:", repr(reply))
        exit(1)


if __name__ == "__main__":
    run_eval()
