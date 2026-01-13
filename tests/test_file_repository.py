"""
FileRepository 단위 테스트

파일 메타데이터 CRUD 작업과 중복 검출 기능을 검증합니다.
"""
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File
from repository.file_repository import FileCreate, FileRepository


@pytest.fixture
async def db_session():
    """테스트 데이터베이스 세션"""
    from core.database import get_async_session
    async with get_async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def file_repository(db_session):
    """FileRepository 인스턴스"""
    return FileRepository(db_session)


class TestFileRepository:
    """FileRepository 테스트 클래스"""

    @pytest.mark.asyncio
    async def test_create_file(self, file_repository):
        """파일 생성 테스트"""
        # Arrange
        file_data = FileCreate(
            chat_room_id=12345,
            filename="test.pdf",
            file_path="/uploads/12345/test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )

        # Act
        file_obj = await file_repository.create(file_data)

        # Assert
        assert file_obj.id is not None
        assert file_obj.filename == "test.pdf"
        assert file_obj.chat_room_id == 12345
        assert file_obj.status == "processing"

    @pytest.mark.asyncio
    async def test_get_by_id(self, file_repository):
        """ID로 파일 조회 테스트"""
        # Arrange
        file_data = FileCreate(
            chat_room_id=12345,
            filename="test.pdf",
            file_path="/uploads/12345/test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )
        created_file = await file_repository.create(file_data)

        # Act
        retrieved_file = await file_repository.get_by_id(created_file.id)

        # Assert
        assert retrieved_file is not None
        assert retrieved_file.id == created_file.id
        assert retrieved_file.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_nonexistent_file(self, file_repository):
        """존재하지 않는 파일 조회 테스트"""
        # Act
        file_obj = await file_repository.get_by_id(99999)

        # Assert
        assert file_obj is None

    @pytest.mark.asyncio
    async def test_get_by_chat_room_id(self, file_repository):
        """채팅방 ID로 파일 목록 조회 테스트"""
        # Arrange
        chat_room_id = 12345
        for i in range(3):
            file_data = FileCreate(
                chat_room_id=chat_room_id,
                filename=f"file{i}.pdf",
                file_path=f"/uploads/{chat_room_id}/file{i}.pdf",
                file_size=1024 * (i + 1),
                content_type="application/pdf"
            )
            await file_repository.create(file_data)

        # Act
        files = await file_repository.get_by_chat_room_id(chat_room_id)

        # Assert
        assert len(files) == 3

    @pytest.mark.asyncio
    async def test_check_duplicate_file(self, file_repository):
        """중복 파일 확인 테스트"""
        # Arrange
        chat_room_id = 12345
        filename = "duplicate.pdf"
        file_data = FileCreate(
            chat_room_id=chat_room_id,
            filename=filename,
            file_path=f"/uploads/{chat_room_id}/{filename}",
            file_size=1024,
            content_type="application/pdf"
        )
        await file_repository.create(file_data)

        # Act
        is_duplicate = await file_repository.check_duplicate(chat_room_id, filename)

        # Assert
        assert is_duplicate is True

        # 다른 파일명으로 확인
        is_not_duplicate = await file_repository.check_duplicate(chat_room_id, "other.pdf")
        assert is_not_duplicate is False

    @pytest.mark.asyncio
    async def test_update_file_status(self, file_repository):
        """파일 상태 업데이트 테스트"""
        # Arrange
        file_data = FileCreate(
            chat_room_id=12345,
            filename="test.pdf",
            file_path="/uploads/12345/test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )
        file_obj = await file_repository.create(file_data)

        # Act
        updated_file = await file_repository.update_status(
            file_obj.id,
            "completed",
            error_message=None
        )

        # Assert
        assert updated_file.status == "completed"
        assert updated_file.error_message is None

    @pytest.mark.asyncio
    async def test_update_file_status_with_error(self, file_repository):
        """파일 상태 업데이트 (에러 포함) 테스트"""
        # Arrange
        file_data = FileCreate(
            chat_room_id=12345,
            filename="test.pdf",
            file_path="/uploads/12345/test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )
        file_obj = await file_repository.create(file_data)

        # Act
        updated_file = await file_repository.update_status(
            file_obj.id,
            "failed",
            error_message="PDF 파싱 실패"
        )

        # Assert
        assert updated_file.status == "failed"
        assert updated_file.error_message == "PDF 파싱 실패"

    @pytest.mark.asyncio
    async def test_delete_file(self, file_repository):
        """파일 삭제 테스트"""
        # Arrange
        file_data = FileCreate(
            chat_room_id=12345,
            filename="test.pdf",
            file_path="/uploads/12345/test.pdf",
            file_size=1024,
            content_type="application/pdf"
        )
        file_obj = await file_repository.create(file_data)

        # Act
        result = await file_repository.delete(file_obj.id)

        # Assert
        assert result is True
        # 삭제 확인
        deleted_file = await file_repository.get_by_id(file_obj.id)
        assert deleted_file is None
