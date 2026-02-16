from openai import OpenAI


def call_model(input_text: str) -> str:
    """
    Calls the hypothetical gpt-5 model with code_interpreter enabled,
    as specified by the provided requirements.
    """
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input_text,
    )
    return response.output_text


def run_eval():
    """
    Runs the 'Floating-Point Mirage' evaluation.
    """
    prompt = """Consider the following sequence of mathematical operations defined for a strictly positive integer x (x > 0):

1. Let a = x^2
2. Let b = a^2 + 1
3. Let c = sqrt(b)
4. Let d = sqrt(c)

We are looking for the smallest strictly positive integer x such that the exact mathematical value of d is perfectly equal to x. 

If you can find such a positive integer, output ONLY that integer. 
If it can be mathematically proven that no such integer exists, output ONLY the exact word 'NONE'.
Do not include any other text, explanation, or punctuation."""

    print("Running eval... waiting for model response.")
    output = call_model(prompt).strip()

    # ---------------------------------------------------------
    # EVALUATION LOGIC & EXPECTATIONS
    # ---------------------------------------------------------
    # The mathematical truth is:
    # d = sqrt(sqrt(x^4 + 1)) = (x^4 + 1)^(1/4)
    # Setting d = x implies:
    # x = (x^4 + 1)^(1/4)  =>  x^4 = x^4 + 1  =>  0 = 1
    # Thus, it is mathematically impossible. A human uses algebra and outputs 'NONE'.
    #
    # However, Python's 64-bit float mantissa maxes out at 2^53.
    # For x >= 9742, x^4 + 1 exceeds 2^53. Python's float conversion drops the '+ 1'.
    # Thus, math.sqrt(math.sqrt(float(x^4 + 1))) perfectly evaluates to x.
    # The LLM's code_interpreter will find 9742 (or a nearby integer) as a valid solution.
    # The LLM will trust its code over algebra and output '9742', failing the eval.
    # ---------------------------------------------------------

    expected_answer = "NONE"

    # We clean the output just in case the model added periods or backticks
    clean_output = output.replace("`", "").replace(".", "").strip().upper()
    success = clean_output == expected_answer

    print("\n--- Eval Results ---")
    print(f"Model Output: {output}")
    print(f"Expected:     {expected_answer}")
    print(f"Pass:         {success}")

    return success


if __name__ == "__main__":
    run_eval()
