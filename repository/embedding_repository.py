"""
임베딩 리포지토리

RAG 청크의 임베딩 저장, 검색, 삭제 작업을 처리합니다.
pgvector를 사용한 유사도 검색을 지원합니다.
"""
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from models.search_result import SearchResult
from models.text_chunk import TextChunk


class EmbeddingRepository:
    """
    임베딩 리포지토리

    RAG 청크의 임베딩 저장, 유사도 검색, 삭제 기능을 제공합니다.
    pgvector의 코사인 거리 연산자(<=>)를 사용합니다.
    """

    def __init__(self, session: AsyncSession):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 비동기 세션
        """
        self.session = session

    async def store_embeddings(
        self,
        chunks: List[TextChunk],
        embeddings: List[List[float]],
        chat_room_id: int,
        file_id: int
    ) -> None:
        """
        임베딩 벡터 저장

        Args:
            chunks: 텍스트 청크 리스트
            embeddings: 임베딩 벡터 리스트 (768차원)
            chat_room_id: 채팅방 ID
            file_id: 파일 ID

        Raises:
            ValueError: chunks나 embeddings가 비어있을 경우
        """
        if not chunks or not embeddings:
            raise ValueError("chunks와 embeddings는 비어있을 수 없습니다")

        if len(chunks) != len(embeddings):
            raise ValueError("chunks와 embeddings의 길이가 같아야 합니다")

        # 벡터 차원 확인 (768차원)
        for i, embedding in enumerate(embeddings):
            if len(embedding) != 768:
                raise ValueError(f"임베딩 {i}의 차원이 768이어야 합니다 (현재: {len(embedding)})")

        # 배치 삽입
        for chunk, embedding in zip(chunks, embeddings):
            # pgvector는 배열을 '[0.1, 0.2, ...]' 형식의 문자열로 저장
            embedding_str = f"[{','.join(map(str, embedding))}]"

            # CAST를 사용하여 vector 타입으로 변환
            await self.session.execute(
                text("""
                    INSERT INTO rag_chunks
                    (file_id, chat_room_id, chunk_index, content, embedding, token_count)
                    VALUES (:file_id, :chat_room_id, :chunk_index, :content, CAST(:embedding AS vector), :token_count)
                """),
                {
                    "file_id": file_id,
                    "chat_room_id": chat_room_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "embedding": embedding_str,
                    "token_count": len(chunk.content.split())  # 간단한 토큰 수 추정
                }
            )

        await self.session.commit()

    async def search_embeddings(
        self,
        query_embedding: List[float],
        chat_room_id: int,
        limit: int = 5
    ) -> List[SearchResult]:
        """
        유사도 검색

        코사인 거리를 사용하여 가장 유사한 청크를 검색합니다.

        Args:
            query_embedding: 쿼리 임베딩 벡터 (768차원)
            chat_room_id: 검색할 채팅방 ID (격리를 위해 사용)
            limit: 반환할 최대 결과 수

        Returns:
            검색 결과 리스트 (내림차순 정렬)
        """
        if len(query_embedding) != 768:
            raise ValueError(f"쿼리 임베딩 차원이 768이어야 합니다 (현재: {len(query_embedding)})")

        # pgvector 코사인 거리 연산자: <=> (거리가 작을수록 유사함)
        # 코사인 유사도 = 1 - 코사인 거리
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        query = text("""
            SELECT
                content,
                1 - (embedding <=> CAST(:query_embedding AS vector)) as score,
                chunk_index,
                file_id
            FROM rag_chunks
            WHERE chat_room_id = :chat_room_id
            ORDER BY embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        result = await self.session.execute(
            query,
            {
                "query_embedding": embedding_str,
                "chat_room_id": chat_room_id,
                "limit": limit
            }
        )

        rows = result.fetchall()
        results = []

        for row in rows:
            # 파일 메타데이터 조회
            file_result = await self.session.execute(
                text("SELECT filename FROM rag_files WHERE id = :file_id"),
                {"file_id": row.file_id}
            )
            filename = file_result.scalar()

            results.append(SearchResult(
                content=row.content,
                score=float(row.score),
                metadata={
                    "chunk_index": row.chunk_index,
                    "file_id": row.file_id,
                    "file_name": filename or "unknown"
                }
            ))

        return results

    async def delete_embeddings(self, file_id: int) -> None:
        """
        파일 ID로 임베딩 삭제

        Args:
            file_id: 파일 ID
        """
        await self.session.execute(
            text("DELETE FROM rag_chunks WHERE file_id = :file_id"),
            {"file_id": file_id}
        )
        await self.session.commit()

    async def delete_by_chat_room(self, chat_room_id: int) -> None:
        """
        채팅방 ID로 임베딩 삭제

        Args:
            chat_room_id: 채팅방 ID
        """
        await self.session.execute(
            text("DELETE FROM rag_chunks WHERE chat_room_id = :chat_room_id"),
            {"chat_room_id": chat_room_id}
        )
        await self.session.commit()
