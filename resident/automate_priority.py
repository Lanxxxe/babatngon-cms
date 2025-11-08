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

def prompt_details(details: dict) -> str:
    prompt = f"""
    Determine the priority level for the following case details:
    {details}
    """

    return prompt

def main():
    details = {
        "Subject" : "Broken Streetlight",
        "Description" : "The streetlight on 5th Avenue has been flickering for weeks, causing safety concerns for pedestrians at night.",
        "Category" : "Public Safety",
        "Area Description" : "Residential Area",
        "Location" : "5th Avenue, Downtown"
    }

    prompt = f"""
    Determine the priority level for the following case details:
    {details}
    """

    priority = generate_priority(prompt)
    print(f"Response type: {type(priority)}")
    print(f"Generated Priority: {priority}")

# if __name__ == "__main__":
#     main()