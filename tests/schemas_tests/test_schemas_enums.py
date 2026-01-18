"""
Unit tests for enum Pydantic schemas.

Tests enum definitions and validation.
"""

import pytest
from pydantic import ValidationError

from api.schemas.enums import (
    ChatType,
    EvaluationScore,
    FileStatus,
    MessageRole,
)


class TestMessageRole:
    """Test MessageRole enum."""

    def test_values(self):
        """Test all enum values."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"

    def test_is_str_enum(self):
        """Test that it's a string enum."""
        assert isinstance(MessageRole.USER, str)


class TestChatType:
    """Test ChatType enum."""

    def test_values(self):
        """Test all enum values."""
        assert ChatType.PRIVATE == "private"
        assert ChatType.GROUP == "group"
        assert ChatType.SUPERGROUP == "supergroup"
        assert ChatType.CHANNEL == "channel"


class TestEvaluationScore:
    """Test EvaluationScore enum."""

    def test_values(self):
        """Test all enum values."""
        assert EvaluationScore.VERY_POOR == "1"
        assert EvaluationScore.POOR == "2"
        assert EvaluationScore.FAIR == "3"
        assert EvaluationScore.GOOD == "4"
        assert EvaluationScore.EXCELLENT == "5"


class TestFileStatus:
    """Test FileStatus enum."""

    def test_values(self):
        """Test all enum values."""
        assert FileStatus.PENDING == "pending"
        assert FileStatus.PROCESSING == "processing"
        assert FileStatus.COMPLETED == "completed"
        assert FileStatus.FAILED == "failed"
