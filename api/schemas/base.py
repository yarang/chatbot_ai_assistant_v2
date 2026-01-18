"""
Core base models for Pydantic v2 schemas.

This module provides reusable base classes and mixins for consistent
schema definitions across the application.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ConfigDict, Field, field_serializer
from pydantic import BaseModel as PydanticBaseModel


class BaseModel(PydanticBaseModel):
    """
    Base model with common Pydantic v2 configuration.

    All schemas should inherit from this class for consistent behavior.
    """

    model_config = ConfigDict(
        # Use enum values (not names) in serialization
        use_enum_values=True,
        # Validate defaults on instantiation
        validate_default=True,
        # Validate assignment on attribute setting
        validate_assignment=True,
        # Extra fields are forbidden (strict mode)
        extra="ignore",
        # JSON schemas will use field titles
        json_schema_mode_override="validation",
    )


class TimestampMixin(BaseModel):
    """
    Mixin for models with timestamp fields.

    Provides automatic serialization of datetime fields to ISO format.
    """

    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    @field_serializer("created_at", "updated_at")
    @classmethod
    def serialize_datetime(cls, value: datetime | None) -> str | None:
        """Serialize datetime to ISO format string."""
        if value is None:
            return None
        return value.isoformat()


class UUIDMixin(BaseModel):
    """
    Mixin for models with UUID primary key.

    Ensures consistent UUID field naming and serialization.
    """

    id: UUID = Field(description="Unique identifier (UUID)")

    @field_serializer("id")
    @classmethod
    def serialize_uuid(cls, value: UUID) -> str:
        """Serialize UUID to string."""
        return str(value)


class ResponseModel(BaseModel):
    """
    Base response model with common metadata fields.

    All API response models should inherit from this class.
    """

    model_config = ConfigDict(
        # Exclude None values from response
        exclude_none=True,
    )


class RequestModel(BaseModel):
    """
    Base request model with common validation settings.

    All API request models should inherit from this class.
    """

    model_config = ConfigDict(
        # Extra fields are forbidden for requests
        extra="forbid",
    )


class PaginationParams(RequestModel):
    """
    Standard pagination parameters for list endpoints.
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Number of items per page"
    )

    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Get limit for database queries."""
        return self.page_size


class PaginatedResponse(ResponseModel):
    """
    Standard paginated response wrapper.
    """

    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Number of items per page")
    total_pages: int = Field(description="Total number of pages")

    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        """
        Create a paginated response dictionary.

        Args:
            items: List of items for current page
            total: Total number of items across all pages
            page: Current page number
            page_size: Number of items per page

        Returns:
            Dictionary with pagination metadata
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
        }
