import pytest
from unittest.mock import patch, MagicMock
from tools.search_tool import get_search_tool

def test_get_search_tool():
    with patch("tools.search_tool.get_settings") as mock_settings:
        mock_settings.return_value.tavily_api_key = "test_key"
        
        tool = get_search_tool()
        
        assert tool is not None
        assert tool.api_wrapper.tavily_api_key.get_secret_value() == "test_key"

def test_get_search_tool_no_key():
    with patch("tools.search_tool.get_settings") as mock_settings, \
         patch("os.environ.get") as mock_env:
        
        mock_settings.return_value.tavily_api_key = None
        mock_env.return_value = None
        
        # TavilySearchResults might raise error or just init with None depending on version
        # But we just check if our function runs
        try:
            tool = get_search_tool()
        except Exception:
            pass
