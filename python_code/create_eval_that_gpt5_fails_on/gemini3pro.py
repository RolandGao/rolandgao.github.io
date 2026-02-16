import random
import string
from openai import OpenAI


# Provided model call function
def call_model(input):
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


def run_eval():
    """
    Runs the Autoregressive Copy-Paste Bottleneck Eval.
    """
    print("Generating eval data...")

    # 1. Generate a massive list of random 5-letter alphabetical tokens.
    # We use random tokens to prevent the LLM from relying on semantic compression
    # or existing patterns in its training data.
    vocab_size = 10000
    vocab = [
        "".join(random.choices(string.ascii_lowercase, k=5)) for _ in range(vocab_size)
    ]

    # Select exactly 5000 unique tokens
    prompt_tokens = random.sample(vocab, 5000)

    # 2. Pick a deep, random target index that is impossible to count via pure attention
    target_index = random.randint(3000, 4800)
    target_word = prompt_tokens[target_index]

    # 3. Construct the prompt
    # The instruction is clear, restricting the output to just the target word.
    text_block = " ".join(prompt_tokens)
    prompt = (
        f"Below is a string of 5000 space-separated random words. "
        f"Your task is to extract the word exactly at index {target_index} (0-indexed) "
        f"from this list. You must use your code interpreter to ensure accuracy. "
        f"Output ONLY the exact word and nothing else.\n\n"
        f"{text_block}"
    )

    # 4. Execute the model call
    print(f"Calling gpt-5 to find the word at index {target_index}...")
    try:
        model_output = call_model(prompt).strip()
    except Exception as e:
        model_output = f"API Error: {e}"

    # 5. Evaluate the result
    # We strip punctuation just in case the model adds a period to its response
    cleaned_output = "".join(char for char in model_output if char.isalpha())

    success = cleaned_output == target_word

    print("-" * 30)
    print(f"Target Word Expected : {target_word}")
    print(f"Model Output Received: {model_output}")
    print(f"Eval Result          : {'PASS' if success else 'FAIL'}")
    print("-" * 30)

    return success


if __name__ == "__main__":
    run_eval()
