import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.graph import summarize_conversation_node, ChatState
from langchain_core.messages import HumanMessage, AIMessage

@pytest.mark.asyncio
async def test_summarize_conversation_node():
    # Mock dependencies
    with patch("core.graph.get_history") as mock_get_history, \
         patch("core.graph.get_llm") as mock_get_llm, \
         patch("core.graph.update_chat_room_summary") as mock_update_summary:
         
        # Scenario 1: Short history, no summary needed
        mock_get_history.return_value = [("user", "hi")]
        state = {"chat_room_id": "123", "model_name": "gemini-pro", "summary": "old summary"}
        
        result = await summarize_conversation_node(state)
        assert result == {}
        assert not mock_get_llm.called
        
        # Scenario 2: Long history, summary needed
        # Create 15 messages
        long_history = [("user", f"msg {i}") for i in range(15)]
        mock_get_history.return_value = long_history
        
        mock_llm = MagicMock()
        mock_response = AIMessage(content="New Summary")
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm
        
        result = await summarize_conversation_node(state)
        
        assert result == {"summary": "New Summary"}
        assert mock_get_llm.called
        assert mock_update_summary.called
        
        # Verify prompt contains messages except last 4
        call_args = mock_llm.ainvoke.call_args
        prompt_msg = call_args[0][0][0]
        assert isinstance(prompt_msg, HumanMessage)
        assert "msg 0" in prompt_msg.content
        assert "msg 10" in prompt_msg.content
        # msg 11, 12, 13, 14 should be excluded (last 4)
        assert "msg 14" not in prompt_msg.content
