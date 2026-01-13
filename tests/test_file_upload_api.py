"""
FastAPI 파일 업로드 엔드포인트 통합 테스트

TASK-009: FastAPI 파일 업로드 엔드포인트 구현
POST /api/chat-rooms/{chat_room_id}/files 엔드포인트 테스트
"""
import asyncio
import io
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_async_session
from main import create_app


@pytest.fixture
async def app():
    """FastAPI 앱 인스턴스 생성"""
    return create_app()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션"""
    from core.database import get_async_session_maker

    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def async_client(app, db_session) -> AsyncGenerator[AsyncClient, None]:
    """비동기 HTTP 테스트 클라이언트"""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_content():
    """샘플 PDF 파일 내용"""
    # 작은 PDF 파일 바이너리 (실제 PDF 헤더)
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 0\n/Kids []\n>>\nendobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\ntrailer\n<<\n/Size 3\n/Root 1 0 R\n>>\nstartxref\n110\n%%EOF"


@pytest.fixture
def sample_txt_content():
    """샘플 텍스트 파일 내용"""
    return b"This is a sample text file for testing file upload functionality."


@pytest.fixture
def large_file_content():
    """50MB 초과 대용량 파일 내용"""
    # 51MB 생성
    return b"x" * (51 * 1024 * 1024)


@pytest.fixture
def mock_chat_room():
    """Mock 채팅방 객체"""
    mock_room = MagicMock()
    mock_room.id = 1
    mock_room.telegram_chat_id = 1
    return mock_room


class TestFileUploadSuccess:
    """파일 업로드 성공 시나리오 테스트"""

    @pytest.mark.asyncio
    async def test_upload_pdf_file_success(
        self, async_client: AsyncClient, sample_pdf_content, mock_chat_room
    ):
        """PDF 파일 업로드 성공 테스트"""
        # Given: 유효한 PDF 파일과 chat_room_id
        chat_room_id = 1
        files = {
            "file": ("document.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }

        # Mock services
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ), patch(
            "api.file_upload_router.FileRepository.check_duplicate",
            return_value=False,
        ), patch(
            "api.file_upload_router.FileRepository.create",
            return_value=MagicMock(
                id=1,
                filename="document.pdf",
                file_size=len(sample_pdf_content),
                content_type="application/pdf",
                status="processing",
                chat_room_id=chat_room_id,
                created_at=datetime.now(timezone.utc),
            ),
        ), patch(
            "api.file_upload_router.FileStorageService.save_file",
            return_value=MagicMock(
                name="document.pdf", exists=lambda: True,
            ),
        ), patch("api.file_upload_router.BackgroundTaskService"), patch(
            "asyncio.create_task"
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 성공 응답 검증
            assert response.status_code == 200
            data = response.json()
            assert data["file_id"] == 1
            assert data["file_name"] == "document.pdf"
            assert data["file_size"] == len(sample_pdf_content)
            assert data["content_type"] == "application/pdf"
            assert data["status"] == "processing"
            assert "uploaded_at" in data

    @pytest.mark.asyncio
    async def test_upload_txt_file_success(
        self, async_client: AsyncClient, sample_txt_content, mock_chat_room
    ):
        """텍스트 파일 업로드 성공 테스트"""
        # Given: 유효한 텍스트 파일과 chat_room_id
        chat_room_id = 1
        files = {
            "file": ("notes.txt", io.BytesIO(sample_txt_content), "text/plain")
        }

        # Mock services
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ), patch(
            "api.file_upload_router.FileRepository.check_duplicate",
            return_value=False,
        ), patch(
            "api.file_upload_router.FileRepository.create",
            return_value=MagicMock(
                id=2,
                filename="notes.txt",
                file_size=len(sample_txt_content),
                content_type="text/plain",
                status="processing",
                chat_room_id=chat_room_id,
                created_at=datetime.now(timezone.utc),
            ),
        ), patch(
            "api.file_upload_router.FileStorageService.save_file",
            return_value=MagicMock(
                name="notes.txt", exists=lambda: True,
            ),
        ), patch("api.file_upload_router.BackgroundTaskService"), patch(
            "asyncio.create_task"
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 성공 응답 검증
            assert response.status_code == 200
            data = response.json()
            assert data["file_id"] == 2
            assert data["file_name"] == "notes.txt"
            assert data["content_type"] == "text/plain"


class TestFileUploadValidation:
    """파일 업로드 유효성 검사 테스트"""

    @pytest.mark.asyncio
    async def test_upload_file_exceeds_size_limit(
        self, async_client: AsyncClient, large_file_content, mock_chat_room
    ):
        """파일 크기 초과 에러 테스트 (50MB 제한)"""
        # Given: 50MB 초과 파일
        chat_room_id = 1
        files = {
            "file": (
                "large.pdf",
                io.BytesIO(large_file_content),
                "application/pdf",
            )
        }

        # Mock chat room only (file storage will fail size check)
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 400 Bad Request 응답
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(
        self, async_client: AsyncClient, mock_chat_room
    ):
        """잘못된 파일 타입 업로드 에러 테스트"""
        # Given: 허용되지 않은 파일 타입
        chat_room_id = 1
        files = {
            "file": (
                "malicious.exe",
                io.BytesIO(b"fake executable content"),
                "application/x-executable",
            )
        }

        # Mock chat room only (file storage will fail type check)
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 400 Bad Request 응답
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_upload_empty_file(
        self, async_client: AsyncClient, mock_chat_room
    ):
        """빈 파일 업로드 에러 테스트"""
        # Given: 빈 파일
        chat_room_id = 1
        files = {
            "file": ("empty.pdf", io.BytesIO(b""), "application/pdf")
        }

        # Mock chat room only
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 400 Bad Request 응답
            assert response.status_code == 400
            data = response.json()
            assert "detail" in data


class TestFileUploadDuplicateDetection:
    """파일 중복 업로드 감지 테스트"""

    @pytest.mark.asyncio
    async def test_upload_duplicate_file_409_conflict(
        self, async_client: AsyncClient, sample_pdf_content, mock_chat_room
    ):
        """중복 파일 업로드 시 409 Conflict 응답 테스트"""
        # Given: 이미 존재하는 파일
        chat_room_id = 1
        files = {
            "file": ("document.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }

        # Mock: 중복 파일 반환
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ), patch(
            "api.file_upload_router.FileRepository.check_duplicate",
            return_value=True,
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 409 Conflict 응답
            assert response.status_code == 409
            data = response.json()
            assert "detail" in data


class TestFileUploadBackgroundTask:
    """백그라운드 태스크 트리거 테스트"""

    @pytest.mark.asyncio
    async def test_background_task_triggered_on_upload(
        self, async_client: AsyncClient, sample_pdf_content, mock_chat_room
    ):
        """파일 업로드 후 백그라운드 태스크 트리거 확인 테스트"""
        # Given: 유효한 PDF 파일
        chat_room_id = 1
        files = {
            "file": ("document.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }

        # Mock: 백그라운드 태스크 실행 확인
        mock_create_task = MagicMock()

        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ), patch(
            "api.file_upload_router.FileRepository.check_duplicate",
            return_value=False,
        ), patch(
            "api.file_upload_router.FileRepository.create",
            return_value=MagicMock(
                id=1,
                filename="document.pdf",
                file_size=len(sample_pdf_content),
                content_type="application/pdf",
                status="processing",
                chat_room_id=chat_room_id,
                created_at=datetime.now(timezone.utc),
            ),
        ), patch(
            "api.file_upload_router.FileStorageService.save_file",
            return_value=MagicMock(
                name="document.pdf", exists=lambda: True,
            ),
        ), patch("api.file_upload_router.BackgroundTaskService"), patch(
            "asyncio.create_task",
            mock_create_task
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 성공 응답과 백그라운드 태스크 생성 확인
            assert response.status_code == 200
            assert mock_create_task.called


class TestFileUploadErrorHandling:
    """파일 업로드 에러 처리 테스트"""

    @pytest.mark.asyncio
    async def test_chat_room_not_found_404(
        self, async_client: AsyncClient, sample_pdf_content
    ):
        """존재하지 않는 채팅방 ID로 업로드 시 404 응답 테스트"""
        # Given: 존재하지 않는 chat_room_id
        chat_room_id = 99999
        files = {
            "file": ("document.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }

        # Mock: 채팅방 미존재
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=None,
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 404 Not Found 응답
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    @pytest.mark.asyncio
    async def test_upload_file_without_file_field(
        self, async_client: AsyncClient
    ):
        """file 필드 없이 업로드 시도 테스트"""
        # Given: file 필드 없는 요청
        chat_room_id = 1

        # When: 파일 없이 업로드 요청
        response = await async_client.post(
            f"/api/chat-rooms/{chat_room_id}/files", data={}
        )

        # Then: 422 Unprocessable Entity 응답
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_upload_file_internal_error_500(
        self, async_client: AsyncClient, sample_pdf_content
    ):
        """서버 내부 에러 발생 시 500 응답 테스트"""
        # Given: 유효한 파일
        chat_room_id = 1
        files = {
            "file": ("document.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }

        # Mock: 서비스 에러 발생
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            side_effect=Exception("Database connection failed"),
        ):
            # When: 파일 업로드 요청
            response = await async_client.post(
                f"/api/chat-rooms/{chat_room_id}/files", files=files
            )

            # Then: 500 Internal Server Error 응답
            assert response.status_code == 500


class TestFileUploadConcurrent:
    """동시 파일 업로드 테스트"""

    @pytest.mark.asyncio
    async def test_concurrent_file_uploads(
        self, async_client: AsyncClient, sample_pdf_content, mock_chat_room
    ):
        """동시 파일 업로드 처리 테스트"""
        # Given: 동일 파일 업로드 요청 2개
        chat_room_id = 1
        files = {
            "file": ("document.pdf", io.BytesIO(sample_pdf_content), "application/pdf")
        }

        # Mock: 첫 번째 요청 성공, 두 번째 요청 중복 감지
        with patch(
            "api.file_upload_router.ChatRoomRepository.get_chat_room_by_telegram_id",
            return_value=mock_chat_room,
        ), patch(
            "api.file_upload_router.FileRepository.check_duplicate",
            side_effect=[False, True],  # 첫 번째는 중복 아님, 두 번째는 중복
        ), patch(
            "api.file_upload_router.FileRepository.create",
            return_value=MagicMock(
                id=1,
                filename="document.pdf",
                file_size=len(sample_pdf_content),
                content_type="application/pdf",
                status="processing",
                chat_room_id=chat_room_id,
                created_at=datetime.now(timezone.utc),
            ),
        ), patch(
            "api.file_upload_router.FileStorageService.save_file",
            return_value=MagicMock(
                name="document.pdf", exists=lambda: True,
            ),
        ), patch("api.file_upload_router.BackgroundTaskService"), patch(
            "asyncio.create_task"
        ):
            # When: 동시에 파일 업로드 요청
            responses = await asyncio.gather(
                async_client.post(f"/api/chat-rooms/{chat_room_id}/files", files=files),
                async_client.post(f"/api/chat-rooms/{chat_room_id}/files", files=files),
            )

            # Then: 하나는 성공(200), 하나는 중복(409)
            status_codes = [r.status_code for r in responses]
            assert 200 in status_codes
            assert 409 in status_codes
