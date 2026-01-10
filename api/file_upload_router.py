"""
파일 업로드 API 라우터

TASK-009: FastAPI 파일 업로드 엔드포인트 구현
POST /api/chat-rooms/{chat_room_id}/files
"""

import asyncio
import logging
from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from repository.chat_room_repository import ChatRoomRepository
from repository.file_repository import FileRepository, FileCreate
from services.background_task_service import BackgroundTaskService
from services.file_storage_service import FileStorageService

from api.schemas.file_upload import FileUploadResponse

# 로거 설정
logger = logging.getLogger(__name__)

# 라우터 정의
router = APIRouter()


@router.post(
    "/chat-rooms/{chat_room_id}/files",
    response_model=FileUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="파일 업로드",
    description="채팅방에 파일을 업로드하고 RAG 처리를 시작합니다",
)
async def upload_file(
    chat_room_id: int,
    file: Annotated[UploadFile, File(description="업로드할 파일 (PDF, TXT 등)")],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    파일 업로드 엔드포인트

    Args:
        chat_room_id: 채팅방 ID
        file: 업로드할 파일
        session: 데이터베이스 세션

    Returns:
        FileUploadResponse: 업로드된 파일 정보

    Raises:
        HTTPException 404: 채팅방을 찾을 수 없음
        HTTPException 400: 파일 유효성 검증 실패
        HTTPException 409: 중복 파일
        HTTPException 500: 서버 내부 에러
    """
    # 서비스 인스턴스 생성
    file_repository = FileRepository(session)
    file_storage_service = FileStorageService()
    chat_room_repository = ChatRoomRepository()

    try:
        # 1. 채팅방 존재 확인 (telegram_chat_id로 조회)
        # File 모델은 chat_room_id를 Integer로 저장하므로, ChatRoom의 telegram_chat_id와 매핑
        chat_room = await chat_room_repository.get_chat_room_by_telegram_id(
            session=session, telegram_chat_id=chat_room_id
        )
        if not chat_room:
            logger.warning(f"채팅방을 찾을 수 없음: telegram_chat_id={chat_room_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"채팅방을 찾을 수 없습니다: chat_room_id={chat_room_id}",
            )

        # 2. 파일명 추출
        filename = file.filename or "unnamed"
        content_type = file.content_type

        logger.info(
            f"파일 업로드 시작: chat_room_id={chat_room_id}, "
            f"filename={filename}, content_type={content_type}"
        )

        # 3. 중복 파일 확인
        is_duplicate = await file_repository.check_duplicate(chat_room_id, filename)
        if is_duplicate:
            logger.warning(
                f"중복 파일 감지: chat_room_id={chat_room_id}, filename={filename}"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"동일한 이름의 파일이 이미 존재합니다: {filename}",
            )

        # 4. 파일 내용 읽기
        file_content = await file.read()
        file_size = len(file_content)

        # 5. 파일 저장소 서비스를 통한 저장 (유효성 검증 포함)
        try:
            file_path = await file_storage_service.save_file(
                filename=filename,
                content=file_content,
                chat_room_id=chat_room_id,
                content_type=content_type,
            )
            logger.info(f"파일 저장 완료: {file_path}")
        except Exception as e:
            logger.error(f"파일 저장 실패: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"파일 저장 실패: {str(e)}",
            )

        # 6. 데이터베이스 메타데이터 저장
        file_create_data = FileCreate(
            chat_room_id=chat_room_id,
            filename=filename,
            file_path=str(file_path),
            file_size=file_size,
            content_type=content_type,
        )

        db_file = await file_repository.create(file_create_data)
        logger.info(f"파일 메타데이터 저장 완료: file_id={db_file.id}")

        # 7. 백그라운드 태스크 트리거 (RAG 처리)
        background_task_service = BackgroundTaskService(session)

        # asyncio.create_task로 비동기 처리 실행
        async def run_background_task():
            """백그라운드 태스크 실행 래퍼"""
            try:
                logger.info(f"백그라운드 RAG 처리 시작: file_id={db_file.id}")
                await background_task_service.process_file(db_file.id, chat_room_id)
                logger.info(f"백그라운드 RAG 처리 완료: file_id={db_file.id}")
            except Exception as e:
                logger.error(
                    f"백그라운드 RAG 처리 실패: file_id={db_file.id}, error={str(e)}"
                )

        # 백그라운드 태스크 생성 (비동기 실행)
        asyncio.create_task(run_background_task())

        # 8. 응답 반환
        response = FileUploadResponse(
            file_id=db_file.id,
            file_name=db_file.filename,
            file_size=db_file.file_size,
            content_type=db_file.content_type or "application/octet-stream",
            status=db_file.status,
            uploaded_at=db_file.created_at.replace(tzinfo=timezone.utc),
        )

        logger.info(
            f"파일 업로드 성공: file_id={db_file.id}, "
            f"chat_room_id={chat_room_id}, filename={filename}"
        )

        return response

    except HTTPException:
        # HTTP 예외는 그대로 전파
        raise
    except Exception as e:
        logger.error(
            f"파일 업로드 중 예상치 못한 에러 발생: "
            f"chat_room_id={chat_room_id}, error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 업로드 실패: {str(e)}",
        )
