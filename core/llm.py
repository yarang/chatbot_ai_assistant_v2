from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)

def get_llm(model_name: Optional[str] = None):
    settings = get_settings()
    llm_api = settings.llm_api.lower()
    
    # 1. Local LLM (Explicitly set or legacy flag)
    if llm_api == "local" or settings.local_llm.enabled:
        base_url = settings.local_llm.base_url
        if not base_url:
            logger.warning("Local LLM selected but LOCAL_LLM_BASE_URL is not set. Falling back to Gemini.")
            # Verify if fallback should happen or error out. Continuing to Gemini flow.
        else:
            local_model = settings.local_llm.model
            if model_name and model_name != local_model:
                logger.info(f"Local LLM selected. Overriding requested model '{model_name}' with local model '{local_model}'")
            
            # OpenAI client for Local/Exo
            logger.info(f"Initializing Local LLM with model: {local_model} at {base_url}")
            return ChatOpenAI(
                base_url=base_url,
                api_key="not-needed", # Local usually doesn't need key, or provided in env
                model=local_model,
                temperature=0.7
            )

    # 2. Groq
    if llm_api == "groq":
        api_key = settings.groq.api_key
        if not api_key:
             logger.error("Groq API key not found. Please set GROQ_API_KEY in .env")
             # Fallback to Gemini if key missing? Or raise error? 
             # For now, let's fall through or error. 
             # If we return None, it will break. Let's try to proceed or fallback.
        else:
            # Use configured model if no model_name provided
            if model_name is None:
                model_name = settings.groq.model_name
            
            # If model_name is a Gemini model but we are in Groq mode, force Groq model
            if model_name.lower().startswith("gemini"):
                logger.warning(f"Groq API selected but Gemini model '{model_name}' requested. Overriding with default Groq model: {settings.groq.model_name}")
                model_name = settings.groq.model_name
            
            logger.info(f"Initializing Groq with model: {model_name}")
            return ChatOpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key,
                model=model_name,
                temperature=0.7
            )

    # 3. Z.ai (Zhipu AI)
    if llm_api in ["z.ai", "zai"]:
        api_key = settings.zai.api_key
        if not api_key:
            logger.error("Z.ai API key not found. Please set ZAI_API_KEY in .env")
        else:
            if model_name is None:
                model_name = settings.zai.model_name
            
            # Handle Gemini/Groq model name leak
            if model_name.lower().startswith("gemini") or model_name.lower().startswith("llama"):
                 logger.warning(f"Z.ai API selected but incompatible model '{model_name}' requested. Overriding with default Z.ai model: {settings.zai.model_name}")
                 model_name = settings.zai.model_name

            logger.info(f"Initializing Z.ai with model: {model_name}")
            return ChatOpenAI(
                base_url="https://open.bigmodel.cn/api/paas/v4",
                api_key=api_key,
                model=model_name,
                temperature=0.7
            )

    # 4. Gemini (Default)
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
        await llm.ainvoke("ping")
        return True
    except Exception as e:
        logger.error(f"LLM API health check failed: {e}")
        return False
