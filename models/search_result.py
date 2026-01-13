"""
검색 결과 모델

벡터 유사도 검색 결과를 나타내는 모델입니다.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchResult(BaseModel):
    """
    검색 결과 모델

    벡터 유사도 검색의 결과를 나타냅니다.

    Attributes:
        content: 검색된 텍스트 콘텐츠
        score: 유사도 점수 (0~1 사이의 값, 높을수록 유사함)
        metadata: 메타데이터 (파일명, 페이지, 청크 인덱스 등)
    """

    content: str = Field(..., description="검색된 텍스트 콘텐츠")
    score: float = Field(..., ge=0.0, le=1.0, description="유사도 점수 (0~1)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="메타데이터")

    model_config = ConfigDict(from_attributes=True)
