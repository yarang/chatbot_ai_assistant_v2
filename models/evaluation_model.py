from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, TIMESTAMP, func, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

if TYPE_CHECKING:
    from models.user_model import User
    from models.persona_model import Persona


class PersonaEvaluation(Base):
    """
    Persona 평가 모델 클래스
    
    사용자가 Persona에 대해 점수와 코멘트를 남길 수 있습니다.
    한 사용자는 한 Persona에 대해 하나의 평가만 남길 수 있습니다.
    
    Attributes:
        id: Evaluation ID (Primary Key, UUID)
        persona_id: 대상 Persona ID (Foreign Key -> personas.id)
        user_id: 평가자 User ID (Foreign Key -> users.id)
        score: 점수 (1-5)
        comment: 평가 코멘트 (Optional)
        created_at: 생성 일시
        
    Relationships:
        persona: 대상 Persona 정보
        user: 평가자 정보
    """
    __tablename__ = "persona_evaluations"
    __table_args__ = (
        CheckConstraint('score >= 1 AND score <= 5', name='check_score_range'),
        UniqueConstraint('persona_id', 'user_id', name='uq_persona_user_evaluation'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    persona_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Relationships
    persona: Mapped["Persona"] = relationship("Persona", back_populates="evaluations")
    user: Mapped["User"] = relationship("User", back_populates="evaluations")

    def __repr__(self) -> str:
        return f"<PersonaEvaluation(id={self.id!r}, persona_id={self.persona_id!r}, user_id={self.user_id!r}, score={self.score})>"
