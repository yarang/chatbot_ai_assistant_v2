"""
Conversation-related Pydantic schemas.

This module defines request and response models for conversation messages.
"""

from uuid import UUID

from pydantic import Field

from api.schemas.base import RequestModel, ResponseModel, TimestampMixin, UUIDMixin
from api.schemas.enums import MessageRole


class ConversationBase(ResponseModel):
    """Base conversation model with common fields."""

    chat_room_id: int = Field(
        ...,
        description="Associated chat room ID",
    )
    role: MessageRole = Field(
        ...,
        description="Message role (user, assistant, or system)",
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=100000,
        description="Message content",
    )
    tokens: int | None = Field(
        default=None,
        ge=0,
        description="Number of tokens in the message",
    )


class ConversationCreate(ConversationBase, RequestModel):
    """
    Schema for creating a new conversation message.

    The message is associated with a specific chat room.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "chat_room_id": 1,
                    "role": "user",
                    "message": "Hello, how are you?",
                    "tokens": 7,
                }
            ]
        }
    }


class ConversationResponse(UUIDMixin, TimestampMixin, ConversationBase):
    """
    Schema for conversation message response data.

    Includes timestamps and UUID serialization.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "chat_room_id": 1,
                    "role": "user",
                    "message": "Hello, how are you?",
                    "tokens": 7,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": None,
                }
            ]
        }
    }


class ConversationsListResponse(ResponseModel):
    """
    Schema for paginated list of conversation messages.

    Used for retrieving conversation history for a chat room.
    """

    items: list[ConversationResponse] = Field(
        default_factory=list,
        description="List of conversation messages",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of messages",
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
                            "chat_room_id": 1,
                            "role": "user",
                            "message": "Hello!",
                            "tokens": 2,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": None,
                        }
                    ],
                    "total": 50,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 3,
                }
            ]
        }
    }
