import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from tools.memory_tool import get_memory_tool
from core.graph import save_conversation_node
from langchain_core.messages import HumanMessage, AIMessage

@pytest.mark.asyncio
async def test_get_memory_tool():
    with patch("tools.memory_tool.get_vector_store") as mock_get_store:
        mock_store = MagicMock()
        mock_retriever = AsyncMock()
        mock_store.as_retriever.return_value = mock_retriever
        mock_get_store.return_value = mock_store
        
        tool = get_memory_tool()
        
        # Verify it uses the correct collection
        mock_get_store.assert_called_with(collection_name="conversation_history")
        
        # Verify tool properties
        assert tool.name == "search_conversation_history"
        
        # Test the coroutine
        mock_doc = MagicMock()
        mock_doc.page_content = "Test content"
        mock_doc.metadata = {"role": "user", "timestamp": "2023-01-01"}
        mock_retriever.ainvoke.return_value = [mock_doc]
        
        result = await tool.coroutine("query")
        assert "Test content" in result
        assert "user" in result

@pytest.mark.asyncio
async def test_save_conversation_node_indexing():
    # Mock dependencies
    with patch("core.graph.add_message", new_callable=AsyncMock) as mock_add_message, \
         patch("core.graph.get_vector_store") as mock_get_store:
         
        mock_vector_store = MagicMock()
        mock_vector_store.add_documents = MagicMock()
        mock_get_store.return_value = mock_vector_store
        
        state = {
            "user_id": "user123",
            "chat_room_id": "room123",
            "messages": [
                HumanMessage(content="Hello"),
                AIMessage(content="Hi there")
            ],
            "model_name": "gemini-pro"
        }
        
        await save_conversation_node(state)
        
        # Verify vector store interaction
        mock_get_store.assert_called_with(collection_name="conversation_history")
        assert mock_vector_store.add_documents.called
        
        # Verify documents passed
        call_args = mock_vector_store.add_documents.call_args
        docs = call_args[0][0]
        assert len(docs) == 2
        assert docs[0].page_content == "Hello"
        assert docs[0].metadata["role"] == "user"
        assert docs[1].page_content == "Hi there"
        assert docs[1].metadata["role"] == "assistant"
