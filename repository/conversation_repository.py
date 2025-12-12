import uuid
from typing import List, Tuple, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from core.database import get_async_session
from models.conversation_model import Conversation
from models.user_model import User


class ConversationRepository:
    """대화 Repository 클래스"""

    async def add_message(
        self,
        session: AsyncSession,
        user_id: Union[uuid.UUID, str],
        chat_room_id: Union[uuid.UUID, str],
        role: str,
        message: str,
        model: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> Conversation:
        """
        메시지 추가
        
        Args:
            session: AsyncSession 인스턴스
            user_id: 사용자 식별자 (UUID 또는 UUID 문자열)
            chat_room_id: 채팅방 식별자 (UUID 또는 UUID 문자열)
            role: 역할 (user/assistant)
            message: 메시지 내용
            model: 사용한 AI 모델 (assistant 메시지의 경우)
            input_tokens: 입력 토큰 수 (assistant 메시지의 경우)
            output_tokens: 출력 토큰 수 (assistant 메시지의 경우)
            
        Returns:
            생성된 Conversation 인스턴스
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if isinstance(chat_room_id, str):
            chat_room_id = uuid.UUID(chat_room_id)
            
        conversation = Conversation(
            user_id=user_id,
            chat_room_id=chat_room_id,
            role=role,
            message=message,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        session.add(conversation)
        await session.flush()
        await session.refresh(conversation)
        return conversation

    async def get_history(
        self,
        session: AsyncSession,
        chat_room_id: Union[uuid.UUID, str],
        limit: int = 20,
    ) -> List[Tuple[str, str, str]]:
        """
        채팅방의 대화 이력 조회
        
        Args:
            session: AsyncSession 인스턴스
            chat_room_id: 채팅방 식별자 (UUID 또는 UUID 문자열)
            limit: 조회할 최대 개수
            
        Returns:
            (role, message) 튜플 리스트
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(chat_room_id, str):
            chat_room_id = uuid.UUID(chat_room_id)
            
        stmt = (
            select(
                Conversation.role, 
                Conversation.message,
                User.first_name,
                User.username
            )
            .join(User, Conversation.user_id == User.id)
            .where(Conversation.chat_room_id == chat_room_id)
            .order_by(desc(Conversation.created_at))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        rows = result.all()
        
        # 역순으로 반환 (오래된 것부터)
        history = []
        for row in reversed(rows):
            role = row.role
            message = row.message
            # Determine name: first_name > username > "Unknown"
            name = row.first_name or row.username or "Unknown"
            history.append((role, message, name))
            
        return history


# 싱글톤 인스턴스
_conversation_repository = ConversationRepository()


async def add_message(
    user_id: Union[uuid.UUID, str],
    chat_room_id: Union[uuid.UUID, str],
    role: str,
    message: str,
    model: Optional[str] = None,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
) -> None:
    """
    메시지 추가 (편의 함수)
    
    Args:
        user_id: 사용자 식별자 (UUID 또는 UUID 문자열)
        chat_room_id: 채팅방 식별자 (UUID 또는 UUID 문자열)
        role: 역할 (user/assistant)
        message: 메시지 내용
        model: 사용한 AI 모델 (assistant 메시지의 경우)
        input_tokens: 입력 토큰 수 (assistant 메시지의 경우)
        output_tokens: 출력 토큰 수 (assistant 메시지의 경우)
    """
    async with get_async_session() as session:
        await _conversation_repository.add_message(
            session=session,
            user_id=user_id,
            chat_room_id=chat_room_id,
            role=role,
            message=message,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


async def get_history(chat_room_id: Union[uuid.UUID, str], limit: int = 20) -> List[Tuple[str, str, str]]:
    """
    채팅방의 대화 이력 조회 (편의 함수)
    
    Args:
        chat_room_id: 채팅방 식별자 (UUID 또는 UUID 문자열)
        limit: 조회할 최대 개수
        
    Returns:
        (role, message) 튜플 리스트
    """
    async with get_async_session() as session:
        return await _conversation_repository.get_history(
            session=session,
            chat_room_id=chat_room_id,
            limit=limit,
        )
