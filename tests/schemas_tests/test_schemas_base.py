"""
Unit tests for base Pydantic schemas.

Tests core base models and mixins.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas.base import (
    BaseModel,
    PaginatedResponse,
    PaginationParams,
    RequestModel,
    ResponseModel,
)
from api.schemas.chat_room import ChatRoomResponse
from api.schemas.enums import ChatType


class TestBaseModel:
    """Test BaseModel configuration."""

    def test_use_enum_values(self):
        """Test that enum values are used in serialization."""
        model = ChatRoomResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            telegram_chat_id=-1001234567890,
            chat_type=ChatType.SUPERGROUP,
            persona_id="660e8400-e29b-41d4-a716-446655440001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert model.chat_type == "supergroup"

    def test_extra_ignore(self):
        """Test that extra fields are ignored."""

        # Create a simple test model for this test
        class TestModel(BaseModel):
            field1: str

        model = TestModel.model_validate({"field1": "value1", "extra_field": "extra"})
        assert model.field1 == "value1"
        assert not hasattr(model, "extra_field")


class TestUUIDMixin:
    """Test UUIDMixin functionality."""

    def test_uuid_serialization(self):
        """Test that UUID is serialized to string in model_dump()."""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        model = ChatRoomResponse(
            id=uuid_str,
            telegram_chat_id=-1001234567890,
            chat_type=ChatType.PRIVATE,
            persona_id="660e8400-e29b-41d4-a716-446655440001",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        # UUID is stored as UUID object
        assert str(model.id) == uuid_str
        # model_dump() serializes to string
        data = model.model_dump()
        assert data["id"] == uuid_str


class TestTimestampMixin:
    """Test TimestampMixin functionality."""

    def test_datetime_serialization(self):
        """Test that datetime is serialized to ISO format in model_dump()."""
        now = datetime.now()
        iso_now = now.isoformat()
        model = ChatRoomResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            telegram_chat_id=-1001234567890,
            chat_type=ChatType.PRIVATE,
            persona_id="660e8400-e29b-41d4-a716-446655440001",
            created_at=now,
            updated_at=now,
        )
        # Datetime is stored as datetime object
        assert model.created_at == now
        # model_dump() serializes to ISO string
        data = model.model_dump()
        assert data["created_at"] == iso_now
        assert data["updated_at"] == iso_now


class TestRequestModel:
    """Test RequestModel configuration."""

    def test_extra_forbid(self):
        """Test that extra fields are forbidden for requests."""

        class TestRequestModel(RequestModel):
            field1: str

        with pytest.raises(ValidationError):
            TestRequestModel.model_validate(
                {"field1": "value1", "extra_field": "extra"}
            )


class TestResponseModel:
    """Test ResponseModel configuration."""

    def test_exclude_none(self):
        """Test that None values are excluded from response."""

        class TestResponseModel(ResponseModel):
            field1: str
            field2: str | None = None

        model = TestResponseModel(field1="value1", field2=None)
        data = model.model_dump(exclude_none=True)
        assert "field1" in data
        assert "field2" not in data


class TestPaginationParams:
    """Test PaginationParams functionality."""

    def test_default_values(self):
        """Test default pagination values."""
        params = PaginationParams()
        assert params.page == 1
        assert params.page_size == 20

    def test_offset_calculation(self):
        """Test offset calculation."""
        params = PaginationParams(page=2, page_size=10)
        assert params.offset == 10
        assert params.limit == 10

    def test_page_validation(self):
        """Test that page must be >= 1."""
        with pytest.raises(ValidationError):
            PaginationParams(page=0)

    def test_page_size_validation(self):
        """Test page_size bounds (1-100)."""
        # Valid
        params = PaginationParams(page_size=1)
        assert params.page_size == 1

        params = PaginationParams(page_size=100)
        assert params.page_size == 100

        # Invalid
        with pytest.raises(ValidationError):
            PaginationParams(page_size=0)

        with pytest.raises(ValidationError):
            PaginationParams(page_size=101)


class TestPaginatedResponse:
    """Test PaginatedResponse functionality."""

    def test_create_method(self):
        """Test PaginatedResponse.create factory method."""
        items = [{"id": 1}, {"id": 2}]
        result = PaginatedResponse.create(items=items, total=10, page=1, page_size=5)
        assert result["items"] == items
        assert result["total"] == 10
        assert result["page"] == 1
        assert result["page_size"] == 5
        assert result["total_pages"] == 2

    def test_total_pages_calculation(self):
        """Test total_pages calculation."""
        # Exactly divisible
        result = PaginatedResponse.create(items=[], total=10, page=1, page_size=5)
        assert result["total_pages"] == 2

        # Remainder
        result = PaginatedResponse.create(items=[], total=11, page=1, page_size=5)
        assert result["total_pages"] == 3

        # Empty
        result = PaginatedResponse.create(items=[], total=0, page=1, page_size=5)
        assert result["total_pages"] == 0
