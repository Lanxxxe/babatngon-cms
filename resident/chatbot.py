from google import genai
from google.genai import types
from decouple import config


def get_chatbot_response(user_prompt: str) -> str:
    """
    Generate chatbot response from Gemini AI with minimal token usage
    """
    client = genai.Client(api_key=config("GEMINI_API_KEY"))

    system_instruction = """
    You are a helpful Barangay CMS assistant. Provide concise, helpful responses about barangay services.
    Keep responses under 50 words. Focus on directing users to specific features or providing brief information.
    Available features: File Complaint, Request Assistance, My Complaints, My Assistance, Profile, Notifications.
    """

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash-8b",  # Smaller, cheaper model
            config=types.GenerateContentConfig(
                response_modalities=['TEXT'],
                max_output_tokens=100,  # Limit output tokens
                temperature=0.3,  # Lower creativity for consistent responses
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0  # No thinking budget to save tokens
                ),
                system_instruction=system_instruction
            ),
            contents=user_prompt,
        )
        
        return response.candidates[0].content.parts[0].text.strip()
    
    except Exception as e:
        return get_fallback_response(user_prompt)


def get_fallback_response(user_prompt: str) -> str:
    """
    Provide fallback responses without API calls to save tokens
    """
    prompt_lower = user_prompt.lower()
    
    # Common barangay-related queries
    if any(word in prompt_lower for word in ['complaint', 'report', 'problem']):
        return "Use 'File Complaint' in the sidebar to report issues or concerns."
    
    elif any(word in prompt_lower for word in ['assistance', 'help', 'support']):
        return "Go to 'Request Assistance' to submit your assistance request."
    
    elif any(word in prompt_lower for word in ['status', 'track', 'check']):
        return "Check 'My Complaints' and 'My Assistance' for status updates."
    
    elif any(word in prompt_lower for word in ['profile', 'account', 'update']):
        return "Visit your 'Profile' section to update your information."
    
    elif any(word in prompt_lower for word in ['notification', 'alert']):
        return "Check the 'Notifications' section for updates and alerts."
    
    elif any(word in prompt_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I can help you navigate the Barangay CMS. What do you need?"
    
    elif any(word in prompt_lower for word in ['thank', 'thanks']):
        return "You're welcome! Let me know if you need more help."
    
    else:
        return "I can help with complaints, assistance requests, status tracking, and navigation. What do you need?"


def chunk_long_prompt(prompt: str, max_length: int = 100) -> str:
    """
    Truncate long prompts to save input tokens
    """
    if len(prompt) > max_length:
        return prompt[:max_length] + "..."
    return prompt


def is_simple_query(prompt: str) -> bool:
    """
    Check if query can be answered with fallback responses
    """
    simple_keywords = [
        'hello', 'hi', 'hey', 'thanks', 'thank',
        'complaint', 'assistance', 'status', 'profile', 
        'notification', 'help', 'support'
    ]
    
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in simple_keywords)


def get_smart_response(user_prompt: str) -> str:
    """
    Smart response function that uses fallback when possible to save tokens
    """
    # Truncate long prompts
    chunked_prompt = chunk_long_prompt(user_prompt)
    
    # Use fallback for simple queries
    if is_simple_query(chunked_prompt):
        return get_fallback_response(chunked_prompt)
    
    # Use AI for complex queries
    return get_chatbot_response(chunked_prompt)
