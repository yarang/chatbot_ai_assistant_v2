"""
RAG 검색 API 스키마
"""

import re
from typing import List

from pydantic import BaseModel, Field, field_validator


class ChunkResult(BaseModel):
    """검색된 텍스트 청크 결과"""

    chunk_id: str = Field(..., description="청크 ID")
    content: str = Field(..., description="청크 내용")
    file_id: int = Field(..., description="파일 ID")
    filename: str = Field(..., description="파일명")
    similarity: float = Field(..., ge=0.0, le=1.0, description="유사도 (0-1, 높을수록 유사)")

    model_config = {"from_attributes": True}

    @field_validator('chunk_id')
    @classmethod
    def validate_chunk_id(cls, v: str) -> str:
        """청크 ID 형식 검증 (UUID 또는 숫자 문자열)"""
        if not re.match(r'^[0-9a-fA-F-]+$', v):
            raise ValueError(f'chunk_id는 UUID 형식이어야 합니다: {v}')
        return v


class RAGSearchRequest(BaseModel):
    """RAG 검색 요청"""

    query: str = Field(..., min_length=1, max_length=1000, description="검색 질문")
    chat_room_id: int = Field(..., gt=0, description="채팅방 ID")
    limit: int = Field(5, ge=1, le=20, description="반환할 최대 결과 수")
    threshold: float = Field(
        0.5, ge=0.0, le=1.0, description="유사도 임계값 (0-1, 높을수록 엄격)"
    )

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """검색 질문 검증 (빈 문자열, 공백만 있는 경우 제거)"""
        if not v.strip():
            raise ValueError('query는 공백만으로 구성될 수 없습니다')
        return v.strip()


class RAGSearchResponse(BaseModel):
    """RAG 검색 응답"""

    chunks: List[ChunkResult] = Field(default_factory=list, description="검색된 청크 리스트")
    total_chunks: int = Field(..., ge=0, description="검색된 총 청크 수")
