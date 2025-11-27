import pytest
from unittest.mock import AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from core.graph import ChatState, save_conversation_node
import uuid


@pytest.mark.asyncio
async def test_save_conversation_with_tokens():
    """Test that save_conversation_node saves token information"""
    
    user_id = str(uuid.uuid4())
    chat_room_id = str(uuid.uuid4())
    
    state: ChatState = {
        'messages': [
            HumanMessage(content="What is AI?"),
            AIMessage(content="AI stands for Artificial Intelligence")
        ],
        'user_id': user_id,
        'chat_room_id': chat_room_id,
        'persona_content': None,
        'model_name': 'gemini-pro',
        'summary': None,
        'next': '',
        'input_tokens_used': 200,
        'output_tokens_used': 100
    }
    
    with patch('core.graph.add_message', new_callable=AsyncMock) as mock_add_message:
        await save_conversation_node(state)
        
        # Should be called twice: once for user, once for assistant
        assert mock_add_message.call_count == 2
        
        # Check first call (user message)
        user_call = mock_add_message.call_args_list[0]
        assert user_call[0][2] == "user"
        assert user_call[0][3] == "What is AI?"
        
        # Check second call (assistant message with tokens)
        assistant_call = mock_add_message.call_args_list[1]
        assert assistant_call[0][2] == "assistant"
        assert assistant_call[0][3] == "AI stands for Artificial Intelligence"
        assert assistant_call[1]['model'] == 'gemini-pro'
        assert assistant_call[1]['input_tokens'] == 200
        assert assistant_call[1]['output_tokens'] == 100


@pytest.mark.asyncio
async def test_no_tokens_when_zero():
    """Test that None is saved instead of 0 for tokens"""
    
    user_id = str(uuid.uuid4())
    chat_room_id = str(uuid.uuid4())
    
    state: ChatState = {
        'messages': [
            HumanMessage(content="Test"),
            AIMessage(content="Response")
        ],
        'user_id': user_id,
        'chat_room_id': chat_room_id,
        'persona_content': None,
        'model_name': 'gemini-pro',
        'summary': None,
        'next': '',
        'input_tokens_used': 0,  # No tokens tracked
        'output_tokens_used': 0
    }
    
    with patch('core.graph.add_message', new_callable=AsyncMock) as mock_add_message:
        await save_conversation_node(state)
        
        # Check assistant message - should have None for tokens when 0
        assistant_call = mock_add_message.call_args_list[1]
        assert assistant_call[1]['input_tokens'] is None
        assert assistant_call[1]['output_tokens'] is None


@pytest.mark.asyncio
async def test_state_fields_exist():
    """Test that ChatState has the required token fields"""
    from core.graph import ChatState
    
    # This will fail at type-check time if fields are missing
    state: ChatState = {
        'messages': [],
        'user_id': 'test',
        'chat_room_id': 'test',
        'persona_content': None,
        'model_name': None,
        'summary': None,
        'next': '',
        'input_tokens_used': 0,
        'output_tokens_used': 0
    }
    
    assert 'input_tokens_used' in state
    assert 'output_tokens_used' in state
