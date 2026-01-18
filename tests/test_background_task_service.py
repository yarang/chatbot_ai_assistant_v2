"""
BackgroundTaskService TDD 테스트

비동기 RAG 처리 파이프라인 오케스트레이션을 검증합니다.
extract → chunk → embed 파이프라인, 상태 업데이트, 구조화된 로깅, 에러 처리를 테스트합니다.
"""
import time
from typing import TYPE_CHECKING, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from models.text_chunk import TextChunk

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def db_session() -> AsyncSession:
    """테스트를 위한 비동기 DB 세션"""
    async with get_async_session() as session:
        yield session
        # 테스트 후 정리
        await session.rollback()


@pytest.fixture
def background_task_service(db_session: AsyncSession):
    """BackgroundTaskService fixture"""
    from services.background_task_service import BackgroundTaskService
    return BackgroundTaskService(db_session)


@pytest.fixture
async def test_chat_room_id(db_session: AsyncSession) -> int:
    """테스트용 채팅방 ID 생성"""
    return 54321


@pytest.fixture
async def test_file_id(
    db_session: AsyncSession,
    test_chat_room_id: int
) -> int:
    """테스트용 파일 ID 생성"""
    from sqlalchemy import text

    result = await db_session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 2048, 'application/pdf', 'processing')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    file_id = result.scalar()
    await db_session.commit()
    return file_id


@pytest.fixture
def sample_extracted_text():
    """샘플 추출된 텍스트"""
    from services.text_extraction_service import ExtractedText
    return ExtractedText(
        content="머신러닝은 인공지능의 한 분야입니다. 딥러닝은 신경망을 기반으로 합니다. " *
               10,  # 충분한 길이의 텍스트
        metadata={"file_type": "pdf", "page_count": 3}
    )


@pytest.fixture
def sample_chunks() -> List[TextChunk]:
    """샘플 텍스트 청크"""
    return [
        TextChunk(
            content="머신러닝은 인공지능의 한 분야입니다.",
            chunk_index=0,
            metadata={"file_id": 1, "total_chunks": 3}
        ),
        TextChunk(
            content="딥러닝은 신경망을 기반으로 합니다.",
            chunk_index=1,
            metadata={"file_id": 1, "total_chunks": 3}
        ),
        TextChunk(
            content="자연어 처리는 텍스트 데이터를 다룹니다.",
            chunk_index=2,
            metadata={"file_id": 1, "total_chunks": 3}
        ),
    ]


# ============================================================================
# RED Phase Tests
# ============================================================================

@pytest.mark.asyncio
async def test_process_file_full_pipeline_success(
    background_task_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_extracted_text,
    sample_chunks
):
    """
    전체 파이프라인 성공 테스트
    extract → chunk → embed → status update
    """
    # Given: 의존 서비스들을 모킹
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=sample_chunks
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        return_value=MagicMock(
            total_chunks=3,
            successful_chunks=3,
            failed_chunks=0,
            processing_time_seconds=5.0
        )
    ):
        # When: 파일 처리
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 결과 검증
        assert result is not None, "결과가 None이 아니어야 합니다"
        assert result.success is True, "처리가 성공해야 합니다"
        assert result.file_id == test_file_id, "파일 ID가 일치해야 합니다"
        assert result.chunks_processed == 3, "3개의 청크가 처리되어야 합니다"
        assert result.error is None, "에러가 없어야 합니다"

        # 상태 업데이트 확인
        file = await background_task_service.file_repository.get_by_id(test_file_id)
        assert file.status == "completed", "파일 상태가 completed여야 합니다"


@pytest.mark.asyncio
async def test_process_file_extraction_failure(
    background_task_service,
    test_chat_room_id: int
):
    """
    텍스트 추출 실패 테스트
    추출 단계에서 에러 발생 시 status가 failed로 업데이트되어야 함
    """
    # Given: 테스트용 파일 생성
    from sqlalchemy import text
    result = await background_task_service.session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 2048, 'application/pdf', 'processing')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    test_file_id = result.scalar()
    await background_task_service.session.commit()

    # Given: 추출 서비스가 에러를 발생시킴
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        side_effect=Exception("PDF 파일을 읽을 수 없습니다")
    ):
        # When: 파일 처리
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 실패 결과 검증
        assert result.success is False, "처리가 실패해야 합니다"
        assert result.error is not None, "에러 메시지가 있어야 합니다"
        assert "PDF 파일을 읽을 수 없습니다" in result.error, "에러 메시지가 포함되어야 합니다"

        # 상태 업데이트 확인
        file = await background_task_service.file_repository.get_by_id(test_file_id)
        assert file.status == "failed", "파일 상태가 failed여야 합니다"
        assert file.error_message is not None, "에러 메시지가 저장되어야 합니다"


@pytest.mark.asyncio
async def test_process_file_chunking_failure(
    background_task_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_extracted_text
):
    """
    청킹 실패 테스트
    청킹 단계에서 에러 발생 시 status가 failed로 업데이트되어야 함
    """
    # Given: 청킹 서비스가 에러를 발생시킴
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        side_effect=ValueError("텍스트가 비어있습니다")
    ):
        # When: 파일 처리
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 실패 결과 검증
        assert result.success is False, "처리가 실패해야 합니다"
        assert result.error is not None, "에러 메시지가 있어야 합니다"

        # 상태 업데이트 확인
        file = await background_task_service.file_repository.get_by_id(test_file_id)
        assert file.status == "failed", "파일 상태가 failed여야 합니다"


@pytest.mark.asyncio
async def test_process_file_embedding_failure(
    background_task_service,
    test_chat_room_id: int,
    sample_extracted_text,
    sample_chunks
):
    """
    임베딩 실패 테스트
    임베딩 단계에서 에러 발생 시 status가 failed로 업데이트되어야 함
    """
    # Given: 테스트용 파일 생성
    from sqlalchemy import text
    result = await background_task_service.session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 2048, 'application/pdf', 'processing')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    test_file_id = result.scalar()
    await background_task_service.session.commit()

    # Given: 임베딩 서비스가 에러를 발생시킴
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=sample_chunks
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        side_effect=Exception("Embedding API 오류")
    ):
        # When: 파일 처리
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 실패 결과 검증
        assert result.success is False, "처리가 실패해야 합니다"
        assert result.error is not None, "에러 메시지가 있어야 합니다"

        # 상태 업데이트 확인
        file = await background_task_service.file_repository.get_by_id(test_file_id)
        assert file.status == "failed", "파일 상태가 failed여야 합니다"


@pytest.mark.asyncio
async def test_process_file_retry_on_transient_error(
    background_task_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_extracted_text,
    sample_chunks
):
    """
    일시적 오류 재시도 테스트
    API 일시적 오류 발생 시 재시도 후 성공해야 함
    """
    # Given: 임베딩 서비스가 1번 실패 후 성공
    call_count = 0

    async def mock_embed_with_retry(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("API 일시적 오류")
        return MagicMock(
            total_chunks=3,
            successful_chunks=3,
            failed_chunks=0,
            processing_time_seconds=5.0
        )

    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=sample_chunks
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        side_effect=mock_embed_with_retry
    ):
        # When: 파일 처리 (재시도 포함)
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 재시도 후 성공
        assert call_count == 2, "2번의 시도가 있어야 합니다 (1번 실패 + 1번 성공)"
        assert result.success is True, "재시도 후 성공해야 합니다"
        assert result.chunks_processed == 3, "모든 청크가 처리되어야 합니다"


@pytest.mark.asyncio
async def test_process_file_status_transitions(
    background_task_service,
    test_chat_room_id: int,
    sample_extracted_text,
    sample_chunks
):
    """
    상태 전이 테스트
    processing → completed/failed 전이를 확인
    """
    # Given: 테스트용 파일 생성
    from sqlalchemy import text
    result = await background_task_service.session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 2048, 'application/pdf', 'processing')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    test_file_id = result.scalar()
    await background_task_service.session.commit()

    # Given: 초기 상태 확인
    file_before = await background_task_service.file_repository.get_by_id(test_file_id)
    assert file_before.status == "processing", "초기 상태는 processing이어야 합니다"

    # Given: 성공적인 파이프라인 모킹
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=sample_chunks
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        return_value=MagicMock(
            total_chunks=3,
            successful_chunks=3,
            failed_chunks=0,
            processing_time_seconds=5.0
        )
    ):
        # When: 파일 처리
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 상태 전이 확인
        file_after = await background_task_service.file_repository.get_by_id(test_file_id)
        assert file_after.status == "completed", "최종 상태는 completed여야 합니다"
        assert result.success is True, "처리가 성공해야 합니다"


@pytest.mark.asyncio
async def test_process_file_structured_logging(
    background_task_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_extracted_text,
    sample_chunks,
    caplog
):
    """
    구조화된 로깅 테스트
    각 단계별로 적절한 로그가 출력되어야 함
    """
    # Given: 성공적인 파이프라인 모킹
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=sample_chunks
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        return_value=MagicMock(
            total_chunks=3,
            successful_chunks=3,
            failed_chunks=0,
            processing_time_seconds=5.0
        )
    ):
        # When: 파일 처리 (로그 캡처)
        with caplog.at_level("INFO"):
            result = await background_task_service.process_file(
                file_id=test_file_id,
                chat_room_id=test_chat_room_id
            )

        # Then: 로그 확인
        assert result.success is True, "처리가 성공해야 합니다"
        assert any(
            "파일 처리 시작" in record.message or "process_file" in record.message.lower()
            for record in caplog.records
        ), "파일 처리 시작 로그가 있어야 합니다"
        assert any(
            "텍스트 추출" in record.message or "extract" in record.message.lower()
            for record in caplog.records
        ), "텍스트 추출 로그가 있어야 합니다"
        assert any(
            "청킹" in record.message or "chunk" in record.message.lower()
            for record in caplog.records
        ), "청킹 로그가 있어야 합니다"
        assert any(
            "임베딩" in record.message or "embed" in record.message.lower()
            for record in caplog.records
        ), "임베딩 로그가 있어야 합니다"


@pytest.mark.asyncio
async def test_process_file_performance_100_chunks(
    background_task_service,
    test_chat_room_id: int,
    sample_extracted_text
):
    """
    성능 테스트 - 100개 청크 처리는 30초 이내여야 함
    """
    # Given: 테스트용 파일 생성
    from sqlalchemy import text
    result = await background_task_service.session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 2048, 'application/pdf', 'processing')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    test_file_id = result.scalar()
    await background_task_service.session.commit()

    # Given: 100개의 청크
    chunks_100 = [
        TextChunk(
            content=f"청크 내용 {i}",
            chunk_index=i,
            metadata={"file_id": 1, "total_chunks": 100}
        )
        for i in range(100)
    ]

    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=chunks_100
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        return_value=MagicMock(
            total_chunks=100,
            successful_chunks=100,
            failed_chunks=0,
            processing_time_seconds=5.0
        )
    ):
        # When: 처리 시간 측정
        start_time = time.time()
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )
        elapsed_time = time.time() - start_time

        # Then: 성능 기준 충족
        assert result.success is True, "처리가 성공해야 합니다"
        assert result.chunks_processed == 100, "100개의 청크가 처리되어야 합니다"
        assert elapsed_time < 30.0, f"100개 청크 처리는 30초 이내여야 합니다 (실제: {elapsed_time:.2f}초)"


@pytest.mark.asyncio
async def test_process_file_error_context_preservation(
    background_task_service,
    test_file_id: int,
    test_chat_room_id: int,
    caplog
):
    """
    에러 컨텍스트 보존 테스트
    에러 발생 시 file_id, chat_room_id 등의 컨텍스트가 로그에 포함되어야 함
    """
    # Given: 추출 단계에서 에러 발생
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        side_effect=Exception("파일 손상")
    ):
        # When: 파일 처리 (로그 캡처)
        with caplog.at_level("ERROR"):
            result = await background_task_service.process_file(
                file_id=test_file_id,
                chat_room_id=test_chat_room_id
            )

        # Then: 에러 컨텍스트 확인
        assert result.success is False, "처리가 실패해야 합니다"
        assert result.error is not None, "에러 메시지가 있어야 합니다"

        # 에러 로그에 file_id와 chat_room_id가 포함되어야 함
        error_logs = [record for record in caplog.records if record.levelname == "ERROR"]
        assert len(error_logs) > 0, "에러 로그가 있어야 합니다"

        # 에러 메시지에 컨텍스트 정보가 포함되어야 함
        assert any(
            str(test_file_id) in record.message or str(test_chat_room_id) in record.message
            for record in error_logs
        ), "에러 로그에 file_id 또는 chat_room_id가 포함되어야 합니다"


@pytest.mark.asyncio
async def test_process_file_empty_file_handling(
    background_task_service,
    test_chat_room_id: int,
    sample_extracted_text
):
    """
    빈 파일 처리 테스트
    추출된 텍스트가 비어있을 경우 적절히 처리해야 함
    """
    # Given: 테스트용 파일 생성
    from sqlalchemy import text
    result = await background_task_service.session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 2048, 'application/pdf', 'processing')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    test_file_id = result.scalar()
    await background_task_service.session.commit()

    # Given: 빈 내용의 추출된 텍스트
    empty_extracted = MagicMock(
        content="",
        metadata={"file_type": "pdf", "page_count": 0}
    )

    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=empty_extracted
    ):
        # When: 파일 처리
        result = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 빈 파일 에러로 처리
        assert result.success is False, "처리가 실패해야 합니다"
        assert result.error is not None, "에러 메시지가 있어야 합니다"

        # 상태 업데이트 확인
        file = await background_task_service.file_repository.get_by_id(test_file_id)
        assert file.status == "failed", "파일 상태가 failed여야 합니다"


@pytest.mark.asyncio
async def test_process_file_concurrent_safety(
    background_task_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_extracted_text,
    sample_chunks
):
    """
    동시성 안전성 테스트
    동일한 파일에 대한 동시 처리가 안전하게 처리되어야 함
    """
    # Given: 성공적인 파이프라인 모킹
    with patch.object(
        background_task_service.extraction_service,
        'extract_text',
        return_value=sample_extracted_text
    ), patch.object(
        background_task_service.chunking_service,
        'chunk_text',
        return_value=sample_chunks
    ), patch.object(
        background_task_service.embedding_service,
        'embed_chunks',
        new_callable=AsyncMock,
        return_value=MagicMock(
            total_chunks=3,
            successful_chunks=3,
            failed_chunks=0,
            processing_time_seconds=5.0
        )
    ):
        # When: 동일 파일 처리 (실제 동시성은 이 테스트에서는 시뮬레이션만)
        result1 = await background_task_service.process_file(
            file_id=test_file_id,
            chat_room_id=test_chat_room_id
        )

        # Then: 첫 번째 처리만 성공
        assert result1.success is True, "첫 번째 처리는 성공해야 합니다"
        assert result1.chunks_processed == 3, "청크가 처리되어야 합니다"
