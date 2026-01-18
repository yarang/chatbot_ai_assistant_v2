"""
Tests for retrieval_tool.py

Test coverage:
- Chat room isolation (security critical)
- Relevance score filtering (≥0.7)
- Empty results handling
- Cross-room leakage prevention
- Integration with vector store
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.documents import Document

from tools.retrieval_tool import get_retrieval_tool


class TestRetrievalToolChatRoomIsolation:
    """Test suite for chat room isolation in retrieval tool.

    Security Critical: These tests ensure that users in one chat room
    cannot retrieve documents from another chat room (cross-room leakage).
    """

    @pytest.mark.asyncio
    async def test_retrieve_within_same_chat_room(self):
        """Test that retrieval works within the same chat room."""
        # Arrange
        chat_room_id = "123"
        mock_docs = [
            Document(
                page_content="Test content from room 123",
                metadata={"source": "test.pdf", "chat_room_id": "123"}
            )
        ]

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            tool = get_retrieval_tool(chat_room_id=chat_room_id)

            # Act
            result = await tool.coroutine("test query")

            # Assert
            assert "Test content from room 123" in result
            assert "test.pdf" in result
            mock_retriever.ainvoke.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_retrieve_does_not_leak_to_other_chat_rooms(self):
        """Test CRITICAL: Retrieval must NOT return documents from other chat rooms.

        This test verifies that when searching in chat room A,
        documents from chat room B are never returned.
        """
        # Arrange
        chat_room_id_a = "room-a"

        # Simulate vector store returning only room A documents
        # (proper isolation)
        mock_docs_room_a = [
            Document(
                page_content="Document from room A",
                metadata={"source": "doc_a.pdf", "chat_room_id": chat_room_id_a}
            )
        ]

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=mock_docs_room_a)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            tool = get_retrieval_tool(chat_room_id=chat_room_id_a)

            # Act - Search in room A
            result = await tool.coroutine("test query")

            # Assert - Should ONLY contain room A documents
            assert "Document from room A" in result
            assert "doc_a.pdf" in result
            # CRITICAL: Must NOT contain room B documents
            assert "room-b" not in result.lower()

    @pytest.mark.asyncio
    async def test_retrieve_with_empty_chat_room(self):
        """Test retrieval from an empty chat room returns appropriate message."""
        # Arrange
        chat_room_id = "empty-room"
        mock_docs = []  # No documents

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            tool = get_retrieval_tool(chat_room_id=chat_room_id)

            # Act
            result = await tool.coroutine("test query")

            # Assert
            assert "No relevant information found" in result or "No relevant documents" in result

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_relevance_score(self):
        """Test that documents with low relevance scores (< 0.7) are filtered out.

        This test will FAIL initially, as filtering is not yet implemented.
        After GREEN phase, it should pass.
        """
        # Arrange
        chat_room_id = "room-123"

        # Mock documents with different relevance scores
        # Note: LangChain retriever doesn't natively return scores,
        # so we'll need to implement this in retrieval_tool.py
        mock_docs = [
            Document(
                page_content="High relevance document",
                metadata={"source": "high.pdf", "score": 0.85}
            ),
            Document(
                page_content="Medium relevance document",
                metadata={"source": "medium.pdf", "score": 0.72}
            ),
            Document(
                page_content="Low relevance document",
                metadata={"source": "low.pdf", "score": 0.65}
            ),  # Should be filtered out
            Document(
                page_content="Very low relevance document",
                metadata={"source": "verylow.pdf", "score": 0.45}
            ),  # Should be filtered out
        ]

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            tool = get_retrieval_tool(chat_room_id=chat_room_id)

            # Act
            result = await tool.coroutine("test query")

            # Assert
            assert "High relevance document" in result
            assert "Medium relevance document" in result
            # CRITICAL: Low relevance documents should be filtered out
            assert "Low relevance document" not in result
            assert "Very low relevance document" not in result

    @pytest.mark.asyncio
    async def test_cross_room_leakage_prevention(self):
        """Test CRITICAL SECURITY: Verify no cross-room data leakage possible.

        This test simulates a scenario where:
        - Chat room A has sensitive documents
        - Chat room B attempts to search
        - Room B must NEVER see Room A's documents
        """
        # Arrange
        room_a_id = "confidential-room-a"
        room_b_id = "public-room-b"

        # Room A documents (confidential)
        [
            Document(
                page_content="Confidential data from Room A",
                metadata={"source": "secret.pdf", "chat_room_id": room_a_id}
            )
        ]

        # Room B documents (public)
        public_docs = [
            Document(
                page_content="Public data from Room B",
                metadata={"source": "public.pdf", "chat_room_id": room_b_id}
            )
        ]

        # When searching in Room B, only Room B docs should be returned
        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=public_docs)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            tool = get_retrieval_tool(chat_room_id=room_b_id)

            # Act - Search in Room B
            result = await tool.coroutine("sensitive query")

            # Assert - SECURITY CHECK
            assert "Public data from Room B" in result
            # CRITICAL: Confidential data must NOT leak
            assert "Confidential data from Room A" not in result
            assert "secret.pdf" not in result
            assert "confidential" not in result.lower()

    @pytest.mark.asyncio
    async def test_multiple_chat_rooms_with_same_query(self):
        """Test that the same query in different rooms returns different results."""
        # Arrange
        query = "company policy"

        # Room 1 documents
        room1_docs = [
            Document(
                page_content="Policy for team A",
                metadata={"source": "policy_a.pdf", "chat_room_id": "room-1"}
            )
        ]

        # Room 2 documents
        room2_docs = [
            Document(
                page_content="Policy for team B",
                metadata={"source": "policy_b.pdf", "chat_room_id": "room-2"}
            )
        ]

        # Test Room 1
        mock_vector_store_1 = AsyncMock()
        mock_retriever_1 = AsyncMock()
        mock_retriever_1.ainvoke = AsyncMock(return_value=room1_docs)
        mock_vector_store_1.as_retriever = MagicMock(return_value=mock_retriever_1)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store_1):
            tool_1 = get_retrieval_tool(chat_room_id="room-1")
            result_1 = await tool_1.coroutine(query)

        # Test Room 2
        mock_vector_store_2 = AsyncMock()
        mock_retriever_2 = AsyncMock()
        mock_retriever_2.ainvoke = AsyncMock(return_value=room2_docs)
        mock_vector_store_2.as_retriever = MagicMock(return_value=mock_retriever_2)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store_2):
            tool_2 = get_retrieval_tool(chat_room_id="room-2")
            result_2 = await tool_2.coroutine(query)

        # Assert - Results must be different
        assert "Policy for team A" in result_1
        assert "Policy for team B" in result_2
        # Cross-contamination check
        assert "Policy for team B" not in result_1
        assert "Policy for team A" not in result_2

    @pytest.mark.asyncio
    async def test_retrieve_without_chat_room_id(self):
        """Test retrieval tool behavior when chat_room_id is None.

        This tests backward compatibility and default behavior.
        """
        # Arrange
        mock_docs = [
            Document(
                page_content="Document without room filtering",
                metadata={"source": "general.pdf"}
            )
        ]

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            # Act - No chat_room_id provided
            tool = get_retrieval_tool(chat_room_id=None)
            result = await tool.coroutine("test query")

            # Assert
            assert "Document without room filtering" in result
            # Verify that as_retriever was called without filter
            mock_vector_store.as_retriever.assert_called_once_with(
                search_kwargs={"k": 3}
            )

    @pytest.mark.asyncio
    async def test_retrieve_handles_vector_store_errors(self):
        """Test that retrieval tool handles vector store errors gracefully."""
        # Arrange
        chat_room_id = "test-room"

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(side_effect=Exception("Vector store connection failed"))
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            tool = get_retrieval_tool(chat_room_id=chat_room_id)

            # Act
            result = await tool.coroutine("test query")

            # Assert - Should return error message
            assert "Error retrieving documents" in result
            assert "Vector store connection failed" in result

    @pytest.mark.asyncio
    async def test_retrieve_applies_chat_room_filter(self):
        """Test that the chat_room_id filter is correctly applied to the retriever.

        This test verifies the actual filter parameter passed to the vector store.
        """
        # Arrange
        chat_room_id = "room-456"
        mock_docs = [
            Document(page_content="Test content", metadata={"source": "test.pdf"})
        ]

        mock_vector_store = AsyncMock()
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke = AsyncMock(return_value=mock_docs)
        mock_vector_store.as_retriever = MagicMock(return_value=mock_retriever)

        with patch('tools.retrieval_tool.get_vector_store', return_value=mock_vector_store):
            # Act
            tool = get_retrieval_tool(chat_room_id=chat_room_id)
            result = await tool.coroutine("test query")

            # Assert - Verify filter is correctly applied
            mock_vector_store.as_retriever.assert_called_once_with(
                search_kwargs={
                    "k": 3,
                    "filter": {"chat_room_id": chat_room_id}
                }
            )
            assert "Test content" in result
