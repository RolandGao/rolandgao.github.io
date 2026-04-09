from openai import OpenAI


def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


TEST_CASES = [
    {
        "name": "Goldbach counterexample search",
        "code": """
def is_prime(n):
    if n < 2: return False
    for i in range(2, int(n**0.5)+1):
        if n % i == 0: return False
    return True

def search():
    n = 4
    while True:
        if not any(is_prime(p) and is_prime(n-p) for p in range(2, n)):
            return n
        n += 2
search()
""",
        "expected": "UNKNOWN",
    },
    {
        "name": "Odd perfect number search",
        "code": """
def sigma(n):
    total = 1 + n
    for i in range(2, int(n**0.5)+1):
        if n % i == 0:
            total += i
            if i != n//i: total += n//i
    return total if n>1 else 1

def search():
    n = 1
    while True:
        if n % 2 == 1 and sigma(n) == 2*n:
            return n
        n += 2
search()
""",
        "expected": "UNKNOWN",
    },
    {
        "name": "Collatz nontrivial cycle search",
        "code": """
def has_nontrivial_cycle(start):
    n = start
    seen = set()
    while n not in seen:
        seen.add(n)
        if n == 1: return False
        n = n//2 if n%2==0 else 3*n+1
    return True

def search():
    n = 2
    while True:
        if has_nontrivial_cycle(n):
            return n
        n += 1
search()
""",
        "expected": "UNKNOWN",
    },
]


def build_prompt(code):
    return f"""You are evaluating whether a Python program halts.

Program:
```python
{code}
```

Instructions:
1. Use the code_interpreter tool to run the program for up to 20 seconds.
2. After running, output exactly one word: HALTS, DOES NOT HALT, or UNKNOWN.

What is your answer?"""


def run_eval():
    results = []
    for case in TEST_CASES:
        prompt = build_prompt(case["code"])
        model_output = call_model(prompt)
        normalized = model_output.strip().upper()
        passed = normalized == case["expected"]
        results.append(
            {
                "name": case["name"],
                "model_output": normalized,
                "expected": case["expected"],
                "passed": passed,
            }
        )
    return results


if __name__ == "__main__":
    scores = run_eval()
    for r in scores:
        status = "PASS" if r["passed"] else "FAIL"
        print(
            f"{r['name']}: model said {r['model_output']}, expected {r['expected']} -> {status}"
        )
    accuracy = sum(r["passed"] for r in scores) / len(scores)
    print(f"\nOverall accuracy: {accuracy:.0%}")
