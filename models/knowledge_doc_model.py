from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID

from core.database import Base

if TYPE_CHECKING:
    from models.chat_room_model import ChatRoom
    from models.user_model import User


class KnowledgeDoc(Base):
    """
    RAG 지식 문서 모델 클래스
    
    Attributes:
        id: 문서 ID (Primary Key, UUID)
        chat_room_id: 채팅방 ID (Foreign Key)
        user_id: 업로드한 사용자 ID (Foreign Key)
        filename: 원본 파일명
        file_path: 저장된 파일 경로
        file_type: 파일 타입 (pdf, txt 등)
        processing_method: 처리 방식 (text, vision)
        size: 파일 크기 (bytes)
        created_at: 생성 일시
    """
    __tablename__ = "knowledge_docs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    chat_room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    processing_method: Mapped[str] = mapped_column(String, default="text")
    size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    # Relationships (Optional, if needed for back-populates)
    # chat_room: Mapped["ChatRoom"] = relationship("ChatRoom", backref="knowledge_docs")
    # user: Mapped["User"] = relationship("User", backref="knowledge_docs")

    def __repr__(self) -> str:
        return f"<KnowledgeDoc(id={self.id!r}, filename={self.filename!r}, chat_room_id={self.chat_room_id})>"
