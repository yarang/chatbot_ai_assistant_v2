"""
백그라운드 태스크 서비스

비동기 RAG 처리 파이프라인을 오케스트레이션합니다.
extract → chunk → embed 파이프라인을 실행하고 상태를 업데이트합니다.
구조화된 로깅과 에러 처리를 제공합니다.
"""

import logging
import time
from typing import Optional

from repository.file_repository import FileRepository
from services.embedding_service import EmbeddingService
from services.text_chunking_service import TextChunkingService
from services.text_extraction_service import TextExtractionService

from models.processing_result import ProcessingResult

# 로거 설정
logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """
    백그라운드 태스크 서비스

    비동기 RAG 처리 파이프라인을 오케스트레이션합니다.
    텍스트 추출 → 청킹 → 임베딩 → 상태 업데이트 순서로 처리합니다.

    Attributes:
        session: SQLAlchemy 비동기 세션
        file_repository: 파일 리포지토리
        extraction_service: 텍스트 추출 서비스
        chunking_service: 텍스트 청킹 서비스
        embedding_service: 임베딩 서비스
        max_retries: 최대 재시도 횟수 (기본값: 3)
    """

    def __init__(self, session):
        """
        BackgroundTaskService 초기화

        Args:
            session: SQLAlchemy 비동기 세션
        """
        self.session = session
        self.file_repository = FileRepository(session)
        self.extraction_service = TextExtractionService()
        self.chunking_service = TextChunkingService()
        self.embedding_service = EmbeddingService(session)
        self.max_retries = 3

        logger.info("BackgroundTaskService 초기화 완료")

    async def process_file(self, file_id: int, chat_room_id: int) -> ProcessingResult:
        """
        파일 처리 파이프라인 실행

        extract → chunk → embed 파이프라인을 순차적으로 실행합니다.
        각 단계에서 에러 발생 시 status를 failed로 업데이트합니다.
        일시적 오류 발생 시 재시도를 수행합니다.

        Args:
            file_id: 파일 ID
            chat_room_id: 채팅방 ID

        Returns:
            ProcessingResult: 처리 결과 (성공/실패, 청크 수, 에러 메시지)

        Raises:
            Exception: 파일 조회 실패 시

        Example:
            >>> result = await service.process_file(file_id=1, chat_room_id=100)
            >>> if result.success:
            ...     print(f"처리 완료: {result.chunks_processed} 청크")
        """
        start_time = time.time()

        logger.info(f"파일 처리 시작: file_id={file_id}, chat_room_id={chat_room_id}")

        # 파일 조회
        file = await self.file_repository.get_by_id(file_id)
        if not file:
            error_msg = f"파일을 찾을 수 없습니다: file_id={file_id}"
            logger.error(error_msg)
            raise Exception(error_msg)

        try:
            # Step 1: 텍스트 추출
            logger.info(f"텍스트 추출 시작: file_id={file_id}")

            # content_type에서 파일 타입 추출 (예: "application/pdf" -> "pdf")
            file_type = self._extract_file_type_from_content_type(file.content_type)

            extracted_text = await self._extract_with_retry(file.file_path, file_type)

            if not extracted_text.content.strip():
                error_msg = "추출된 텍스트가 비어있습니다"
                logger.warning(f"텍스트 추출 실패: file_id={file_id} - {error_msg}")
                await self._update_file_status(file_id, "failed", error_msg)
                return ProcessingResult(
                    success=False,
                    file_id=file_id,
                    chat_room_id=chat_room_id,
                    chunks_processed=0,
                    processing_time_seconds=time.time() - start_time,
                    error=error_msg,
                    status="failed",
                )

            logger.info(
                f"텍스트 추출 완료: file_id={file_id}, "
                f"길이={len(extracted_text.content)}자"
            )

            # Step 2: 텍스트 청킹
            logger.info(f"텍스트 청킹 시작: file_id={file_id}")
            chunks = self.chunking_service.chunk_text(extracted_text, file_id)

            logger.info(f"텍스트 청킹 완료: file_id={file_id}, 청크 수={len(chunks)}")

            # Step 3: 임베딩 생성
            logger.info(f"임베딩 생성 시작: file_id={file_id}, chunks={len(chunks)}")
            embedding_result = await self._embed_with_retry(
                chunks, chat_room_id, file_id
            )

            processing_time = time.time() - start_time

            # 성공 상태 업데이트
            await self._update_file_status(file_id, "completed")

            logger.info(
                f"파일 처리 완료: file_id={file_id}, "
                f"chunks={embedding_result.successful_chunks}, "
                f"시간={processing_time:.2f}초"
            )

            return ProcessingResult(
                success=True,
                file_id=file_id,
                chat_room_id=chat_room_id,
                chunks_processed=embedding_result.successful_chunks,
                processing_time_seconds=processing_time,
                error=None,
                status="completed",
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)

            logger.error(
                f"파일 처리 실패: file_id={file_id}, "
                f"chat_room_id={chat_room_id}, error={error_msg}"
            )

            # 실패 상태 업데이트
            await self._update_file_status(file_id, "failed", error_msg)

            return ProcessingResult(
                success=False,
                file_id=file_id,
                chat_room_id=chat_room_id,
                chunks_processed=0,
                processing_time_seconds=processing_time,
                error=error_msg,
                status="failed",
            )

    async def _extract_with_retry(self, file_path: str, file_type: str):
        """
        텍스트 추출 (재시도 포함)

        일시적 오류 발생 시 재시도를 수행합니다.

        Args:
            file_path: 파일 경로
            file_type: 파일 형식

        Returns:
            ExtractedText: 추출된 텍스트

        Raises:
            Exception: 최대 재시도 횟수 초과 시

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            process_file() 메서드를 통해 호출됩니다.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return self.extraction_service.extract_text(file_path, file_type)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"텍스트 추출 실패 (시도 {attempt + 1}/{self.max_retries}), "
                        f"재시도 진행: {str(e)}"
                    )
                    await self._sleep_backoff(attempt)
                else:
                    logger.error(
                        f"텍스트 추출 최종 실패 (시도 {attempt + 1}/{self.max_retries}): "
                        f"{str(e)}"
                    )
                    raise

        # 이 코드는 도달하지 않음 (raise로 인해)
        raise last_error

    async def _embed_with_retry(self, chunks, chat_room_id: int, file_id: int):
        """
        임베딩 생성 (재시도 포함)

        일시적 오류 발생 시 재시도를 수행합니다.

        Args:
            chunks: 텍스트 청크 리스트
            chat_room_id: 채팅방 ID
            file_id: 파일 ID

        Returns:
            EmbeddingResult: 임베딩 결과

        Raises:
            Exception: 최대 재시도 횟수 초과 시

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            process_file() 메서드를 통해 호출됩니다.
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                return await self.embedding_service.embed_chunks(
                    chunks, chat_room_id, file_id
                )
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"임베딩 생성 실패 (시도 {attempt + 1}/{self.max_retries}), "
                        f"재시도 진행: {str(e)}"
                    )
                    await self._sleep_backoff(attempt)
                else:
                    logger.error(
                        f"임베딩 생성 최종 실패 (시도 {attempt + 1}/{self.max_retries}): "
                        f"{str(e)}"
                    )
                    raise

        # 이 코드는 도달하지 않음 (raise로 인해)
        raise last_error

    def _extract_file_type_from_content_type(self, content_type: str) -> str:
        """
        content_type에서 파일 타입 추출

        Args:
            content_type: MIME 타입 (예: "application/pdf", "text/plain")

        Returns:
            str: 파일 타입 ("pdf", "txt")

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            process_file() 메서드를 통해 호출됩니다.
        """
        if not content_type:
            # 기본값: 파일 확장자에서 추론 시도
            return "pdf"  # 대부분의 경우 PDF

        content_type_lower = content_type.lower()

        if "pdf" in content_type_lower:
            return "pdf"
        elif "text" in content_type_lower or "plain" in content_type_lower:
            return "txt"
        else:
            # 기본값
            logger.warning(
                f"알 수 없는 content_type: {content_type}, 기본값 'pdf' 사용"
            )
            return "pdf"

    async def _sleep_backoff(self, attempt: int) -> None:
        """
        지수 백오프 대기

        Args:
            attempt: 현재 시도 횟수 (0-based)

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            _extract_with_retry(), _embed_with_retry() 메서드를 통해 호출됩니다.
        """
        import asyncio

        # 지수 백오프: 1초, 2초, 4초
        wait_time = 2**attempt
        logger.debug(f"재시도 대기: {wait_time}초")
        await asyncio.sleep(wait_time)

    async def _update_file_status(
        self, file_id: int, status: str, error_message: Optional[str] = None
    ) -> None:
        """
        파일 상태 업데이트

        Args:
            file_id: 파일 ID
            status: 새로운 상태 (completed/failed)
            error_message: 에러 메시지 (선택)

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            process_file() 메서드를 통해 호출됩니다.
        """
        await self.file_repository.update_status(file_id, status, error_message)
        logger.info(f"파일 상태 업데이트: file_id={file_id}, status={status}")
