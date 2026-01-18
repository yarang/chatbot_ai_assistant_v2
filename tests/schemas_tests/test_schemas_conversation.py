"""
Unit tests for Conversation Pydantic schemas.

Tests conversation-related request and response models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationsListResponse,
)
from api.schemas.enums import MessageRole


class TestConversationCreate:
    """Test ConversationCreate schema."""

    def test_valid_conversation(self):
        """Test creating valid conversation."""
        conv = ConversationCreate(
            chat_room_id=1,
            role=MessageRole.USER,
            message="Hello, world!",
        )
        assert conv.chat_room_id == 1
        assert conv.role == "user"
        assert conv.message == "Hello, world!"
        assert conv.tokens is None

    def test_conversation_with_tokens(self):
        """Test conversation with token count."""
        conv = ConversationCreate(
            chat_room_id=1,
            role=MessageRole.ASSISTANT,
            message="Response",
            tokens=10,
        )
        assert conv.tokens == 10

    def test_message_too_short(self):
        """Test that empty message raises validation error."""
        with pytest.raises(ValidationError):
            ConversationCreate(
                chat_room_id=1,
                role=MessageRole.USER,
                message="",
            )

    def test_message_too_long(self):
        """Test that message exceeding max length raises validation error."""
        with pytest.raises(ValidationError):
            ConversationCreate(
                chat_room_id=1,
                role=MessageRole.USER,
                message="a" * 100001,
            )

    def test_negative_tokens(self):
        """Test that negative tokens raise validation error."""
        with pytest.raises(ValidationError):
            ConversationCreate(
                chat_room_id=1,
                role=MessageRole.USER,
                message="Test",
                tokens=-1,
            )

    def test_valid_roles(self):
        """Test all valid role values."""
        for role in [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.SYSTEM]:
            conv = ConversationCreate(
                chat_room_id=1,
                role=role,
                message="Test",
            )
            assert conv.role == role


class TestConversationResponse:
    """Test ConversationResponse schema."""

    def test_full_response(self):
        """Test complete conversation response."""
        conv = ConversationResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            chat_room_id=1,
            role=MessageRole.USER,
            message="Hello",
            tokens=5,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert conv.role == "user"
        assert conv.message == "Hello"


class TestConversationsListResponse:
    """Test ConversationsListResponse schema."""

    def test_list_response(self):
        """Test paginated list response."""
        response = ConversationsListResponse(
            items=[
                ConversationResponse(
                    id="550e8400-e29b-41d4-a716-446655440000",
                    chat_room_id=1,
                    role=MessageRole.USER,
                    message="Hello",
                    tokens=5,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
            ],
            total=10,
            page=1,
            page_size=20,
            total_pages=1,
        )
        assert len(response.items) == 1
        assert response.total == 10
