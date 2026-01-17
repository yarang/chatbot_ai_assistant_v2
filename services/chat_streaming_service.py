"""
ChatStreamingService - Real-time chat streaming with SSE support.

This module provides a service for managing real-time chat streaming using
Server-Sent Events (SSE) protocol. It handles text chunk streaming, typing
indicators, completion metadata, and error recovery for web-based chat interfaces.

Design TAG: SPEC-STREAM-001-T001
Function TAG: SPEC-STREAM-001-F001

Features:
- Server-Sent Events (SSE) formatting for real-time communication
- Typing indicator management (start/stop)
- Adaptive message buffering with configurable thresholds
- Stream completion metadata (token usage, finish reasons)
- Comprehensive error handling and recovery
- Async iterator support for streaming sources
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StreamEvent:
    """
    Represents a single streaming event for SSE communication.

    Attributes:
        event_type: Type of event (text_chunk, typing_indicator, completion, error)
        data: Event data as dictionary (will be serialized to JSON)

    Example:
        >>> event = StreamEvent(event_type="text_chunk", data={"content": "Hello"})
        >>> event.to_json()
        '{"content": "Hello"}'
    """

    event_type: str
    data: dict = field(default_factory=dict)

    def to_json(self) -> str:
        """
        Convert event data to JSON string for SSE transmission.

        Returns:
            JSON-encoded string representation of event data

        Example:
            >>> event = StreamEvent(event_type="typing", data={"is_typing": True})
            >>> event.to_json()
            '{"is_typing": true}'
        """
        return json.dumps(self.data)


class ChatStreamingService:
    """
    Service for managing real-time chat streaming with Server-Sent Events.

    Handles text chunk streaming, typing indicators, and completion metadata
    for web-based chat interfaces using SSE protocol.
    """

    def __init__(
        self,
        retry_max_attempts: int = 3,
        retry_delay_ms: int = 1000,
        buffer_char_threshold: int = 25,
        buffer_time_threshold_sec: float = 0.3,
    ):
        """
        Initialize the chat streaming service.

        Args:
            retry_max_attempts: Maximum retry attempts for failed connections
            retry_delay_ms: Delay between retries in milliseconds
            buffer_char_threshold: Character threshold for buffer flushing
            buffer_time_threshold_sec: Time threshold for buffer flushing
        """
        self.retry_max_attempts = retry_max_attempts
        self.retry_delay_ms = retry_delay_ms
        self.buffer_char_threshold = buffer_char_threshold
        self.buffer_time_threshold_sec = buffer_time_threshold_sec

    def format_sse_event(self, event: StreamEvent) -> str:
        """
        Format a stream event as Server-Sent Event.

        Args:
            event: StreamEvent to format

        Returns:
            Formatted SSE string
        """
        return f"event: {event.event_type}\ndata: {event.to_json()}\n\n"

    def create_typing_event(self, is_typing: bool) -> StreamEvent:
        """
        Create a typing indicator event.

        Args:
            is_typing: Whether typing is in progress

        Returns:
            StreamEvent for typing indicator
        """
        return StreamEvent(
            event_type="typing_indicator",
            data={"is_typing": is_typing},
        )

    def create_completion_event(
        self,
        finish_reason: str,
        total_tokens: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> StreamEvent:
        """
        Create a stream completion event with metadata.

        Args:
            finish_reason: Reason for stream completion
            total_tokens: Total tokens used
            prompt_tokens: Tokens in prompt
            completion_tokens: Tokens in completion

        Returns:
            StreamEvent for completion
        """
        data = {"finish_reason": finish_reason}

        if total_tokens is not None:
            data["total_tokens"] = total_tokens
        if prompt_tokens is not None:
            data["prompt_tokens"] = prompt_tokens
        if completion_tokens is not None:
            data["completion_tokens"] = completion_tokens

        return StreamEvent(
            event_type="completion",
            data=data,
        )

    def create_error_event(
        self,
        message: str,
        code: str = "stream_error",
    ) -> StreamEvent:
        """
        Create an error event.

        Args:
            message: Error message
            code: Error code

        Returns:
            StreamEvent for error
        """
        return StreamEvent(
            event_type="error",
            data={"message": message, "code": code},
        )

    async def stream_text_chunks(
        self,
        stream: AsyncIterator[str],
    ) -> AsyncIterator[StreamEvent]:
        """
        Stream text chunks as SSE events.

        Args:
            stream: Async iterator yielding text chunks

        Yields:
            StreamEvent objects for each chunk
        """
        try:
            # Send typing indicator start
            yield self.create_typing_event(True)

            # Stream text chunks
            chunk_index = 0
            async for chunk in stream:
                if chunk:
                    yield StreamEvent(
                        event_type="text_chunk",
                        data={"content": chunk, "index": chunk_index},
                    )
                    chunk_index += 1

            # Send completion event
            yield self.create_completion_event(finish_reason="stop")

        except Exception as e:
            logger.error(f"Error in stream_text_chunks: {e}")
            yield self.create_error_event(str(e), "stream_error")

        finally:
            # Always send typing indicator stop
            yield self.create_typing_event(False)

    async def stream_messages(self, messages: list) -> AsyncIterator[StreamEvent]:
        """
        Stream a list of messages as SSE events.

        Args:
            messages: List of messages to stream

        Yields:
            StreamEvent objects for each message
        """
        try:
            if not messages:
                yield self.create_completion_event(finish_reason="stop")
                return

            # Stream each message
            for message in messages:
                if isinstance(message, str):
                    yield StreamEvent(
                        event_type="text_chunk",
                        data={"content": message, "index": 0},
                    )

            # Send completion event
            yield self.create_completion_event(finish_reason="stop")

        except Exception as e:
            logger.error(f"Error in stream_messages: {e}")
            yield self.create_error_event(str(e), "stream_error")
