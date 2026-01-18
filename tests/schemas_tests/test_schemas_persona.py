"""
Unit tests for Persona Pydantic schemas.

Tests persona-related request and response models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas.persona import (
    BulkOperationRequest,
    ChatRoomPersonaSet,
    PersonaCreate,
    PersonaResponse,
    PersonaUpdate,
)


class TestPersonaCreate:
    """Test PersonaCreate schema."""

    def test_valid_persona(self):
        """Test creating valid persona."""
        persona = PersonaCreate(
            name="Test Persona",
            content="This is a test persona content.",
        )
        assert persona.name == "Test Persona"
        assert persona.content == "This is a test persona content."
        assert persona.is_public is False

    def test_persona_with_optional_fields(self):
        """Test persona with all optional fields."""
        persona = PersonaCreate(
            name="Test Persona",
            content="Content",
            description="A description",
            category="test",
            tags=["tag1", "tag2"],
            is_public=True,
        )
        assert persona.description == "A description"
        assert persona.category == "test"
        assert persona.tags == ["tag1", "tag2"]
        assert persona.is_public is True

    def test_name_too_short(self):
        """Test that empty name raises validation error."""
        with pytest.raises(ValidationError):
            PersonaCreate(name="", content="Content")

    def test_name_too_long(self):
        """Test that name exceeding max length raises validation error."""
        with pytest.raises(ValidationError):
            PersonaCreate(name="a" * 101, content="Content")

    def test_content_too_long(self):
        """Test that content exceeding max length raises validation error."""
        with pytest.raises(ValidationError):
            PersonaCreate(name="Test", content="a" * 50001)

    def test_tags_validation_empty_string(self):
        """Test that empty strings in tags raise validation error."""
        with pytest.raises(ValidationError):
            PersonaCreate(name="Test", content="Content", tags=["valid", ""])

    def test_tags_validation_whitespace(self):
        """Test that whitespace-only tags are trimmed."""
        persona = PersonaCreate(
            name="Test", content="Content", tags=[" tag1 ", " tag2 "]
        )
        assert persona.tags == ["tag1", "tag2"]

    def test_name_whitespace_trimming(self):
        """Test that name whitespace is trimmed."""
        persona = PersonaCreate(name="  Test Persona  ", content="Content")
        assert persona.name == "Test Persona"

    def test_name_whitespace_only(self):
        """Test that whitespace-only name raises validation error."""
        with pytest.raises(ValidationError):
            PersonaCreate(name="   ", content="Content")


class TestPersonaUpdate:
    """Test PersonaUpdate schema."""

    def test_partial_update(self):
        """Test updating only some fields."""
        persona = PersonaUpdate(name="Updated Name")
        assert persona.name == "Updated Name"
        assert persona.content is None
        assert persona.is_public is None

    def test_update_all_fields(self):
        """Test updating all fields."""
        persona = PersonaUpdate(
            name="New Name",
            content="New Content",
            description="New Description",
            category="new",
            tags=["new1"],
            is_public=True,
        )
        assert persona.name == "New Name"
        assert persona.content == "New Content"
        assert persona.is_public is True

    def test_update_with_invalid_name(self):
        """Test that invalid name in update raises validation error."""
        with pytest.raises(ValidationError):
            PersonaUpdate(name="")

    def test_update_with_invalid_tags(self):
        """Test that invalid tags in update raise validation error."""
        with pytest.raises(ValidationError):
            PersonaUpdate(tags=["valid", ""])


class TestPersonaResponse:
    """Test PersonaResponse schema."""

    def test_full_response(self):
        """Test complete persona response."""
        persona = PersonaResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            user_id="660e8400-e29b-41d4-a716-446655440001",
            name="Test Persona",
            content="Content",
            description="Description",
            category="test",
            tags=["tag1"],
            is_public=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert persona.name == "Test Persona"
        assert persona.tags == ["tag1"]


class TestChatRoomPersonaSet:
    """Test ChatRoomPersonaSet schema."""

    def test_set_persona(self):
        """Test setting a persona."""
        request = ChatRoomPersonaSet(persona_id="550e8400-e29b-41d4-a716-446655440000")
        # UUID is stored as UUID object, compare as string
        assert str(request.persona_id) == "550e8400-e29b-41d4-a716-446655440000"

    def test_remove_persona(self):
        """Test removing a persona."""
        request = ChatRoomPersonaSet(persona_id=None)
        assert request.persona_id is None


class TestBulkOperationRequest:
    """Test BulkOperationRequest schema."""

    def test_valid_bulk_request(self):
        """Test valid bulk operation request."""
        request = BulkOperationRequest(
            persona_ids=[
                "550e8400-e29b-41d4-a716-446655440000",
                "660e8400-e29b-41d4-a716-446655440001",
            ],
            action="delete",
        )
        assert len(request.persona_ids) == 2
        assert request.action == "delete"

    def test_empty_persona_ids(self):
        """Test that empty persona_ids raises validation error."""
        with pytest.raises(ValidationError):
            BulkOperationRequest(persona_ids=[], action="delete")

    def test_invalid_action(self):
        """Test that invalid action raises validation error."""
        with pytest.raises(ValidationError):
            BulkOperationRequest(
                persona_ids=["550e8400-e29b-41d4-a716-446655440000"],
                action="invalid",
            )

    def test_valid_actions(self):
        """Test all valid action values."""
        for action in ["delete", "make_public", "make_private"]:
            request = BulkOperationRequest(
                persona_ids=["550e8400-e29b-41d4-a716-446655440000"],
                action=action,
            )
            assert request.action == action
