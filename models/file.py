"""
파일 메타데이터 모델

RAG 파일 정보를 저장하는 데이터베이스 모델입니다.
"""
from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text

from core.database import Base


class File(Base):
    """
    RAG 파일 메타데이터 모델

    Attributes:
        id: 파일 ID (PK)
        chat_room_id: 채팅방 ID
        filename: 파일명
        file_path: 파일 시스템 경로
        file_size: 파일 크기 (bytes)
        content_type: MIME 타입
        status: 처리 상태 (processing, completed, failed)
        error_message: 에러 메시지
        created_at: 생성일시
        updated_at: 수정일시
    """
    __tablename__ = "rag_files"

    id = Column(Integer, primary_key=True, index=True)
    chat_room_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    content_type = Column(String(100))
    status = Column(String(50), default="processing", index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename={self.filename}, chat_room_id={self.chat_room_id})>"
