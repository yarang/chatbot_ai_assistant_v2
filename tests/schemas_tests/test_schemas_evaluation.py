"""
Unit tests for Evaluation Pydantic schemas.

Tests evaluation-related request and response models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from api.schemas.evaluation import EvaluationCreate, EvaluationResponse


class TestEvaluationCreate:
    """Test EvaluationCreate schema."""

    def test_valid_evaluation(self):
        """Test creating valid evaluation."""
        eval = EvaluationCreate(score=5)
        assert eval.score == 5
        assert eval.comment is None

    def test_evaluation_with_comment(self):
        """Test evaluation with comment."""
        eval = EvaluationCreate(score=4, comment="Good response!")
        assert eval.score == 4
        assert eval.comment == "Good response!"

    def test_score_too_low(self):
        """Test that score below 1 raises validation error."""
        with pytest.raises(ValidationError):
            EvaluationCreate(score=0)

    def test_score_too_high(self):
        """Test that score above 5 raises validation error."""
        with pytest.raises(ValidationError):
            EvaluationCreate(score=6)

    def test_all_valid_scores(self):
        """Test all valid score values (1-5)."""
        for score in [1, 2, 3, 4, 5]:
            eval = EvaluationCreate(score=score)
            assert eval.score == score

    def test_comment_too_long(self):
        """Test that comment exceeding max length raises validation error."""
        with pytest.raises(ValidationError):
            EvaluationCreate(score=5, comment="a" * 1001)

    def test_whitespace_comment_stripped(self):
        """Test that whitespace-only comment becomes None."""
        eval = EvaluationCreate(score=5, comment="   ")
        assert eval.comment is None

    def test_whitespace_comment_trimmed(self):
        """Test that comment whitespace is trimmed."""
        eval = EvaluationCreate(score=5, comment="  Good!  ")
        assert eval.comment == "Good!"


class TestEvaluationResponse:
    """Test EvaluationResponse schema."""

    def test_full_response(self):
        """Test complete evaluation response."""
        eval = EvaluationResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            persona_id="660e8400-e29b-41d4-a716-446655440001",
            user_id="770e8400-e29b-41d4-a716-446655440002",
            score=5,
            comment="Excellent!",
            created_at=datetime.now(),
            updated_at=None,
        )
        assert eval.score == 5
        assert eval.comment == "Excellent!"
        assert eval.updated_at is None
