"""
처리 결과 모델

BackgroundTaskService의 처리 결과를 나타내는 Pydantic 모델입니다.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ProcessingResult(BaseModel):
    """
    처리 결과 모델

    비동기 RAG 처리 파이프라인의 실행 결과를 나타냅니다.

    Attributes:
        success: 처리 성공 여부
        file_id: 파일 ID
        chat_room_id: 채팅방 ID
        chunks_processed: 처리된 청크 수
        processing_time_seconds: 총 처리 시간 (초)
        error: 에러 메시지 (실패 시)
        status: 최종 파일 상태 (completed/failed)
    """

    success: bool = Field(..., description="처리 성공 여부")
    file_id: int = Field(..., gt=0, description="파일 ID")
    chat_room_id: int = Field(..., gt=0, description="채팅방 ID")
    chunks_processed: int = Field(default=0, ge=0, description="처리된 청크 수")
    processing_time_seconds: float = Field(
        default=0.0, ge=0.0, description="총 처리 시간 (초)"
    )
    error: Optional[str] = Field(None, description="에러 메시지 (실패 시)")
    status: str = Field(..., description="최종 파일 상태 (completed/failed)")

    model_config = {"from_attributes": True}
