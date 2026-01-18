"""
Multi-engine web search tool implementation.

Supports:
- DuckDuckGo (default, free, no API key required)
- Tavily (premium, excellent results)
- Google Custom Search (free tier: 100 queries/day)
"""

import logging

from langchain_core.tools import Tool
from langchain_community.tools.ddg_search import DuckDuckGoSearchRun
from langchain_community.tools.tavily_search import TavilySearchResults

# Google search is optional
try:
    from langchain_google_community import GoogleSearchAPIWrapper
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

from core.config import get_settings

logger = logging.getLogger(__name__)


def get_ddg_search_tool(max_results: int = 3) -> Tool:
    """
    DuckDuckGo 검색 도구를 반환합니다.
    무료이며 API 키가 필요하지 않습니다.

    Args:
        max_results: 반환할 최대 검색 결과 수

    Returns:
        Tool: DuckDuckGo 검색 도구
    """
    try:
        search = DuckDuckGoSearchRun()
        search.description = (
            "Searches the web using DuckDuckGo. "
            "Useful for finding current information, facts, and online content. "
            "Input should be a search query string."
        )
        logger.info("DuckDuckGo search tool initialized")
        return search
    except Exception as e:
        logger.error(f"Failed to initialize DuckDuckGo search: {e}")
        raise


def get_tavily_search_tool(api_key: str, max_results: int = 3) -> Tool:
    """
    Tavily 검색 도구를 반환합니다.
    유료 서비스이지만 우수한 검색 결과를 제공합니다.

    Args:
        api_key: Tavily API 키
        max_results: 반환할 최대 검색 결과 수

    Returns:
        Tool: Tavily 검색 도구
    """
    if not api_key:
        raise ValueError("Tavily API key is required for Tavily search engine")

    try:
        search = TavilySearchResults(
            max_results=max_results,
            tavily_api_key=api_key,
            search_depth="advanced",  # basic or advanced
            include_answer=True,
            include_raw_content=False,
            include_images=False,
        )
        logger.info("Tavily search tool initialized")
        return search
    except Exception as e:
        logger.error(f"Failed to initialize Tavily search: {e}")
        raise


def get_google_search_tool(
    api_key: str,
    cse_id: str,
    max_results: int = 3,
) -> Tool:
    """
    Google Custom Search 검색 도구를 반환합니다.
    무료 tier는 하루 100회 쿼리를 제공합니다.

    Args:
        api_key: Google API 키
        cse_id: Google Custom Search Engine ID
        max_results: 반환할 최대 검색 결과 수

    Returns:
        Tool: Google 검색 도구
    """
    if not GOOGLE_AVAILABLE:
        raise ImportError(
            "langchain-google-community is not installed. "
            "Install it with: pip install langchain-google-community"
        )

    if not api_key or not cse_id:
        raise ValueError(
            "Google API key and CSE ID are required for Google search engine"
        )

    try:
        wrapper = GoogleSearchAPIWrapper(
            google_api_key=api_key,
            google_cse_id=cse_id,
            k=max_results,  # Number of results
        )

        # Create a tool from the wrapper
        search = Tool(
            name="google_search",
            description=(
                "Searches the web using Google Custom Search. "
                "Useful for finding current information, facts, and online content. "
                "Input should be a search query string."
            ),
            func=wrapper.run,
        )
        logger.info("Google search tool initialized")
        return search
    except Exception as e:
        logger.error(f"Failed to initialize Google search: {e}")
        raise


def get_search_tool() -> Tool:
    """
    설정된 검색 엔진에 따라 적절한 검색 도구를 반환합니다.

    검색 엔진 우선순위:
    1. SEARCH_ENGINE 환경변수로 지정된 엔진
    2. DuckDuckGo (기본값, 무료)

    Returns:
        Tool: 검색 도구 인스턴스

    Raises:
        ValueError: 지원되지 않는 검색 엔진 또는 필수 API 키 누락
    """
    settings = get_settings()
    search_config = settings.search
    engine = search_config.engine.lower()
    max_results = search_config.max_results

    # Backward compatibility: Use old tavily_api_key if search.tavily_api_key is not set
    tavily_key = search_config.tavily_api_key or settings.tavily_api_key

    logger.info(f"Initializing search tool with engine: {engine}")

    if engine == "ddg" or engine == "duckduckgo":
        # DuckDuckGo - No API key required (default)
        return get_ddg_search_tool(max_results=max_results)

    elif engine == "tavily":
        # Tavily - Requires API key
        if not tavily_key:
            logger.warning(
                "Tavily API key not found. Falling back to DuckDuckGo search."
            )
            return get_ddg_search_tool(max_results=max_results)

        return get_tavily_search_tool(api_key=tavily_key, max_results=max_results)

    elif engine == "google":
        # Google Custom Search - Requires API key and CSE ID
        google_key = search_config.google_api_key
        cse_id = search_config.google_cse_id

        if not google_key or not cse_id:
            logger.warning(
                "Google API key or CSE ID not found. Falling back to DuckDuckGo search."
            )
            return get_ddg_search_tool(max_results=max_results)

        return get_google_search_tool(
            api_key=google_key, cse_id=cse_id, max_results=max_results
        )

    else:
        logger.warning(
            f"Unknown search engine: {engine}. Falling back to DuckDuckGo."
        )
        return get_ddg_search_tool(max_results=max_results)
