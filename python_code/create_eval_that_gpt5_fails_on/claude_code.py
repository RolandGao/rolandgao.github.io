from openai import OpenAI
import json
from typing import Any


def call_model(input_text: str) -> str:
    """Call gpt-5 with code_interpreter tool"""
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input_text,
    )
    return response.output_text


def parse_solution(output: str) -> dict[str, Any]:
    """Parse model output to extract count"""
    try:
        # Extract just the integer count from output
        count_str = "".join(filter(str.isdigit, output.strip().split("\n")[-1]))
        if count_str:
            return {"count": int(count_str)}
        return {"error": "No number found in output"}
    except:
        return {"error": "Failed to parse output"}


def evaluate_solution(solution: dict[str, Any], correct_answer: dict[str, Any]) -> bool:
    """Verify solution correctness - only check count"""
    if "error" in solution:
        return False

    if "count" not in solution:
        return False

    # Only check: does the count match?
    return solution["count"] == correct_answer["count"]


def create_eval_prompt() -> str:
    """Generate the evaluation task"""
    task = """TASK: Scheduling Problem with Constraints

You have 10 tasks (labeled 0-9) that must be scheduled in a specific order.

CONSTRAINTS:
- Task 0 must come before task 5
- Task 1 must come before task 2
- Task 3 must come before task 4
- Task 6 must come before task 7
- Task 8 must come before task 9
- Tasks 0, 2, 4, 6, 8 cannot be adjacent to each other (no two even indices next to each other)
- Tasks 1, 3, 5, 7, 9 cannot be adjacent to each other (no two odd indices next to each other)

Count the total number of valid permutations of tasks 0-9 that satisfy ALL these constraints.

Output ONLY the integer count, nothing else."""
    return task


def compute_correct_answer() -> dict[str, Any]:
    """Compute the correct answer by brute force"""
    from itertools import permutations

    def is_valid(perm):
        # Constraint 1: 0 before 5
        if perm.index(0) >= perm.index(5):
            return False
        # Constraint 2: 1 before 2
        if perm.index(1) >= perm.index(2):
            return False
        # Constraint 3: 3 before 4
        if perm.index(3) >= perm.index(4):
            return False
        # Constraint 4: 6 before 7
        if perm.index(6) >= perm.index(7):
            return False
        # Constraint 5: 8 before 9
        if perm.index(8) >= perm.index(9):
            return False

        # Constraint 6: No two even indices adjacent
        for i in range(len(perm) - 1):
            if perm[i] % 2 == 0 and perm[i + 1] % 2 == 0:
                return False

        # Constraint 7: No two odd indices adjacent
        for i in range(len(perm) - 1):
            if perm[i] % 2 == 1 and perm[i + 1] % 2 == 1:
                return False

        return True

    valid = [list(p) for p in permutations(range(10)) if is_valid(p)]

    return {
        "valid_permutations": valid,
        "count": len(valid),
        "optimization_metric": "min_conflicts",
        "sample_valid": valid[:3] if valid else [],
    }


def run_eval(num_trials: int = 1) -> dict[str, Any]:
    """Run the evaluation multiple times"""
    correct = compute_correct_answer()
    results = {
        "correct_answer_count": correct["count"],
        "trials": [],
        "passed": 0,
        "failed": 0,
    }

    for trial_num in range(num_trials):
        print(f"\n{'=' * 60}")
        print(f"TRIAL {trial_num + 1}/{num_trials}")
        print(f"{'=' * 60}")

        prompt = create_eval_prompt()

        try:
            print("Calling model...")
            model_output = call_model(prompt)
            print(f"Model output received ({len(model_output)} chars)")

            solution = parse_solution(model_output)
            passed = evaluate_solution(solution, correct)

            trial_result = {
                "trial": trial_num + 1,
                "passed": passed,
                "model_count": solution.get("count", "N/A"),
                "correct_count": correct["count"],
                "sample_output": model_output[:500] + "..."
                if len(model_output) > 500
                else model_output,
            }

            if passed:
                results["passed"] += 1
                print("✓ PASSED")
            else:
                results["failed"] += 1
                print("✗ FAILED")
                if solution.get("count") != correct["count"]:
                    print(
                        f"  Reason: Wrong count (got {solution.get('count')}, expected {correct['count']})"
                    )

            results["trials"].append(trial_result)

        except Exception as e:
            results["failed"] += 1
            results["trials"].append(
                {"trial": trial_num + 1, "passed": False, "error": str(e)}
            )
            print(f"✗ ERROR: {e}")

    print(f"\n{'=' * 60}")
    print(f"FINAL RESULTS: {results['passed']}/{num_trials} passed")
    print(f"{'=' * 60}")

    return results


if __name__ == "__main__":
    results = run_eval(num_trials=1)
    print(json.dumps(results, indent=2))
