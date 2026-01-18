"""
Evaluation-related Pydantic schemas.

This module defines request and response models for persona evaluations.
"""

from uuid import UUID

from pydantic import Field, field_validator

from api.schemas.base import RequestModel, ResponseModel, TimestampMixin, UUIDMixin
from api.schemas.enums import EvaluationScore


class EvaluationBase(ResponseModel):
    """Base evaluation model with common fields."""

    score: int = Field(
        ...,
        ge=1,
        le=5,
        description="Evaluation score from 1 (very poor) to 5 (excellent)",
    )
    comment: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional comment (max 1000 characters)",
    )


class EvaluationCreate(EvaluationBase, RequestModel):
    """
    Schema for creating a new persona evaluation.

    Score must be between 1 and 5 inclusive.
    """

    @field_validator("comment")
    @classmethod
    def validate_comment(cls, value: str | None) -> str | None:
        """Validate that comment is not just whitespace."""
        if value is not None:
            value = value.strip()
            if not value:
                return None
        return value

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "score": 5,
                    "comment": "Excellent response!",
                }
            ]
        }
    }


class EvaluationResponse(UUIDMixin, TimestampMixin, EvaluationBase):
    """
    Schema for evaluation response data.

    Includes timestamps and UUID serialization.
    """

    persona_id: UUID = Field(
        ...,
        description="Evaluated persona UUID",
    )
    user_id: UUID = Field(
        ...,
        description="Evaluator user UUID",
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "persona_id": "660e8400-e29b-41d4-a716-446655440001",
                    "user_id": "770e8400-e29b-41d4-a716-446655440002",
                    "score": 5,
                    "comment": "Excellent response!",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": None,
                }
            ]
        },
    }


class EvaluationsListResponse(ResponseModel):
    """
    Schema for paginated list of evaluations.

    Used for retrieving evaluations for a persona.
    """

    items: list[EvaluationResponse] = Field(
        default_factory=list,
        description="List of evaluations",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of evaluations",
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
                            "persona_id": "660e8400-e29b-41d4-a716-446655440001",
                            "user_id": "770e8400-e29b-41d4-a716-446655440002",
                            "score": 5,
                            "comment": "Excellent!",
                            "created_at": "2024-01-01T00:00:00Z",
                            "updated_at": None,
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
