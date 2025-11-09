from google import genai
from google.genai import types
from decouple import config


def generate_priority(prompt: str) -> str:
    client = genai.Client(api_key=config("GEMINI_API_KEY"))

    system_instruction = f"""
    Based on the following details given by the user, determine the priority level of the case.
    You response should be ONLY a single word. The priority levels are: Low, Medium, High, Urgent.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            response_modalities=['TEXT'],
            thinking_config=types.ThinkingConfig(
                thinking_budget=0
            ),
            system_instruction=system_instruction
        ),
        contents=prompt,
    )

    return response.candidates[0].content.parts[0].text

def prompt_details(details: dict, is_follow_up: bool = False) -> str:
    prompt = ""
    if is_follow_up:
        prompt = f"""
        Update the priority level base on the follow up message of the user on the following case details:
        {details}
        """

    else:   
        prompt = f"""
        Determine the priority level for the following case details:
        {details}
        """

    return prompt
