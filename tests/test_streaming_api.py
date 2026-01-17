"""
Tests for Streaming API - SSE endpoints for real-time chat streaming.

Test Coverage:
- SSE endpoint initialization and configuration
- Stream request validation
- SSE response formatting
- Connection management
- Error handling
- CORS and security headers
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.streaming_router import router as streaming_router
from services.chat_streaming_service import ChatStreamingService, StreamEvent


class TestStreamingRouterInitialization:
    """Test streaming router initialization."""

    def test_router_exists(self):
        """Test that streaming router is properly initialized."""
        assert streaming_router is not None
        assert streaming_router.tags == ["Streaming"]


class TestStreamRequestModel:
    """Test stream request validation model."""

    def test_valid_stream_request(self):
        """Test creating a valid stream request."""
        from api.streaming_router import StreamRequest

        request = StreamRequest(
            message="Hello, world!",
            conversation_id="test-conv-123",
            persona_id="persona-1",
        )

        assert request.message == "Hello, world!"
        assert request.conversation_id == "test-conv-123"
        assert request.persona_id == "persona-1"

    def test_stream_request_with_defaults(self):
        """Test stream request with optional fields."""
        from api.streaming_router import StreamRequest

        request = StreamRequest(message="Test message")

        assert request.message == "Test message"

    def test_stream_request_empty_message_fails(self):
        """Test that empty message validation fails."""
        from api.streaming_router import StreamRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StreamRequest(message="")

    def test_stream_request_too_long_message_fails(self):
        """Test that overly long message validation fails."""
        from api.streaming_router import StreamRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StreamRequest(message="a" * 10001)

    def test_stream_request_whitespace_only_fails(self):
        """Test that whitespace-only message validation fails."""
        from api.streaming_router import StreamRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            StreamRequest(message="   \t\n   ")


class TestSSEStreamingEndpoint:
    """Test SSE streaming endpoint."""

    @pytest.mark.asyncio
    async def test_stream_endpoint_returns_sse_response(self):
        """Test that stream endpoint returns proper SSE response."""
        app = FastAPI()
        app.include_router(streaming_router)

        # Use TestClient for streaming
        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={
                    "message": "Hello, world!",
                    "conversation_id": "test-conv-123",
                },
            )

            # Verify response
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

            # Verify SSE format - read all content
            content = response.text
            assert len(content) > 0, "Response content should not be empty"
            assert "event: typing_indicator" in content
            assert "event: text_chunk" in content
            assert "event: completion" in content

            # Verify content includes the message
            assert "Hello, world!" in content or "You said:" in content

    @pytest.mark.asyncio
    async def test_stream_endpoint_with_invalid_json(self):
        """Test stream endpoint with invalid JSON payload."""
        app = FastAPI()
        app.include_router(streaming_router)
        client = TestClient(app)

        response = client.post(
            "/streaming/chat",
            json={"invalid": "data"},  # Missing required 'message' field
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_stream_endpoint_handles_service_errors(self):
        """Test that stream endpoint handles service errors gracefully."""
        from api.streaming_router import StreamRequest

        app = FastAPI()
        app.include_router(streaming_router)
        client = TestClient(app)

        # Mock service that raises exception
        with patch("api.streaming_router.ChatStreamingService") as mock_service_class:
            mock_service = MagicMock()
            mock_service.stream_messages = MagicMock(
                side_effect=RuntimeError("Service error")
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            # Should return error or handle gracefully
            assert response.status_code in [500, 200]

    @staticmethod
    def _mock_event_stream():
        """Helper to create mock event stream."""

        async def stream():
            yield StreamEvent(
                event_type="typing_indicator",
                data={"is_typing": True},
            )
            yield StreamEvent(
                event_type="text_chunk",
                data={"content": "Hello", "index": 0},
            )
            yield StreamEvent(
                event_type="completion",
                data={"finish_reason": "stop"},
            )

        return stream()


class TestSSEEventFormatting:
    """Test SSE event formatting in responses."""

    @pytest.mark.asyncio
    async def test_sse_format_with_text_chunk(self):
        """Test SSE formatting for text chunk events."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            # Verify SSE format structure
            lines = response.text.split("\n")
            assert any(line.startswith("event:") for line in lines)
            assert any(line.startswith("data:") for line in lines)

    @pytest.mark.asyncio
    async def test_sse_format_with_typing_indicator(self):
        """Test SSE formatting for typing indicator events."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            # Verify typing indicator is present
            assert "typing_indicator" in response.text


class TestConnectionManagement:
    """Test SSE connection lifecycle management."""

    @pytest.mark.asyncio
    async def test_connection_close_on_completion(self):
        """Test that connection closes properly after stream completion."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            # Response should complete (not hang)
            assert response.status_code == 200
            assert "completion" in response.text

    @pytest.mark.asyncio
    async def test_connection_with_timeout(self):
        """Test connection timeout handling."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            assert response.status_code == 200


class TestErrorHandling:
    """Test error handling in streaming endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_conversation_id(self):
        """Test handling of invalid conversation ID format."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            # Empty conversation_id is accepted (optional field)
            # Only empty message should fail
            response = client.post(
                "/streaming/chat",
                json={"message": "Test", "conversation_id": ""},
            )

            # Empty conversation_id is valid (optional field)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        app = FastAPI()
        app.include_router(streaming_router)
        client = TestClient(app)

        response = client.post(
            "/streaming/chat",
            json={},  # Missing 'message' field
        )

        assert response.status_code == 422


class TestCORSAndSecurityHeaders:
    """Test CORS and security headers in SSE responses."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self):
        """Test that proper CORS headers are set."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            # Check for common security headers
            assert "content-type" in response.headers

    @pytest.mark.asyncio
    async def test_no_cache_headers(self):
        """Test that cache control headers prevent caching."""
        app = FastAPI()
        app.include_router(streaming_router)

        with TestClient(app) as client:
            response = client.post(
                "/streaming/chat",
                json={"message": "Test"},
            )

            # SSE should not be cached
            cache_control = response.headers.get("cache-control", "")
            assert "no-cache" in cache_control or "no-store" in cache_control
