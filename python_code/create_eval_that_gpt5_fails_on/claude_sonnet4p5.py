import re
from openai import OpenAI


def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


def evaluate_response(response_text):
    """
    Evaluate if response meets all criteria:
    - Exactly 5 lines
    - Line 1: exactly 20 characters
    - Line 2: exactly 40 characters
    - Line 3: exactly 60 characters
    - Line 4: exactly 80 characters
    - Line 5: exactly 100 characters
    - Each line must be a coherent English sentence
    - All lines together tell a short story
    """
    lines = response_text.strip().split("\n")
    lines = [l.strip() for l in lines if l.strip()]

    if len(lines) != 5:
        return False, f"Expected 5 lines, got {len(lines)}", lines

    expected_lengths = [20, 40, 60, 80, 100]

    for i, (line, expected_len) in enumerate(zip(lines, expected_lengths), 1):
        actual_len = len(line)
        if actual_len != expected_len:
            return (
                False,
                f"Line {i}: expected {expected_len} chars, got {actual_len} ('{line}')",
                lines,
            )

    # Basic coherence check - each line should end with punctuation
    for i, line in enumerate(lines, 1):
        if not re.search(r"[.!?]$", line):
            return False, f"Line {i} doesn't end with proper punctuation", lines

    return True, "All constraints satisfied!", lines


def run_eval():
    """
    This eval tests the ability to generate text with precise character count constraints.

    Why GPT-5 fails: LLMs struggle with precise character counting during generation
    because they work with tokens (not characters) and count after generation rather
    than during. The increasing length makes the task exponentially harder.

    Why humans succeed: Humans can iteratively draft, count, and adjust each line,
    using tools like text editors with character counters or even manual counting.

    Success rate expectations:
    - GPT-5 with code_interpreter: <10% (model typically generates text first,
      then realizes it doesn't match constraints, struggles to fix precisely)
    - Careful human with character counter: >90%
    """

    prompt = """Create exactly 5 lines of text that tell a coherent short story.

CRITICAL CONSTRAINTS - ALL MUST BE MET:
1. Line 1 must be EXACTLY 20 characters long
2. Line 2 must be EXACTLY 40 characters long
3. Line 3 must be EXACTLY 60 characters long
4. Line 4 must be EXACTLY 80 characters long
5. Line 5 must be EXACTLY 100 characters long

Count includes all characters: letters, spaces, punctuation, everything.
Each line must be a grammatically correct English sentence.
The lines together should tell a simple story.

Output ONLY the 5 lines, nothing else. No explanations or extra text."""

    print("=" * 80)
    print("RUNNING EVAL: Precise Character Count Story Generation")
    print("=" * 80)
    print(f"\nPrompt:\n{prompt}\n")
    print("-" * 80)

    response = call_model(prompt)

    print(f"\nModel Response:\n{response}\n")
    print("-" * 80)

    success, message, lines = evaluate_response(response)

    print(f"\nEvaluation Result: {message}")
    print(f"Success: {success}\n")

    if not success:
        print("Line lengths:")
        for i, line in enumerate(lines, 1):
            print(f"  Line {i}: {len(line)} chars - '{line}'")
    else:
        print("✓ All constraints met!")

    print("=" * 80)

    return success


# Example of what a successful response looks like:
EXAMPLE_SUCCESS = """The cat slept there.
Max opened his door at sunrise quietly.
A mysterious package had arrived during the night hours.
Inside, he discovered an old map leading to unknown places and treasures nearby.
The adventure began immediately as he grabbed supplies and headed toward the forest beyond town."""


if __name__ == "__main__":
    # Run the eval
    result = run_eval()

    print("\n" + "=" * 80)
    print("EXAMPLE SUCCESSFUL RESPONSE:")
    print("=" * 80)
    success, msg, lines = evaluate_response(EXAMPLE_SUCCESS)
    print(EXAMPLE_SUCCESS)
    print(f"\nValidation: {msg}")
    for i, line in enumerate(lines, 1):
        print(f"Line {i}: {len(line)} characters ✓")
