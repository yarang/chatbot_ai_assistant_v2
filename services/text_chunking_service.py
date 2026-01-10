"""
텍스트 청킹 서비스

텍스트를 토큰 제한에 맞춰 지능적으로 분할합니다.
- tiktoken을 사용한 정확한 토큰 카운팅
- 문단 경계 보존
- 오버랩 적용
- 한글/영어 혼합 지원
"""
import logging
from typing import Any

import tiktoken
from services.text_extraction_service import ExtractedText
from models.text_chunk import TextChunk


# 로거 설정
logger = logging.getLogger(__name__)


class TextChunkingService:
    """
    텍스트 청킹 서비스

    문서를 토큰 제한에 맞춰 지능적으로 분할합니다.
    문단 경계를 보존하고 오버랩을 적용하여 문맥을 유지합니다.

    Attributes:
        encoding: tiktoken 인코더 (cl100k_base)
        default_max_chunk_size: 기본 최대 청크 크기 (500 토큰)
        default_overlap_size: 기본 오버랩 크기 (50 토큰, 10%)
    """

    def __init__(self):
        """TextChunkingService 초기화"""
        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.error(f"tiktoken 인코딩 로드 실패: {e}")
            raise

        self.default_max_chunk_size = 500
        self.default_overlap_size = 50  # 500의 10%

        logger.info("TextChunkingService 초기화 완료")

    def chunk_text(
        self,
        extracted_text: ExtractedText,
        file_id: int,
        max_chunk_size: int = 500,
        overlap_size: int = 50,
    ) -> list[TextChunk]:
        """
        텍스트를 청킹으로 분할

        추출된 텍스트를 토큰 제한에 맞춰 분할하고 문단 경계를 보존합니다.
        오버랩을 적용하여 청크 간 문맥을 유지합니다.

        Args:
            extracted_text: ExtractedText 객체 (텍스트와 메타데이터)
            file_id: 파일 ID
            max_chunk_size: 최대 청크 크기 (토큰 수, 기본값: 500)
            overlap_size: 청크 간 오버랩 크기 (토큰 수, 기본값: 50)

        Returns:
            list[TextChunk]: 분할된 텍스트 청크 리스트

        Raises:
            ValueError: 텍스트가 비어있는 경우

        Example:
            >>> service = TextChunkingService()
            >>> chunks = service.chunk_text(extracted_text, file_id=1)
            >>> print(f"생성된 청크 수: {len(chunks)}")
        """
        # 텍스트 비어있음 확인
        content = extracted_text.content.strip()

        if not content:
            error_msg = "텍스트가 비어있습니다. 청킹을 수행할 수 없습니다."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            f"텍스트 청킹 시작: file_id={file_id}, "
            f"전체 토큰 수={self._count_tokens(content)}, "
            f"max_chunk_size={max_chunk_size}, overlap_size={overlap_size}"
        )

        # 텍스트가 작으면 단일 청크 반환
        total_tokens = self._count_tokens(content)

        if total_tokens <= max_chunk_size:
            logger.info(f"텍스트가 작아서 단일 청크로 반환: {total_tokens} 토큰")
            chunk_metadata = self._create_chunk_metadata(
                extracted_text.metadata, file_id, 0, 1
            )
            return [
                TextChunk(
                    content=content,
                    chunk_index=0,
                    metadata=chunk_metadata,
                )
            ]

        # 텍스트 분할
        chunks_text = self._split_into_chunks(
            content, max_chunk_size, overlap_size
        )

        # 문단 경계 존중
        chunks_text = self._respect_boundaries(chunks_text, max_chunk_size)

        # TextChunk 객체 생성
        chunks = []
        for idx, chunk_text in enumerate(chunks_text):
            chunk_metadata = self._create_chunk_metadata(
                extracted_text.metadata, file_id, idx, len(chunks_text)
            )

            chunk = TextChunk(
                content=chunk_text.strip(),
                chunk_index=idx,
                metadata=chunk_metadata,
            )
            chunks.append(chunk)

            logger.debug(
                f"청크 {idx + 1}/{len(chunks_text)} 생성: "
                f"{self._count_tokens(chunk_text)} 토큰"
            )

        logger.info(f"텍스트 청킹 완료: {len(chunks)} 청크 생성")

        return chunks

    def _count_tokens(self, text: str) -> int:
        """
        텍스트의 토큰 수 계산

        tiktoken을 사용하여 정확한 토큰 수를 계산합니다.
        한글과 영어를 모두 정확하게 처리합니다.

        Args:
            text: 토큰을 셀 텍스트

        Returns:
            int: 토큰 수

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            chunk_text() 메서드를 통해 호출됩니다.
        """
        try:
            tokens = self.encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error(f"토큰 카운팅 실패: {e}")
            # 실패 시 대략적인 추정치 반환 (문자 수 / 4)
            return len(text) // 4

    def _split_into_chunks(
        self, text: str, max_size: int, overlap: int
    ) -> list[str]:
        """
        텍스트를 청크로 분할

        토큰 제한에 맞춰 텍스트를 분할하고 오버랩을 적용합니다.
        이진 탐색을 사용하여 최적의 분할 지점을 찾습니다.

        Args:
            text: 분할할 텍스트
            max_size: 최대 청크 크기 (토큰 수)
            overlap: 오버랩 크기 (토큰 수)

        Returns:
            list[str]: 분할된 텍스트 청크 리스트

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            chunk_text() 메서드를 통해 호출됩니다.
        """
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # 이진 탐색으로 최적의 끝 위치 찾기
            end = self._binary_search_chunk_end(text, start, max_size, text_length)

            # 현재 청크 추출
            current_chunk = text[start:end].strip()

            if not current_chunk:
                # 빈 청크면 건너뛰기
                start = end
                continue

            chunks.append(current_chunk)

            # 다음 시작 위치 계산 (오버랩 적용)
            overlap_ratio = overlap / max_size
            overlap_chars = int(len(current_chunk) * overlap_ratio)
            start = max(end - overlap_chars, end - 100)  # 최대 100자 오버랩

            # 진전이 없으면 강제 진전
            if start <= end - 100:
                start = end

        return chunks

    def _binary_search_chunk_end(
        self, text: str, start: int, max_size: int, max_end: int
    ) -> int:
        """
        이진 탐색으로 청크의 끝 위치 찾기

        토큰 수가 max_size에 가장 가까운 끝 위치를 찾습니다.

        Args:
            text: 전체 텍스트
            start: 청크 시작 위치
            max_size: 최대 토큰 수
            max_end: 최대 끝 위치

        Returns:
            int: 청크 끝 위치

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            _split_into_chunks() 메서드를 통해 호출됩니다.
        """
        left = start
        right = min(max_end, start + max_size * 4)  # 대략적인 상한

        best_end = start

        while left <= right:
            mid = (left + right) // 2
            current_text = text[start:mid]
            token_count = self._count_tokens(current_text)

            if token_count <= max_size:
                best_end = mid
                left = mid + 1
            else:
                right = mid - 1

        return best_end

    def _respect_boundaries(
        self, chunks: list[str], max_size: int
    ) -> list[str]:
        """
        문단 경계 존중

        청크가 문단 중간에서 끝나지 않도록 조정합니다.
        빈 줄(\\n\\n)을 문단 경계로 인식합니다.

        Args:
            chunks: 원본 청크 리스트
            max_size: 최대 청크 크기 (토큰 수)

        Returns:
            list[str]: 경계가 조정된 청크 리스트

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            chunk_text() 메서드를 통해 호출됩니다.
        """
        adjusted_chunks = []

        for chunk in chunks:
            # 토큰 수 확인
            token_count = self._count_tokens(chunk)

            # 토큰 수가 여유가 있으면 문단 경계로 조정
            if token_count < max_size * 0.9:
                # 마지막 문장 끝으로 조정
                last_sentence_end = self._find_last_sentence_end(chunk)
                if last_sentence_end > 0:
                    adjusted_chunks.append(chunk[:last_sentence_end])
                else:
                    adjusted_chunks.append(chunk)
            else:
                adjusted_chunks.append(chunk)

        return adjusted_chunks

    def _find_last_sentence_end(self, text: str) -> int:
        """
        마지막 문장 끝 위치 찾기

        텍스트에서 마지막 문장 끝 부호(. ! ?)의 위치를 찾습니다.

        Args:
            text: 검색할 텍스트

        Returns:
            int: 마지막 문장 끝 위치 (인덱스), 찾지 못하면 0

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            _respect_boundaries() 메서드를 통해 호출됩니다.
        """
        # 문장 끝 부호 찾기 (뒤에서부터)
        sentence_endings = (".", "!", "?", "。", "\n\n")

        for i in range(len(text) - 1, -1, -1):
            if text[i] in sentence_endings:
                # 해당 위치부터 끝까지의 공백 확인
                remaining = text[i + 1 :]
                if not remaining.strip():
                    return i + 1
                elif i < len(text) - 1 and text[i + 1] == " ":
                    return i + 1

        return 0

    def _create_chunk_metadata(
        self,
        original_metadata: dict[str, Any],
        file_id: int,
        chunk_index: int,
        total_chunks: int,
    ) -> dict[str, Any]:
        """
        청크 메타데이터 생성

        원본 문서의 메타데이터와 청크 정보를 결합합니다.

        Args:
            original_metadata: 원본 문서 메타데이터
            file_id: 파일 ID
            chunk_index: 청크 인덱스
            total_chunks: 전체 청크 수

        Returns:
            dict[str, Any]: 청크 메타데이터

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            chunk_text() 메서드를 통해 호출됩니다.
        """
        chunk_metadata = original_metadata.copy()

        # 청크 관련 메타데이터 추가
        chunk_metadata.update(
            {
                "file_id": file_id,
                "chunk_index": chunk_index,
                "total_chunks": total_chunks,
            }
        )

        return chunk_metadata
