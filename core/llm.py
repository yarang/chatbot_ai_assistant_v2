from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)

def get_llm(model_name: Optional[str] = None):
    settings = get_settings()
    
    # Check if we should use Local LLM (e.g. Exo, Ollama)
    if settings.use_local_llm:
        base_url = settings.local_llm_base_url
        if not base_url:
            logger.warning("USE_LOCAL_LLM is True but LOCAL_LLM_BASE_URL is not set. Falling back to Gemini.")
        else:
            # Force using the configured local model to avoid sending cloud model names (e.g. gemini-pro) to local server
            local_model = settings.local_llm_model
            if model_name and model_name != local_model:
                logger.info(f"USE_LOCAL_LLM is True. Overriding requested model '{model_name}' with local model '{local_model}'")
            
            api_key = settings.local_llm_api_key
            
            logger.info(f"Initializing Local LLM (Exo/OpenAI) with model: {local_model} at {base_url}")
            return ChatOpenAI(
                base_url=base_url,
                api_key=api_key,
                model=local_model,
                temperature=0.7
            )

    # Fallback / Default to Gemini
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


async def check_llm_health() -> bool:
    """
    Checks if the configured LLM API is reachable and responsive.
    """
    try:
        llm = get_llm()
        # Simple ping-like request
        response = await llm.ainvoke("ping")
        return True
    except Exception as e:
        logger.error(f"LLM API health check failed: {e}")
        return False
