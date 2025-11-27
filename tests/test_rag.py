import pytest
import importlib
from unittest.mock import patch, MagicMock
from core.vector_store import get_vector_store
from tools.retrieval_tool import get_retrieval_tool

def test_get_vector_store():
    with patch("core.vector_store.PGVector") as mock_pgvector, \
         patch("core.vector_store.get_embeddings") as mock_embeddings, \
         patch("core.database.get_settings") as mock_settings:
         
        mock_settings.return_value.database.user = "user"
        mock_settings.return_value.database.password = "password"
        mock_settings.return_value.database.host = "localhost"
        mock_settings.return_value.database.port = 5432
        mock_settings.return_value.database.name = "db"
        mock_settings.return_value.gemini.api_key = "key"
        
        store = get_vector_store()
        
        assert mock_pgvector.called
        # Verify connection string
        call_args = mock_pgvector.call_args
        assert "postgresql+psycopg://user:password@localhost:5432/db" in call_args.kwargs["connection"]

def test_get_retrieval_tool():
    with patch("tools.retrieval_tool.get_vector_store") as mock_get_store, \
         patch("tools.retrieval_tool.create_retriever_tool") as mock_create_tool:
         
        mock_store = MagicMock()
        mock_get_store.return_value = mock_store
        
        tool = get_retrieval_tool()
        
        assert mock_store.as_retriever.called
        assert mock_create_tool.called
