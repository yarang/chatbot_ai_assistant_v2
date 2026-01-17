"""
RAG 검색 서비스

업로드된 파일의 텍스트 청크에서 관련 내용을 검색합니다.
sentence-transformers 임베딩(768차원)과 pgvector를 사용합니다.
"""

import asyncio
import json
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from core.cache import generate_cache_key, rag_result_cache
from core.database import get_async_session
from models.chat_room_model import ChatRoom
from models.text_chunk import TextChunk

logger = logging.getLogger(__name__)


class RAGSearchService:
    """
    RAG 검색 서비스

    업로드된 파일의 텍스트 청크에서 사용자 질문과 관련된 내용을 검색합니다.
    pgvector의 코사인 유사도(<=>)를 사용하여 가장 유사한 청크를 찾습니다.
    """

    def __init__(self):
        # 임베딩 모델은 나중에 지연 로딩
        self.embedding_model = None
        logger.info("RAGSearchService 초기화 완료")

    async def search(
        self,
        query: str,
        chat_room_id: str,
        limit: int = 5,
        threshold: float = 0.5,
    ) -> List[dict]:
        """
        질문과 관련된 텍스트 청크 검색

        Args:
            query: 사용자 질문
            chat_room_id: 채팅방 ID (UUID string)
            limit: 반환할 최대 청크 수 (기본값: 5)
            threshold: 유사도 임계값 (0-1, 기본값: 0.5)

        Returns:
            List[dict]: 검색된 청크 리스트
                [
                    {
                        "chunk_id": "uuid",
                        "content": "청크 내용",
                        "file_id": 123,
                        "filename": "document.pdf",
                        "similarity": 0.85
                    },
                    ...
                ]
        """
        logger.info(
            f"RAG 검색 시작: chat_room_id={chat_room_id}, query='{query[:50]}...'"
        )

        # 0. 캐시 확인
        cache_key = generate_cache_key("rag", chat_room_id, query, limit, threshold)
        cached_result = await rag_result_cache.get(cache_key)
        if cached_result is not None:
            logger.info(f"RAG 검색 캐시 적중: chat_room_id={chat_room_id}")
            return cached_result

        # 1. Validate chat_room_id is a valid UUID
        try:
            actual_chat_room_id = UUID(chat_room_id)
        except ValueError:
            logger.warning(f"잘못된 채팅방 ID 형식: chat_room_id={chat_room_id}")
            raise ValueError(
                f"잘못된 채팅방 ID 형식입니다: chat_room_id={chat_room_id}"
            )

        # 2. 질문 임베딩 생성 (캐싱 포함)
        try:
            query_embedding = await self._embed_query(query)
            logger.debug(f"질문 임베딩 생성 완료: 차원={len(query_embedding)}")
        except Exception as e:
            logger.error(f"질문 임베딩 생성 실패: {e}")
            raise RuntimeError(f"질문 임베딩 생성 실패: {str(e)}") from e

        # 3. pgvector로 유사한 청크 검색
        async with get_async_session() as session:
            try:
                chunks = await self._search_similar_chunks(
                    session=session,
                    chat_room_id=actual_chat_room_id,
                    query_embedding=query_embedding,
                    limit=limit,
                    threshold=threshold,
                )

                # 결과 캐싱
                await rag_result_cache.set(cache_key, chunks)

                logger.info(
                    f"RAG 검색 완료: chat_room_id={chat_room_id}, "
                    f"검색된 청크 수={len(chunks)}"
                )
                return chunks

            except Exception as e:
                logger.error(f"RAG 검색 실패: {e}", exc_info=True)
                raise RuntimeError(f"RAG 검색 실패: {str(e)}") from e

    async def _embed_query(self, query: str) -> List[float]:
        """
        질문 텍스트를 임베딩으로 변환

        Args:
            query: 질문 텍스트

        Returns:
            List[float]: 768차원 임베딩 벡터

        Raises:
            Exception: 임베딩 생성 실패 시
        """
        # 싱글톤 모델 관리자에서 임베딩 모델 가져오기
        from core.embedding_model_manager import get_embedding_model

        if self.embedding_model is None:
            self.embedding_model = await get_embedding_model()

        # 임베딩 생성
        embeddings = self.embedding_model.encode(
            [query], convert_to_numpy=True, normalize_embeddings=True
        )
        return embeddings[0].tolist()

    async def _search_similar_chunks(
        self,
        session: AsyncSession,
        chat_room_id: UUID,
        query_embedding: List[float],
        limit: int,
        threshold: float,
    ) -> List[dict]:
        """
        pgvector를 사용하여 유사한 청크 검색

        코사인 유사도(<=> 연산자)를 사용하여 쿼리 임베딩과 가장 유사한 청크를 찾습니다.

        Args:
            session: DB 세션
            chat_room_id: 채팅방 ID (UUID)
            query_embedding: 쿼리 임베딩 벡터
            limit: 반환할 최대 청크 수
            threshold: 유사도 임계값 (0-1, 낮을수록 유사)

        Returns:
            List[dict]: 검색된 청크 리스트
        """
        # pgvector 쿼리: 코사인 거리(<=>) 사용
        # 거리는 0-2 범위 (0=완전 일치, 2=완전 반대)
        # 유사도 = 1 - (거리 / 2)

        # 임베딩 벡터를 배열 문자열로 변환
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        sql_query = text("""
            SELECT
                rc.id as chunk_id,
                rc.content,
                rc.file_id,
                f.filename,
                1 - (rc.embedding <=> CAST(:query_embedding AS vector)) as similarity
            FROM rag_chunks rc
            JOIN rag_files f ON f.id = rc.file_id
            WHERE rc.chat_room_id = :chat_room_id
                AND (rc.embedding <=> CAST(:query_embedding AS vector)) / 2 < :threshold
            ORDER BY rc.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :limit
        """)

        result = await session.execute(
            sql_query,
            {
                "chat_room_id": chat_room_id,
                "query_embedding": embedding_str,
                "threshold": threshold,
                "limit": limit,
            },
        )

        rows = result.fetchall()

        # 결과를 딕셔너리 리스트로 변환
        chunks = []
        for row in rows:
            chunks.append(
                {
                    "chunk_id": str(row.chunk_id),
                    "content": row.content,
                    "file_id": row.file_id,
                    "filename": row.filename,
                    "similarity": float(row.similarity),
                }
            )

        return chunks

    async def get_file_context(self, chunk_id: str, window_size: int = 2) -> dict:
        """
        청크의 주변 문맥 반환

        지정된 청크의 이전/다음 청크를 포함한 문맥을 제공합니다.

        Args:
            chunk_id: 청크 ID
            window_size: 앞뒤로 포함할 청크 수 (기본값: 2)

        Returns:
            dict: 문맥 정보
                {
                    "current": {"content": "...", "chunk_index": 5},
                    "before": [{"content": "...", "chunk_index": 3}, ...],
                    "after": [{"content": "...", "chunk_index": 7}, ...],
                    "file_id": 123,
                    "filename": "document.pdf"
                }
        """
        async with get_async_session() as session:
            # 현재 청크 조회
            stmt = text("""
                SELECT rc.id, rc.content, rc.chunk_index, rc.file_id, f.filename
                FROM rag_chunks rc
                JOIN rag_files f ON f.id = rc.file_id
                WHERE rc.id = :chunk_id
            """)

            result = await session.execute(stmt, {"chunk_id": chunk_id})
            row = result.fetchone()

            if not row:
                logger.warning(f"청크를 찾을 수 없음: chunk_id={chunk_id}")
                return {}

            current_chunk_index = row.chunk_index
            file_id = row.file_id
            filename = row.filename

            # 같은 파일의 청크들을 인덱스 순서로 조회
            stmt = text("""
                SELECT id, content, chunk_index
                FROM rag_chunks
                WHERE file_id = :file_id
                    AND chunk_index BETWEEN :min_index AND :max_index
                ORDER BY chunk_index
            """)

            result = await session.execute(
                stmt,
                {
                    "file_id": file_id,
                    "min_index": current_chunk_index - window_size,
                    "max_index": current_chunk_index + window_size,
                },
            )
            rows = result.fetchall()

            # before, current, after로 분류
            before = []
            after = []
            current = None

            for r in rows:
                chunk_data = {
                    "content": r.content,
                    "chunk_index": r.chunk_index,
                }

                if r.chunk_index < current_chunk_index:
                    before.append(chunk_data)
                elif r.chunk_index > current_chunk_index:
                    after.append(chunk_data)
                else:
                    current = chunk_data

            return {
                "current": current,
                "before": before,
                "after": after,
                "file_id": file_id,
                "filename": filename,
            }


# 싱글톤 인스턴스
_service_instance: Optional[RAGSearchService] = None
_service_lock = asyncio.Lock()


async def get_rag_search_service() -> RAGSearchService:
    """
    RAG 검색 서비스 싱글톤 인스턴스 반환 (스레드 안전)

    asyncio.Lock을 사용하여 멀티스레딩 환경에서도 안전하게 인스턴스를 생성합니다.

    Returns:
        RAGSearchService: 검색 서비스 인스턴스
    """
    global _service_instance

    # double-check locking pattern
    if _service_instance is None:
        async with _service_lock:
            # 락 획득 후 다시 확인
            if _service_instance is None:
                logger.info("RAGSearchService 싱글톤 인스턴스 생성")
                _service_instance = RAGSearchService()

    return _service_instance
