import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from core.graph import general_assistant_node, ChatState
from langchain_core.messages import HumanMessage
from datetime import datetime

@pytest.mark.asyncio
async def test_general_assistant_node_time_injection():
    with patch("core.graph.get_llm") as mock_get_llm:
        mock_llm = MagicMock()
        mock_chain = MagicMock()
        # Mock the chain to return a response
        mock_response = MagicMock()
        mock_response.usage_metadata = {}
        mock_chain.ainvoke = AsyncMock(return_value=mock_response)
        
        # We need to mock the pipe operator |
        # prompt | llm
        # The prompt is a ChatPromptTemplate.
        # When we do prompt | llm, it creates a RunnableSequence.
        
        # Instead of mocking the chain construction which is hard, 
        # let's mock ChatPromptTemplate.from_messages to inspect the input.
        with patch("langchain_core.prompts.ChatPromptTemplate.from_messages") as mock_from_messages:
            mock_from_messages.return_value.__or__.return_value = mock_chain
            
            state = {
                "messages": [HumanMessage(content="Hello")],
                "model_name": "gemini-pro",
                "persona_content": "You are a bot."
            }
            
            await general_assistant_node(state)
            
            # Verify from_messages was called
            assert mock_from_messages.called
            args = mock_from_messages.call_args[0][0]
            
            # args is a list of messages/tuples
            # [("system", content), MessagesPlaceholder...]
            system_msg = args[0]
            assert system_msg[0] == "system"
            content = system_msg[1]
            
            # Check if time is in content
            current_date = datetime.now().strftime('%Y-%m-%d')
            assert "Current Time:" in content
            assert current_date in content
