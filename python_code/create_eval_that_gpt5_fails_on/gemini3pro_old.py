import random
from openai import OpenAI


# ---------------------------------------------------------
# Mock of the specific API usage requested in the prompt.
# In a real scenario, this would call the actual GPT-5 endpoint.
# ---------------------------------------------------------
def call_model(input_text):
    """
    Calls the hypothetical GPT-5 model with Code Interpreter enabled.
    Note: This function assumes the environment has the OpenAI client configured.
    """
    try:
        client = OpenAI()
        response = client.responses.create(
            model="gpt-5",
            tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
            input=input_text,
            reasoning={"effort": "high"},
        )
        return response.output_text
    except Exception as e:
        return f"Error calling model: {str(e)}"


# ---------------------------------------------------------
# The Evaluation Logic
# ---------------------------------------------------------


class ASCIIStroopEval:
    def __init__(self):
        # A dictionary defining 7x7 grid bitmaps for capital letters.
        # 1 represents ink, 0 represents empty space.
        self.font_map = {
            "A": [
                "   1   ",
                "  1 1  ",
                " 1   1 ",
                " 11111 ",
                " 1   1 ",
                " 1   1 ",
                " 1   1 ",
            ],
            "B": [
                " 1111  ",
                " 1   1 ",
                " 1   1 ",
                " 1111  ",
                " 1   1 ",
                " 1   1 ",
                " 1111  ",
            ],
            "C": [
                "  111  ",
                " 1   1 ",
                " 1     ",
                " 1     ",
                " 1     ",
                " 1   1 ",
                "  111  ",
            ],
            "H": [
                " 1   1 ",
                " 1   1 ",
                " 1   1 ",
                " 11111 ",
                " 1   1 ",
                " 1   1 ",
                " 1   1 ",
            ],
            "X": [
                " 1   1 ",
                " 1   1 ",
                "  1 1  ",
                "   1   ",
                "  1 1  ",
                " 1   1 ",
                " 1   1 ",
            ],
            "Z": [
                " 11111 ",
                "     1 ",
                "    1  ",
                "   1   ",
                "  1    ",
                " 1     ",
                " 11111 ",
            ],
        }

    def generate_puzzle(self):
        """
        Generates a single text-based puzzle.
        Returns:
            prompt (str): The instruction and the ASCII art.
            ground_truth (str): The letter depicted by the shape.
        """

        # 1. Select the Target Shape (Ground Truth)
        target_letter = random.choice(list(self.font_map.keys()))

        # 2. Select the Distractor Ink (The character used to draw the shape)
        # It must be different from the target to cause the Stroop effect.
        choices = list(self.font_map.keys())
        if target_letter in choices:
            choices.remove(target_letter)
        ink_char = random.choice(choices)

        # 3. Select Background Noise characters
        # Using subtle characters to make simple 'density' checks harder for code,
        # but distinct enough for human vision.
        bg_chars = [".", ",", "`"]

        # 4. Build the ASCII Grid
        bitmap = self.font_map[target_letter]
        ascii_lines = []

        for row in bitmap:
            line_str = ""
            for pixel in row:
                if pixel == "1":
                    line_str += ink_char
                else:
                    # Add noise or empty space
                    line_str += (
                        random.choice(bg_chars) if random.random() > 0.7 else " "
                    )
            ascii_lines.append(line_str)

        ascii_art = "\n".join(ascii_lines)

        # 5. Construct the Prompt
        # We explicitly tell the model to look at the shape, knowing the
        # conflict between 'ink_char' and 'target_letter' will confuse it.
        prompt = (
            "You are visually analyzing a 2D grid of text.\n"
            "The characters in the grid below are arranged to form the shape of a large capital letter.\n"
            "The specific characters used to draw the lines are 'ink' and should be ignored semantically.\n"
            "Focus ONLY on the macro-shape formed by the non-whitespace characters.\n\n"
            "Grid:\n"
            "```\n"
            f"{ascii_art}\n"
            "```\n\n"
            "Question: Which single capital letter is visually depicted above?\n"
            "Reply with the single letter only (e.g., 'Q')."
        )

        return prompt, target_letter

    def evaluate(self, num_trials=1):
        """
        Runs the evaluation loop.
        """
        print(f"Starting Stroop ASCII Eval ({num_trials} trials)...")
        score = 0

        for i in range(num_trials):
            prompt, ground_truth = self.generate_puzzle()

            print(f"\n--- Trial {i + 1} ---")
            # For debugging purposes, print the ground truth (hidden from model)
            print(f"[System] Target Shape: {ground_truth}")
            print(f"[System] Input sent to model:\n{prompt}")

            # Call the model
            try:
                output = call_model(prompt)
                cleaned_output = (
                    output.strip().upper().replace("'", "").replace('"', "")
                )

                # Extract just the first letter if the model was verbose
                if len(cleaned_output) > 1:
                    cleaned_output = cleaned_output[0]

                print(f"[Model] Output: {cleaned_output}")

                if cleaned_output == ground_truth:
                    print("Result: SUCCESS")
                    score += 1
                else:
                    print("Result: FAIL")
            except Exception as e:
                print(f"Result: ERROR ({e})")

        print(f"\nFinal Score: {score}/{num_trials}")
        return score


if __name__ == "__main__":
    # Instantiate and run the evaluation
    evaluator = ASCIIStroopEval()
    # Running 1 trial as a demonstration
    evaluator.evaluate(num_trials=5)
