from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from pgvector.sqlalchemy import Vector

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
        nullable=False,
        index=True
    )
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)
    processing_method: Mapped[str] = mapped_column(String, default="text")
    size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), index=True)

    # Added for RAG
    content: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # Text content
    embedding = mapped_column(Vector(1536))  # OpenAI embedding dimension
    
    # Metadata columns
    source_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<KnowledgeDoc(id={self.id!r}, filename={self.filename!r}, source_type={self.source_type!r})>"
