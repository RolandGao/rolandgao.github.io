from google import genai


def call_gemini_model(prompt: str) -> str:
    """
    Calls the Gemini-3-Pro-Preview model with the given prompt.
    Note: This function assumes the environment has the Google GenAI client configured.
    """
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3-pro-preview",
        contents=prompt,
    )
    return response.text
