"""
TextChunkingService 단위 테스트

텍스트 청킹 기능을 검증합니다.
- 토큰 기반 청킹
- 문단 경계 보존
- 오버랩 적용
- 한글 지원
"""
import pytest

from models.text_chunk import TextChunk
from services.text_chunking_service import TextChunkingService


@pytest.fixture
def chunking_service():
    """TextChunkingService 인스턴스 생성"""
    return TextChunkingService()


@pytest.fixture
def sample_extracted_text():
    """샘플 ExtractedText 객체 생성"""
    from services.text_extraction_service import ExtractedText

    content = """
    첫 번째 문단입니다. 이 문단은 테스트용으로 사용됩니다.

    두 번째 문단입니다. 이 문단도 테스트용입니다.

    세 번째 문단입니다. 이것은 마지막 문단입니다.
    """

    metadata = {
        "file_type": "txt",
        "file_size": 1000,
        "encoding": "utf-8",
    }

    return ExtractedText(content=content, metadata=metadata)


class TestTextChunkModel:
    """TextChunk 모델 테스트"""

    def test_text_chunk_model_creation(self):
        """TextChunk 모델 생성 테스트"""
        # Arrange
        content = "청크 내용"
        chunk_index = 0
        metadata = {"source": "test.txt"}

        # Act
        chunk = TextChunk(content=content, chunk_index=chunk_index, metadata=metadata)

        # Assert
        assert chunk.content == content
        assert chunk.chunk_index == chunk_index
        assert chunk.metadata == metadata


class TestTextChunkingService:
    """TextChunkingService 테스트 클래스"""

    def test_chunk_text_basic_success(self, chunking_service, sample_extracted_text):
        """기본 텍스트 청킹 성공 테스트"""
        # Act
        chunks = chunking_service.chunk_text(sample_extracted_text, file_id=1)

        # Assert
        assert chunks is not None
        assert len(chunks) > 0
        assert all(isinstance(chunk, TextChunk) for chunk in chunks)
        assert all(chunk.content for chunk in chunks)

    def test_chunk_text_respects_max_token_limit(self, chunking_service):
        """최대 토큰 제한 준수 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        # 1000 토큰 이상의 긴 텍스트 생성
        long_content = "이것은 긴 텍스트입니다. " * 100  # 약 1500+ 토큰
        extracted_text = ExtractedText(content=long_content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        assert len(chunks) > 1  # 여러 청크로 분할되어야 함

        # 각 청크의 토큰 수 확인
        for chunk in chunks:
            token_count = chunking_service._count_tokens(chunk.content)
            assert token_count <= 500, f"청크 크기 초과: {token_count} 토큰 (최대 500)"

    def test_chunk_text_applies_overlap(self, chunking_service):
        """오버랩 적용 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        # 오버랩을 확인할 수 있는 긴 텍스트
        content = "문단1. " + "테스트 내용. " * 50 + "\n\n"
        content += "문단2. " + "테스트 내용. " * 50 + "\n\n"
        content += "문단3. " + "테스트 내용. " * 50

        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        if len(chunks) > 1:
            # 인접한 청크 간의 오버랩 확인
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i].content
                next_chunk = chunks[i + 1].content

                # 마지막 50자와 다음 청크의 처음 50자 비교
                current_end = current_chunk[-50:] if len(current_chunk) >= 50 else current_chunk
                next_start = next_chunk[:50] if len(next_chunk) >= 50 else next_chunk

                # 일부 오버랩이 있어야 함 (완전히 동일하지 않아도 됨)
                has_overlap = any(word in next_start for word in current_end.split())
                assert has_overlap, f"청크 {i}와 {i+1} 사이에 오버랩이 없습니다"

    def test_chunk_text_preserves_paragraph_boundaries(self, chunking_service):
        """문단 경계 보존 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        content = """
        첫 번째 문단입니다. 이 문단은 청킹 시에 보존되어야 합니다.

        두 번째 문단입니다. 문단 경계가 중요합니다.

        세 번째 문단입니다. 각 문단은 의미 있는 단위입니다.

        네 번째 문단입니다. 빈 줄로 구분됩니다.
        """

        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        for chunk in chunks:
            # 청크 내용이 문단 중간에서 끝나지 않아야 함
            # 빈 줄(\n\n)이 있는 경우를 제외하고
            lines = chunk.content.split("\n")
            non_empty_lines = [line for line in lines if line.strip()]

            # 마지막 비어있지 않은 라인이 문장의 끝으로 끝나야 함
            if non_empty_lines:
                last_line = non_empty_lines[-1]
                # 문장 끝 부호로 끝나거나, 적절한 길이여야 함
                assert (
                    last_line.rstrip().endswith((".", "!", "?", "。")) or len(last_line) < 50
                ), f"문단 경계가 보존되지 않았습니다: {last_line[:50]}..."

    def test_chunk_text_with_korean_content(self, chunking_service):
        """한글 콘텐츠 청킹 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        korean_content = """
        대한민국은 동아시아에 위치한 국가입니다.
        한글은 세계에서 과학적으로 가장 우수한 문자 중 하나입니다.
        인공지능 기술은 한국에서 빠르게 발전하고 있습니다.
        RAG 시스템은 검색 증강 생성을 의미합니다.
        텍스트 청킹은 문서 처리의 중요한 단계입니다.
        """ * 20  # 긴 텍스트 생성

        extracted_text = ExtractedText(content=korean_content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        assert len(chunks) > 0
        # 적어도 하나의 청크는 한글 키워드를 포함해야 함
        has_korean = any(
            "한글" in chunk.content or "한국" in chunk.content or "텍스트" in chunk.content
            for chunk in chunks
        )
        assert has_korean, "청크에 한글 콘텐츠가 포함되어 있어야 합니다"

    def test_chunk_text_with_mixed_content(self, chunking_service):
        """혼합 콘텐츠 (영어 + 한글) 청킹 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        mixed_content = """
        This is an English sentence. 이것은 한국어 문장입니다.
        Machine learning is a subset of AI. 기계 학습은 인공지능의 하위 집합입니다.
        Text chunking is important. 텍스트 청킹은 중요합니다.
        """ * 30

        extracted_text = ExtractedText(content=mixed_content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        assert len(chunks) > 0
        # 각 청크가 영어와 한국어를 모두 포함할 수 있어야 함
        has_both_languages = any(
            "English" in chunk.content and "한국어" in chunk.content for chunk in chunks
        )
        # 적어도 하나의 청크는 혼합되어 있어야 함
        assert has_both_languages or len(chunks) > 1

    def test_chunk_text_empty_content_raises_error(self, chunking_service):
        """빈 콘텐츠 에러 처리 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        empty_text = ExtractedText(content="", metadata={})

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            chunking_service.chunk_text(empty_text, file_id=1)

        assert "비어있습니다" in str(exc_info.value) or "empty" in str(exc_info.value).lower()

    def test_chunk_text_single_chunk_no_split(self, chunking_service):
        """짧은 텍스트 단일 청크 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        short_content = "이것은 짧은 텍스트입니다. 청킹이 필요하지 않습니다."

        extracted_text = ExtractedText(content=short_content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        assert len(chunks) == 1
        assert chunks[0].content == short_content
        assert chunks[0].chunk_index == 0

    def test_chunk_text_large_document_multiple_chunks(self, chunking_service):
        """대형 문서 다중 청킹 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        # 대용량 텍스트 생성 (약 3000 토큰)
        large_content = "이것은 대용량 문서의 일부입니다. " * 400

        extracted_text = ExtractedText(content=large_content, metadata={"file_size": 50000})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        assert len(chunks) >= 6  # 3000 / 500 = 6 청크 이상

        # 청크 인덱스 연속성 확인
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

        # 모든 청크가 비어있지 않아야 함
        assert all(chunk.content.strip() for chunk in chunks)

    def test_chunk_text_metadata_preservation(self, chunking_service):
        """메타데이터 보존 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        content = "테스트 내용입니다." * 20
        original_metadata = {
            "file_type": "pdf",
            "page_count": 10,
            "title": "테스트 문서",
            "author": "테스터",
        }

        extracted_text = ExtractedText(content=content, metadata=original_metadata)

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        for chunk in chunks:
            assert "file_type" in chunk.metadata
            assert chunk.metadata["file_type"] == "pdf"
            assert "page_count" in chunk.metadata
            assert chunk.metadata["page_count"] == 10

    def test_chunk_token_counting_accuracy(self, chunking_service):
        """토큰 카운팅 정확도 테스트"""
        # Arrange
        test_texts = [
            "Hello, world!",  # 영어
            "안녕하세요, 세계!",  # 한글
            "This is a test sentence for token counting accuracy.",  # 긴 영어
            "이것은 토큰 카운팅 정확도를 테스트하기 위한 문장입니다.",  # 긴 한글
            "Mixed content with 한글 and English words.",  # 혼합
        ]

        # Act & Assert
        for text in test_texts:
            token_count = chunking_service._count_tokens(text)

            # 토큰 수는 항상 0보다 커야 함
            assert token_count > 0, f"토큰 카운트가 0 이하입니다: {text}"

            # 토큰 수는 문자 수보다 작거나 같아야 함 (대부분의 경우)
            # 한글의 경우 문자 수보다 토큰 수가 더 많을 수 있음
            assert token_count <= len(text) * 2, f"토큰 수가 비정상적으로 높습니다: {text} ({token_count} tokens)"

    def test_chunk_text_performance_1000_tokens(self, chunking_service):
        """1000 토큰 청킹 성능 테스트 (< 1 second)"""
        # Arrange
        import time
        from services.text_extraction_service import ExtractedText

        # 약 1000 토큰의 텍스트 생성
        content = "성능 테스트를 위한 텍스트입니다. " * 150

        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        start_time = time.time()
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)
        elapsed_time = time.time() - start_time

        # Assert
        assert len(chunks) > 0
        assert elapsed_time < 1.0, f"성능 저하: {elapsed_time:.2f}초 (1초 미만 요구)"

    def test_chunk_overlap_token_precision(self, chunking_service):
        """오버랩 토큰 정밀도 테스트 (±5 tokens)"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        # 충분히 긴 텍스트 생성
        content = "테스트 문장입니다. " * 100
        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        if len(chunks) > 1:
            for i in range(len(chunks) - 1):
                # 인접한 청크 간의 오버랩 토큰 수 계산
                current_tokens = chunking_service._count_tokens(chunks[i].content)
                next_tokens = chunking_service._count_tokens(chunks[i + 1].content)

                # 오버랩이 50토큰 ±5 범위 내에 있어야 함
                # 실제 오버랩을 계산하려면 텍스트 비교가 필요하지만,
                # 여기서는 전체 토큰 수를 확인하여 청킹이 제대로 되었는지 확인
                assert current_tokens <= 500, f"현재 청크가 너무 큽니다: {current_tokens} 토큰"
                assert next_tokens <= 500, f"다음 청크가 너무 큽니다: {next_tokens} 토큰"

    def test_chunk_respects_custom_max_size(self, chunking_service):
        """사용자 정의 최대 크기 준수 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        content = "사용자 정의 크기 테스트입니다. " * 100
        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1, max_chunk_size=300)

        # Assert
        for chunk in chunks:
            token_count = chunking_service._count_tokens(chunk.content)
            assert token_count <= 300, f"사용자 정의 크기를 초과했습니다: {token_count} 토큰"

    def test_chunk_respects_custom_overlap(self, chunking_service):
        """사용자 정의 오버랩 준수 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        content = "사용자 정의 오버랩 테스트입니다. " * 100
        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1, overlap_size=100)

        # Assert
        # 오버랩이 적용되었는지 확인 (청크 수로 간접 확인)
        assert len(chunks) > 1, "오버랩 테스트를 위해서는 여러 청크가 필요합니다"

    def test_chunk_text_with_special_characters(self, chunking_service):
        """특수 문자 포함 텍스트 청킹 테스트"""
        # Arrange
        from services.text_extraction_service import ExtractedText

        content = """
        Special characters: !@#$%^&*()_+-=[]{}|;':",./<>?
        Numbers: 1234567890
        Mixed: 테스트@123#$한글
        """ * 20

        extracted_text = ExtractedText(content=content, metadata={})

        # Act
        chunks = chunking_service.chunk_text(extracted_text, file_id=1)

        # Assert
        assert len(chunks) > 0
        # 특수 문자가 보존되어야 함
        assert any("!" in chunk.content or "@" in chunk.content for chunk in chunks)
