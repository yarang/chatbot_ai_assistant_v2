import uuid
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_async_session
from models.user_model import User


class UserRepository:
    """사용자 Repository 클래스"""

    async def upsert_user(
        self,
        session: AsyncSession,
        email: str,
        telegram_id: Optional[int] = None,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> User:
        """
        사용자 생성 또는 업데이트 (UPSERT)
        
        Args:
            session: AsyncSession 인스턴스
            email: 사용자 이메일
            telegram_id: Telegram 사용자 ID
            username: 사용자명
            first_name: 이름
            last_name: 성
            
        Returns:
            생성 또는 업데이트된 User 인스턴스
        """
        # 먼저 기존 사용자 조회 (email 또는 telegram_id로)
        existing_user = None
        if email:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
        
        if not existing_user and telegram_id:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
        
        if existing_user:
            # 기존 사용자 업데이트
            existing_user.email = email
            existing_user.telegram_id = telegram_id
            existing_user.username = username
            existing_user.first_name = first_name
            existing_user.last_name = last_name
            await session.flush()
            await session.refresh(existing_user)
            return existing_user
        else:
            # 새 사용자 생성
            new_user = User(
                email=email,
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(new_user)
            await session.flush()
            await session.refresh(new_user)
            return new_user

    async def get_user_by_id(self, session: AsyncSession, user_id: Union[uuid.UUID, str]) -> Optional[User]:
        """
        ID로 사용자 조회
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 ID (UUID 또는 UUID 문자열)
            
        Returns:
            User 인스턴스 또는 None
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await session.get(User, user_id)
        return result

    async def get_user_by_email(self, session: AsyncSession, email: str) -> Optional[User]:
        """
        이메일로 사용자 조회
        
        Args:
            session: AsyncSession 인스턴스
            email: 사용자 이메일
            
        Returns:
            User 인스턴스 또는 None
        """
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_telegram_id(self, session: AsyncSession, telegram_id: int) -> Optional[User]:
        """
        Telegram ID로 사용자 조회
        
        Args:
            session: AsyncSession 인스턴스
            telegram_id: Telegram 사용자 ID
            
        Returns:
            User 인스턴스 또는 None
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# 싱글톤 인스턴스
_user_repository = UserRepository()


async def upsert_user(
    email: str,
    telegram_id: Optional[int] = None,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> User:
    """
    사용자 생성 또는 업데이트 (편의 함수)
    
    Args:
        email: 사용자 이메일
        telegram_id: Telegram 사용자 ID
        username: 사용자명
        first_name: 이름
        last_name: 성
        
    Returns:
        생성 또는 업데이트된 User 인스턴스
    """
    async with get_async_session() as session:
        return await _user_repository.upsert_user(
            session=session,
            email=email,
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )


async def get_user_by_id(user_id: Union[uuid.UUID, str]) -> Optional[User]:
    """
    ID로 사용자 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID (UUID 또는 UUID 문자열)
        
    Returns:
        User 인스턴스 또는 None
    """
    async with get_async_session() as session:
        return await _user_repository.get_user_by_id(session, user_id)


async def get_user_by_email(email: str) -> Optional[User]:
    """
    이메일로 사용자 조회 (편의 함수)
    
    Args:
        email: 사용자 이메일
        
    Returns:
        User 인스턴스 또는 None
    """
    async with get_async_session() as session:
        return await _user_repository.get_user_by_email(session, email)
