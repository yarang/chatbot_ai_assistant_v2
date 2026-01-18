"""
Chat room-related Pydantic schemas.

This module defines request and response models for chat room entities.
"""

from uuid import UUID

from pydantic import Field

from api.schemas.base import RequestModel, ResponseModel, TimestampMixin, UUIDMixin
from api.schemas.enums import ChatType


class ChatRoomBase(ResponseModel):
    """Base chat room model with common fields."""

    telegram_chat_id: int = Field(
        ...,
        description="Telegram chat ID",
    )
    chat_type: ChatType = Field(
        ...,
        description="Type of chat (private, group, supergroup, channel)",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Chat room title (optional for private chats)",
    )


class ChatRoomCreate(ChatRoomBase, RequestModel):
    """
    Schema for creating a new chat room.

    Links a Telegram chat to a persona for AI interactions.
    """

    persona_id: UUID = Field(
        ...,
        description="Associated persona UUID",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "telegram_chat_id": -1001234567890,
                    "chat_type": "supergroup",
                    "title": "My Group",
                    "persona_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            ]
        }
    }


class ChatRoomUpdate(RequestModel):
    """Schema for updating an existing chat room."""

    persona_id: UUID | None = Field(
        default=None,
        description="Associated persona UUID",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Chat room title",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "persona_id": "550e8400-e29b-41d4-a716-446655440000",
                    "title": "Updated Group Name",
                }
            ]
        }
    }


class ChatRoomResponse(UUIDMixin, TimestampMixin, ChatRoomBase):
    """
    Schema for chat room response data.

    Includes timestamps, UUID serialization, and related persona info.
    """

    persona_id: UUID = Field(
        ...,
        description="Associated persona UUID",
    )
    persona_name: str | None = Field(
        default=None,
        description="Associated persona name",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "telegram_chat_id": -1001234567890,
                    "chat_type": "supergroup",
                    "title": "My Group",
                    "persona_id": "660e8400-e29b-41d4-a716-446655440001",
                    "persona_name": "Helpful Assistant",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                }
            ]
        }
    }


class ChatRoomsListResponse(ResponseModel):
    """
    Schema for paginated list of chat rooms.

    Used for retrieving all chat rooms for a user.
    """

    items: list[ChatRoomResponse] = Field(
        default_factory=list,
        description="List of chat rooms",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of chat rooms",
    )
    page: int = Field(
        ...,
        ge=1,
        description="Current page number",
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Number of items per page",
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "items": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "telegram_chat_id": -1001234567890,
                            "chat_type": "supergroup",
                            "title": "My Group",
                            "persona_id": "660e8400-e29b-41d4-a716-446655440001",
                            "persona_name": "Helpful Assistant",
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-02T00:00:00Z",
                        }
                    ],
                    "total": 10,
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 1,
                }
            ]
        }
    }
