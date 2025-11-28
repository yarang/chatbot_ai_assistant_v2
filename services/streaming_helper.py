"""
Streaming helper utilities for buffering and processing LangGraph stream events.
"""

import asyncio
import time
from typing import Optional, AsyncIterator
from langchain_core.messages import AIMessage, ToolMessage

class StreamBuffer:
    """
    Buffer for accumulating streaming text chunks.
    Flushes when time or character threshold is reached.
    """
    
    def __init__(self, time_threshold_sec: float = 0.5, char_threshold: int = 50):
        """
        Args:
            time_threshold_sec: Flush if this many seconds have passed since last flush
            char_threshold: Flush if buffer has this many characters
        """
        self.buffer = ""
        self.time_threshold = time_threshold_sec
        self.char_threshold = char_threshold
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
            len(self.buffer) >= self.char_threshold or
            time_elapsed >= self.time_threshold
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
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                            return "".join(text_parts)
                        return str(last_msg.content)
                
                # Skip ToolMessage (internal tool results)
                elif isinstance(last_msg, ToolMessage):
                    continue
    
    return None


async def stream_with_buffer(
    stream: AsyncIterator[dict],
    buffer: StreamBuffer
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
