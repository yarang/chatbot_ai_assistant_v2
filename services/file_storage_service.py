"""
파일 저장소 서비스

파일 업로드, 삭제, 경로 해결 기능을 제공합니다.
채팅방별로 파일을 격리하여 저장합니다.
"""
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional


class FileStorageError(Exception):
    """파일 저장소 관련 에러"""
    pass


class FileStorageService:
    """
    파일 저장소 서비스

    채팅방 ID를 기준으로 파일을 격리 저장하고,
    파일 중복 처리, 특수 문자 제거 등의 기능을 제공합니다.
    """

    # 최대 파일 크기 (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # 허용된 파일 타입 (화이트리스트)
    ALLOWED_CONTENT_TYPES = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
        "text/csv",
        "text/markdown",
        "application/json",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    }

    # 허용된 파일 확장자
    ALLOWED_EXTENSIONS = {
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".csv", ".md", ".json",
        ".jpg", ".jpeg", ".png", ".gif", ".webp"
    }

    def __init__(self):
        """서비스 초기화"""
        # 프로젝트 루트 디렉토리 기준으로 업로드 디렉토리 설정
        project_root = Path(__file__).parent.parent
        self._upload_dir = project_root / "uploads"

        # 업로드 디렉토리가 없으면 생성
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        """
        파일명에서 특수 문자 제거

        Args:
            filename: 원본 파일명

        Returns:
            정제된 파일명

        Raises:
            FileStorageError: 파일명이 유효하지 않은 경우
        """
        if not filename:
            raise FileStorageError("파일명은 비어있을 수 없습니다")

        # 파일명과 확장자 분리
        name, ext = os.path.splitext(filename)

        # 확장자 검증 (화이트리스트)
        if ext.lower() not in self.ALLOWED_EXTENSIONS:
            raise FileStorageError(
                f"허용되지 않은 파일 형식입니다: {ext}. "
                f"허용된 형식: {', '.join(self.ALLOWED_EXTENSIONS)}"
            )

        # 알파벳, 숫자, 한글, 언더스코어, 하이픈만 유지
        # 공백은 언더스코어로 변환
        sanitized = re.sub(r'[^\w\uAC00-\uD7A3\s-]', '', name)
        sanitized = re.sub(r'\s+', '_', sanitized)

        # 빈 문자열인 경우 기본 이름 사용
        if not sanitized:
            sanitized = "unnamed"

        return f"{sanitized}{ext}"

    def _validate_path_security(self, file_path: Path) -> None:
        """
        경로 보안 검증 (directory traversal 방지)

        Args:
            file_path: 검증할 파일 경로

        Raises:
            FileStorageError: 경로가 안전하지 않은 경우
        """
        try:
            # 절대 경로로 변환하여 확인
            resolved_path = file_path.resolve()
            resolved_upload_dir = self._upload_dir.resolve()

            # 경로가 업로드 디렉토리 내부에 있는지 확인
            resolved_path.relative_to(resolved_upload_dir)
        except ValueError:
            raise FileStorageError(
                "잘못된 파일 경로입니다: 경로가 업로드 디렉토리를 벗어납니다"
            )

    def _validate_content_type(self, content_type: Optional[str]) -> None:
        """
        Content-Type 검증

        Args:
            content_type: MIME 타입

        Raises:
            FileStorageError: Content-Type이 허용되지 않은 경우
        """
        if content_type and content_type not in self.ALLOWED_CONTENT_TYPES:
            raise FileStorageError(
                f"허용되지 않은 Content-Type입니다: {content_type}. "
                f"허용된 타입: {', '.join(self.ALLOWED_CONTENT_TYPES)}"
            )

    def _validate_chat_room_id(self, chat_room_id: int) -> None:
        """
        채팅방 ID 검증

        Args:
            chat_room_id: 채팅방 ID

        Raises:
            FileStorageError: ID가 유효하지 않은 경우
        """
        if not isinstance(chat_room_id, int) or chat_room_id <= 0:
            raise FileStorageError(
                f"잘못된 채팅방 ID입니다: {chat_room_id}. "
                "양의 정수여야 합니다."
            )

    def _generate_unique_filename(self, filepath: Path) -> Path:
        """
        중복 파일명 처리를 위한 고유 이름 생성

        Args:
            filepath: 원본 파일 경로

        Returns:
            고유한 파일 경로
        """
        if not filepath.exists():
            return filepath

        # 파일명과 확장자 분리
        name, ext = os.path.splitext(filepath.name)
        parent = filepath.parent

        # 중복 방지를 위한 카운터
        counter = 1
        while True:
            new_name = f"{name}_{counter}{ext}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def get_file_path(self, filename: str, chat_room_id: int) -> Path:
        """
        채팅방 ID를 기준으로 파일 경로 생성

        Args:
            filename: 파일명
            chat_room_id: 채팅방 ID

        Returns:
            파일의 전체 경로

        Raises:
            FileStorageError: 파일명이나 ID가 유효하지 않은 경우
        """
        # 입력 검증
        self._validate_chat_room_id(chat_room_id)

        if not filename:
            raise FileStorageError("파일명은 비어있을 수 없습니다")

        # 채팅방별 디렉토리 경로
        chat_room_dir = self._upload_dir / str(chat_room_id)

        # 정제된 파일명 (확장자 검증 포함)
        sanitized_filename = self._sanitize_filename(filename)

        file_path = chat_room_dir / sanitized_filename

        # 경로 보안 검증
        self._validate_path_security(file_path)

        return file_path

    async def save_file(
        self,
        filename: str,
        content: bytes,
        chat_room_id: int,
        content_type: Optional[str] = None
    ) -> Path:
        """
        파일 저장

        Args:
            filename: 파일명
            content: 파일 내용
            chat_room_id: 채팅방 ID
            content_type: MIME 타입 (선택)

        Returns:
            저장된 파일의 경로

        Raises:
            FileStorageError: 파일 저장 실패 시
        """
        # 입력 검증
        if not filename:
            raise FileStorageError("파일명은 비어있을 수 없습니다")

        if not content:
            raise FileStorageError("파일 내용은 비어있을 수 없습니다")

        # Content-Type 검증
        self._validate_content_type(content_type)

        # 파일 크기 확인
        file_size = len(content)
        if file_size > self.MAX_FILE_SIZE:
            raise FileStorageError(
                f"파일 크기가 제한을 초과했습니다: "
                f"{file_size} bytes (최대 {self.MAX_FILE_SIZE} bytes)"
            )

        # 파일 경로 생성 (입력 검증 포함)
        file_path = self.get_file_path(filename, chat_room_id)

        # 중복 처리
        file_path = self._generate_unique_filename(file_path)

        # 디렉토리 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 비동기 파일 쓰기
        try:
            # Python 3.12+에서는 aiofiles 사용 권장
            import aiofiles  # type: ignore
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
        except ImportError:
            # 폴백: 동기 파일 쓰기
            with open(file_path, 'wb') as f:
                f.write(content)

        return file_path

    async def delete_file(self, file_path: Path) -> bool:
        """
        파일 삭제

        Args:
            file_path: 삭제할 파일 경로

        Returns:
            삭제 성공 여부
        """
        if not file_path or not file_path.exists():
            return False

        try:
            # 경로 보안 검증 (업로드 디렉토리 내부인지 확인)
            self._validate_path_security(file_path)

            # 삭제
            file_path.unlink()

            # 빈 디렉토리 정리 (선택적)
            parent_dir = file_path.parent
            if parent_dir != self._upload_dir and not any(parent_dir.iterdir()):
                parent_dir.rmdir()

            return True
        except (ValueError, OSError, FileStorageError):
            # 경로가 업로드 디렉토리 외부이거나 삭제 실패
            return False

    def get_relative_path(self, file_path: Path) -> str:
        """
        업로드 디렉토리 기준 상대 경로 반환

        Args:
            file_path: 파일의 전체 경로

        Returns:
            상대 경로 문자열

        Raises:
            FileStorageError: 경로가 업로드 디렉토리 외부인 경우
        """
        try:
            # 경로 보안 검증
            self._validate_path_security(file_path)
            return str(file_path.relative_to(self._upload_dir))
        except ValueError:
            # 경로가 업로드 디렉토리 외부인 경우
            raise FileStorageError(
                "잘못된 파일 경로입니다: 경로가 업로드 디렉토리를 벗어납니다"
            )

    async def get_file_stats(self, file_path: Path) -> Dict[str, Any]:
        """
        파일 통계 정보 조회

        Args:
            file_path: 파일 경로

        Returns:
            파일 통계 정보 딕셔너리
        """
        if not file_path or not file_path.exists():
            return {
                "exists": False,
                "size": 0,
                "path": str(file_path) if file_path else None
            }

        stat = file_path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "path": str(file_path)
        }
