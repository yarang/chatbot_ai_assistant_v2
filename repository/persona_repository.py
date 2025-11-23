import uuid
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from core.database import get_async_session
from models.persona_model import Persona


class PersonaRepository:
    """Persona Repository 클래스"""

    async def create_persona(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        name: str,
        content: str,
        description: Optional[str] = None,
        is_public: bool = False,
    ) -> Persona:
        """
        Persona 생성
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 생성자 User ID (UUID 또는 UUID 문자열)
            name: Persona 이름
            content: Persona 내용 (시스템 프롬프트)
            description: Persona 설명 (선택)
            is_public: 공개 여부
            
        Returns:
            생성된 Persona 인스턴스
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        persona = Persona(
            user_id=user_id,
            name=name,
            content=content,
            description=description,
            is_public=is_public,
        )
        session.add(persona)
        await session.flush()
        await session.refresh(persona)
        return persona

    async def get_persona_by_id(
        self,
        session: AsyncSession,
        persona_id: Union[uuid.UUID, str],
        user_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Optional[Persona]:
        """
        Persona 조회
        
        Args:
            session: AsyncSession 인스턴스
            persona_id: Persona ID (UUID 또는 UUID 문자열)
            user_id: 조회하는 사용자 ID (소유자 또는 공개 Persona만 조회 가능, UUID 또는 UUID 문자열)
            
        Returns:
            Persona 인스턴스 또는 None
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(persona_id, str):
            persona_id = uuid.UUID(persona_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        stmt = select(Persona).where(Persona.id == persona_id)
        
        if user_id:
            # 소유자이거나 공개 Persona만 조회 가능
            stmt = stmt.where(
                or_(
                    Persona.user_id == user_id,
                    Persona.is_public == True
                )
            )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_personas(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        include_public: bool = True,
    ) -> List[Persona]:
        """
        사용자의 Persona 목록 조회
        
        Args:
            session: AsyncSession 인스턴스
            user_id: User ID (UUID 또는 UUID 문자열)
            include_public: 공개 Persona 포함 여부
            
        Returns:
            Persona 리스트
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        conditions = [Persona.user_id == user_id]
        
        if include_public:
            stmt = select(Persona).where(
                or_(
                    Persona.user_id == user_id,
                    Persona.is_public == True
                )
            )
        else:
            stmt = select(Persona).where(and_(*conditions))
        
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_persona(
        self,
        session: AsyncSession,
        persona_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
        name: Optional[str] = None,
        content: Optional[str] = None,
        description: Optional[str] = None,
        is_public: Optional[bool] = None,
    ) -> Optional[Persona]:
        """
        Persona 수정 (소유자만 가능)
        
        Args:
            session: AsyncSession 인스턴스
            persona_id: Persona ID (UUID 또는 UUID 문자열)
            user_id: 수정하는 사용자 ID (소유자만 가능, UUID 또는 UUID 문자열)
            name: Persona 이름
            content: Persona 내용
            description: Persona 설명
            is_public: 공개 여부
            
        Returns:
            수정된 Persona 인스턴스 또는 None
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(persona_id, str):
            persona_id = uuid.UUID(persona_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        stmt = select(Persona).where(
            and_(
                Persona.id == persona_id,
                Persona.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        persona = result.scalar_one_or_none()
        
        if not persona:
            return None
        
        if name is not None:
            persona.name = name
        if content is not None:
            persona.content = content
        if description is not None:
            persona.description = description
        if is_public is not None:
            persona.is_public = is_public
        
        await session.flush()
        await session.refresh(persona)
        return persona

    async def delete_persona(
        self,
        session: AsyncSession,
        persona_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
    ) -> bool:
        """
        Persona 삭제 (소유자만 가능)
        
        Args:
            session: AsyncSession 인스턴스
            persona_id: Persona ID (UUID 또는 UUID 문자열)
            user_id: 삭제하는 사용자 ID (소유자만 가능, UUID 또는 UUID 문자열)
            
        Returns:
            삭제 성공 여부
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(persona_id, str):
            persona_id = uuid.UUID(persona_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        stmt = select(Persona).where(
            and_(
                Persona.id == persona_id,
                Persona.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        persona = result.scalar_one_or_none()
        
        if not persona:
            return False
        
        await session.delete(persona)
        await session.flush()
        return True

    async def get_public_personas(
        self,
        session: AsyncSession,
        limit: int = 50,
    ) -> List[Persona]:
        """
        공개 Persona 목록 조회
        
        Args:
            session: AsyncSession 인스턴스
            limit: 조회할 최대 개수
            
        Returns:
            공개 Persona 리스트
        """
        stmt = (
            select(Persona)
            .where(Persona.is_public == True)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


# 싱글톤 인스턴스
_persona_repository = PersonaRepository()


# 편의 함수들
async def create_persona(
    user_id: Union[uuid.UUID, str],
    name: str,
    content: str,
    description: Optional[str] = None,
    is_public: bool = False,
) -> Persona:
    """Persona 생성 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.create_persona(
            session=session,
            user_id=user_id,
            name=name,
            content=content,
            description=description,
            is_public=is_public,
        )


async def get_persona_by_id(
    persona_id: Union[uuid.UUID, str],
    user_id: Optional[Union[uuid.UUID, str]] = None,
) -> Optional[Persona]:
    """Persona 조회 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.get_persona_by_id(
            session=session,
            persona_id=persona_id,
            user_id=user_id,
        )


async def get_user_personas(
    user_id: Union[uuid.UUID, str],
    include_public: bool = True,
) -> List[Persona]:
    """사용자의 Persona 목록 조회 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.get_user_personas(
            session=session,
            user_id=user_id,
            include_public=include_public,
        )


async def update_persona(
    persona_id: Union[uuid.UUID, str],
    user_id: Union[uuid.UUID, str],
    name: Optional[str] = None,
    content: Optional[str] = None,
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> Optional[Persona]:
    """Persona 수정 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.update_persona(
            session=session,
            persona_id=persona_id,
            user_id=user_id,
            name=name,
            content=content,
            description=description,
            is_public=is_public,
        )


async def delete_persona(
    persona_id: Union[uuid.UUID, str],
    user_id: Union[uuid.UUID, str],
) -> bool:
    """Persona 삭제 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.delete_persona(
            session=session,
            persona_id=persona_id,
            user_id=user_id,
        )


async def get_public_personas(limit: int = 50) -> List[Persona]:
    """공개 Persona 목록 조회 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.get_public_personas(
            session=session,
            limit=limit,
        )

