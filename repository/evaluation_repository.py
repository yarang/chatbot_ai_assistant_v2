from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from core.database import get_async_session
from models.evaluation_model import PersonaEvaluation


async def create_evaluation(
    persona_id: UUID,
    user_id: UUID,
    score: int,
    comment: Optional[str] = None
) -> PersonaEvaluation:
    """
    Persona에 대한 평가를 생성합니다.
    """
    async with get_async_session() as session:
        # 이미 평가가 존재하는지 확인
        existing = await get_user_evaluation_for_persona(persona_id, user_id)
        if existing:
            # 업데이트 로직으로 분기하거나 에러 처리. 
            # 여기서는 새로 생성하는 대신 기존 평가를 업데이트하는 방식으로 구현할 수도 있지만,
            # 요구사항에 따라 중복 방지 에러를 내거나 덮어씌울 수 있음.
            # 일단은 덮어씌우는 것으로 구현 (또는 에러).
            # Unique Constraint가 있으므로 에러가 날 것임.
            # 여기서는 덮어씌우지 않고 에러를 발생시키도록 놔두거나, 
            # 호출 측에서 먼저 확인하도록 함.
            pass

        evaluation = PersonaEvaluation(
            persona_id=persona_id,
            user_id=user_id,
            score=score,
            comment=comment
        )
        session.add(evaluation)
        await session.commit()
        await session.refresh(evaluation)
        return evaluation


async def get_persona_evaluations(persona_id: UUID) -> List[PersonaEvaluation]:
    """
    특정 Persona에 대한 모든 평가를 조회합니다.
    """
    async with get_async_session() as session:
        stmt = select(PersonaEvaluation).options(
            selectinload(PersonaEvaluation.user)
        ).where(
            PersonaEvaluation.persona_id == persona_id
        ).order_by(PersonaEvaluation.created_at.desc())
        
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_user_evaluation_for_persona(persona_id: UUID, user_id: UUID) -> Optional[PersonaEvaluation]:
    """
    특정 사용자가 특정 Persona에 대해 남긴 평가를 조회합니다.
    """
    async with get_async_session() as session:
        stmt = select(PersonaEvaluation).where(
            and_(
                PersonaEvaluation.persona_id == persona_id,
                PersonaEvaluation.user_id == user_id
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_persona_average_score(persona_id: UUID) -> Optional[float]:
    """
    특정 Persona의 평균 평점을 계산합니다.
    """
    async with get_async_session() as session:
        stmt = select(func.avg(PersonaEvaluation.score)).where(
            PersonaEvaluation.persona_id == persona_id
        )
        result = await session.execute(stmt)
        average = result.scalar()
        return float(average) if average else None
