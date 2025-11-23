import uuid
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.sql import extract

from core.database import get_async_session
from models.conversation_model import Conversation


class UsageRepository:
    """
    사용량 통계 Repository 클래스
    
    Note: 토큰 정보는 Conversation 모델에서 직접 관리됩니다.
    이 Repository는 Conversation 기반으로 통계를 집계합니다.
    """

    async def get_user_statistics(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        사용자별 사용량 통계 조회 (Conversation 기반)
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 ID (UUID 또는 UUID 문자열)
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
            
        Returns:
            통계 정보 딕셔너리:
            - total_input_tokens: 총 입력 토큰
            - total_output_tokens: 총 출력 토큰
            - total_tokens: 총 토큰 수
            - request_count: 요청 횟수 (assistant 메시지 수)
            - model_breakdown: 모델별 사용량
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        # Conversation에서 assistant 메시지만 집계 (토큰 정보가 있는 메시지)
        conditions = [
            Conversation.user_id == user_id,
            Conversation.role == "assistant",
            Conversation.input_tokens.isnot(None),
            Conversation.output_tokens.isnot(None)
        ]
        if start_date:
            conditions.append(Conversation.created_at >= start_date)
        if end_date:
            conditions.append(Conversation.created_at <= end_date)
        
        # 전체 집계
        stmt = (
            select(
                func.sum(Conversation.input_tokens).label("total_input"),
                func.sum(Conversation.output_tokens).label("total_output"),
                func.count(Conversation.id).label("request_count")
            )
            .where(and_(*conditions))
        )
        result = await session.execute(stmt)
        row = result.first()
        
        total_input = row.total_input or 0
        total_output = row.total_output or 0
        request_count = row.request_count or 0
        
        # 모델별 집계
        model_stmt = (
            select(
                Conversation.model,
                func.sum(Conversation.input_tokens).label("input_tokens"),
                func.sum(Conversation.output_tokens).label("output_tokens"),
                func.count(Conversation.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(Conversation.model)
        )
        model_result = await session.execute(model_stmt)
        model_breakdown = [
            {
                "model": row.model or "unknown",
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "total_tokens": (row.input_tokens or 0) + (row.output_tokens or 0),
                "request_count": row.count or 0,
            }
            for row in model_result.all()
        ]
        
        return {
            "user_id": user_id,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "request_count": request_count,
            "model_breakdown": model_breakdown,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }
        }

    async def get_user_daily_statistics(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        days: int = 30,
    ) -> List[Dict]:
        """
        사용자별 일별 사용량 통계 조회 (Conversation 기반)
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 ID (UUID 또는 UUID 문자열)
            days: 조회할 일수 (기본 30일)
            
        Returns:
            일별 통계 리스트
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        # Conversation에서 assistant 메시지만 집계
        stmt = (
            select(
                func.date(Conversation.created_at).label("date"),
                func.sum(Conversation.input_tokens).label("input_tokens"),
                func.sum(Conversation.output_tokens).label("output_tokens"),
                func.count(Conversation.id).label("request_count")
            )
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.role == "assistant",
                    Conversation.input_tokens.isnot(None),
                    Conversation.output_tokens.isnot(None)
                )
            )
            .group_by(func.date(Conversation.created_at))
            .order_by(func.date(Conversation.created_at).desc())
            .limit(days)
        )
        result = await session.execute(stmt)
        
        return [
            {
                "date": row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "total_tokens": (row.input_tokens or 0) + (row.output_tokens or 0),
                "request_count": row.request_count or 0,
            }
            for row in result.all()
        ]

    async def get_user_monthly_statistics(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        months: int = 12,
    ) -> List[Dict]:
        """
        사용자별 월별 사용량 통계 조회 (Conversation 기반)
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 ID (UUID 또는 UUID 문자열)
            months: 조회할 개월수 (기본 12개월)
            
        Returns:
            월별 통계 리스트
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        # Conversation에서 assistant 메시지만 집계
        stmt = (
            select(
                extract('year', Conversation.created_at).label("year"),
                extract('month', Conversation.created_at).label("month"),
                func.sum(Conversation.input_tokens).label("input_tokens"),
                func.sum(Conversation.output_tokens).label("output_tokens"),
                func.count(Conversation.id).label("request_count")
            )
            .where(
                and_(
                    Conversation.user_id == user_id,
                    Conversation.role == "assistant",
                    Conversation.input_tokens.isnot(None),
                    Conversation.output_tokens.isnot(None)
                )
            )
            .group_by(
                extract('year', Conversation.created_at),
                extract('month', Conversation.created_at)
            )
            .order_by(
                extract('year', Conversation.created_at).desc(),
                extract('month', Conversation.created_at).desc()
            )
            .limit(months)
        )
        result = await session.execute(stmt)
        
        return [
            {
                "year": int(row.year),
                "month": int(row.month),
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "total_tokens": (row.input_tokens or 0) + (row.output_tokens or 0),
                "request_count": row.request_count or 0,
            }
            for row in result.all()
        ]

    async def get_all_users_statistics(
        self,
        session: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        모든 사용자별 사용량 통계 조회 (Conversation 기반, 사용량 순으로 정렬)
        
        Args:
            session: AsyncSession 인스턴스
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
            limit: 조회할 최대 사용자 수
            
        Returns:
            사용자별 통계 리스트
        """
        conditions = [
            Conversation.role == "assistant",
            Conversation.input_tokens.isnot(None),
            Conversation.output_tokens.isnot(None)
        ]
        if start_date:
            conditions.append(Conversation.created_at >= start_date)
        if end_date:
            conditions.append(Conversation.created_at <= end_date)
        
        stmt = (
            select(
                Conversation.user_id,
                func.sum(Conversation.input_tokens).label("total_input"),
                func.sum(Conversation.output_tokens).label("total_output"),
                func.count(Conversation.id).label("request_count")
            )
            .where(and_(*conditions))
            .group_by(Conversation.user_id)
            .order_by(
                (func.sum(Conversation.input_tokens) + func.sum(Conversation.output_tokens)).desc()
            )
            .limit(limit)
        )
        result = await session.execute(stmt)
        
        return [
            {
                "user_id": row.user_id,
                "total_input_tokens": row.total_input or 0,
                "total_output_tokens": row.total_output or 0,
                "total_tokens": (row.total_input or 0) + (row.total_output or 0),
                "request_count": row.request_count or 0,
            }
            for row in result.all()
        ]

    async def get_chat_room_statistics(
        self,
        session: AsyncSession,
        chat_room_id: Union[uuid.UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        채팅방별 사용량 통계 조회 (Conversation 기반)
        
        Args:
            session: AsyncSession 인스턴스
            chat_room_id: 채팅방 ID (UUID 또는 UUID 문자열)
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
            
        Returns:
            통계 정보 딕셔너리
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(chat_room_id, str):
            chat_room_id = uuid.UUID(chat_room_id)
            
        conditions = [
            Conversation.chat_room_id == chat_room_id,
            Conversation.role == "assistant",
            Conversation.input_tokens.isnot(None),
            Conversation.output_tokens.isnot(None)
        ]
        if start_date:
            conditions.append(Conversation.created_at >= start_date)
        if end_date:
            conditions.append(Conversation.created_at <= end_date)
        
        # 전체 집계
        stmt = (
            select(
                func.sum(Conversation.input_tokens).label("total_input"),
                func.sum(Conversation.output_tokens).label("total_output"),
                func.count(Conversation.id).label("request_count")
            )
            .where(and_(*conditions))
        )
        result = await session.execute(stmt)
        row = result.first()
        
        total_input = row.total_input or 0
        total_output = row.total_output or 0
        request_count = row.request_count or 0
        
        # 모델별 집계
        model_stmt = (
            select(
                Conversation.model,
                func.sum(Conversation.input_tokens).label("input_tokens"),
                func.sum(Conversation.output_tokens).label("output_tokens"),
                func.count(Conversation.id).label("count")
            )
            .where(and_(*conditions))
            .group_by(Conversation.model)
        )
        model_result = await session.execute(model_stmt)
        model_breakdown = [
            {
                "model": row.model or "unknown",
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "total_tokens": (row.input_tokens or 0) + (row.output_tokens or 0),
                "request_count": row.count or 0,
            }
            for row in model_result.all()
        ]
        
        return {
            "chat_room_id": chat_room_id,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "request_count": request_count,
            "model_breakdown": model_breakdown,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }
        }

    async def get_user_chat_room_statistics(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        chat_room_id: Union[uuid.UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict:
        """
        특정 사용자의 특정 채팅방 사용량 통계 조회 (Conversation 기반)
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 ID (UUID 또는 UUID 문자열)
            chat_room_id: 채팅방 ID (UUID 또는 UUID 문자열)
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
            
        Returns:
            통계 정보 딕셔너리
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if isinstance(chat_room_id, str):
            chat_room_id = uuid.UUID(chat_room_id)
            
        conditions = [
            Conversation.user_id == user_id,
            Conversation.chat_room_id == chat_room_id,
            Conversation.role == "assistant",
            Conversation.input_tokens.isnot(None),
            Conversation.output_tokens.isnot(None)
        ]
        if start_date:
            conditions.append(Conversation.created_at >= start_date)
        if end_date:
            conditions.append(Conversation.created_at <= end_date)
        
        stmt = (
            select(
                func.sum(Conversation.input_tokens).label("total_input"),
                func.sum(Conversation.output_tokens).label("total_output"),
                func.count(Conversation.id).label("request_count")
            )
            .where(and_(*conditions))
        )
        result = await session.execute(stmt)
        row = result.first()
        
        total_input = row.total_input or 0
        total_output = row.total_output or 0
        request_count = row.request_count or 0
        
        return {
            "user_id": user_id,
            "chat_room_id": chat_room_id,
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "request_count": request_count,
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            }
        }

    async def get_user_chat_rooms_breakdown(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict]:
        """
        사용자의 채팅방별 사용량 분해 통계 조회 (Conversation 기반)
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 ID (UUID 또는 UUID 문자열)
            start_date: 시작 날짜 (선택)
            end_date: 종료 날짜 (선택)
            
        Returns:
            채팅방별 통계 리스트
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
            
        conditions = [
            Conversation.user_id == user_id,
            Conversation.role == "assistant",
            Conversation.input_tokens.isnot(None),
            Conversation.output_tokens.isnot(None)
        ]
        if start_date:
            conditions.append(Conversation.created_at >= start_date)
        if end_date:
            conditions.append(Conversation.created_at <= end_date)
        
        stmt = (
            select(
                Conversation.chat_room_id,
                func.sum(Conversation.input_tokens).label("input_tokens"),
                func.sum(Conversation.output_tokens).label("output_tokens"),
                func.count(Conversation.id).label("request_count")
            )
            .where(and_(*conditions))
            .group_by(Conversation.chat_room_id)
            .order_by(
                (func.sum(Conversation.input_tokens) + func.sum(Conversation.output_tokens)).desc()
            )
        )
        result = await session.execute(stmt)
        
        return [
            {
                "chat_room_id": row.chat_room_id,
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "total_tokens": (row.input_tokens or 0) + (row.output_tokens or 0),
                "request_count": row.request_count or 0,
            }
            for row in result.all()
        ]


# 싱글톤 인스턴스
_usage_repository = UsageRepository()


async def get_user_statistics(
    user_id: Union[uuid.UUID, str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict:
    """
    사용자별 사용량 통계 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        
    Returns:
        통계 정보 딕셔너리
    """
    async with get_async_session() as session:
        return await _usage_repository.get_user_statistics(
            session=session,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )


async def get_user_daily_statistics(
    user_id: Union[uuid.UUID, str],
    days: int = 30,
) -> List[Dict]:
    """
    사용자별 일별 사용량 통계 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID
        days: 조회할 일수 (기본 30일)
        
    Returns:
        일별 통계 리스트
    """
    async with get_async_session() as session:
        return await _usage_repository.get_user_daily_statistics(
            session=session,
            user_id=user_id,
            days=days,
        )


async def get_user_monthly_statistics(
    user_id: Union[uuid.UUID, str],
    months: int = 12,
) -> List[Dict]:
    """
    사용자별 월별 사용량 통계 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID
        months: 조회할 개월수 (기본 12개월)
        
    Returns:
        월별 통계 리스트
    """
    async with get_async_session() as session:
        return await _usage_repository.get_user_monthly_statistics(
            session=session,
            user_id=user_id,
            months=months,
        )


async def get_all_users_statistics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
) -> List[Dict]:
    """
    모든 사용자별 사용량 통계 조회 (편의 함수)
    
    Args:
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        limit: 조회할 최대 사용자 수
        
    Returns:
        사용자별 통계 리스트
    """
    async with get_async_session() as session:
        return await _usage_repository.get_all_users_statistics(
            session=session,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )


async def get_chat_room_statistics(
    chat_room_id: Union[uuid.UUID, str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict:
    """
    채팅방별 사용량 통계 조회 (편의 함수)
    
    Args:
        chat_room_id: 채팅방 ID
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        
    Returns:
        통계 정보 딕셔너리
    """
    async with get_async_session() as session:
        return await _usage_repository.get_chat_room_statistics(
            session=session,
            chat_room_id=chat_room_id,
            start_date=start_date,
            end_date=end_date,
        )


async def get_user_chat_room_statistics(
    user_id: Union[uuid.UUID, str],
    chat_room_id: Union[uuid.UUID, str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict:
    """
    특정 사용자의 특정 채팅방 사용량 통계 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID
        chat_room_id: 채팅방 ID
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        
    Returns:
        통계 정보 딕셔너리
    """
    async with get_async_session() as session:
        return await _usage_repository.get_user_chat_room_statistics(
            session=session,
            user_id=user_id,
            chat_room_id=chat_room_id,
            start_date=start_date,
            end_date=end_date,
        )


async def get_user_chat_rooms_breakdown(
    user_id: Union[uuid.UUID, str],
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict]:
    """
    사용자의 채팅방별 사용량 분해 통계 조회 (편의 함수)
    
    Args:
        user_id: 사용자 ID
        start_date: 시작 날짜 (선택)
        end_date: 종료 날짜 (선택)
        
    Returns:
        채팅방별 통계 리스트
    """
    async with get_async_session() as session:
        return await _usage_repository.get_user_chat_rooms_breakdown(
            session=session,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
        )
