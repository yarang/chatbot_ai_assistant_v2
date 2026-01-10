"""
텍스트 추출 서비스

PDF 및 텍스트 파일에서 텍스트와 메타데이터를 추출합니다.

이 모듈은 다음과 같은 기능을 제공합니다:
- PDF 파일에서 텍스트 및 메타데이터 추출
- 텍스트 파일에서 내용 추출
- 암호화된 PDF, 손상된 파일, 빈 문서 처리
- 다양한 인코딩 지원 (UTF-8, CP949)
"""
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from pypdf import PdfReader


# 로거 설정
logger = logging.getLogger(__name__)


class TextExtractionError(Exception):
    """텍스트 추출 기본 에러"""

    pass


class EncryptedPDFError(TextExtractionError):
    """암호화된 PDF 에러"""

    pass


class CorruptedFileError(TextExtractionError):
    """손상된 파일 에러"""

    pass


class EmptyDocumentError(TextExtractionError):
    """빈 문서 에러"""

    pass


class ExtractedText(BaseModel):
    """
    추출된 텍스트 모델

    Attributes:
        content: 추출된 텍스트 내용
        metadata: 문서 메타데이터 (제목, 작성자, 페이지 수 등)
    """

    content: str
    metadata: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


class TextExtractionService:
    """
    텍스트 추출 서비스

    PDF 및 텍스트 파일에서 텍스트와 메타데이터를 추출합니다.
    다양한 파일 형식과 인코딩을 지원하며, 에러 처리를 통해
    안정적인 텍스트 추출을 제공합니다.

    Attributes:
        SUPPORTED_TYPES: 지원하는 파일 형식 집합
    """

    # 지원하는 파일 형식
    SUPPORTED_TYPES: set[str] = {"pdf", "txt"}

    def extract_text(self, file_path: str, file_type: str) -> ExtractedText:
        """
        파일에서 텍스트 추출

        지원하는 파일 형식(PDF, TXT)에서 텍스트와 메타데이터를 추출합니다.
        파일 존재 여부, 형식 유효성, 암호화 여부 등을 검증합니다.

        Args:
            file_path: 파일 경로 (절대 경로 또는 상대 경로)
            file_type: 파일 형식 ("pdf" 또는 "txt")

        Returns:
            ExtractedText: 추출된 텍스트와 메타데이터를 포함하는 객체

        Raises:
            ValueError: 지원하지 않는 파일 형식인 경우
            FileNotFoundError: 파일이 존재하지 않는 경우
            EncryptedPDFError: PDF가 암호화된 경우
            CorruptedFileError: 파일이 손상된 경우
            EmptyDocumentError: 문서가 비어있는 경우

        Example:
            >>> service = TextExtractionService()
            >>> result = service.extract_text("document.pdf", "pdf")
            >>> print(result.content)
            >>> print(result.metadata["page_count"])
        """
        # 파일 형식 검증
        if file_type not in self.SUPPORTED_TYPES:
            supported_formats = ", ".join(sorted(self.SUPPORTED_TYPES))
            error_msg = (
                f"지원하지 않는 파일 형식입니다: {file_type}. "
                f"지원 형식: {supported_formats}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # 파일 존재 확인
        self._validate_file_exists(file_path)

        logger.info(f"텍스트 추출 시작: {file_path} (타입: {file_type})")

        # 파일 형식에 따른 추출
        try:
            if file_type == "pdf":
                result = self._extract_pdf(file_path)
            elif file_type == "txt":
                result = self._extract_txt(file_path)
            else:
                # 이 코드는 도달하지 않음 (file_type 검증으로 인해)
                raise ValueError(f"지원하지 않는 파일 형식: {file_type}")

            logger.info(
                f"텍스트 추출 완료: {file_path} "
                f"(길이: {len(result.content)}자, "
                f"페이지/파일: {result.metadata.get('page_count', 'N/A')})"
            )
            return result

        except Exception as e:
            logger.error(f"텍스트 추출 실패: {file_path} - {str(e)}")
            raise

    def _extract_pdf(self, file_path: str) -> ExtractedText:
        """
        PDF에서 텍스트 추출

        PDF 파일의 모든 페이지에서 텍스트를 추출하고 메타데이터를 수집합니다.
        암호화된 PDF의 경우 에러를 발생시킵니다.

        Args:
            file_path: PDF 파일 경로

        Returns:
            ExtractedText: 추출된 텍스트와 메타데이터

        Raises:
            EncryptedPDFError: PDF가 암호화된 경우
            CorruptedFileError: PDF가 손상된 경우
            EmptyDocumentError: PDF가 비어있는 경우

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            extract_text() 메서드를 통해 호출됩니다.
        """
        try:
            # PDF 리더 생성
            reader = PdfReader(file_path)
            logger.debug(f"PDF 로드 완료: {len(reader.pages)}페이지")

            # 암호화 확인
            if reader.is_encrypted:
                logger.warning(f"암호화된 PDF 감지: {file_path}")
                # 암호 해제 시도
                try:
                    # 빈 비밀번호로 시도
                    if not reader.decrypt(""):
                        raise EncryptedPDFError(
                            "암호화된 PDF 파일입니다. 비밀번호가 필요합니다."
                        )
                    logger.info("PDF 암호 해제 성공 (빈 비밀번호)")
                except Exception as decrypt_error:
                    error_msg = "암호화된 PDF 파일입니다. 비밀번호가 필요합니다."
                    logger.error(error_msg)
                    raise EncryptedPDFError(error_msg) from decrypt_error

            # 모든 페이지에서 텍스트 추출
            text_parts: list[str] = []
            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                        logger.debug(f"페이지 {page_num} 추출 완료: {len(page_text)}자")
                    else:
                        logger.debug(f"페이지 {page_num}: 텍스트 없음")
                except Exception as e:
                    # 페이지 추출 실패 시 계속 진행
                    logger.warning(f"페이지 {page_num} 추출 실패: {str(e)}")
                    continue

            # 텍스트 결합
            content = "\n".join(text_parts).strip()

            # 빈 문서 확인
            if not content:
                error_msg = "PDF 문서가 비어있습니다."
                logger.warning(error_msg)
                raise EmptyDocumentError(error_msg)

            # 메타데이터 추출
            metadata: dict[str, Any] = {
                "file_type": "pdf",
                "page_count": len(reader.pages),
            }

            # PDF 메타데이터가 있는 경우 추출
            if reader.metadata:
                if "/Title" in reader.metadata:
                    metadata["title"] = reader.metadata["/Title"]
                if "/Author" in reader.metadata:
                    metadata["author"] = reader.metadata["/Author"]
                if "/Creator" in reader.metadata:
                    metadata["creator"] = reader.metadata["/Creator"]
                if "/Producer" in reader.metadata:
                    metadata["producer"] = reader.metadata["/Producer"]

                logger.debug(f"PDF 메타데이터 추출 완료: {list(metadata.keys())}")

            return ExtractedText(content=content, metadata=metadata)

        except EncryptedPDFError:
            # 암호화 에러는 그대로 전달
            raise
        except EmptyDocumentError:
            # 빈 문서 에러는 그대로 전달
            raise
        except Exception as e:
            # 그 외 에러는 손상된 파일로 처리
            error_msg = f"손상된 PDF 파일입니다: {str(e)}"
            logger.error(error_msg)
            raise CorruptedFileError(error_msg) from e

    def _extract_txt(self, file_path: str) -> ExtractedText:
        """
        텍스트 파일에서 내용 추출

        텍스트 파일을 읽고 내용을 추출합니다. UTF-8 인코딩을 우선 시도하며,
        실패 시 CP949 인코딩으로 재시도합니다.

        Args:
            file_path: 텍스트 파일 경로

        Returns:
            ExtractedText: 추출된 텍스트와 메타데이터

        Raises:
            EmptyDocumentError: 파일이 비어있는 경우
            CorruptedFileError: 파일을 읽을 수 없는 경우

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            extract_text() 메서드를 통해 호출됩니다.
        """
        path = Path(file_path)

        try:
            # 파일 읽기 (UTF-8 인코딩)
            content = path.read_text(encoding="utf-8").strip()
            encoding = "utf-8"
            logger.debug(f"텍스트 파일 읽기 완료 (UTF-8): {len(content)}자")

        except UnicodeDecodeError:
            # UTF-8 디코딩 실패 시 다른 인코딩 시도
            logger.warning(f"UTF-8 디코딩 실패, CP949 시도: {file_path}")
            try:
                content = path.read_text(encoding="cp949").strip()
                encoding = "cp949"
                logger.debug(f"텍스트 파일 읽기 완료 (CP949): {len(content)}자")
            except Exception as e:
                error_msg = f"텍스트 파일을 읽을 수 없습니다: {str(e)}"
                logger.error(error_msg)
                raise CorruptedFileError(error_msg) from e

        # 빈 문서 확인
        if not content:
            error_msg = "텍스트 파일이 비어있습니다."
            logger.warning(error_msg)
            raise EmptyDocumentError(error_msg)

        # 메타데이터 생성
        metadata: dict[str, Any] = {
            "file_type": "txt",
            "file_size": path.stat().st_size,
            "encoding": encoding,
        }

        return ExtractedText(content=content, metadata=metadata)

    def _validate_file_exists(self, file_path: str) -> None:
        """
        파일 존재 확인

        파일이 존재하고 실제 파일인지 검증합니다.

        Args:
            file_path: 검증할 파일 경로

        Raises:
            FileNotFoundError: 파일이 존재하지 않거나 파일이 아닌 경우

        Private Method:
            이 메서드는 내부 사용을 위한 것이며,
            extract_text() 메서드를 통해 호출됩니다.
        """
        path = Path(file_path)

        if not path.exists():
            error_msg = f"파일을 찾을 수 없습니다: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        if not path.is_file():
            error_msg = f"파일이 아닙니다: {file_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
