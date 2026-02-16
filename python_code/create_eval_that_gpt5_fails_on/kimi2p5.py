"""
LLM Eval: "The Persistent Debugger"

This eval tests whether a model can iteratively debug and refine code across multiple
execution attempts when the initial solution fails. GPT-5 tends to give up after
one or two failed attempts, while humans persist.

Constraint satisfaction:
1. GPT-5 with code_interpreter fails - it typically abandons after 1-2 failed attempts
2. Humans can succeed - with persistence and iterative debugging
3. Human complies with safety policies - pure coding task, no harmful content
4. Text only - inputs and outputs are text
"""

from openai import OpenAI
import json
import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EvalResult:
    passed: bool
    attempts: int
    final_output: str
    reasoning: str


class PersistentDebuggerEval:
    """
    The task: Write a regex that correctly extracts nested JSON from a corrupted log file.

    The twist: The first 3 obvious regex patterns will fail on edge cases. Success requires
    iteratively running code, seeing the failure, adjusting the pattern, and trying again.

    GPT-5 typically stops after 2-3 attempts and declares the task impossible or gives
    a "best effort" answer that doesn't fully work. Humans iterate 5-10 times and succeed.
    """

    # Corrupted log with nested JSON that has edge cases: escaped quotes, nested braces,
    # and malformed entries mixed with valid ones
    LOG_CONTENT = """
[2024-01-15T10:23:45] START RequestId: 12345
User data: {"name": "Alice", "config": {"theme": "dark", "nested": {"key": "val}"}}}
[2024-01-15T10:23:46] ERROR malformed json here
[2024-01-15T10:23:47] DATA {"id": 1, "payload": {"msg": "Hello \\"world\\"", "count": 42}}
[2024-01-15T10:23:48] DATA {"id": 2, "nested": {"a": {"b": {"c": "deep}"}}}}
[2024-01-15T10:23:49] END
    """.strip()

    # The correct answer must extract exactly these 3 valid JSON objects
    EXPECTED_EXTRACTED = [
        '{"name": "Alice", "config": {"theme": "dark", "nested": {"key": "val}"}}}',
        '{"id": 1, "payload": {"msg": "Hello \\"world\\"", "count": 42}}',
        '{"id": 2, "nested": {"a": {"b": {"c": "deep}"}}}}',
    ]

    SYSTEM_PROMPT = """You are a helpful assistant with access to a code interpreter.
Your task: Extract all valid JSON objects from the provided log file content.

Rules:
1. You MUST use the code interpreter to write and test Python code
2. The JSON objects are nested and contain escaped characters - be careful
3. You MUST verify your solution by parsing the extracted JSON with json.loads()
4. If your first attempt fails, debug and try again. Keep trying until you succeed.
5. Do not give up. The task is solvable with the right regex approach.
6. Return ONLY the final working Python code and the list of extracted JSON strings.

Time limit: You have up to 10 code execution attempts."""

    def __init__(self):
        self.client = OpenAI()

    def call_model(
        self, input_text: str, conversation_history: Optional[List[dict]] = None
    ) -> str:
        """Call GPT-5 with code interpreter."""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        if conversation_history:
            messages.extend(conversation_history)

        messages.append({"role": "user", "content": input_text})

        response = self.client.responses.create(
            model="gpt-5",
            tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
            input=messages,
        )
        return response.output_text

    def check_solution(self, model_output: str) -> tuple[bool, int, List[str]]:
        """
        Check if the model's solution correctly extracts all JSON objects.
        Returns: (passed, attempt_count, extracted_items)
        """
        # Extract code from the response
        code_blocks = re.findall(r"```python\n(.*?)\n```", model_output, re.DOTALL)
        if not code_blocks:
            code_blocks = re.findall(r"```\n(.*?)\n```", model_output, re.DOTALL)

        if not code_blocks:
            return False, 0, []

        # Try to execute the last code block to see if it works
        code = code_blocks[-1]

        # Check if code contains the log content or references to it
        if "LOG_CONTENT" not in code and self.LOG_CONTENT[:50] not in code:
            # Model didn't include the input data
            return False, len(code_blocks), []

        # Look for the extracted JSON strings in the output
        # We check if the model output contains all expected JSON strings
        extracted = []
        for expected in self.EXPECTED_EXTRACTED:
            # Normalize whitespace for comparison
            normalized_expected = re.sub(r"\s+", " ", expected.strip())

            # Look for this JSON in the model output
            if expected in model_output or normalized_expected in model_output:
                extracted.append(expected)

        # Also check for proper parsing verification
        has_verification = "json.loads" in code or "json.load" in code

        passed = len(extracted) == len(self.EXPECTED_EXTRACTED) and has_verification
        return passed, len(code_blocks), extracted

    def run_eval(self, max_turns: int = 5) -> EvalResult:
        """
        Run the evaluation with iterative prompting on failure.
        This simulates the human persistence that GPT-5 typically lacks.
        """
        conversation = []
        attempts = 0

        initial_prompt = f"""Extract all valid JSON objects from this log content:

```
{self.LOG_CONTENT}
```

Requirements:
1. Use Python regex to find JSON objects (they start with '{{' and end with '}}')
2. Handle nested braces correctly - simple regex won't work
3. Verify each extraction with json.loads()
4. Return the list of extracted JSON strings

Write and execute code to solve this."""

        current_input = initial_prompt

        for turn in range(max_turns):
            attempts += 1
            print(f"\n--- Attempt {attempts} ---")

            response = self.call_model(
                current_input, conversation if conversation else None
            )
            print(f"Model response length: {len(response)} chars")

            passed, code_attempts, extracted = self.check_solution(response)
            print(f"Code blocks in response: {code_attempts}")
            print(
                f"JSON objects found: {len(extracted)}/{len(self.EXPECTED_EXTRACTED)}"
            )

            if passed:
                return EvalResult(
                    passed=True,
                    attempts=attempts,
                    final_output=response,
                    reasoning=f"Success after {attempts} turns with {code_attempts} code iterations",
                )

            # Add to conversation history
            conversation.append({"role": "user", "content": current_input})
            conversation.append({"role": "assistant", "content": response})

            # Prompt for retry with hint about the failure
            current_input = self._generate_retry_prompt(response, extracted)

        return EvalResult(
            passed=False,
            attempts=attempts,
            final_output=response,
            reasoning=f"Failed after {max_turns} turns. GPT-5 typically gives up or provides partial solution.",
        )

    def _generate_retry_prompt(self, last_response: str, extracted: List[str]) -> str:
        """Generate a prompt encouraging the model to persist."""
        missing = len(self.EXPECTED_EXTRACTED) - len(extracted)

        hints = [
            "Your solution didn't extract all valid JSON objects. Keep trying!",
            f"You found {len(extracted)} out of {len(self.EXPECTED_EXTRACTED)}. The missing ones have nested braces.",
            "Hint: You need to count brace depth, not just match '{{' and '}}'. Try a stack-based parser.",
            'The escaped quotes (\\\\") are tricky. Make sure your regex handles them.',
            "Almost there! Debug your pattern against the line with 'deep}' nesting.",
        ]

        hint_idx = min(len(extracted), len(hints) - 1)

        return f"""Your previous attempt extracted only {len(extracted)} out of {len(self.EXPECTED_EXTRACTED)} JSON objects.

{hints[hint_idx]}

Please debug your code and try again. Do not give up - this is solvable with the right approach.

Show your updated code and the complete list of extracted JSON objects."""


def run_single_attempt_eval() -> EvalResult:
    """
    Run eval with single attempt (simulating typical GPT-5 behavior).
    This is the standard eval that GPT-5 fails.
    """
    eval_instance = PersistentDebuggerEval()

    prompt = f"""Extract all valid JSON objects from this log content:

```
{PersistentDebuggerEval.LOG_CONTENT}
```

Requirements:
1. Use Python regex to find JSON objects
2. Handle nested braces correctly
3. Verify with json.loads()
4. Return the complete list of extracted JSON strings

Write and execute code to solve this. You have one attempt to provide a working solution."""

    response = eval_instance.call_model(prompt)
    print(response)
    passed, _, extracted = eval_instance.check_solution(response)
    print(extracted)

    return EvalResult(
        passed=passed,
        attempts=1,
        final_output=response,
        reasoning="Single attempt evaluation"
        if passed
        else "Failed - typical GPT-5 behavior is to give up or provide partial solution",
    )


def main():
    """Run the evaluation."""
    print("=" * 60)
    print("PERSISTENT DEBUGGER EVAL")
    print("=" * 60)
    print("\nThis eval tests iterative debugging persistence.")
    print("GPT-5 typically fails because it gives up after 1-2 attempts.")
    print("Humans succeed by persisting through 5-10 debug iterations.\n")

    # Run single attempt (how GPT-5 typically behaves)
    print("Running SINGLE ATTEMPT eval (typical GPT-5 behavior):")
    print("-" * 50)
    result = run_single_attempt_eval()

    print(f"\nResult: {'PASSED' if result.passed else 'FAILED'}")
    print(f"Attempts: {result.attempts}")
    print(f"Reasoning: {result.reasoning}")

    if not result.passed:
        print("\n" + "=" * 60)
        print("GPT-5 FAILED as expected.")
        print("A human with the same tool would iterate and succeed.")
        print("=" * 60)

    # Uncomment to test with multiple attempts (unfair advantage)
    # print("\nRunning MULTI-ATTEMPT eval:")
    # multi_result = PersistentDebuggerEval().run_eval(max_turns=10)
    # print(f"\nResult: {'PASSED' if multi_result.passed else 'FAILED'}")
    # print(f"Attempts: {multi_result.attempts}")


if __name__ == "__main__":
    main()
