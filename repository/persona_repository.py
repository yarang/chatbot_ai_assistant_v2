import uuid
from datetime import datetime
from typing import List, Optional, Union

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
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
            category: Persona 카테고리 (선택)
            tags: Persona 태그 목록 (선택)
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
            category=category,
            tags=tags,
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
            stmt = stmt.where(or_(Persona.user_id == user_id, Persona.is_public))

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
                or_(Persona.user_id == user_id, Persona.is_public)
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
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
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
            category: Persona 카테고리
            tags: Persona 태그 목록
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
            and_(Persona.id == persona_id, Persona.user_id == user_id)
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
        if category is not None:
            persona.category = category
        if tags is not None:
            persona.tags = tags
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
            and_(Persona.id == persona_id, Persona.user_id == user_id)
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
        stmt = select(Persona).where(Persona.is_public).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_personas(
        self,
        session: AsyncSession,
        limit: int = 50,
    ) -> List[Persona]:
        """
        모든 Persona 목록 조회 (관리자용)

        Args:
            session: AsyncSession 인스턴스
            limit: 조회할 최대 개수

        Returns:
            모든 Persona 리스트
        """
        stmt = select(Persona).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def duplicate_persona(
        self,
        session: AsyncSession,
        persona_id: Union[uuid.UUID, str],
        user_id: Union[uuid.UUID, str],
    ) -> Optional[Persona]:
        """
        Persona 복제 (소유자만 가능)

        Args:
            session: AsyncSession 인스턴스
            persona_id: 복제할 Persona ID
            user_id: 복제하는 사용자 ID (소유자만 가능)

        Returns:
            복제된 Persona 인스턴스 또는 None
        """
        if isinstance(persona_id, str):
            persona_id = uuid.UUID(persona_id)
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # 원본 Persona 조회
        stmt = select(Persona).where(
            and_(Persona.id == persona_id, Persona.user_id == user_id)
        )
        result = await session.execute(stmt)
        original = result.scalar_one_or_none()

        if not original:
            return None

        # 복제본 생성 (이름에 "(Copy)" 추가)
        copy_name = f"{original.name} (Copy)"

        # 중복 확인 후 숫자 추가
        # PERFORMANCE: Use count() instead of fetching all rows
        # This avoids loading all persona objects into memory just to count them
        check_stmt = select(func.count(Persona.id)).where(
            and_(
                Persona.user_id == user_id,
                Persona.name.like(f"{original.name} (Copy%"),
            )
        )
        check_result = await session.execute(check_stmt)
        existing_copies = check_result.scalar() or 0

        if existing_copies > 0:
            copy_name = f"{original.name} (Copy {existing_copies + 1})"

        duplicated = Persona(
            user_id=user_id,
            name=copy_name,
            content=original.content,
            description=original.description,
            category=original.category,
            tags=original.tags.copy() if original.tags else None,
            is_public=False,  # 복제본은 항상 비공개
        )
        session.add(duplicated)
        await session.flush()
        await session.refresh(duplicated)
        return duplicated

    async def bulk_delete_personas(
        self,
        session: AsyncSession,
        persona_ids: List[Union[uuid.UUID, str]],
        user_id: Union[uuid.UUID, str],
    ) -> dict:
        """
        Persona 일괄 삭제 (소유자만 가능)

        PERFORMANCE OPTIMIZATION: Uses bulk DELETE instead of sequential queries.
        Reduces N queries to 1 query for significant performance improvement.

        Args:
            session: AsyncSession 인스턴스
            persona_ids: 삭제할 Persona ID 목록
            user_id: 삭제하는 사용자 ID (소유자만 가능)

        Returns:
            삭제 결과 딕셔너리 {success: int, failed: int, errors: list}
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # Convert all persona_ids to UUID
        persona_uuids = []
        for persona_id in persona_ids:
            if isinstance(persona_id, str):
                persona_uuids.append(uuid.UUID(persona_id))
            else:
                persona_uuids.append(persona_id)

        result = {"success": 0, "failed": 0, "errors": []}

        try:
            # PERFORMANCE: Single bulk DELETE query instead of N individual queries
            # This reduces database round-trips from N to 1
            stmt = delete(Persona).where(
                and_(
                    Persona.id.in_(persona_uuids),
                    Persona.user_id == user_id,
                )
            )
            delete_result = await session.execute(stmt)
            deleted_count = delete_result.rowcount

            result["success"] = deleted_count

            # If not all personas were deleted, some were not found or not owned
            if deleted_count < len(persona_uuids):
                result["failed"] = len(persona_uuids) - deleted_count
                result["errors"].append(
                    f"{result['failed']} personas not found or permission denied"
                )

        except Exception as e:
            result["failed"] = len(persona_uuids)
            result["errors"].append(f"Bulk delete failed: {str(e)}")

        return result

    async def bulk_toggle_public(
        self,
        session: AsyncSession,
        persona_ids: List[Union[uuid.UUID, str]],
        user_id: Union[uuid.UUID, str],
        is_public: bool,
    ) -> dict:
        """
        Persona 일괄 공개/비공개 전환 (소유자만 가능)

        PERFORMANCE OPTIMIZATION: Uses bulk UPDATE instead of sequential queries.
        Reduces 2N queries (fetch + update) to 1 query for significant performance improvement.

        Args:
            session: AsyncSession 인스턴스
            persona_ids: 대상 Persona ID 목록
            user_id: 사용자 ID (소유자만 가능)
            is_public: 공개 여부

        Returns:
            결과 딕셔너리 {success: int, failed: int, errors: list}
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        # Convert all persona_ids to UUID
        persona_uuids = []
        for persona_id in persona_ids:
            if isinstance(persona_id, str):
                persona_uuids.append(uuid.UUID(persona_id))
            else:
                persona_uuids.append(persona_id)

        result = {"success": 0, "failed": 0, "errors": []}

        try:
            # PERFORMANCE: Single bulk UPDATE query instead of N individual UPDATE queries
            # This reduces database round-trips from N to 1 and avoids SELECT queries
            stmt = (
                update(Persona)
                .where(
                    and_(
                        Persona.id.in_(persona_uuids),
                        Persona.user_id == user_id,
                    )
                )
                .values(is_public=is_public)
                .returning(Persona.id)
            )
            update_result = await session.execute(stmt)
            updated_ids = update_result.scalars().all()

            result["success"] = len(updated_ids)

            # If not all personas were updated, some were not found or not owned
            if len(updated_ids) < len(persona_uuids):
                result["failed"] = len(persona_uuids) - len(updated_ids)
                result["errors"].append(
                    f"{result['failed']} personas not found or permission denied"
                )

        except Exception as e:
            result["failed"] = len(persona_uuids)
            result["errors"].append(f"Bulk update failed: {str(e)}")

        return result

    async def export_personas(
        self,
        session: AsyncSession,
        persona_ids: List[Union[uuid.UUID, str]],
        user_id: Union[uuid.UUID, str],
    ) -> List[dict]:
        """
        Persona 내보내기 (JSON 형식)

        Args:
            session: AsyncSession 인스턴스
            persona_ids: 내보낼 Persona ID 목록
            user_id: 사용자 ID (소유자 또는 공개 Persona)

        Returns:
            Persona 데이터 리스트
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        exported_data = []

        for persona_id in persona_ids:
            if isinstance(persona_id, str):
                persona_id = uuid.UUID(persona_id)

            persona = await self.get_persona_by_id(session, persona_id, user_id)
            if persona:
                exported_data.append(
                    {
                        "name": persona.name,
                        "content": persona.content,
                        "description": persona.description,
                        "category": persona.category,
                        "tags": persona.tags,
                        "is_public": persona.is_public,
                        "exported_at": datetime.now().isoformat(),
                    }
                )

        return exported_data

    async def import_personas(
        self,
        session: AsyncSession,
        personas_data: List[dict],
        user_id: Union[uuid.UUID, str],
        overwrite_names: bool = False,
    ) -> dict:
        """
        Persona 가져오기 (JSON 형식)

        Args:
            session: AsyncSession 인스턴스
            personas_data: 가져올 Persona 데이터 리스트
            user_id: 가져오는 사용자 ID
            overwrite_names: 중복 이름일 경우 덮어쓰기 여부

        Returns:
            결과 딕셔너리 {imported: int, skipped: int, errors: list}
        """
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        result = {"imported": 0, "skipped": 0, "errors": []}

        for data in personas_data:
            try:
                # 중복 이름 확인
                existing_stmt = select(Persona).where(
                    and_(Persona.user_id == user_id, Persona.name == data["name"])
                )
                existing_result = await session.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()

                if existing and not overwrite_names:
                    result["skipped"] += 1
                    continue

                # 생성 또는 업데이트
                if existing and overwrite_names:
                    await self.update_persona(
                        session,
                        existing.id,
                        user_id,
                        content=data.get("content"),
                        description=data.get("description"),
                        category=data.get("category"),
                        tags=data.get("tags"),
                        is_public=data.get("is_public", False),
                    )
                else:
                    await self.create_persona(
                        session,
                        user_id,
                        name=data["name"],
                        content=data["content"],
                        description=data.get("description"),
                        category=data.get("category"),
                        tags=data.get("tags"),
                        is_public=data.get("is_public", False),
                    )
                result["imported"] += 1

            except Exception as e:
                result["errors"].append(
                    f"Failed to import {data.get('name', 'unknown')}: {str(e)}"
                )

        return result


# 싱글톤 인스턴스
_persona_repository = PersonaRepository()


# 편의 함수들
async def create_persona(
    user_id: Union[uuid.UUID, str],
    name: str,
    content: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
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
            category=category,
            tags=tags,
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
    category: Optional[str] = None,
    tags: Optional[List[str]] = None,
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
            category=category,
            tags=tags,
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


async def get_all_personas(limit: int = 50) -> List[Persona]:
    """모든 Persona 목록 조회 (편의 함수, 관리자용)"""
    async with get_async_session() as session:
        return await _persona_repository.get_all_personas(
            session=session,
            limit=limit,
        )


async def duplicate_persona(
    persona_id: Union[uuid.UUID, str],
    user_id: Union[uuid.UUID, str],
) -> Optional[Persona]:
    """Persona 복제 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.duplicate_persona(
            session=session,
            persona_id=persona_id,
            user_id=user_id,
        )


async def bulk_delete_personas(
    persona_ids: List[Union[uuid.UUID, str]],
    user_id: Union[uuid.UUID, str],
) -> dict:
    """Persona 일괄 삭제 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.bulk_delete_personas(
            session=session,
            persona_ids=persona_ids,
            user_id=user_id,
        )


async def bulk_toggle_public(
    persona_ids: List[Union[uuid.UUID, str]],
    user_id: Union[uuid.UUID, str],
    is_public: bool,
) -> dict:
    """Persona 일괄 공개/비공개 전환 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.bulk_toggle_public(
            session=session,
            persona_ids=persona_ids,
            user_id=user_id,
            is_public=is_public,
        )


async def export_personas(
    persona_ids: List[Union[uuid.UUID, str]],
    user_id: Union[uuid.UUID, str],
) -> List[dict]:
    """Persona 내보내기 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.export_personas(
            session=session,
            persona_ids=persona_ids,
            user_id=user_id,
        )


async def import_personas(
    personas_data: List[dict],
    user_id: Union[uuid.UUID, str],
    overwrite_names: bool = False,
) -> dict:
    """Persona 가져오기 (편의 함수)"""
    async with get_async_session() as session:
        return await _persona_repository.import_personas(
            session=session,
            personas_data=personas_data,
            user_id=user_id,
            overwrite_names=overwrite_names,
        )
