from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)

def get_llm(model_name: Optional[str] = None):
    settings = get_settings()
    api_key = settings.gemini.api_key
    
    # Use configured model if no model_name provided
    if model_name is None:
        model_name = settings.gemini.model_name
    
    logger.info(f"Initializing Gemini with model: {model_name}")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.7
    )


async def check_gemini_health() -> bool:
    """
    Checks if the Gemini API is reachable and responsive.
    """
    try:
        llm = get_llm()
        # Simple ping-like request
        response = await llm.ainvoke("ping")
        return True
    except Exception as e:
        logger.error(f"Gemini API health check failed: {e}")
        return False
