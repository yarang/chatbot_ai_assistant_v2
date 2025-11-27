import os
from langchain_tavily import TavilySearch
from langchain_core.tools import Tool
from core.config import get_settings

def get_search_tool():
    """
    Tavily Search Tool을 반환합니다.
    """
    settings = get_settings()
    # TavilySearchResults automatically looks for TAVILY_API_KEY env var,
    # but we can also pass it explicitly if we loaded it from config.
    api_key = settings.tavily_api_key
    
    if not api_key:
        # Fallback to os.getenv if not in config (though config should load it)
        api_key = os.getenv("TAVILY_API_KEY")
        
        print("Warning: TAVILY_API_KEY not found. Search tool may fail.")
    
    # Initialize the tool
    # max_results=3 is a reasonable default
    tool = TavilySearch(
        max_results=3,
        tavily_api_key=api_key
    )
    return tool
