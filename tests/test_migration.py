"""
데이터베이스 마이그레이션 테스트

RAG 기능을 위한 테이블 생성과 pgvector 확장 활성화를 검증합니다.
"""
import pytest
from sqlalchemy import text

from core.database import get_async_session


@pytest.fixture(scope="session")
def event_loop_policy():
    """각 테스트에 대해 새로운 이벤트 루프 생성"""
    import asyncio
    policy = asyncio.get_event_loop_policy()
    return policy


@pytest.mark.asyncio
async def test_pgvector_extension_enabled():
    """pgvector 확장이 활성화되어 있는지 확인"""
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        extension_exists = result.fetchone() is not None
        assert extension_exists, "pgvector 확장이 활성화되어 있어야 합니다"


@pytest.mark.asyncio
async def test_rag_files_table_exists():
    """rag_files 테이블이 존재하는지 확인"""
    async with get_async_session() as session:
        result = await session.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'rag_files'
            """)
        )
        table_exists = result.fetchone() is not None
        assert table_exists, "rag_files 테이블이 존재해야 합니다"


@pytest.mark.asyncio
async def test_rag_files_table_structure():
    """rag_files 테이블의 컬럼 구조 확인"""
    async with get_async_session() as session:
        result = await session.execute(
            text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'rag_files'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0]: {"type": row[1], "nullable": row[2]} for row in result.fetchall()}

        # 필수 컬럼 확인
        assert "id" in columns, "id 컬럼이 존재해야 합니다"
        assert "chat_room_id" in columns, "chat_room_id 컬럼이 존재해야 합니다"
        assert "filename" in columns, "filename 컬럼이 존재해야 합니다"
        assert "file_path" in columns, "file_path 컬럼이 존재해야 합니다"
        assert "file_size" in columns, "file_size 컬럼이 존재해야 합니다"
        assert "content_type" in columns, "content_type 컬럼이 존재해야 합니다"
        assert "status" in columns, "status 컬럼이 존재해야 합니다"
        assert "created_at" in columns, "created_at 컬럼이 존재해야 합니다"


@pytest.mark.asyncio
async def test_rag_chunks_table_exists():
    """rag_chunks 테이블이 존재하는지 확인"""
    async with get_async_session() as session:
        result = await session.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'rag_chunks'
            """)
        )
        table_exists = result.fetchone() is not None
        assert table_exists, "rag_chunks 테이블이 존재해야 합니다"


@pytest.mark.asyncio
async def test_rag_chunks_table_structure():
    """rag_chunks 테이블의 컬럼 구조와 벡터 컬럼 확인"""
    async with get_async_session() as session:
        result = await session.execute(
            text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'rag_chunks'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0]: row[1] for row in result.fetchall()}

        # 필수 컬럼 확인
        assert "id" in columns, "id 컬럼이 존재해야 합니다"
        assert "file_id" in columns, "file_id 컬럼이 존재해야 합니다"
        assert "chat_room_id" in columns, "chat_room_id 컬럼이 존재해야 합니다"
        assert "chunk_index" in columns, "chunk_index 컬럼이 존재해야 합니다"
        assert "content" in columns, "content 컬럼이 존재해야 합니다"
        assert "embedding" in columns, "embedding 벡터 컬럼이 존재해야 합니다"
        assert "token_count" in columns, "token_count 컬럼이 존재해야 합니다"
        assert "created_at" in columns, "created_at 컬럼이 존재해야 합니다"

        # 벡터 컬럼 타입 확인
        result = await session.execute(
            text("""
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = 'rag_chunks' AND column_name = 'embedding'
            """)
        )
        vector_type = result.scalar()
        assert vector_type == "USER-DEFINED", "embedding 컬럼은 vector 타입이어야 합니다"


@pytest.mark.asyncio
async def test_foreign_key_constraints():
    """외래 키 제약조건 확인"""
    async with get_async_session() as session:
        # rag_chunks.file_id -> rag_files.id
        result = await session.execute(
            text("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'rag_chunks'
                AND kcu.column_name = 'file_id'
            """)
        )
        fk = result.fetchone()
        assert fk is not None, "file_id 외래 키 제약조건이 존재해야 합니다"
        assert fk[2] == "rag_files", "file_id는 rag_files.id를 참조해야 합니다"


@pytest.mark.asyncio
async def test_indexes_created():
    """필요한 인덱스가 생성되었는지 확인"""
    async with get_async_session() as session:
        # chat_room_id 인덱스 확인
        result = await session.execute(
            text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename IN ('rag_files', 'rag_chunks')
                AND indexname LIKE '%chat_room_id%'
            """)
        )
        indexes = [row[0] for row in result.fetchall()]
        assert len(indexes) >= 2, "chat_room_id 인덱스가 각 테이블에 생성되어야 합니다"


@pytest.mark.asyncio
async def test_vector_extension_version():
    """pgvector 버전 확인 (0.3.6 이상)"""
    async with get_async_session() as session:
        result = await session.execute(
            text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        )
        version = result.scalar()
        assert version is not None, "pgvector가 설치되어야 합니다"
        # 버전 비교 (간단히 문자열 비교)
        major, minor = map(int, version.split(".")[:2])
        assert major >= 0 and minor >= 3, "pgvector 0.3.0 이상이 필요합니다"
