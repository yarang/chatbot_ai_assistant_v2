"""
Unit tests for ChatRoom Pydantic schemas.

Tests chat room-related request and response models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas.chat_room import (
    ChatRoomCreate,
    ChatRoomResponse,
    ChatRoomUpdate,
)
from api.schemas.enums import ChatType


class TestChatRoomCreate:
    """Test ChatRoomCreate schema."""

    def test_valid_chat_room(self):
        """Test creating valid chat room."""
        room = ChatRoomCreate(
            telegram_chat_id=-1001234567890,
            chat_type=ChatType.SUPERGROUP,
            persona_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert room.telegram_chat_id == -1001234567890
        assert room.chat_type == "supergroup"
        # UUID is stored as UUID object, compare as string
        assert str(room.persona_id) == "550e8400-e29b-41d4-a716-446655440000"

    def test_private_chat_without_title(self):
        """Test private chat without optional title."""
        room = ChatRoomCreate(
            telegram_chat_id=123456789,
            chat_type=ChatType.PRIVATE,
            persona_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert room.title is None

    def test_group_chat_with_title(self):
        """Test group chat with title."""
        room = ChatRoomCreate(
            telegram_chat_id=-1001234567890,
            chat_type=ChatType.GROUP,
            title="Test Group",
            persona_id="550e8400-e29b-41d4-a716-446655440000",
        )
        assert room.title == "Test Group"

    def test_title_too_long(self):
        """Test that title exceeding max length raises validation error."""
        with pytest.raises(ValidationError):
            ChatRoomCreate(
                telegram_chat_id=-1001234567890,
                chat_type=ChatType.GROUP,
                title="a" * 256,
                persona_id="550e8400-e29b-41d4-a716-446655440000",
            )

    def test_valid_chat_types(self):
        """Test all valid chat type values."""
        for chat_type in [
            ChatType.PRIVATE,
            ChatType.GROUP,
            ChatType.SUPERGROUP,
            ChatType.CHANNEL,
        ]:
            room = ChatRoomCreate(
                telegram_chat_id=-1001234567890,
                chat_type=chat_type,
                persona_id="550e8400-e29b-41d4-a716-446655440000",
            )
            assert room.chat_type == chat_type


class TestChatRoomUpdate:
    """Test ChatRoomUpdate schema."""

    def test_update_persona_only(self):
        """Test updating only persona."""
        room = ChatRoomUpdate(persona_id="660e8400-e29b-41d4-a716-446655440001")
        assert str(room.persona_id) == "660e8400-e29b-41d4-a716-446655440001"
        assert room.title is None

    def test_update_title_only(self):
        """Test updating only title."""
        room = ChatRoomUpdate(title="Updated Title")
        assert room.title == "Updated Title"
        assert room.persona_id is None

    def test_update_both(self):
        """Test updating both fields."""
        room = ChatRoomUpdate(
            persona_id="660e8400-e29b-41d4-a716-446655440001",
            title="Updated Title",
        )
        assert str(room.persona_id) == "660e8400-e29b-41d4-a716-446655440001"
        assert room.title == "Updated Title"


class TestChatRoomResponse:
    """Test ChatRoomResponse schema."""

    def test_full_response(self):
        """Test complete chat room response."""
        room = ChatRoomResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            telegram_chat_id=-1001234567890,
            chat_type=ChatType.SUPERGROUP,
            title="Test Group",
            persona_id="660e8400-e29b-41d4-a716-446655440001",
            persona_name="Test Persona",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert room.telegram_chat_id == -1001234567890
        assert room.chat_type == "supergroup"
        assert str(room.persona_id) == "660e8400-e29b-41d4-a716-446655440001"
        assert room.persona_name == "Test Persona"
