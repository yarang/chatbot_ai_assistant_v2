"""
텍스트 청크 모델

문서를 청킹한 결과를 저장하는 모델입니다.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict


class TextChunk(BaseModel):
    """
    텍스트 청크 모델

    문서를 토큰 제한에 맞춰 분할한 청크를 나타냅니다.

    Attributes:
        content: 청크의 텍스트 내용
        chunk_index: 청크의 순서 인덱스 (0부터 시작)
        metadata: 청크의 메타데이터 (원본 문서 정보 등)
    """

    content: str
    chunk_index: int
    metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)
