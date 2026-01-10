"""
TextExtractionService 단위 테스트

PDF 및 텍스트 파일에서 텍스트 추출 기능을 검증합니다.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.text_extraction_service import (
    CorruptedFileError,
    EmptyDocumentError,
    EncryptedPDFError,
    ExtractedText,
    TextExtractionService,
)


@pytest.fixture
def text_extraction_service():
    """TextExtractionService 인스턴스 생성"""
    return TextExtractionService()


@pytest.fixture
def sample_pdf_path(tmp_path):
    """샘플 PDF 파일 경로 생성"""
    return tmp_path / "sample.pdf"


@pytest.fixture
def sample_txt_path(tmp_path):
    """샘플 텍스트 파일 경로 생성"""
    return tmp_path / "sample.txt"


class TestExtractedText:
    """ExtractedText 모델 테스트"""

    def test_extracted_text_model_creation(self):
        """ExtractedText 모델 생성 테스트"""
        # Arrange
        content = "테스트 내용"
        metadata = {"title": "테스트 문서", "author": "테스터", "page_count": 1}

        # Act
        extracted = ExtractedText(content=content, metadata=metadata)

        # Assert
        assert extracted.content == content
        assert extracted.metadata == metadata


class TestTextExtractionService:
    """TextExtractionService 테스트 클래스"""

    def test_extract_text_from_pdf_success(
        self, text_extraction_service, sample_pdf_path
    ):
        """PDF 텍스트 추출 성공 테스트"""
        # Arrange
        pdf_content = b"PDF Test Content"
        sample_pdf_path.write_bytes(pdf_content)

        # Mock PdfReader to return sample text
        with patch(
            "services.text_extraction_service.PdfReader"
        ) as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Sample PDF content"

            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_reader.metadata = {
                "/Title": "Test PDF",
                "/Author": "Test Author",
            }
            mock_reader.is_encrypted = False
            mock_reader.encrypted = False

            mock_pdf_reader.return_value = mock_reader

            # Act
            result = text_extraction_service.extract_text(
                str(sample_pdf_path), "pdf"
            )

            # Assert
            assert result is not None
            assert isinstance(result, ExtractedText)
            assert "Sample PDF content" in result.content
            assert result.metadata["page_count"] == 1

    def test_extract_text_from_txt_success(
        self, text_extraction_service, sample_txt_path
    ):
        """TXT 텍스트 추출 성공 테스트"""
        # Arrange
        content = "테스트 파일 내용입니다.\n한글 텍스트 추출 테스트."
        sample_txt_path.write_text(content, encoding="utf-8")

        # Act
        result = text_extraction_service.extract_text(str(sample_txt_path), "txt")

        # Assert
        assert result is not None
        assert isinstance(result, ExtractedText)
        assert result.content == content
        assert result.metadata["file_type"] == "txt"

    def test_extract_pdf_metadata(
        self, text_extraction_service, sample_pdf_path
    ):
        """PDF 메타데이터 추출 테스트"""
        # Arrange - 실제 파일 생성 필요
        sample_pdf_path.write_bytes(b"Mock PDF content")

        with patch(
            "services.text_extraction_service.PdfReader"
        ) as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Content"

            mock_reader = MagicMock()
            mock_reader.pages = [mock_page, mock_page]  # 2 pages
            mock_reader.metadata = {
                "/Title": "Test Document",
                "/Author": "John Doe",
                "/Creator": "Test Creator",
            }
            mock_reader.is_encrypted = False
            mock_reader.encrypted = False

            mock_pdf_reader.return_value = mock_reader

            # Act
            result = text_extraction_service.extract_text(
                str(sample_pdf_path), "pdf"
            )

            # Assert
            assert result.metadata["title"] == "Test Document"
            assert result.metadata["author"] == "John Doe"
            assert result.metadata["page_count"] == 2

    def test_extract_encrypted_pdf_raises_error(
        self, text_extraction_service, sample_pdf_path
    ):
        """암호화된 PDF 에러 처리 테스트"""
        # Arrange - 실제 파일 생성 필요
        sample_pdf_path.write_bytes(b"Encrypted PDF content")

        with patch(
            "services.text_extraction_service.PdfReader"
        ) as mock_pdf_reader:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = True
            mock_reader.encrypted = True
            mock_reader.decrypt.return_value = False  # Decryption fails

            mock_pdf_reader.return_value = mock_reader

            # Act & Assert
            with pytest.raises(EncryptedPDFError) as exc_info:
                text_extraction_service.extract_text(str(sample_pdf_path), "pdf")

            assert "암호화된 PDF" in str(exc_info.value)

    def test_extract_corrupted_pdf_raises_error(
        self, text_extraction_service, sample_pdf_path
    ):
        """손상된 PDF 에러 처리 테스트"""
        # Arrange
        sample_pdf_path.write_bytes(b"Corrupted PDF content")

        # 실제 PdfReader를 사용하여 손상된 PDF 처리 테스트
        # Act & Assert
        with pytest.raises(CorruptedFileError) as exc_info:
            text_extraction_service.extract_text(str(sample_pdf_path), "pdf")

        assert "손상된 PDF" in str(exc_info.value) or "손상된 파일" in str(exc_info.value)

    def test_extract_empty_pdf_raises_error(
        self, text_extraction_service, sample_pdf_path
    ):
        """빈 PDF 에러 처리 테스트"""
        # Arrange - 실제 파일 생성 필요
        sample_pdf_path.write_bytes(b"Empty PDF content")

        with patch(
            "services.text_extraction_service.PdfReader"
        ) as mock_pdf_reader:
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""  # Empty text

            mock_reader = MagicMock()
            mock_reader.pages = [mock_page]
            mock_reader.is_encrypted = False
            mock_reader.encrypted = False

            mock_pdf_reader.return_value = mock_reader

            # Act & Assert
            with pytest.raises(EmptyDocumentError) as exc_info:
                text_extraction_service.extract_text(str(sample_pdf_path), "pdf")

            assert "빈 문서" in str(exc_info.value) or "비어있습니다" in str(exc_info.value)

    def test_extract_text_performance_10_pages(
        self, text_extraction_service, sample_pdf_path
    ):
        """10페이지 PDF 추출 성능 테스트 (< 5 seconds)"""
        # Arrange
        import time

        # 실제 파일 생성 필요
        sample_pdf_path.write_bytes(b"Performance test PDF")

        with patch(
            "services.text_extraction_service.PdfReader"
        ) as mock_pdf_reader:
            # Create 10 mock pages
            mock_pages = []
            for i in range(10):
                mock_page = MagicMock()
                mock_page.extract_text.return_value = f"Page {i + 1} content\n"
                mock_pages.append(mock_page)

            mock_reader = MagicMock()
            mock_reader.pages = mock_pages
            mock_reader.metadata = {"/Title": "Performance Test PDF"}
            mock_reader.is_encrypted = False
            mock_reader.encrypted = False

            mock_pdf_reader.return_value = mock_reader

            # Act
            start_time = time.time()
            result = text_extraction_service.extract_text(
                str(sample_pdf_path), "pdf"
            )
            elapsed_time = time.time() - start_time

            # Assert
            assert result is not None
            assert result.metadata["page_count"] == 10
            assert elapsed_time < 5.0, f"성능 저하: {elapsed_time:.2f}초 (5초 미만 요구)"

    def test_extract_text_returns_korean_content(
        self, text_extraction_service, sample_txt_path
    ):
        """한글 텍스트 추출 테스트"""
        # Arrange
        korean_content = """
        한국어 텍스트 추출 테스트입니다.
        RAG 시스템을 위한 문서 처리 기능을 테스트합니다.
        """
        sample_txt_path.write_text(korean_content, encoding="utf-8")

        # Act
        result = text_extraction_service.extract_text(
            str(sample_txt_path), "txt"
        )

        # Assert
        assert result is not None
        assert "한국어" in result.content
        assert "텍스트 추출" in result.content
        assert "UTF-8" not in result.content  # Content only, not encoding info

    def test_extract_text_nonexistent_file(
        self, text_extraction_service, tmp_path
    ):
        """존재하지 않는 파일 에러 처리 테스트"""
        # Arrange
        nonexistent_path = tmp_path / "nonexistent.pdf"

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            text_extraction_service.extract_text(str(nonexistent_path), "pdf")

    def test_extract_text_unsupported_file_type(
        self, text_extraction_service, sample_txt_path
    ):
        """지원하지 않는 파일 타입 에러 처리 테스트"""
        # Arrange
        sample_txt_path.write_text("Content")

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            text_extraction_service.extract_text(str(sample_txt_path), "exe")

        assert "지원하지 않는 파일 형식" in str(exc_info.value)

    def test_extract_text_empty_txt_file(
        self, text_extraction_service, sample_txt_path
    ):
        """빈 텍스트 파일 에러 처리 테스트"""
        # Arrange
        sample_txt_path.write_text("", encoding="utf-8")

        # Act & Assert
        with pytest.raises(EmptyDocumentError) as exc_info:
            text_extraction_service.extract_text(str(sample_txt_path), "txt")

        # 에러 메시지 확인 (더 유연한 검사)
        error_msg = str(exc_info.value)
        assert "비어있습니다" in error_msg or "빈 문서" in error_msg or "empty" in error_msg.lower()

    def test_extract_text_directory_path_raises_error(
        self, text_extraction_service, tmp_path
    ):
        """디렉토리 경로 에러 처리 테스트"""
        # Arrange - 디렉토리 생성
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()

        # Act & Assert
        with pytest.raises(FileNotFoundError) as exc_info:
            text_extraction_service.extract_text(str(dir_path), "txt")

        assert "파일이 아닙니다" in str(exc_info.value)
