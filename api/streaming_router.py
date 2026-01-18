"""
Streaming API Router - SSE endpoints for real-time chat streaming.

This module provides FastAPI endpoints for Server-Sent Events (SSE) streaming,
enabling real-time bidirectional communication for chat interfaces.

Design TAG: SPEC-STREAM-001-T002
Function TAG: SPEC-STREAM-001-F002

Endpoints:
- POST /api/streaming/chat - Stream chat responses via SSE
"""

from typing import AsyncIterator, Optional

from fastapi import APIRouter, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from services.chat_streaming_service import ChatStreamingService

router = APIRouter(prefix="/streaming", tags=["Streaming"])


class StreamRequest(BaseModel):
    """
    Request model for streaming chat endpoint.

    Attributes:
        message: User message to process (required, 1-10000 characters)
        conversation_id: Optional conversation identifier
        persona_id: Optional persona identifier for customization
    """

    message: str = Field(
        ..., min_length=1, max_length=10000, description="User message"
    )
    conversation_id: Optional[str] = Field(None, description="Conversation identifier")
    persona_id: Optional[str] = Field(None, description="Persona identifier")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty or whitespace only."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


async def _generate_sse_stream(
    message: str,
    conversation_id: Optional[str],
    persona_id: Optional[str],
    service: Optional[ChatStreamingService] = None,
) -> AsyncIterator[str]:
    """
    Generate SSE stream from chat service.

    Args:
        message: User message
        conversation_id: Conversation identifier
        persona_id: Persona identifier
        service: Optional ChatStreamingService instance (for testing)

    Yields:
        Formatted SSE event strings
    """
    if service is None:
        service = ChatStreamingService()

    # Create async iterator for message stream
    async def message_stream():
        """Mock message stream - replace with actual LLM integration."""
        # In production, this would call the actual chat service
        # For now, we'll echo the message
        chunks = [f"You said: {message}"]
        for chunk in chunks:
            yield chunk

    try:
        # Stream events
        async for event in service.stream_text_chunks(message_stream()):
            yield service.format_sse_event(event)

    except Exception as e:
        # Handle any streaming errors
        error_event = service.create_error_event(str(e), "streaming_error")
        yield service.format_sse_event(error_event)


@router.post("/chat", response_class=StreamingResponse)
async def stream_chat(
    request: StreamRequest,
    x_conversation_id: Optional[str] = Header(None),
):
    """
    Stream chat responses via Server-Sent Events (SSE).

    This endpoint establishes an SSE connection and streams chat responses
    in real-time, including:
    - Typing indicators
    - Text chunks
    - Completion metadata

    Args:
        request: Stream request with message and metadata
        x_conversation_id: Optional conversation ID from header

    Returns:
        StreamingResponse with SSE events

    Example:
        ```python
        import requests

        response = requests.post(
            "http://localhost:8000/api/streaming/chat",
            json={"message": "Hello!"},
            stream=True
        )

        for line in response.iter_lines():
            if line:
                print(line.decode())
        ```
    """
    # Use conversation_id from header if not in body
    conversation_id = request.conversation_id or x_conversation_id

    # Create SSE generator
    stream_generator = _generate_sse_stream(
        message=request.message,
        conversation_id=conversation_id,
        persona_id=request.persona_id,
    )

    # Return SSE response
    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/health")
async def streaming_health_check():
    """
    Health check endpoint for streaming service.

    Returns:
        Status of streaming service
    """
    return {"status": "healthy", "service": "streaming"}
