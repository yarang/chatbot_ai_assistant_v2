"""
파일 업로드 API 스키마

Pydantic v2.9 기반 요청/응답 모델 정의
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileUploadResponse(BaseModel):
    """파일 업로드 성공 응답"""

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )

    file_id: int = Field(..., description="파일 ID")
    file_name: str = Field(..., description="파일명")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    content_type: str = Field(..., description="MIME 타입")
    status: str = Field(..., description="처리 상태 (processing, completed, failed)")
    uploaded_at: datetime = Field(..., description="업로드 일시")


class ErrorResponse(BaseModel):
    """에러 응답"""

    detail: str = Field(..., description="에러 메시지")


class FileValidationError(BaseModel):
    """파일 유효성 검증 에러"""

    detail: str = Field(..., description="에러 메시지")
    error_code: str = Field(..., description="에러 코드")
    allowed_types: list[str] = Field(..., description="허용된 파일 타입 목록")
    max_size_bytes: int = Field(..., description="최대 파일 크기 (bytes)")
