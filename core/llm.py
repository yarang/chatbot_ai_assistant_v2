from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import load_config

def get_llm(model_name: str = None):
    config = load_config()
    api_key = config["gemini"]["api_key"]
    model = model_name or config["gemini"]["model"]
    
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.7
    )
