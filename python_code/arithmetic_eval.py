from openai import OpenAI
import json
import re
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, InvalidOperation, getcontext
from typing import Any, Dict, Optional


def call_model(input_text: str) -> str:
    """Send the prompt to gpt-5 and return the raw text output."""
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        input=input_text,
    )
    return response.output_text


# Configure decimal precision high enough for the eval set
getcontext().prec = 28

# Regex to capture the first numeric token (optionally signed with decimals)
NUMBER_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?")

# Allow tiny rounding differences when comparing model outputs
NUMERIC_TOLERANCE = Decimal("0.000001")

# Definition of the arithmetic evaluation set
EVAL_SET = [
    {
        "name": "bigint_cross_multiply",
        "question": "1234567890123456789*9876543210987654321=",
        "expected": "12193263113702179522374638011112635269",
    },
    {
        "name": "near_power_of_ten_product",
        "question": "999999999999999999*888888888888888888=",
        "expected": "888888888888888887111111111111111112",
    },
    {
        "name": "pi_times_e_precision",
        "question": "314159265358979323846*271828182845904523536=",
        "expected": "85397342226735670654554622909226073039456",
    },
    {
        "name": "repeated_digit_blocks",
        "question": "11111111111111111111*22222222222222222222=",
        "expected": "246913580246913580241975308641975308642",
    },
    {
        "name": "alternating_digit_product",
        "question": "13579135791357913579*24680246802468024680=",
        "expected": "335136422694940256528933958626279129720",
    },
    {
        "name": "almost_square_large",
        "question": "100000000000000000001*100000000000000000003=",
        "expected": "10000000000000000000400000000000000000003",
    },
    {
        "name": "max_uint64_square",
        "question": "18446744073709551615*18446744073709551615=",
        "expected": "340282366920938463426481119284349108225",
    },
    {
        "name": "large_even_blocks",
        "question": "42949672964294967296*65536000006553600000=",
        "expected": "2814749767669509953449459497671065600000",
    },
    {
        "name": "mixed_length_product",
        "question": "98765432123456789*123456789987654321=",
        "expected": "12193263211705532552354824112635269",
    },
    {
        "name": "staggered_pairs",
        "question": "11223344556677889900*99887766554433221100=",
        "expected": "1121074821037409877779037412408156890000",
    },
    {
        "name": "very_long_sequences",
        "question": "1234567890123456789012345*5432109876543210987654321=",
        "expected": "6706308429202743325773481771063937052277861592745",
    },
    {
        "name": "prime_like_square",
        "question": "9999991*9999991=",
        "expected": "99999820000081",
    },
]


def build_prompt(question: str) -> str:
    """Ensure every prompt starts with the required instruction."""
    return f"do not use tools. {question}"


def parse_numeric_response(raw_output: str) -> Optional[Decimal]:
    """Extract the first numeric value from the model response, if present."""
    if not raw_output:
        return None
    sanitized = raw_output.replace(",", "")
    match = NUMBER_PATTERN.search(sanitized)
    if not match:
        return None
    token = match.group(0)
    try:
        return Decimal(token)
    except InvalidOperation:
        return None


def evaluate_output(output: str, expected: Decimal) -> Dict[str, Any]:
    """Compare the model output against the expected value."""
    parsed = parse_numeric_response(output)
    if parsed is None:
        return {
            "pass": False,
            "detail": "no numeric answer found",
            "parsed": None,
        }

    delta = abs(parsed - expected)
    if delta <= NUMERIC_TOLERANCE:
        return {
            "pass": True,
            "detail": f"answer matches within tolerance (Δ={delta})",
            "parsed": str(parsed),
        }
    return {
        "pass": False,
        "detail": f"expected {expected} but got {parsed} (Δ={delta})",
        "parsed": str(parsed),
    }


def run_eval() -> None:
    """Run the arithmetic eval set against gpt-5."""
    def _run_task(index: int, item: Dict[str, str]) -> Dict[str, Any]:
        prompt = build_prompt(item["question"])
        expected_decimal = Decimal(item["expected"])
        raw_output = call_model(prompt)
        evaluation = evaluate_output(raw_output, expected_decimal)
        return {
            "index": index,
            "name": item["name"],
            "question": item["question"],
            "prompt": prompt,
            "expected": str(expected_decimal),
            "raw_output": raw_output,
            "evaluation": evaluation,
        }

    results = []
    max_workers = min(8, len(EVAL_SET)) or 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_run_task, index, item)
            for index, item in enumerate(EVAL_SET, start=1)
        ]
        for future in futures:
            results.append(future.result())

    results.sort(key=lambda r: r["index"])

    printable_results = []
    for result in results:
        raw_output = result["raw_output"]
        eval_detail = result["evaluation"]
        parsed_output = eval_detail["parsed"]
        passed = eval_detail["pass"]

        display_output = raw_output if raw_output != "" else "<EMPTY STRING>"
        print(f"\n=== Problem {result['index']}: {result['name']} ===")
        print(f"Prompt: {result['prompt']}")
        print(f"Model output: {display_output}")
        print(f"Result: {'PASS' if passed else 'FAIL'} — {eval_detail['detail']}")

        printable_results.append(
            {
                "name": result["name"],
                "question": result["question"],
                "prompt": result["prompt"],
                "expected": result["expected"],
                "raw_output": raw_output,
                "parsed_output": parsed_output,
                "pass": passed,
                "detail": eval_detail["detail"],
            }
        )

    total = len(printable_results)
    passed = sum(1 for r in printable_results if r["pass"])

    print("\n=== SUMMARY ===")
    print(
        json.dumps(
            {
                "total": total,
                "passed": passed,
                "failed": total - passed,
                "details": printable_results,
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    if passed < total:
        raise SystemExit(1)


if __name__ == "__main__":
    run_eval()
