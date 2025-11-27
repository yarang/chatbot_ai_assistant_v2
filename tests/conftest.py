import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Set dummy env vars for Pydantic Settings validation
os.environ["TELEGRAM__BOT_TOKEN"] = "dummy_token"
os.environ["GEMINI__API_KEY"] = "dummy_key"
os.environ["TAVILY_API_KEY"] = "dummy_key"

# Mock telegram module to avoid import errors during tests
mock_telegram = MagicMock()
mock_telegram.Update = MagicMock
mock_telegram.Bot = MagicMock
mock_telegram.User = MagicMock
mock_telegram.Chat = MagicMock
mock_telegram.Message = MagicMock
sys.modules["telegram"] = mock_telegram

from langchain_core.tools import BaseTool

# Mock GoogleGenerativeAIEmbeddings to avoid auth errors during import
mock_embeddings = MagicMock()
sys.modules["langchain_google_genai"] = MagicMock()
sys.modules["langchain_google_genai"].GoogleGenerativeAIEmbeddings = mock_embeddings

# Mock PGVector to avoid DB connection during import
mock_pgvector = MagicMock()
sys.modules["langchain_postgres"] = MagicMock()
sys.modules["langchain_postgres"].PGVector = mock_pgvector

from langchain_core.tools import BaseTool

class MockTool(BaseTool):
    name: str = "search_internal_knowledge"
    description: str = "Mock tool"
    def _run(self, query: str): return "mock result"
    async def _arun(self, query: str): return "mock result"

from unittest.mock import patch

# Mock create_retriever_tool globally to return a valid BaseTool
# This is needed because core/graph.py calls get_retrieval_tool() at import time
patcher = patch("langchain_core.tools.create_retriever_tool", return_value=MockTool())
patcher.start()

# Also patch where it might be imported directly if needed, but patching the source should work if done early

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
