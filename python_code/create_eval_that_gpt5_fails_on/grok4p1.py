from openai import OpenAI
import re


def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


test_cases = [
    {
        "prompt": "What is the exact product of 123456789 and 987654321?",
        "expected": "121932631112635269",
    },
    {"prompt": "What is 111111111 squared?", "expected": "12345678987654321"},
    {"prompt": "What is 20 factorial?", "expected": "2432902008176640000"},
]


def extract_number(text):
    # Extract the first sequence of digits from the output text
    match = re.search(r"\d+", text)
    return match.group(0) if match else None


def run_eval():
    results = []
    for case in test_cases:
        output = call_model(case["prompt"])
        extracted = extract_number(output)
        correct = extracted == case["expected"]
        results.append(correct)
        print(f"Prompt: {case['prompt'][:50]}...")
        print(f"Model Output: {output}")
        print(f"Extracted: {extracted}")
        print(f"Expected: {case['expected']}")
        print(f"Correct: {correct}\n")

    score = sum(1 for r in results if r) / len(results)
    print(f"Overall Score: {score:.2f} ({sum(results)}/{len(results)})")
    return score


if __name__ == "__main__":
    run_eval()
