"""
EmbeddingRepository TDD 테스트

RAG 청크의 임베딩 저장, 검색, 삭제 기능을 검증합니다.
pgvector를 사용한 유사도 검색과 채팅방 격리를 테스트합니다.
"""
import time
import uuid
from typing import List

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from models.search_result import SearchResult
from models.text_chunk import TextChunk
from repository.embedding_repository import EmbeddingRepository


@pytest.fixture
async def db_session() -> AsyncSession:
    """테스트를 위한 비동기 DB 세션"""
    async with get_async_session() as session:
        yield session
        # 테스트 후 정리
        await session.rollback()


@pytest.fixture
async def embedding_repo(db_session: AsyncSession) -> EmbeddingRepository:
    """EmbeddingRepository fixture"""
    return EmbeddingRepository(db_session)


@pytest.fixture
async def test_chat_room_id(db_session: AsyncSession) -> int:
    """테스트용 채팅방 ID 생성 (정수 ID 사용)"""
    # RAG 테이블은 정수 타입의 chat_room_id를 사용하므로,
    # 별도의 ID 생성 없이 직접 정수 ID 사용
    return 12345


@pytest.fixture
async def test_file_id(db_session: AsyncSession, test_chat_room_id: int) -> int:
    """테스트용 파일 ID 생성"""
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
def sample_embeddings() -> List[List[float]]:
    """샘플 임베딩 벡터 (768차원)"""
    # 실제 임베딩이 아니라 테스트용 더미 벡터
    return [[0.1] * 768 for _ in range(3)]


@pytest.mark.asyncio
async def test_store_embeddings_success(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """임베딩 저장 성공 테스트"""
    # When: 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 데이터베이스에 저장됨
    result = await embedding_repo.session.execute(
        text("SELECT COUNT(*) FROM rag_chunks WHERE file_id = :file_id"),
        {"file_id": test_file_id}
    )
    count = result.scalar()
    assert count == 3, "3개의 청크가 저장되어야 합니다"


@pytest.mark.asyncio
async def test_store_empty_embeddings_raises_error(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int
):
    """빈 임베딩 저장 시 에러 발생 테스트"""
    # When & Then: 빈 청크로 저장 시도하면 ValueError 발생
    with pytest.raises(ValueError, match="chunks와 embeddings는 비어있을 수 없습니다"):
        await embedding_repo.store_embeddings(
            chunks=[],
            embeddings=[],
            chat_room_id=test_chat_room_id,
            file_id=test_file_id
        )


@pytest.mark.asyncio
async def test_search_embeddings_by_similarity(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """유사도 검색 테스트"""
    # Given: 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # When: 유사한 쿼리로 검색
    query_embedding = [0.1] * 768  # 첫 번째 청크와 유사한 쿼리
    results = await embedding_repo.search_embeddings(
        query_embedding=query_embedding,
        chat_room_id=test_chat_room_id,
        limit=5
    )

    # Then: 검색 결과 반환
    assert len(results) > 0, "검색 결과가 있어야 합니다"
    assert isinstance(results[0], SearchResult), "결과는 SearchResult 타입이어야 합니다"
    assert results[0].content is not None, "콘텐츠가 있어야 합니다"
    assert results[0].score is not None, "유사도 점수가 있어야 합니다"


@pytest.mark.asyncio
async def test_search_embeddings_chat_room_isolation(
    embedding_repo: EmbeddingRepository,
    db_session: AsyncSession,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """채팅방 격리 테스트 - 다른 채팅방의 청크는 검색되지 않아야 함"""
    # Given: 첫 번째 채팅방에 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Given: 두 번째 채팅방의 파일 생성 및 임베딩 저장
    other_chat_room_id = 67890
    result = await db_session.execute(
        text("""
            INSERT INTO rag_files (chat_room_id, filename, file_path, file_size, content_type, status)
            VALUES (:chat_room_id, 'other.pdf', '/tmp/other.pdf', 2048, 'application/pdf', 'completed')
            RETURNING id
        """),
        {"chat_room_id": other_chat_room_id}
    )
    other_file_id = result.scalar()
    await db_session.commit()

    other_chunks = [
        TextChunk(
            content="다른 채팅방의 청크",
            chunk_index=0,
            metadata={"file_name": "other.pdf"}
        )
    ]
    other_embeddings = [[0.2] * 768]
    await embedding_repo.store_embeddings(
        chunks=other_chunks,
        embeddings=other_embeddings,
        chat_room_id=other_chat_room_id,
        file_id=other_file_id
    )

    # When: 첫 번째 채팅방에서 검색
    query_embedding = [0.1] * 768
    results = await embedding_repo.search_embeddings(
        query_embedding=query_embedding,
        chat_room_id=test_chat_room_id,
        limit=10
    )

    # Then: 첫 번째 채팅방의 결과만 반환
    assert len(results) == 3, "첫 번째 채팅방의 3개 청크만 검색되어야 합니다"


@pytest.mark.asyncio
async def test_search_embeddings_top_k_results(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """Top-K 결과 제한 테스트"""
    # Given: 10개의 청크 저장
    many_chunks = [
        TextChunk(
            content=f"청크 내용 {i}",
            chunk_index=i,
            metadata={"page": 1, "file_name": "test.pdf"}
        )
        for i in range(10)
    ]
    many_embeddings = [[0.1] * 768 for _ in range(10)]

    await embedding_repo.store_embeddings(
        chunks=many_chunks,
        embeddings=many_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # When: limit=5로 검색
    query_embedding = [0.1] * 768
    results = await embedding_repo.search_embeddings(
        query_embedding=query_embedding,
        chat_room_id=test_chat_room_id,
        limit=5
    )

    # Then: 최대 5개 결과만 반환
    assert len(results) <= 5, "최대 5개의 결과만 반환되어야 합니다"


@pytest.mark.asyncio
async def test_delete_embeddings_by_file_id(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """파일 ID로 임베딩 삭제 테스트"""
    # Given: 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # When: 파일 ID로 삭제
    await embedding_repo.delete_embeddings(file_id=test_file_id)

    # Then: 데이터베이스에서 삭제됨
    result = await embedding_repo.session.execute(
        text("SELECT COUNT(*) FROM rag_chunks WHERE file_id = :file_id"),
        {"file_id": test_file_id}
    )
    count = result.scalar()
    assert count == 0, "모든 청크가 삭제되어야 합니다"


@pytest.mark.asyncio
async def test_delete_embeddings_cascade_by_chat_room(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """채팅방 ID로 임베딩 삭제 테스트 (delete_by_chat_room 메서드)"""
    # Given: 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # When: 채팅방 ID로 삭제
    await embedding_repo.delete_by_chat_room(chat_room_id=test_chat_room_id)

    # Then: 모든 청크 삭제됨
    result = await embedding_repo.session.execute(
        text("""
            SELECT COUNT(*) FROM rag_chunks
            WHERE chat_room_id = :chat_room_id
        """),
        {"chat_room_id": test_chat_room_id}
    )
    count = result.scalar()
    assert count == 0, "채팅방 ID로 청크가 삭제되어야 합니다"


@pytest.mark.asyncio
async def test_search_returns_relevance_scores(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """검색 결과가 유사도 점수를 포함하는지 테스트"""
    # Given: 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # When: 검색
    query_embedding = [0.1] * 768
    results = await embedding_repo.search_embeddings(
        query_embedding=query_embedding,
        chat_room_id=test_chat_room_id,
        limit=5
    )

    # Then: 모든 결과에 score가 있음
    for result in results:
        assert result.score is not None, "모든 결과에 유사도 점수가 있어야 합니다"
        assert 0 <= result.score <= 1, "점수는 0에서 1 사이여야 합니다 (코사인 유사도)"


@pytest.mark.asyncio
async def test_search_performance_top_5_under_500ms(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int,
    sample_chunks: List[TextChunk],
    sample_embeddings: List[List[float]]
):
    """검색 성능 테스트 - Top-5는 500ms 이내여야 함"""
    # Given: 임베딩 저장
    await embedding_repo.store_embeddings(
        chunks=sample_chunks,
        embeddings=sample_embeddings,
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # When: 검색 시간 측정
    query_embedding = [0.1] * 768
    start_time = time.time()
    results = await embedding_repo.search_embeddings(
        query_embedding=query_embedding,
        chat_room_id=test_chat_room_id,
        limit=5
    )
    elapsed_time = (time.time() - start_time) * 1000  # 밀리초 변환

    # Then: 500ms 이내여야 함
    assert elapsed_time < 500, f"검색은 500ms 이내여야 합니다 (실제: {elapsed_time:.2f}ms)"
    assert len(results) <= 5, "최대 5개 결과"


@pytest.mark.asyncio
async def test_vector_dimensions_match_768(
    embedding_repo: EmbeddingRepository,
    test_file_id: int,
    test_chat_room_id: int
):
    """벡터 차원이 768인지 확인하는 테스트"""
    # Given: 768차원 임베딩
    chunk = TextChunk(
        content="테스트 청크",
        chunk_index=0,
        metadata={"page": 1}
    )
    embedding = [0.1] * 768

    # When: 저장
    await embedding_repo.store_embeddings(
        chunks=[chunk],
        embeddings=[embedding],
        chat_room_id=test_chat_room_id,
        file_id=test_file_id
    )

    # Then: 벡터 차원 확인
    result = await embedding_repo.session.execute(
        text("""
            SELECT array_length(embedding, 1) as dim
            FROM rag_chunks
            LIMIT 1
        """)
    )
    dimension = result.scalar()
    assert dimension == 768, f"벡터 차원은 768이어야 합니다 (실제: {dimension})"


@pytest.mark.asyncio
async def test_concurrent_embedding_operations(
    test_file_id: int,
    test_chat_room_id: int
):
    """동시 임베딩 작업 테스트 - 순차 실행으로 변경 (SQLAlchemy 세션는 동시 작업을 지원하지 않음)"""
    import asyncio

    # Given: 여러 개의 청크 세트
    async def store_chunk_set(index: int):
        # 각 작업에 별도의 세션 사용
        async with get_async_session() as session:
            repo = EmbeddingRepository(session)
            chunks = [
                TextChunk(
                    content=f"세트 {index} - 청크 {j}",
                    chunk_index=j,
                    metadata={"set": index}
                )
                for j in range(3)
            ]
            embeddings = [[0.1] * 768 for _ in range(3)]
            await repo.store_embeddings(
                chunks=chunks,
                embeddings=embeddings,
                chat_room_id=test_chat_room_id,
                file_id=test_file_id
            )

    # When: 동시에 3개 세트 저장 (각 세션은 독립적)
    await asyncio.gather(
        store_chunk_set(1),
        store_chunk_set(2),
        store_chunk_set(3)
    )

    # Then: 모든 청크가 저장됨
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM rag_chunks WHERE file_id = :file_id"),
            {"file_id": test_file_id}
        )
        count = result.scalar()
        assert count == 9, "9개의 청크가 모두 저장되어야 합니다 (3세트 × 3청크)"
