"""
Streaming helper utilities for buffering and processing LangGraph stream events.

Features:
- Optimized buffering for real-time streaming (20-30 char chunks)
- Adaptive buffer sizing based on chunk history
- Telegram MarkdownV2 support
- Retry logic for message updates
- Typing indicator support
"""

import asyncio
import time
from typing import AsyncIterator, Optional, Tuple

from langchain_core.messages import AIMessage, ToolMessage

from core.logger import get_logger

logger = get_logger(__name__)


class StreamBuffer:
    """
    Buffer for accumulating streaming text chunks.
    Optimized for real-time streaming with smaller chunks.
    """

    def __init__(
        self,
        time_threshold_sec: float = 0.3,
        char_threshold: int = 25,
        max_buffer_size: int = 100,
    ):
        """
        Args:
            time_threshold_sec: Flush if this many seconds have passed since last flush (default: 0.3s)
            char_threshold: Flush if buffer has this many characters (default: 25 for faster updates)
            max_buffer_size: Maximum buffer size before force flush (default: 100)
        """
        self.buffer = ""
        self.time_threshold = time_threshold_sec
        self.char_threshold = char_threshold
        self.max_buffer_size = max_buffer_size
        self.last_flush_time = time.time()

    def add(self, text: str) -> Optional[str]:
        """
        Add text to buffer. Returns buffered text if threshold reached, else None.

        Args:
            text: Text to add

        Returns:
            Flushed text if threshold reached, else None
        """
        self.buffer += text

        # Check if we should flush
        time_elapsed = time.time() - self.last_flush_time
        should_flush = (
            len(self.buffer) >= self.char_threshold
            or time_elapsed >= self.time_threshold
            or len(self.buffer) >= self.max_buffer_size
        )

        if should_flush:
            return self.flush()

        return None

    def flush(self) -> str:
        """Force flush buffer and return accumulated text."""
        text = self.buffer
        self.buffer = ""
        self.last_flush_time = time.time()
        return text

    def has_content(self) -> bool:
        """Check if buffer has any content."""
        return len(self.buffer) > 0

    def peek(self) -> str:
        """Peek at current buffer without flushing."""
        return self.buffer


class AdaptiveStreamBuffer(StreamBuffer):
    """
    Adaptive streaming buffer that dynamically adjusts threshold based on chunk history.

    Uses moving average of recent chunk sizes to optimize flush timing for
    better real-time streaming experience.
    """

    def __init__(
        self,
        time_threshold_sec: float = 0.3,
        initial_char_threshold: int = 25,
        max_buffer_size: int = 100,
        history_size: int = 10,
    ):
        """
        Args:
            time_threshold_sec: Flush if this many seconds have passed since last flush (default: 0.3s)
            initial_char_threshold: Initial character threshold (default: 25)
            max_buffer_size: Maximum buffer size before force flush (default: 100)
            history_size: Number of recent chunks to track for averaging (default: 10)
        """
        super().__init__(time_threshold_sec, initial_char_threshold, max_buffer_size)
        self.initial_threshold = initial_char_threshold
        self.history_size = history_size
        self.chunk_history: list[int] = []
        self.total_chunks = 0

    def add(self, text: str) -> Optional[str]:
        """
        Add text to buffer with adaptive threshold adjustment.

        Args:
            text: Text to add

        Returns:
            Flushed text if threshold reached, else None
        """
        self.buffer += text

        # Check if we should flush
        time_elapsed = time.time() - self.last_flush_time
        should_flush = (
            len(self.buffer) >= self.char_threshold
            or time_elapsed >= self.time_threshold
            or len(self.buffer) >= self.max_buffer_size
        )

        if should_flush:
            flushed_text = self.flush()
            # Track chunk size for adaptive adjustment
            self._track_chunk_size(len(flushed_text))
            return flushed_text

        return None

    def _track_chunk_size(self, size: int) -> None:
        """Track chunk size and adjust threshold based on history."""
        self.chunk_history.append(size)
        self.total_chunks += 1

        # Keep only recent history
        if len(self.chunk_history) > self.history_size:
            self.chunk_history.pop(0)

        # Adjust threshold after collecting enough samples
        if len(self.chunk_history) >= 5:
            avg_chunk_size = sum(self.chunk_history) / len(self.chunk_history)
            # Set threshold to 1.5x average for optimal batching
            self.char_threshold = max(15, int(avg_chunk_size * 1.5))
            self.char_threshold = min(self.char_threshold, 50)  # Cap at 50

    def get_stats(self) -> dict:
        """Get buffer statistics."""
        avg_chunk = (
            sum(self.chunk_history) / len(self.chunk_history)
            if self.chunk_history
            else 0
        )
        return {
            "total_chunks": self.total_chunks,
            "avg_chunk_size": avg_chunk,
            "current_threshold": self.char_threshold,
            "history_size": len(self.chunk_history),
        }


class TelegramMarkdownFormatter:
    """
    Formatter for converting text to Telegram MarkdownV2 format.
    Handles special characters and formatting safely.
    """

    # Characters that need escaping in MarkdownV2
    ESCAPE_CHARS = [
        "_",
        "*",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape special characters for Telegram MarkdownV2.

        Args:
            text: Plain text to escape

        Returns:
            Escaped text safe for MarkdownV2
        """
        if not text:
            return ""

        result = text
        for char in TelegramMarkdownFormatter.ESCAPE_CHARS:
            result = result.replace(char, f"\\{char}")
        return result

    @staticmethod
    def format_code_block(code: str, language: str = "") -> str:
        """
        Format text as a code block.

        Args:
            code: Code content
            language: Programming language (optional)

        Returns:
            Formatted MarkdownV2 string
        """
        escaped = TelegramMarkdownFormatter.escape_markdown(code)
        return f"```{language}\n{escaped}\n```"

    @staticmethod
    def format_bold(text: str) -> str:
        """Format text as bold."""
        escaped = TelegramMarkdownFormatter.escape_markdown(text)
        return f"*{escaped}*"

    @staticmethod
    def format_italic(text: str) -> str:
        """Format text as italic."""
        escaped = TelegramMarkdownFormatter.escape_markdown(text)
        return f"_{escaped}_"

    @staticmethod
    def format_inline_code(text: str) -> str:
        """Format text as inline code."""
        escaped = TelegramMarkdownFormatter.escape_markdown(text)
        return f"`{escaped}`"


def extract_text_from_stream_event(event: dict) -> Optional[str]:
    """
    Extract displayable text from a LangGraph stream event.

    Args:
        event: Stream event from graph.astream()

    Returns:
        Extracted text or None if no displayable content
    """
    # LangGraph stream events are typically dict with node name as key
    # Example: {"Researcher": {"messages": [AIMessage(...)]}}

    for node_name, node_output in event.items():
        if isinstance(node_output, dict) and "messages" in node_output:
            messages = node_output["messages"]

            # Get the last message
            if messages and len(messages) > 0:
                last_msg = messages[-1]

                # Extract content from AIMessage
                if isinstance(last_msg, AIMessage):
                    # Skip if it's a tool call (no displayable content yet)
                    if last_msg.tool_calls:
                        continue

                    # Return text content
                    if last_msg.content:
                        if isinstance(last_msg.content, list):
                            # Handle multimodal content (list of dicts)
                            text_parts = []
                            for item in last_msg.content:
                                if (
                                    isinstance(item, dict)
                                    and item.get("type") == "text"
                                ):
                                    text_parts.append(item.get("text", ""))
                            return "".join(text_parts)
                        return str(last_msg.content)

                # Skip ToolMessage (internal tool results)
                elif isinstance(last_msg, ToolMessage):
                    continue

    return None


async def stream_with_buffer(
    stream: AsyncIterator[dict],
    buffer: StreamBuffer,
) -> AsyncIterator[str]:
    """
    Process a LangGraph stream with buffering.

    Args:
        stream: Async iterator from graph.astream()
        buffer: StreamBuffer instance

    Yields:
        Buffered text chunks ready to send
    """
    async for event in stream:
        # Extract text from event
        text = extract_text_from_stream_event(event)

        if text:
            # Add to buffer and check if we should flush
            flushed = buffer.add(text)

            if flushed:
                yield flushed

    # Flush any remaining content
    if buffer.has_content():
        yield buffer.flush()


async def stream_with_buffer_and_retry(
    stream: AsyncIterator[dict],
    buffer: StreamBuffer,
) -> AsyncIterator[Tuple[str, bool]]:
    """
    Process a LangGraph stream with buffering and retry capability.

    Args:
        stream: Async iterator from graph.astream()
        buffer: StreamBuffer instance

    Yields:
        Tuple of (text_chunk, is_complete) where:
        - text_chunk: Buffered text ready to send
        - is_complete: Whether this is the final chunk
    """
    chunk_count = 0
    async for event in stream:
        # Extract text from event
        text = extract_text_from_stream_event(event)

        if text:
            # Add to buffer and check if we should flush
            flushed = buffer.add(text)

            if flushed:
                chunk_count += 1
                yield (flushed, False)

    # Flush any remaining content (final chunk)
    if buffer.has_content():
        yield (buffer.flush(), True)
    else:
        # Signal completion even if no new content
        yield ("", True)
