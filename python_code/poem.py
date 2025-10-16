from openai import OpenAI

client = OpenAI()

result = client.responses.create(
    model="gpt-5",
    input="what's the meaning of life?",
    # reasoning={"effort": "low"},
    # text={"verbosity": "low"},
)

print(result.output_text)
