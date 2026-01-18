"""
FileStorageService 단위 테스트

파일 저장소 서비스의 파일 업로드, 삭제, 경로 해결 기능을 검증합니다.
"""
from unittest.mock import patch

import pytest

from services.file_storage_service import FileStorageError, FileStorageService


@pytest.fixture
def storage_service():
    """FileStorageService 인스턴스 생성"""
    return FileStorageService()


@pytest.fixture
def temp_upload_dir(tmp_path):
    """임시 업로드 디렉토리 생성"""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir


class TestFileStorageService:
    """FileStorageService 테스트 클래스"""

    @pytest.mark.asyncio
    async def test_save_file_success(self, storage_service, temp_upload_dir):
        """파일 저장 성공 테스트"""
        # Arrange
        filename = "test_document.pdf"
        content = b"Test file content"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act
            file_path = await storage_service.save_file(filename, content, chat_room_id)

            # Assert
            assert file_path is not None
            assert file_path.exists()
            assert file_path.name == filename
            assert file_path.parent.name == str(chat_room_id)
            assert file_path.read_bytes() == content

    @pytest.mark.asyncio
    async def test_save_file_with_special_characters(self, storage_service, temp_upload_dir):
        """특수 문자가 포함된 파일명 처리 테스트"""
        # Arrange
        filename = "test file with spaces & special chars!.pdf"
        content = b"Test content"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act
            file_path = await storage_service.save_file(filename, content, chat_room_id)

            # Assert
            assert file_path is not None
            assert file_path.exists()
            # 특수 문자가 제거되었는지 확인
            assert " " not in str(file_path)
            assert "&" not in str(file_path)

    @pytest.mark.asyncio
    async def test_save_file_duplicate_handling(self, storage_service, temp_upload_dir):
        """중복 파일명 처리 테스트"""
        # Arrange
        filename = "duplicate.txt"
        content1 = b"First content"
        content2 = b"Second content"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act - 첫 번째 파일 저장
            file_path1 = await storage_service.save_file(filename, content1, chat_room_id)

            # Act - 두 번째 파일 저장 (같은 이름)
            file_path2 = await storage_service.save_file(filename, content2, chat_room_id)

            # Assert
            assert file_path1 != file_path2
            assert file_path1.exists()
            assert file_path2.exists()
            assert file_path1.read_bytes() == content1
            assert file_path2.read_bytes() == content2

    @pytest.mark.asyncio
    async def test_delete_file_success(self, storage_service, temp_upload_dir):
        """파일 삭제 성공 테스트"""
        # Arrange
        filename = "to_delete.pdf"
        content = b"Content to delete"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            file_path = await storage_service.save_file(filename, content, chat_room_id)
            assert file_path.exists()

            # Act
            result = await storage_service.delete_file(file_path)

            # Assert
            assert result is True
            assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_file(self, storage_service, temp_upload_dir):
        """존재하지 않는 파일 삭제 테스트"""
        # Arrange
        nonexistent_path = temp_upload_dir / "nonexistent.pdf"

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act
            result = await storage_service.delete_file(nonexistent_path)

            # Assert
            assert result is False

    @pytest.mark.asyncio
    async def test_get_file_path(self, storage_service, temp_upload_dir):
        """파일 경로 조회 테스트"""
        # Arrange
        filename = "test_file.txt"
        chat_room_id = 67890

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act
            file_path = storage_service.get_file_path(filename, chat_room_id)

            # Assert
            expected_path = temp_upload_dir / str(chat_room_id) / filename
            assert file_path == expected_path

    @pytest.mark.asyncio
    async def test_create_chat_room_directory(self, storage_service, temp_upload_dir):
        """채팅방 디렉토리 자동 생성 테스트"""
        # Arrange
        filename = "new_room_file.txt"
        content = b"Content"
        chat_room_id = 99999

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act
            file_path = await storage_service.save_file(filename, content, chat_room_id)

            # Assert
            chat_room_dir = temp_upload_dir / str(chat_room_id)
            assert chat_room_dir.exists()
            assert chat_room_dir.is_dir()
            assert file_path.parent == chat_room_dir

    @pytest.mark.asyncio
    async def test_get_relative_path(self, storage_service, temp_upload_dir):
        """상대 경로 반환 테스트"""
        # Arrange
        filename = "relative_test.pdf"
        content = b"Content"
        chat_room_id = 11111

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            file_path = await storage_service.save_file(filename, content, chat_room_id)

            # Act
            relative_path = storage_service.get_relative_path(file_path)

            # Assert
            assert str(chat_room_id) in relative_path
            assert filename in relative_path
            assert str(temp_upload_dir) not in relative_path

    @pytest.mark.asyncio
    async def test_file_size_validation(self, storage_service, temp_upload_dir):
        """파일 크기 제한 테스트"""
        # Arrange
        filename = "large_file.pdf"
        # 51MB 파일 생성 (50MB 제한 초과)
        content = b"0" * (51 * 1024 * 1024)
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act & Assert
            with pytest.raises(FileStorageError) as exc_info:
                await storage_service.save_file(filename, content, chat_room_id)

            # 에러 메시지에 파일 크기 관련 내용이 있는지 확인
            error_msg = str(exc_info.value).lower()
            assert "52428800" in error_msg or "52428800" in error_msg or "초과" in error_msg

    @pytest.mark.asyncio
    async def test_invalid_filename(self, storage_service, temp_upload_dir):
        """잘못된 파일명 처리 테스트"""
        # Arrange
        invalid_filename = ""  # 빈 파일명
        content = b"Content"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act & Assert
            with pytest.raises(FileStorageError):
                await storage_service.save_file(invalid_filename, content, chat_room_id)

    @pytest.mark.asyncio
    async def test_get_file_stats(self, storage_service, temp_upload_dir):
        """파일 통계 정보 조회 테스트"""
        # Arrange
        filename = "stats_test.txt"
        content = b"Content for stats"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            file_path = await storage_service.save_file(filename, content, chat_room_id)

            # Act
            stats = await storage_service.get_file_stats(file_path)

            # Assert
            assert stats is not None
            assert stats["size"] == len(content)
            assert "exists" in stats
            assert stats["exists"] is True

    @pytest.mark.asyncio
    async def test_directory_traversal_prevention(self, storage_service, temp_upload_dir):
        """디렉토리 순회 공격 방지 테스트"""
        # Arrange
        malicious_filename = "../../../etc/passwd"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act & Assert
            # 경로 검증이 실패해야 함
            with pytest.raises(FileStorageError):
                storage_service.get_file_path(malicious_filename, chat_room_id)

    @pytest.mark.asyncio
    async def test_disallowed_file_extension(self, storage_service, temp_upload_dir):
        """허용되지 않은 파일 확장자 테스트"""
        # Arrange
        filename = "malicious.exe"
        content = b"Content"
        chat_room_id = 12345

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            # Act & Assert
            with pytest.raises(FileStorageError) as exc_info:
                await storage_service.save_file(filename, content, chat_room_id)

            error_msg = str(exc_info.value)
            assert "허용되지 않은 파일 형식" in error_msg

    @pytest.mark.asyncio
    async def test_invalid_chat_room_id(self, storage_service, temp_upload_dir):
        """잘못된 채팅방 ID 테스트"""
        # Arrange
        filename = "test.pdf"
        invalid_ids = [-1, 0]

        with patch.object(storage_service, '_upload_dir', temp_upload_dir):
            for invalid_id in invalid_ids:
                # Act & Assert
                with pytest.raises(FileStorageError) as exc_info:
                    storage_service.get_file_path(filename, invalid_id)

                error_msg = str(exc_info.value)
                assert "잘못된 채팅방 ID" in error_msg
