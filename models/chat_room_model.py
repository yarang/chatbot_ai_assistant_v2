from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, BigInteger, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

if TYPE_CHECKING:
    from models.conversation_model import Conversation
    from models.persona_model import Persona


class ChatRoom(Base):
    """
    채팅방 모델 클래스
    
    Attributes:
        id: 채팅방 ID (Primary Key, UUID)
        telegram_chat_id: Telegram 채팅 ID (UNIQUE, BIGINT to support large IDs)
        name: 채팅방 이름 (그룹/채널 제목 또는 개인 채팅의 경우 사용자명)
        type: 채팅 타입 (private, group, supergroup, channel)
        username: 채팅방 사용자명 (선택적, 채널/그룹의 경우)
        persona_id: 사용할 Persona ID (Foreign Key -> personas.id)
        created_at: 생성 일시
        updated_at: 수정 일시
        
    Relationships:
        conversations: 채팅방의 대화 목록
        persona: 채팅방에서 사용하는 Persona (시스템 프롬프트)
    """
    __tablename__ = "chat_rooms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # private, group, supergroup, channel
    username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    persona_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("personas.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="chat_room",
        cascade="all, delete-orphan"
    )
    persona: Mapped[Optional["Persona"]] = relationship("Persona", back_populates="chat_rooms")

    def __repr__(self) -> str:
        return f"<ChatRoom(id={self.id!r}, telegram_chat_id={self.telegram_chat_id}, name={self.name!r}, type={self.type!r})>"

