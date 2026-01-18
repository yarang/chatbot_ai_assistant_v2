"""
Unit tests for User Pydantic schemas.

Tests user-related request and response models.
"""

import pytest
from pydantic import ValidationError

from api.schemas.user import UserCreate, UserResponse, UserUpdate


class TestUserCreate:
    """Test UserCreate schema."""

    def test_valid_user_with_email(self):
        """Test creating user with email."""
        user = UserCreate(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.telegram_id is None

    def test_valid_user_with_telegram_id(self):
        """Test creating user with telegram ID."""
        user = UserCreate(telegram_id=123456789)
        assert user.telegram_id == 123456789
        assert user.email is None

    def test_valid_user_with_both(self):
        """Test creating user with both email and telegram ID."""
        user = UserCreate(email="test@example.com", telegram_id=123456789)
        assert user.email == "test@example.com"
        assert user.telegram_id == 123456789

    def test_invalid_email_format(self):
        """Test that invalid email format raises validation error."""
        with pytest.raises(ValidationError):
            UserCreate(email="invalid-email")

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError):
            UserCreate(email="test@example.com", extra_field="extra")


class TestUserUpdate:
    """Test UserUpdate schema."""

    def test_update_email_only(self):
        """Test updating only email."""
        user = UserUpdate(email="newemail@example.com")
        assert user.email == "newemail@example.com"
        assert user.telegram_id is None

    def test_update_telegram_id_only(self):
        """Test updating only telegram ID."""
        user = UserUpdate(telegram_id=987654321)
        assert user.telegram_id == 987654321
        assert user.email is None

    def test_update_both(self):
        """Test updating both fields."""
        user = UserUpdate(email="new@example.com", telegram_id=987654321)
        assert user.email == "new@example.com"
        assert user.telegram_id == 987654321

    def test_empty_update(self):
        """Test empty update (all None)."""
        user = UserUpdate()
        assert user.email is None
        assert user.telegram_id is None


class TestUserResponse:
    """Test UserResponse schema."""

    def test_full_user_response(self):
        """Test complete user response."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            email="test@example.com",
            telegram_id=123456789,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-02T00:00:00Z",
        )
        # UUID is stored as UUID object, compare as string
        assert str(user.id) == "550e8400-e29b-41d4-a716-446655440000"
        assert user.email == "test@example.com"
        assert user.telegram_id == 123456789

    def test_user_response_with_nulls(self):
        """Test user response with None values."""
        user = UserResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            email=None,
            telegram_id=None,
            created_at="2024-01-01T00:00:00Z",
            updated_at=None,
        )
        assert user.email is None
        assert user.telegram_id is None
