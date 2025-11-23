from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

if TYPE_CHECKING:
    from models.user_model import User
    from models.chat_room_model import ChatRoom


class Persona(Base):
    """
    Persona 모델 클래스 (시스템 프롬프트)
    
    사용자가 생성한 AI 페르소나(프롬프트)를 저장합니다.
    각 채팅방에서 선택하여 사용할 수 있습니다.
    
    Attributes:
        id: Persona ID (Primary Key, UUID)
        user_id: 생성자 User ID (Foreign Key -> users.id)
        name: Persona 이름
        content: Persona 내용 (시스템 프롬프트)
        description: Persona 설명 (선택적)
        is_public: 공개 여부 (다른 사용자도 사용 가능)
        created_at: 생성 일시
        updated_at: 수정 일시
        
    Relationships:
        user: 생성자 정보
        chat_rooms: 이 Persona를 사용하는 채팅방 목록
    """
    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)  # 시스템 프롬프트 내용
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="personas")
    chat_rooms: Mapped[List["ChatRoom"]] = relationship(
        "ChatRoom",
        back_populates="persona"
    )

    def __repr__(self) -> str:
        return f"<Persona(id={self.id!r}, name={self.name!r}, user_id={self.user_id!r}, is_public={self.is_public})>"

