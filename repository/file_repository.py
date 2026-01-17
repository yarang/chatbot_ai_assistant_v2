"""
파일 리포지토리

파일 메타데이터 CRUD 작업을 처리합니다.
SQL Injection 방지를 위해 SQLAlchemy ORM을 사용합니다.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.file import File


class FileCreate(BaseModel):
    """파일 생성 DTO"""

    chat_room_id: UUID = Field(..., description="채팅방 ID (UUID)")
    filename: str = Field(..., min_length=1, max_length=255, description="파일명")
    file_path: str = Field(..., min_length=1, max_length=500, description="파일 경로")
    file_size: int = Field(..., ge=0, description="파일 크기 (bytes)")
    content_type: Optional[str] = Field(None, max_length=100, description="MIME 타입")


class FileUpdate(BaseModel):
    """파일 수정 DTO"""

    status: Optional[str] = Field(None, max_length=50, description="파일 상태")
    error_message: Optional[str] = Field(None, description="에러 메시지")


class FileRepository:
    """
    파일 리포지토리

    파일 메타데이터의 CRUD 작업과 중복 검출 기능을 제공합니다.
    모든 쿼리는 SQLAlchemy ORM을 사용하여 SQL Injection을 방지합니다.
    """

    def __init__(self, session: AsyncSession):
        """
        리포지토리 초기화

        Args:
            session: SQLAlchemy 비동기 세션
        """
        self.session = session

    async def create(self, file_data: FileCreate) -> File:
        """
        파일 생성

        Args:
            file_data: 파일 생성 데이터

        Returns:
            생성된 파일 객체
        """
        db_file = File(**file_data.model_dump())
        self.session.add(db_file)
        await self.session.commit()
        await self.session.refresh(db_file)
        return db_file

    async def get_by_id(self, file_id: int) -> Optional[File]:
        """
        ID로 파일 조회

        Args:
            file_id: 파일 ID

        Returns:
            파일 객체 또는 None
        """
        result = await self.session.execute(select(File).where(File.id == file_id))
        return result.scalar_one_or_none()

    async def get_by_chat_room_id(self, chat_room_id: UUID) -> List[File]:
        """
        채팅방 ID로 파일 목록 조회

        Args:
            chat_room_id: 채팅방 ID (UUID)

        Returns:
            파일 목록
        """
        result = await self.session.execute(
            select(File)
            .where(File.chat_room_id == chat_room_id)
            .order_by(File.created_at.desc())
        )
        return list(result.scalars().all())

    async def check_duplicate(self, chat_room_id: UUID, filename: str) -> bool:
        """
        중복 파일 확인

        Args:
            chat_room_id: 채팅방 ID
            filename: 파일명

        Returns:
            중복 여부
        """
        result = await self.session.execute(
            select(File).where(
                and_(File.chat_room_id == chat_room_id, File.filename == filename)
            )
        )
        return result.scalar_one_or_none() is not None

    async def update_status(
        self, file_id: int, status: str, error_message: Optional[str] = None
    ) -> Optional[File]:
        """
        파일 상태 업데이트

        Args:
            file_id: 파일 ID
            status: 새로운 상태
            error_message: 에러 메시지 (선택)

        Returns:
            업데이트된 파일 객체 또는 None
        """
        db_file = await self.get_by_id(file_id)
        if not db_file:
            return None

        db_file.status = status
        db_file.error_message = error_message
        await self.session.commit()
        await self.session.refresh(db_file)
        return db_file

    async def delete(self, file_id: int) -> bool:
        """
        파일 삭제

        Args:
            file_id: 파일 ID

        Returns:
            삭제 성공 여부
        """
        db_file = await self.get_by_id(file_id)
        if not db_file:
            return False

        await self.session.delete(db_file)
        await self.session.commit()
        return True
