from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import get_settings

def get_llm(model_name: Optional[str] = None):
    settings = get_settings()
    api_key = settings.gemini.api_key
    
    # Use configured model if no model_name provided
    if model_name is None:
        model_name = settings.gemini.model_name
    
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.7
    )
