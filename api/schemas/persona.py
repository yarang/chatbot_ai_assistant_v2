"""
Persona-related Pydantic schemas.

This module defines request and response models for persona entities.
Migrated to Pydantic v2 with ConfigDict and model_serializer.
"""

from uuid import UUID

from pydantic import Field, field_validator

from api.schemas.base import RequestModel, ResponseModel, TimestampMixin, UUIDMixin


class PersonaBase(ResponseModel):
    """Base persona model with common fields."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Persona name (1-100 characters)",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Persona content/prompt (1-50000 characters)",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional description (max 500 characters)",
    )
    category: str | None = Field(
        default=None,
        max_length=50,
        description="Optional category (max 50 characters)",
    )
    tags: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Optional list of tags (max 20)",
    )
    is_public: bool = Field(
        default=False,
        description="Whether the persona is publicly visible",
    )


class PersonaCreate(PersonaBase, RequestModel):
    """
    Schema for creating a new persona.

    All fields except description, category, tags are required.
    """

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        """Validate that all tags are non-empty strings."""
        if value is not None:
            for tag in value:
                if not tag or not tag.strip():
                    raise ValueError("Tags cannot be empty strings")
            return [tag.strip() for tag in value]
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Validate that name is not just whitespace."""
        if not value.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return value.strip()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Helpful Assistant",
                    "content": "You are a helpful AI assistant...",
                    "description": "A friendly persona for customer support",
                    "category": "support",
                    "tags": ["friendly", "helpful"],
                    "is_public": False,
                }
            ]
        }
    }


class PersonaUpdate(RequestModel):
    """
    Schema for updating an existing persona.

    All fields are optional; only provided fields will be updated.
    """

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Persona name (1-100 characters)",
    )
    content: str | None = Field(
        default=None,
        min_length=1,
        max_length=50000,
        description="Persona content/prompt (1-50000 characters)",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional description (max 500 characters)",
    )
    category: str | None = Field(
        default=None,
        max_length=50,
        description="Optional category (max 50 characters)",
    )
    tags: list[str] | None = Field(
        default=None,
        max_length=20,
        description="Optional list of tags (max 20)",
    )
    is_public: bool | None = Field(
        default=None,
        description="Whether the persona is publicly visible",
    )

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, value: list[str] | None) -> list[str] | None:
        """Validate that all tags are non-empty strings."""
        if value is not None:
            for tag in value:
                if not tag or not tag.strip():
                    raise ValueError("Tags cannot be empty strings")
            return [tag.strip() for tag in value]
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        """Validate that name is not just whitespace."""
        if value is not None and not value.strip():
            raise ValueError("Name cannot be empty or whitespace only")
        return value.strip() if value else None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Name",
                    "content": "Updated content...",
                    "is_public": True,
                }
            ]
        }
    }


class PersonaResponse(UUIDMixin, TimestampMixin, PersonaBase):
    """
    Schema for persona response data.

    Includes timestamps, UUID serialization, and user association.
    """

    user_id: UUID = Field(
        ...,
        description="Owner user UUID",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "660e8400-e29b-41d4-a716-446655440001",
                    "name": "Helpful Assistant",
                    "content": "You are a helpful AI assistant...",
                    "description": "A friendly persona for customer support",
                    "category": "support",
                    "tags": ["friendly", "helpful"],
                    "is_public": False,
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-02T00:00:00Z",
                }
            ]
        },
    }


class PersonasListResponse(ResponseModel):
    """
    Schema for paginated list of personas.

    Used for retrieving user's personas or public personas.
    """

    items: list[PersonaResponse] = Field(
        default_factory=list,
        description="List of personas",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of personas",
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
                            "user_id": "660e8400-e29b-41d4-a716-446655440001",
                            "name": "Helpful Assistant",
                            "content": "You are helpful...",
                            "description": "Friendly support",
                            "category": "support",
                            "tags": ["friendly"],
                            "is_public": False,
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": "2024-01-02T00:00:00Z",
                        }
                    ],
                    "total": 5,
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 1,
                }
            ]
        }
    }


class ChatRoomPersonaSet(RequestModel):
    """
    Schema for setting persona on a chat room.

    None persona_id removes the current persona.
    """

    persona_id: UUID | None = Field(
        default=None,
        description="Persona UUID to set, or None to remove",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "persona_id": "550e8400-e29b-41d4-a716-446655440000",
                }
            ]
        }
    }


class BulkOperationRequest(RequestModel):
    """
    Schema for bulk persona operations.

    Supports delete, make_public, make_private actions.
    """

    persona_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of persona UUIDs to operate on",
    )
    action: str = Field(
        ...,
        pattern="^(delete|make_public|make_private)$",
        description="Action to perform: delete, make_public, or make_private",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "persona_ids": [
                        "550e8400-e29b-41d4-a716-446655440000",
                        "660e8400-e29b-41d4-a716-446655440001",
                    ],
                    "action": "delete",
                }
            ]
        }
    }


class BulkOperationResponse(ResponseModel):
    """Schema for bulk operation result."""

    success: int = Field(
        ...,
        ge=0,
        description="Number of successful operations",
    )
    failed: int = Field(
        ...,
        ge=0,
        description="Number of failed operations",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of error messages for failed operations",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": 2,
                    "failed": 0,
                    "errors": [],
                }
            ]
        }
    }


class ExportRequest(RequestModel):
    """Schema for exporting personas."""

    persona_ids: list[UUID] = Field(
        ...,
        min_length=1,
        description="List of persona UUIDs to export",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "persona_ids": [
                        "550e8400-e29b-41d4-a716-446655440000",
                    ],
                }
            ]
        }
    }


class ImportRequest(RequestModel):
    """Schema for importing personas."""

    personas: list[dict] = Field(
        ...,
        min_length=1,
        description="List of persona data to import",
    )
    overwrite_names: bool = Field(
        default=False,
        description="Whether to overwrite personas with same names",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "personas": [
                        {
                            "name": "Imported Persona",
                            "content": "Content...",
                            "description": "Description",
                        }
                    ],
                    "overwrite_names": False,
                }
            ]
        }
    }
