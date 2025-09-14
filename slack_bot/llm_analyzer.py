# llm_analyzer.py
# This module uses Google's Gemini AI API for analyzing user messages
# Required environment variable: GEMINI_API_KEY
import google.generativeai as genai
import json
import logging
import os

logging.basicConfig(level=logging.INFO)

def analyze_user_messages(user_conversation_text):
    """Sends a single user's conversations to the LLM for analysis."""
    
    # Configure Gemini API
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # Initialize the model
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    system_prompt = """
    You are an expert analyst. Your task is to analyze a user's messages from a philanthropy-focused Slack channel.
    Extract the following information. Be concise and use short phrases, not sentences. Return the answer as a valid JSON object.

    - strengths: Key strengths based on their contributions (e.g., "Strategic Planning", "Donor Relations").
    - interests: Primary philanthropic interests (e.g., "Education", "Climate Change").
    - expertise: Areas of professional expertise (e.g., "Legal", "Finance", "Marketing").

    If you cannot determine a value for a category, return an empty list for it.
    """

    user_prompt = f"Analyze the following messages from a single user:\n\n{user_conversation_text}"
    
    # Combine system and user prompts for Gemini
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    try:
        response = model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text) # Returns a dict like {"strengths": [...], ...}
    except Exception as e:
        logging.error(f"LLM analysis failed: {e}")
        return {
            "strengths": [],
            "interests": [],
            "expertise": [],
            "communication_style": []
        }