from openai import OpenAI
import re


def call_model(input):
    """Provided model calling function."""
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5",
        tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
        input=input,
    )
    return response.output_text


class ASCIIVisualEval:
    def __init__(self):
        # Background spaces are replaced with dots to simulate noise.
        # This breaks simple split/strip heuristics a model might try to write,
        # but humans effortlessly filter out the background noise visually.
        self.dataset = [
            {
                "word": "SUN",
                "ascii": (
                    ".###...#...#..#...#\n"
                    "#......#...#..##..#\n"
                    ".###...#...#..#.#.#\n"
                    "....#..#...#..#..##\n"
                    ".###....###...#...#"
                ),
            },
            {
                "word": "CUP",
                "ascii": (
                    ".###...#...#..####.\n"
                    "#...#..#...#..#...#\n"
                    "#......#...#..####.\n"
                    "#...#..#...#..#....\n"
                    ".###....###...#...."
                ),
            },
        ]

    def evaluate(self):
        correct = 0
        total = len(self.dataset)

        print("Starting ASCII Visual Eval...")
        print("-" * 30)

        for i, item in enumerate(self.dataset):
            prompt = (
                "Look at the following ASCII art grid where '#' represents the foreground "
                "and '.' represents the background. It spells a 3-letter English word.\n"
                "What is the word? Reply ONLY with the 3 letters, nothing else.\n\n"
                f"{item['ascii']}"
            )

            print(f"Running test case {i + 1}/{total}...")

            # Call the model (equipped with code_interpreter)
            model_output = call_model(prompt)

            # Clean the output to extract just the alphabetic guess
            cleaned_guess = re.sub(r"[^A-Za-z]", "", model_output).upper()

            print(f"Expected: {item['word']} | Model Guess: {cleaned_guess}")

            if cleaned_guess == item["word"]:
                print(f"Result: PASS\n")
                correct += 1
            else:
                print(f"Result: FAIL\n")

        score = correct / total
        print("-" * 30)
        print(f"Final Eval Score: {score * 100}%")

        # Validation of the eval criteria
        if score == 0.0:
            print(
                "Eval criteria successfully met: The model failed completely, whereas a human can read this instantly."
            )
        else:
            print("Eval failure: The model managed to solve the puzzle.")

        return score


if __name__ == "__main__":
    evaluator = ASCIIVisualEval()
    evaluator.evaluate()
