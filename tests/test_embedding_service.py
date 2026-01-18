"""
EmbeddingService TDD 테스트

텍스트 청크의 임베딩 생성, 배치 처리, API 재시도, 비용 모니터링 기능을 검증합니다.
Gemini Embeddings API를 사용한 벡터 생성과 pgvector 저장을 테스트합니다.
"""
import time
from typing import TYPE_CHECKING, List
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from models.text_chunk import TextChunk

if TYPE_CHECKING:
    pass


@pytest.fixture
async def db_session() -> AsyncSession:
    """테스트를 위한 비동기 DB 세션"""
    async with get_async_session() as session:
        yield session
        # 테스트 후 정리
        await session.rollback()


@pytest.fixture
def embedding_service(db_session: AsyncSession):
    """EmbeddingService fixture"""
    from services.embedding_service import EmbeddingService
    return EmbeddingService(db_session)


@pytest.fixture
def sample_chunks() -> List[TextChunk]:
    """샘플 텍스트 청크"""
    return [
        TextChunk(
            content="머신러닝은 인공지능의 한 분야입니다.",
            chunk_index=0,
            metadata={"page": 1, "file_name": "test.pdf"}
        ),
        TextChunk(
            content="딥러닝은 신경망을 기반으로 합니다.",
            chunk_index=1,
            metadata={"page": 1, "file_name": "test.pdf"}
        ),
        TextChunk(
            content="자연어 처리는 텍스트 데이터를 다룹니다.",
            chunk_index=2,
            metadata={"page": 2, "file_name": "test.pdf"}
        ),
    ]


@pytest.fixture
async def test_chat_room_id(db_session: AsyncSession) -> int:
    """테스트용 채팅방 ID 생성"""
    return 12345


@pytest.fixture
async def test_file_id(db_session: AsyncSession, test_chat_room_id: int) -> int:
    """테스트용 파일 ID 생성"""
    from sqlalchemy import text

    result = await db_session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'test.pdf', '/tmp/test.pdf', 1024, 'application/pdf', 'completed')
            RETURNING id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    file_id = result.scalar()
    await db_session.commit()
    return file_id


# ============================================================================
# RED Phase Tests
# ============================================================================

@pytest.mark.asyncio
async def test_embed_chunks_basic_success(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk]
):
    """기본 임베딩 생성 성공 테스트"""
    # When: 청크 임베딩 생성
    result = await embedding_service.embed_chunks(
        chunks=sample_chunks,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 결과 검증
    assert result is not None, "결과가 None이 아니어야 합니다"
    assert result.total_chunks == 3, "3개의 청크가 처리되어야 합니다"
    assert result.successful_chunks == 3, "모든 청크가 성공적으로 임베딩되어야 합니다"
    assert result.failed_chunks == 0, "실패한 청크가 없어야 합니다"
    assert result.embedding_dimension == 768, "임베딩 차원은 768이어야 합니다"


@pytest.mark.asyncio
async def test_embed_chunks_batch_processing(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int
):
    """배치 처리 테스트 - 150개 청크 (2개 배치)"""
    # Given: 150개의 청크 생성
    many_chunks = [
        TextChunk(
            content=f"청크 내용 {i}",
            chunk_index=i,
            metadata={"page": 1, "file_name": "test.pdf"}
        )
        for i in range(150)
    ]

    # When: 배치 처리
    result = await embedding_service.embed_chunks(
        chunks=many_chunks,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 배치 처리 검증
    assert result.total_chunks == 150, "150개의 청크가 처리되어야 합니다"
    assert result.successful_chunks == 150, "모든 청크가 성공적으로 임베딩되어야 합니다"
    assert result.batch_count > 1, "2개 이상의 배치가 사용되어야 합니다"


@pytest.mark.asyncio
async def test_embed_chunks_api_retry_on_failure(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk]
):
    """API 실패 시 재시도 테스트"""
    # Given: API가 처음에 실패했다가 성공하는 시나리오
    call_count = 0

    async def mock_embed(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("API 일시적 오류")
        # 성공 시 더미 임베딩 반환
        return [[0.1] * 768 for _ in range(len(sample_chunks))]

    # When: API 호출 (재시도 포함)
    with patch.object(embedding_service, '_batch_embed', side_effect=mock_embed):
        result = await embedding_service.embed_chunks(
            chunks=sample_chunks,
            chat_room_id=test_chat_room_id,
            file_id=test_file_id
        )

    # Then: 재시도 후 성공
    assert call_count > 1, "API가 재시도되어야 합니다"
    assert result.successful_chunks == 3, "모든 청크가 성공적으로 임베딩되어야 합니다"


@pytest.mark.asyncio
async def test_embed_chunks_cost_monitoring(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    caplog
):
    """비용 모니터링 로깅 테스트"""
    # When: 임베딩 생성 (로그 캡처)
    with caplog.at_level("INFO"):
        result = await embedding_service.embed_chunks(
            chunks=sample_chunks,
            chat_room_id=test_chat_room_id,
            file_id=test_file_id
        )

    # Then: 비용 로그 확인
    assert result.total_chunks == 3, "3개의 청크가 처리되어야 합니다"
    assert any("임베딩 비용" in record.message or "chunk" in record.message.lower()
               for record in caplog.records), "비용 관련 로그가 있어야 합니다"


@pytest.mark.asyncio
async def test_embed_chunks_performance_100_chunks(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int
):
    """성능 테스트 - 100개 청크는 20초 이내여야 함"""
    # Given: 100개의 청크
    chunks_100 = [
        TextChunk(
            content=f"청크 내용 {i}",
            chunk_index=i,
            metadata={"page": 1, "file_name": "test.pdf"}
        )
        for i in range(100)
    ]

    # When: 처리 시간 측정
    start_time = time.time()
    result = await embedding_service.embed_chunks(
        chunks=chunks_100,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )
    elapsed_time = time.time() - start_time

    # Then: 성능 기준 충족
    assert result.total_chunks == 100, "100개의 청크가 처리되어야 합니다"
    assert result.successful_chunks == 100, "모든 청크가 성공적으로 처리되어야 합니다"
    assert elapsed_time < 20.0, f"100개 청크 처리는 20초 이내여야 합니다 (실제: {elapsed_time:.2f}초)"


@pytest.mark.asyncio
async def test_embed_chunks_empty_raises_error(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int
):
    """빈 청크 리스트 에러 테스트"""
    # When & Then: 빈 청크로 시도하면 ValueError 발생
    with pytest.raises(ValueError, match="chunks는 비어있을 수 없습니다"):
        await embedding_service.embed_chunks(
            chunks=[],
            chat_room_id=test_chat_room_id,
            file_id=test_file_id
        )


@pytest.mark.asyncio
async def test_embed_chunks_vector_dimension_768(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk]
):
    """임베딩 벡터 차원이 768인지 확인"""
    # When: 임베딩 생성
    result = await embedding_service.embed_chunks(
        chunks=sample_chunks,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 차원 검증
    assert result.embedding_dimension == 768, "임베딩 차원은 768이어야 합니다"

    # 데이터베이스에서도 확인 (pgvector는 array_length를 지원하지 않으므로 다른 방식 사용)
    from sqlalchemy import text
    db_result = await embedding_service.session.execute(
        text("""
            SELECT embedding FROM rag_chunks
            WHERE file_id = :file_id
            LIMIT 1
        """),
        {"file_id": test_file_id}
    )
    embedding = db_result.scalar()
    assert embedding is not None, "임베딩이 저장되어야 합니다"

    # pgvector는 list로 변환되어 반환됨
    import numpy as np
    embedding_array = np.array(embedding)
    assert len(embedding_array) == 768, f"DB에 저장된 벡터 차원은 768이어야 합니다 (실제: {len(embedding_array)})"


@pytest.mark.asyncio
async def test_embed_chunks_respects_max_batch_size(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int
):
    """최대 배치 사이즈 존중 테스트"""
    # Given: 250개의 청크 (3개 배치 필요: 100 + 100 + 50)
    many_chunks = [
        TextChunk(
            content=f"청크 내용 {i}",
            chunk_index=i,
            metadata={"page": 1, "file_name": "test.pdf"}
        )
        for i in range(250)
    ]

    # When: 배치 처리
    result = await embedding_service.embed_chunks(
        chunks=many_chunks,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 배치 수 검증
    assert result.total_chunks == 250, "250개의 청크가 처리되어야 합니다"
    assert result.batch_count == 3, "3개의 배치가 사용되어야 합니다 (100 + 100 + 50)"
    assert result.successful_chunks == 250, "모든 청크가 성공적으로 처리되어야 합니다"


@pytest.mark.asyncio
async def test_embed_chunks_exponential_backoff_retry(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk]
):
    """지수 백오프 재시도 테스트"""
    # Given: API가 2번 실패 후 3번째에 성공
    call_count = 0
    call_times = []

    async def mock_embed_with_delay(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        call_times.append(time.time())

        if call_count < 3:
            raise Exception("API 일시적 오류")

        # 성공 시 더미 임베딩 반환
        return [[0.1] * 768 for _ in range(len(sample_chunks))]

    # When: 지수 백오프로 재시도
    with patch.object(embedding_service, '_batch_embed', side_effect=mock_embed_with_delay):
        result = await embedding_service.embed_chunks(
            chunks=sample_chunks,
            chat_room_id=test_chat_room_id,
            file_id=test_file_id
        )

    # Then: 재시도 간격 증가 확인
    assert call_count == 3, "3번의 시도가 있어야 합니다 (2번 실패 + 1번 성공)"
    if len(call_times) >= 3:
        # 첫 번째와 두 번째 사이의 간격 < 두 번째와 세 번째 사이의 간격
        first_interval = call_times[1] - call_times[0]
        second_interval = call_times[2] - call_times[1]
        assert second_interval > first_interval, "지수 백오프: 간격이 증가해야 합니다"

    assert result.successful_chunks == 3, "모든 청크가 성공적으로 임베딩되어야 합니다"


@pytest.mark.asyncio
async def test_embed_chunks_partial_failure_handling(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk]
):
    """부분적 실패 처리 테스트 - 일부 청크만 실패"""
    # Given: 첫 번째 배치 성공, 두 번째 배치 실패
    batch_count = 0

    async def mock_embed_partial_failure(chunks):
        nonlocal batch_count
        batch_count += 1
        if batch_count == 1:
            # 첫 번째 배치 성공
            return [[0.1] * 768 for _ in chunks]
        else:
            # 두 번째 배치 실패
            raise Exception("API 배치 실패")

    # When: 부분적 실패 시나리오
    with patch.object(embedding_service, '_batch_embed', side_effect=mock_embed_partial_failure):
        with pytest.raises(Exception, match="API 배치 실패"):
            await embedding_service.embed_chunks(
                chunks=sample_chunks,
                chat_room_id=test_chat_room_id,
                file_id=test_file_id
            )


@pytest.mark.asyncio
async def test_embed_chunks_concurrent_batches(
    embedding_service,
    test_file_id: int,
    test_chat_room_id: int
):
    """동시 배치 처리 테스트 - 배치 간 독립성 확인"""
    # Given: 200개의 청크 (2개 배치)
    many_chunks = [
        TextChunk(
            content=f"청크 내용 {i}",
            chunk_index=i,
            metadata={"page": 1, "file_name": "test.pdf"}
        )
        for i in range(200)
    ]

    # When: 배치 처리
    result = await embedding_service.embed_chunks(
        chunks=many_chunks,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 모든 청크가 순차적으로 처리됨
    assert result.total_chunks == 200, "200개의 청크가 처리되어야 합니다"
    assert result.successful_chunks == 200, "모든 청크가 성공적으로 처리되어야 합니다"

    # 데이터베이스에서 모든 청크 확인
    from sqlalchemy import text
    db_result = await embedding_service.session.execute(
        text("SELECT COUNT(*) FROM rag_chunks WHERE file_id = :file_id"),
        {"file_id": test_file_id}
    )
    count = db_result.scalar()
    assert count == 200, "데이터베이스에 200개의 청크가 저장되어야 합니다"
