"""
RAG 기능을 위한 데이터베이스 마이그레이션

이 마이그레이션은 다음을 수행합니다:
1. pgvector 확장 활성화 확인
2. rag_files 테이블 생성 (업로드된 파일 메타데이터 관리)
3. rag_chunks 테이블 생성 (텍스트 청크와 임베딩 저장)
4. 필요한 인덱스 생성
5. 외래 키 제약조건 생성

생성일: 2025-01-10
버전: 001
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session


async def upgrade():
    """
    RAG 테이블과 인덱스 생성

    Returns:
        None
    """
    async with get_async_session() as session:
        # 1. pgvector 확장 활성화
        await session.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )

        # 2. rag_files 테이블 생성
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS rag_files (
                id SERIAL PRIMARY KEY,
                chat_room_id INTEGER NOT NULL,
                filename VARCHAR(255) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_size BIGINT NOT NULL,
                content_type VARCHAR(100),
                status VARCHAR(50) DEFAULT 'processing',
                error_message TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 3. rag_chunks 테이블 생성 (벡터 컬럼 포함)
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id SERIAL PRIMARY KEY,
                file_id INTEGER NOT NULL REFERENCES rag_files(id) ON DELETE CASCADE,
                chat_room_id INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                token_count INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """))

        # 4. 인덱스 생성
        # rag_files 인덱스
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_files_chat_room_id
            ON rag_files(chat_room_id)
        """))

        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_files_status
            ON rag_files(status)
        """))

        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_files_created_at
            ON rag_files(created_at DESC)
        """))

        # rag_chunks 인덱스
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_file_id
            ON rag_chunks(file_id)
        """))

        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_chat_room_id
            ON rag_chunks(chat_room_id)
        """))

        # 5. 벡터 유사도 검색을 위한 HNSW 인덱스 생성
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding
            ON rag_chunks USING hnsw (embedding vector_cosine_ops)
        """))

        # 6. 복합 인덱스 생성 (chat_room_id + chunk_index)
        await session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rag_chunks_chat_room_chunk
            ON rag_chunks(chat_room_id, chunk_index)
        """))

        await session.commit()
        print("마이그레이션 완료: RAG 테이블과 인덱스가 생성되었습니다.")


async def downgrade():
    """
    RAG 테이블과 인덱스 삭제 (롤백)

    Returns:
        None
    """
    async with get_async_session() as session:
        # 인덱스 먼저 삭제
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_chunks_chat_room_chunk"))
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_chunks_embedding"))
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_chunks_chat_room_id"))
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_chunks_file_id"))
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_files_created_at"))
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_files_status"))
        await session.execute(text("DROP INDEX IF EXISTS idx_rag_files_chat_room_id"))

        # 테이블 삭제 (외래 키 순서 고려)
        await session.execute(text("DROP TABLE IF EXISTS rag_chunks"))
        await session.execute(text("DROP TABLE IF EXISTS rag_files"))

        await session.commit()
        print("롤백 완료: RAG 테이블과 인덱스가 삭제되었습니다.")


if __name__ == "__main__":
    import asyncio

    async def main():
        print("RAG 마이그레이션 시작...")
        await upgrade()
        print("RAG 마이그레이션 완료!")

    asyncio.run(main())
