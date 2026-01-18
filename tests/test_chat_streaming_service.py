"""
Tests for ChatStreamingService - Real-time chat streaming with SSE support.

Test Coverage:
- Service initialization and configuration
- Message streaming with SSE formatting
- Typing indicator management
- Stream completion handling
- Error handling and edge cases
"""

import asyncio

import pytest

from services.chat_streaming_service import ChatStreamingService, StreamEvent


class TestChatStreamingServiceInitialization:
    """Test service initialization and configuration."""

    def test_initialization_with_default_config(self):
        """Test service initialization with default configuration."""
        service = ChatStreamingService()

        assert service is not None
        assert service.retry_max_attempts == 3
        assert service.retry_delay_ms == 1000
        assert service.buffer_char_threshold == 25
        assert service.buffer_time_threshold_sec == 0.3

    def test_initialization_with_custom_config(self):
        """Test service initialization with custom configuration."""
        service = ChatStreamingService(
            retry_max_attempts=5,
            retry_delay_ms=500,
            buffer_char_threshold=50,
            buffer_time_threshold_sec=0.5,
        )

        assert service.retry_max_attempts == 5
        assert service.retry_delay_ms == 500
        assert service.buffer_char_threshold == 50
        assert service.buffer_time_threshold_sec == 0.5


class TestStreamEventCreation:
    """Test StreamEvent data class creation and formatting."""

    def test_create_text_event(self):
        """Test creating a text chunk event."""
        event = StreamEvent(
            event_type="text_chunk",
            data={"content": "Hello, world!", "index": 0},
        )

        assert event.event_type == "text_chunk"
        assert event.data["content"] == "Hello, world!"
        assert event.data["index"] == 0

    def test_create_typing_event(self):
        """Test creating a typing indicator event."""
        event = StreamEvent(
            event_type="typing_indicator",
            data={"is_typing": True},
        )

        assert event.event_type == "typing_indicator"
        assert event.data["is_typing"] is True

    def test_create_completion_event(self):
        """Test creating a completion event."""
        event = StreamEvent(
            event_type="completion",
            data={
                "finish_reason": "stop",
                "total_tokens": 100,
                "prompt_tokens": 20,
                "completion_tokens": 80,
            },
        )

        assert event.event_type == "completion"
        assert event.data["finish_reason"] == "stop"
        assert event.data["total_tokens"] == 100

    def test_create_error_event(self):
        """Test creating an error event."""
        event = StreamEvent(
            event_type="error",
            data={"message": "Connection failed", "code": "connection_error"},
        )

        assert event.event_type == "error"
        assert event.data["message"] == "Connection failed"
        assert event.data["code"] == "connection_error"


class TestFormatSSEEvent:
    """Test SSE event formatting."""

    def test_format_text_chunk_event(self):
        """Test formatting text chunk event for SSE."""
        service = ChatStreamingService()
        event = StreamEvent(
            event_type="text_chunk",
            data={"content": "Hello", "index": 0},
        )

        sse_formatted = service.format_sse_event(event)

        assert "event: text_chunk" in sse_formatted
        assert 'data: {"content": "Hello", "index": 0}' in sse_formatted
        assert sse_formatted.endswith("\n\n")

    def test_format_typing_event(self):
        """Test formatting typing indicator event for SSE."""
        service = ChatStreamingService()
        event = StreamEvent(
            event_type="typing_indicator",
            data={"is_typing": True},
        )

        sse_formatted = service.format_sse_event(event)

        assert "event: typing_indicator" in sse_formatted
        assert 'data: {"is_typing": true}' in sse_formatted

    def test_format_completion_event(self):
        """Test formatting completion event for SSE."""
        service = ChatStreamingService()
        event = StreamEvent(
            event_type="completion",
            data={"finish_reason": "stop"},
        )

        sse_formatted = service.format_sse_event(event)

        assert "event: completion" in sse_formatted
        assert 'data: {"finish_reason": "stop"}' in sse_formatted


class TestStreamMessages:
    """Test message streaming functionality."""

    @pytest.mark.asyncio
    async def test_stream_empty_messages(self):
        """Test streaming with empty message list."""
        service = ChatStreamingService()

        events = []
        async for event in service.stream_messages([]):
            events.append(event)

        # Should still send completion event
        assert len(events) == 1
        assert events[0].event_type == "completion"

    @pytest.mark.asyncio
    async def test_stream_single_message(self):
        """Test streaming a single message."""
        service = ChatStreamingService()

        async def mock_stream():
            """Mock async stream that yields text chunks."""
            yield "Hello, "

        events = []
        async for event in service.stream_text_chunks(mock_stream()):
            events.append(event)

        # Should have at least text and completion events
        assert len(events) >= 1
        assert any(e.event_type == "completion" for e in events)

    @pytest.mark.asyncio
    async def test_stream_with_buffering(self):
        """Test streaming with adaptive buffering."""
        service = ChatStreamingService(
            buffer_char_threshold=10,
            buffer_time_threshold_sec=0.1,
        )

        async def mock_stream():
            """Mock stream with multiple chunks."""
            for chunk in ["Hello", " ", "world", "!"]:
                yield chunk
                await asyncio.sleep(0.05)

        events = []
        async for event in service.stream_text_chunks(mock_stream()):
            events.append(event)

        # Should have text chunks and completion
        text_events = [e for e in events if e.event_type == "text_chunk"]
        completion_events = [e for e in events if e.event_type == "completion"]

        assert len(completion_events) == 1
        assert len(text_events) >= 1


class TestTypingIndicator:
    """Test typing indicator functionality."""

    def test_enable_typing_indicator(self):
        """Test enabling typing indicator."""
        service = ChatStreamingService()

        event = service.create_typing_event(True)
        assert event.data["is_typing"] is True

    def test_disable_typing_indicator(self):
        """Test disabling typing indicator."""
        service = ChatStreamingService()

        event = service.create_typing_event(False)
        assert event.data["is_typing"] is False


class TestCompletionHandling:
    """Test stream completion and metadata."""

    def test_create_completion_event_with_metadata(self):
        """Test creating completion event with usage metadata."""
        service = ChatStreamingService()

        metadata = {
            "finish_reason": "stop",
            "total_tokens": 150,
            "prompt_tokens": 30,
            "completion_tokens": 120,
        }

        event = service.create_completion_event(**metadata)

        assert event.event_type == "completion"
        assert event.data["finish_reason"] == "stop"
        assert event.data["total_tokens"] == 150

    def test_create_completion_event_minimal(self):
        """Test creating completion event with minimal data."""
        service = ChatStreamingService()

        event = service.create_completion_event(finish_reason="stop")

        assert event.event_type == "completion"
        assert event.data["finish_reason"] == "stop"


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_create_error_event_with_message(self):
        """Test creating error event with custom message."""
        service = ChatStreamingService()

        event = service.create_error_event("Stream failed", "stream_error")

        assert event.event_type == "error"
        assert event.data["message"] == "Stream failed"
        assert event.data["code"] == "stream_error"

    @pytest.mark.asyncio
    async def test_stream_with_exception(self):
        """Test streaming when source raises exception."""
        service = ChatStreamingService()

        async def failing_stream():
            """Mock stream that raises exception."""
            yield "Hello"
            raise RuntimeError("Stream error")

        events = []
        async for event in service.stream_text_chunks(failing_stream()):
            events.append(event)

        # Should handle error gracefully
        assert any(e.event_type == "error" for e in events)


class TestStreamInterruption:
    """Test stream interruption and cleanup."""

    @pytest.mark.asyncio
    async def test_stream_cancellation(self):
        """Test handling stream cancellation."""
        service = ChatStreamingService()

        async def slow_stream():
            """Mock stream that yields slowly."""
            for i in range(10):
                yield f"chunk{i}"
                await asyncio.sleep(0.1)

        events = []
        try:
            async for event in service.stream_text_chunks(slow_stream()):
                events.append(event)
                if len(events) >= 3:
                    # Cancel after 3 events
                    break
        except Exception:
            pass

        # Should have received some events before cancellation
        assert len(events) >= 3
