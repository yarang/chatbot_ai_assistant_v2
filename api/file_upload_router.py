"""
파일 업로드 API 라우터

TASK-009: FastAPI 파일 업로드 엔드포인트 구현
POST /api/chat-rooms/{chat_room_id}/files

Phase 4: 파일 관리 API 확장
GET /api/chat-rooms/{chat_room_id}/files - 파일 목록 조회
GET /api/chat-rooms/{chat_room_id}/files/{file_id} - 파일 상태 조회
DELETE /api/chat-rooms/{chat_room_id}/files/{file_id} - 파일 삭제
GET /api/chat-rooms/{chat_room_id}/files/events - SSE 실시간 업데이트
"""

import asyncio
import json
import logging
import os
from datetime import timezone
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from repository.chat_room_repository import ChatRoomRepository
from repository.file_repository import FileRepository, FileCreate
from services.background_task_service import BackgroundTaskService
from services.file_storage_service import FileStorageService

from api.schemas.file_upload import FileUploadResponse

# 로거 설정
logger = logging.getLogger(__name__)

# 보안 설정
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".md", ".html", ".json"}

# 라우터 정의
router = APIRouter()


def validate_file_upload(file: UploadFile) -> None:
    """
    파일 업로드 보안 검증

    Args:
        file: 업로드할 파일

    Raises:
        HTTPException 413: 파일 크기 초과
        HTTPException 415: 지원되지 않는 파일 형식
        HTTPException 400: 파일명 없음
    """
    # 파일명 확인
    filename = file.filename
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일명이 없습니다",
        )

    # 파일 형식 검증 (확장자)
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"지원되지 않는 파일 형식입니다: {file_ext}. "
            f"허용된 형식: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 파일 크기 검증은 파일 내용을 읽은 후 수행


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
        # 0. 파일 보안 검증 (형식, 크기)
        validate_file_upload(file)

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

        # 4.1. 파일 크기 검증
        if file_size > MAX_FILE_SIZE:
            logger.warning(
                f"파일 크기 초과: filename={filename}, "
                f"size={file_size}, max={MAX_FILE_SIZE}"
            )
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"파일 크기는 {MAX_FILE_SIZE // (1024*1024)}MB를 초과할 수 없습니다",
            )

        if file_size == 0:
            logger.warning(f"빈 파일 감지: filename={filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="빈 파일은 업로드할 수 없습니다",
            )

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


@router.get(
    "/chat-rooms/{chat_room_id}/files",
    response_model=List[FileUploadResponse],
    status_code=status.HTTP_200_OK,
    summary="파일 목록 조회",
    description="채팅방의 모든 파일 목록을 조회합니다",
)
async def list_files(
    chat_room_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    파일 목록 조회 엔드포인트

    Args:
        chat_room_id: 채팅방 ID
        session: 데이터베이스 세션

    Returns:
        List[FileUploadResponse]: 파일 목록
    """
    try:
        file_repository = FileRepository(session)

        # 채팅방 존재 확인
        chat_room_repository = ChatRoomRepository()
        chat_room = await chat_room_repository.get_chat_room_by_telegram_id(
            session=session, telegram_chat_id=chat_room_id
        )
        if not chat_room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"채팅방을 찾을 수 없습니다: chat_room_id={chat_room_id}",
            )

        # 파일 목록 조회
        files = await file_repository.get_by_chat_room_id(chat_room_id)

        # FileUploadResponse로 변환
        response = [
            FileUploadResponse(
                file_id=f.id,
                file_name=f.filename,
                file_size=f.file_size,
                content_type=f.content_type or "application/octet-stream",
                status=f.status,
                uploaded_at=f.created_at.replace(tzinfo=timezone.utc),
            )
            for f in files
        ]

        logger.info(f"파일 목록 조회 성공: chat_room_id={chat_room_id}, count={len(response)}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 목록 조회 실패: chat_room_id={chat_room_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 목록 조회 실패: {str(e)}",
        )


@router.get(
    "/chat-rooms/{chat_room_id}/files/{file_id}",
    response_model=FileUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="파일 상태 조회",
    description="특정 파일의 처리 상태를 조회합니다",
)
async def get_file_status(
    chat_room_id: int,
    file_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    파일 상태 조회 엔드포인트

    Args:
        chat_room_id: 채팅방 ID
        file_id: 파일 ID
        session: 데이터베이스 세션

    Returns:
        FileUploadResponse: 파일 상태 정보
    """
    try:
        file_repository = FileRepository(session)

        # 파일 조회
        file_obj = await file_repository.get_by_id(file_id)
        if not file_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"파일을 찾을 수 없습니다: file_id={file_id}",
            )

        # 채팅방 ID 검증
        if file_obj.chat_room_id != chat_room_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 파일에 접근할 권한이 없습니다",
            )

        response = FileUploadResponse(
            file_id=file_obj.id,
            file_name=file_obj.filename,
            file_size=file_obj.file_size,
            content_type=file_obj.content_type or "application/octet-stream",
            status=file_obj.status,
            uploaded_at=file_obj.created_at.replace(tzinfo=timezone.utc),
        )

        logger.info(f"파일 상태 조회 성공: file_id={file_id}, status={file_obj.status}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 상태 조회 실패: file_id={file_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 상태 조회 실패: {str(e)}",
        )


@router.delete(
    "/chat-rooms/{chat_room_id}/files/{file_id}",
    status_code=status.HTTP_200_OK,
    summary="파일 삭제",
    description="파일과 관련 임베딩을 삭제합니다",
)
async def delete_file(
    chat_room_id: int,
    file_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    파일 삭제 엔드포인트

    Args:
        chat_room_id: 채팅방 ID
        file_id: 파일 ID
        session: 데이터베이스 세션

    Returns:
        dict: 삭제 결과
    """
    try:
        file_repository = FileRepository(session)
        file_storage_service = FileStorageService()

        # 파일 조회
        file_obj = await file_repository.get_by_id(file_id)
        if not file_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"파일을 찾을 수 없습니다: file_id={file_id}",
            )

        # 채팅방 ID 검증
        if file_obj.chat_room_id != chat_room_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 파일을 삭제할 권한이 없습니다",
            )

        # 파일 시스템에서 삭제
        try:
            await file_storage_service.delete_file(
                file_path=file_obj.file_path,
                chat_room_id=chat_room_id,
            )
            logger.info(f"파일 시스템 삭제 완료: {file_obj.file_path}")
        except Exception as e:
            logger.warning(f"파일 시스템 삭제 실패 (계속 진행): {str(e)}")

        # 데이터베이스에서 삭제 (임베딩은 CASCADE로 자동 삭제)
        await file_repository.delete(file_id)
        logger.info(f"파일 메타데이터 삭제 완료: file_id={file_id}")

        return {"message": "파일이 삭제되었습니다", "file_id": file_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 삭제 실패: file_id={file_id}, error={str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"파일 삭제 실패: {str(e)}",
        )


@router.get(
    "/chat-rooms/{chat_room_id}/files/events",
    summary="SSE 실시간 업데이트",
    description="파일 처리 상태 변경을 실시간으로 전송합니다",
)
async def file_status_events(
    chat_room_id: int,
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    """
    SSE(Server-Sent Events) 엔드포인트

    채팅방의 파일 상태 변경을 실시간으로 클라이언트에게 전송합니다.

    Args:
        chat_room_id: 채팅방 ID
        session: 데이터베이스 세션

    Returns:
        StreamingResponse: SSE 스트림
    """
    async def event_stream():
        """
        SSE 이벤트 스트림 생성기

        주기적으로 파일 상태를 확인하고 변경사항을 전송합니다.
        """
        # 이전 상태 저장 (변경 감지용)
        previous_states = {}

        try:
            while True:
                try:
                    file_repository = FileRepository(session)
                    files = await file_repository.get_by_chat_room_id(chat_room_id)

                    # 각 파일의 상태 확인
                    for file_obj in files:
                        current_state = {
                            "status": file_obj.status,
                            "error_message": file_obj.error_message,
                            "updated_at": file_obj.updated_at.isoformat(),
                        }

                        # 이전 상태와 비교
                        previous_state = previous_states.get(file_obj.id)

                        # 상태가 변경되었거나 처음 조회하는 경우
                        if previous_state != current_state:
                            # SSE 이벤트 전송
                            event_data = {
                                "file_id": file_obj.id,
                                "file_name": file_obj.filename,
                                "status": file_obj.status,
                                "error_message": file_obj.error_message,
                                "updated_at": current_state["updated_at"],
                            }

                            # SSE 형식: "data: {json}\n\n"
                            yield f"data: {json.dumps(event_data)}\n\n"

                            # 상태 업데이트
                            previous_states[file_obj.id] = current_state
                            logger.info(
                                f"SSE 이벤트 전송: file_id={file_obj.id}, "
                                f"status={file_obj.status}"
                            )

                    # 3초 대기 후 다음 폴링
                    await asyncio.sleep(3)

                except Exception as e:
                    logger.error(f"SSE 스트림 에러: {str(e)}")
                    # 에러 이벤트 전송
                    error_event = {"error": str(e), "type": "stream_error"}
                    yield f"data: {json.dumps(error_event)}\n\n"
                    await asyncio.sleep(5)  # 에러 후 5초 대기

        except asyncio.CancelledError:
            logger.info("SSE 클라이언트 연결 해제")
            raise
        except Exception as e:
            logger.error(f"SSE 스트림 치명적 에러: {str(e)}")
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx buffering 비활성화
        },
    )
