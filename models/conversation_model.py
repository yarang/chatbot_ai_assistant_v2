from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, TIMESTAMP, func

from core.database import Base

if TYPE_CHECKING:
    from models.user_model import User
    from models.chat_room_model import ChatRoom


class Conversation(Base):
    """
    대화 모델 클래스
    
    Attributes:
        id: 대화 ID (Primary Key, UUID)
        user_id: 사용자 ID (Foreign Key -> users.id)
        chat_room_id: 채팅방 ID (Foreign Key -> chat_rooms.id)
        role: 역할 (user/assistant)
        message: 메시지 내용
        model: 사용한 AI 모델 (assistant 메시지의 경우)
        input_tokens: 입력 토큰 수 (assistant 메시지의 경우, 전체 입력 토큰)
        output_tokens: 출력 토큰 수 (assistant 메시지의 경우)
        created_at: 생성 일시
        
    Relationships:
        user: 사용자 정보
        chat_room: 채팅방 정보
    """
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    chat_room_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, server_default="0")
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    chat_room: Mapped["ChatRoom"] = relationship("ChatRoom", back_populates="conversations")

    def __repr__(self) -> str:
        tokens_info = ""
        if self.role == "assistant" and (self.input_tokens or self.output_tokens):
            tokens_info = f", tokens={self.input_tokens or 0}+{self.output_tokens or 0}"
        return f"<Conversation(id={self.id}, user_id={self.user_id!r}, chat_room_id={self.chat_room_id!r}, role={self.role!r}{tokens_info})>"
