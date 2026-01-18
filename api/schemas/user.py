"""
User-related Pydantic schemas.

This module defines request and response models for user entities.
"""

from uuid import UUID

from pydantic import EmailStr, Field

from api.schemas.base import RequestModel, ResponseModel, TimestampMixin, UUIDMixin
from api.schemas.enums import MessageRole


class UserBase(ResponseModel):
    """Base user model with common fields."""

    email: EmailStr | None = Field(
        default=None,
        description="User email address",
    )
    telegram_id: int | None = Field(
        default=None,
        description="Telegram user ID",
    )


class UserCreate(UserBase, RequestModel):
    """
    Schema for creating a new user.

    At least one of email or telegram_id must be provided.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "user@example.com",
                    "telegram_id": 123456789,
                }
            ]
        }
    }


class UserUpdate(RequestModel):
    """Schema for updating an existing user."""

    email: EmailStr | None = Field(
        default=None,
        description="User email address",
    )
    telegram_id: int | None = Field(
        default=None,
        description="Telegram user ID",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "updated@example.com",
                }
            ]
        }
    }


class UserResponse(UUIDMixin, TimestampMixin, UserBase):
    """
    Schema for user response data.

    Includes timestamps and UUID serialization.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "telegram_id": 123456789,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                }
            ]
        }
    }
