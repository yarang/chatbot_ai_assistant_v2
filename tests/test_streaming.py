import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from services.streaming_helper import StreamBuffer, extract_text_from_stream_event, stream_with_buffer
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

def test_stream_buffer_char_threshold():
    """Test StreamBuffer flushes when character threshold is reached"""
    buffer = StreamBuffer(time_threshold_sec=10, char_threshold=10)
    
    # Add text below threshold
    result = buffer.add("hello")
    assert result is None  # Should not flush
    assert buffer.buffer == "hello"
    
    # Add more text to exceed threshold
    result = buffer.add(" world!")
    assert result == "hello world!"  # Should flush
    assert buffer.buffer == ""


def test_stream_buffer_manual_flush():
    """Test manual flush of StreamBuffer"""
    buffer = StreamBuffer(time_threshold_sec=10, char_threshold=100)
    
    buffer.add("test")
    assert buffer.has_content()
    
    result = buffer.flush()
    assert result == "test"
    assert not buffer.has_content()


def test_extract_text_from_stream_event_ai_message():
    """Test extracting text from stream event with AIMessage"""
    event = {
        "GeneralAssistant": {
            "messages": [AIMessage(content="Hello, world!")]
        }
    }
    
    text = extract_text_from_stream_event(event)
    assert text == "Hello, world!"


def test_extract_text_from_stream_event_tool_call():
    """Test that tool calls are ignored (no displayable content)"""
    event = {
        "Researcher": {
            "messages": [AIMessage(content="", tool_calls=[{"name": "search", "args": {}, "id": "1"}])]
        }
    }
    
    text = extract_text_from_stream_event(event)
    assert text is None


def test_extract_text_from_stream_event_empty():
    """Test extracting from empty event"""
    event = {}
    
    text = extract_text_from_stream_event(event)
    assert text is None


@pytest.mark.asyncio
async def test_stream_with_buffer():
    """Test stream_with_buffer yields buffered chunks"""
    
    # Create mock stream
    async def mock_stream():
        yield {"Node1": {"messages": [AIMessage(content="Hello")]}}
        yield {"Node2": {"messages": [AIMessage(content=" world")]}}
        yield {"Node3": {"messages": [AIMessage(content="!")]}}
    
    buffer = StreamBuffer(time_threshold_sec=0, char_threshold=10)
    chunks = []
    
    async for chunk in stream_with_buffer(mock_stream(), buffer):
        chunks.append(chunk)
    
    # Should have concatenated into chunks based on buffer
    assert len(chunks) > 0
    full_text = "".join(chunks)
    assert "Hello world!" in full_text


@pytest.mark.asyncio
async def test_ask_question_stream():
    """Test ask_question_stream function"""
    from services.conversation_service import ask_question_stream
    
    with patch("services.conversation_service.graph") as mock_graph:
        # Mock astream to return some events
        async def mock_astream(state):
            yield {"GeneralAssistant": {"messages": [AIMessage(content="Test")]}}
            yield {"save_conversation": {}}
        
        mock_graph.astream.return_value = mock_astream(None)
        
        chunks = []
        async for chunk in ask_question_stream(
            user_id="test_user",
            chat_room_id="test_room",
            question="Hello"
        ):
            chunks.append(chunk)
        
        # Should get at least one chunk
        assert len(chunks) > 0
