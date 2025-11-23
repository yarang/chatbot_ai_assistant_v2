from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

if TYPE_CHECKING:
    from models.user_model import User
    from models.chat_room_model import ChatRoom


class UsageLog(Base):
    """
    사용량 로그 모델 클래스 (DEPRECATED)
    
    ⚠️ 이 모델은 더 이상 사용되지 않습니다.
    토큰 정보는 Conversation 모델에서 직접 관리됩니다.
    
    데이터베이스 마이그레이션을 위해 유지되지만,
    새로운 코드에서는 사용하지 마세요.
    
    Attributes:
        id: 로그 ID (Primary Key, UUID)
        user_id: 사용자 ID (Foreign Key -> users.id)
        chat_room_id: 채팅방 ID (Foreign Key -> chat_rooms.id)
        model: 사용한 모델 이름
        input_tokens: 입력 토큰 수
        output_tokens: 출력 토큰 수
        created_at: 생성 일시
        
    Note:
        대신 Conversation 모델의 토큰 필드를 사용하세요:
        - Conversation.model
        - Conversation.input_tokens
        - Conversation.output_tokens
    """
    __tablename__ = "usage_logs"

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
    chat_room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    model: Mapped[str] = mapped_column(String, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        index=True
    )

    # Relationships (DEPRECATED - User와 ChatRoom에서 이미 제거됨)
    # user: Mapped["User"] = relationship("User", back_populates="usage_logs")
    # chat_room: Mapped["ChatRoom"] = relationship("ChatRoom", back_populates="usage_logs")

    def __repr__(self) -> str:
        return (
            f"<UsageLog(id={self.id}, user_id={self.user_id!r}, chat_room_id={self.chat_room_id!r}, "
            f"model={self.model!r}, tokens={self.input_tokens}+{self.output_tokens})>"
        )
