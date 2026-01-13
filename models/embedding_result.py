"""
임베딩 결과 모델

임베딩 생성 작업의 결과를 나타내는 모델입니다.
"""
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResult(BaseModel):
    """
    임베딩 결과 모델

    임베딩 생성 작업의 결과와 통계를 나타냅니다.

    Attributes:
        total_chunks: 전체 청크 수
        successful_chunks: 성공적으로 임베딩된 청크 수
        failed_chunks: 실패한 청크 수
        embedding_dimension: 임베딩 벡터 차원 (768)
        batch_count: 사용된 배치 수
        processing_time_seconds: 총 처리 시간 (초)
        metadata: 추가 메타데이터
    """

    total_chunks: int = Field(..., ge=0, description="전체 청크 수")
    successful_chunks: int = Field(..., ge=0, description="성공적으로 처리된 청크 수")
    failed_chunks: int = Field(..., ge=0, description="실패한 청크 수")
    embedding_dimension: int = Field(..., ge=1, description="임베딩 벡터 차원")
    batch_count: int = Field(..., ge=1, description="사용된 배치 수")
    processing_time_seconds: float = Field(..., ge=0.0, description="총 처리 시간 (초)")
    metadata: dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")

    model_config = ConfigDict(from_attributes=True)
