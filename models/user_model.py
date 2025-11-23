from __future__ import annotations

import uuid
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base


class User(Base):
    """
    사용자 모델 클래스
    
    Attributes:
        id: 사용자 ID (Primary Key, UUID)
        email: 사용자 이메일 (UNIQUE)
        telegram_id: Telegram 사용자 ID (UNIQUE)
        username: 사용자명
        first_name: 이름
        last_name: 성
        created_at: 생성 일시
        
    Relationships:
        conversations: 사용자의 대화 목록
        personas: 사용자가 생성한 Persona 목록
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    telegram_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    personas: Mapped[List["Persona"]] = relationship(
        "Persona",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id!r}, email={self.email!r}, telegram_id={self.telegram_id}, username={self.username!r})>"
