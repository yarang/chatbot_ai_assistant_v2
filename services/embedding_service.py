"""
임베딩 서비스

텍스트 청크의 임베딩 생성, 배치 처리, API 재시도, 비용 모니터링을 수행합니다.
Google Generative AI Embeddings API를 사용하여 768차원 벡터를 생성하고 저장합니다.
"""
import logging
import time
from typing import List

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pydantic import SecretStr
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from core.config import get_settings
from models.embedding_result import EmbeddingResult
from models.text_chunk import TextChunk
from repository.embedding_repository import EmbeddingRepository

# 로거 설정
logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    임베딩 서비스

    텍스트 청크를 768차원 임베딩 벡터로 변환하고 데이터베이스에 저장합니다.
    Gemini Embeddings API(text-embedding-004)를 사용하며 배치 처리와 재시도를 지원합니다.

    Attributes:
        session: SQLAlchemy 비동기 세션
        repository: 임베딩 리포지토리
        embedding_model: Gemini 임베딩 모델
        max_batch_size: 최대 배치 크기 (기본값: 100)
        max_retries: 최대 재시도 횟수 (기본값: 3)

    Example:
        >>> service = EmbeddingService(session)
        >>> result = await service.embed_chunks(chunks, chat_room_id=1, file_id=1)
        >>> print(f"처리된 청크: {result.successful_chunks}/{result.total_chunks}")
    """

    def __init__(self, session):
        """
        EmbeddingService 초기화

        Args:
            session: SQLAlchemy 비동기 세션
        """
        self.session = session
        self.repository = EmbeddingRepository(session)
        self.embedding_model = None
        self.max_batch_size = 100
        self.max_retries = 3

        logger.info("EmbeddingService 초기화 완료")

    async def embed_chunks(
        self,
        chunks: List[TextChunk],
        chat_room_id: int,
        file_id: int
    ) -> EmbeddingResult:
        """
        텍스트 청크 임베딩 생성 및 저장

        청크를 배치로 처리하여 임베딩을 생성하고 데이터베이스에 저장합니다.
        배치 크기는 최대 100개이며, API 실패 시 지수 백오프로 재시도합니다.

        Args:
            chunks: 텍스트 청크 리스트
            chat_room_id: 채팅방 ID
            file_id: 파일 ID

        Returns:
            EmbeddingResult: 임베딩 결과 통계

        Raises:
            ValueError: chunks가 비어있는 경우
            Exception: 모든 청크가 실패한 경우

        Example:
            >>> result = await service.embed_chunks(chunks, chat_room_id=1, file_id=1)
            >>> assert result.successful_chunks == len(chunks)
        """
        # 입력 검증
        if not chunks:
            error_msg = "chunks는 비어있을 수 없습니다"
            logger.error(error_msg)
            raise ValueError(error_msg)

        start_time = time.time()
        total_chunks = len(chunks)

        logger.info(
            f"임베딩 생성 시작: file_id={file_id}, "
            f"chat_room_id={chat_room_id}, total_chunks={total_chunks}"
        )

        # 배치 처리
        batch_count = 0
        successful_chunks = 0
        failed_chunks = 0

        for i in range(0, total_chunks, self.max_batch_size):
            batch = chunks[i:i + self.max_batch_size]
            batch_count += 1

            logger.info(f"배치 {batch_count} 처리: {len(batch)} 청크")

            try:
                # 배치 임베딩 생성
                embeddings = await self._batch_embed(batch)

                # 데이터베이스에 저장
                await self.repository.store_embeddings(
                    chunks=batch,
                    embeddings=embeddings,
                    chat_room_id=chat_room_id,
                    file_id=file_id
                )

                successful_chunks += len(batch)
                logger.info(
                    f"배치 {batch_count} 완료: {len(batch)} 청크 임베딩 성공"
                )

            except Exception as e:
                failed_chunks += len(batch)
                logger.error(f"배치 {batch_count} 실패: {e}")
                raise

        processing_time = time.time() - start_time

        # 비용 로깅
        self._log_cost(total_chunks)

        # 결과 생성
        result = EmbeddingResult(
            total_chunks=total_chunks,
            successful_chunks=successful_chunks,
            failed_chunks=failed_chunks,
            embedding_dimension=768,
            batch_count=batch_count,
            processing_time_seconds=processing_time,
            metadata={
                "chat_room_id": chat_room_id,
                "file_id": file_id,
                "model": "text-embedding-004"
            }
        )

        logger.info(
            f"임베딩 완료: {result.successful_chunks}/{result.total_chunks} 청크, "
            f"소요 시간: {processing_time:.2f}초"
        )

        return result

    async def _batch_embed(self, chunks: List[TextChunk]) -> List[List[float]]:
        """
        배치 임베딩 생성 (재시도 포함)

        지수 백오프를 사용하여 API 실패 시 재시도합니다.
        최대 3번 재시도하며, 대기 시간은 1초, 2초, 4초로 증가합니다.

        Args:
            chunks: 임베딩을 생성할 청크 리스트

        Returns:
            List[List[float]]: 임베딩 벡터 리스트 (768차원)

        Raises:
            Exception: 최대 재시도 횟수 초과 시

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            embed_chunks() 메서드를 통해 호출됩니다.
        """
        if self.embedding_model is None:
            self.embedding_model = self._get_embedding_model()

        # 텍스트 추출
        texts = [chunk.content for chunk in chunks]

        # 임베딩 생성 (재시도 로직 포함)
        embeddings = await self._embed_with_retry(texts)

        return embeddings

    def _get_embedding_model(self) -> GoogleGenerativeAIEmbeddings:
        """
        Gemini 임베딩 모델 초기화

        text-embedding-004 모델을 사용하여 768차원 임베딩을 생성합니다.

        Returns:
            GoogleGenerativeAIEmbeddings: 초기화된 임베딩 모델

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            _batch_embed() 메서드를 통해 호출됩니다.
        """
        settings = get_settings()

        model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            api_key=SecretStr(settings.gemini.api_key)
        )

        logger.info("Gemini 임베딩 모델 초기화 완료: text-embedding-004")

        return model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    async def _embed_with_retry(self, texts: List[str]) -> List[List[float]]:
        """
        재시도 로직이 포함된 임베딩 생성

        tenacity를 사용하여 지수 백오프 재시도를 구현합니다.
        API 실패 시 1초, 2초, 4초 대기 후 재시도합니다.

        Args:
            texts: 임베딩을 생성할 텍스트 리스트

        Returns:
            List[List[float]]: 임베딩 벡터 리스트 (768차원)

        Raises:
            Exception: 최대 재시도 횟수(3회) 초과 시

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            _batch_embed() 메서드를 통해 호출됩니다.
        """
        try:
            # 동기 임베딩 호출 (langchain의 GeminiEmbeddings는 동기)
            embeddings = self.embedding_model.embed_documents(texts)

            # 차원 검증
            for i, embedding in enumerate(embeddings):
                if len(embedding) != 768:
                    raise ValueError(
                        f"임베딩 {i}의 차원이 768이어야 합니다 (현재: {len(embedding)})"
                    )

            logger.debug(f"{len(texts)}개 텍스트 임베딩 생성 완료")
            return embeddings

        except Exception as e:
            logger.warning(f"임베딩 생성 실패, 재시도 진행: {e}")
            raise

    def _log_cost(self, chunk_count: int) -> None:
        """
        임베딩 비용 로깅

        처리된 청크 수를 기반으로 비용을 추정하고 로깅합니다.
        Gemini text-embedding-004 가격 기준: $0.025 per 1M characters (approximate)

        Args:
            chunk_count: 처리된 청크 수

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            embed_chunks() 메서드를 통해 호출됩니다.
        """
        # 비용 추정 (문자 수 기준, 대략적 계산)
        # 청크당 평균 500자 가정
        estimated_chars = chunk_count * 500
        estimated_cost_usd = (estimated_chars / 1_000_000) * 0.025

        logger.info(
            f"임베딩 비용: {chunk_count} 청크 처리 "
            f"(추정 {estimated_chars:,} 문자, 약 ${estimated_cost_usd:.6f} USD)"
        )
