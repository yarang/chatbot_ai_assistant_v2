import uuid
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_async_session
from models.chat_room_model import ChatRoom


class ChatRoomRepository:
    """채팅방 Repository 클래스"""

    async def upsert_chat_room(
        self,
        session: AsyncSession,
        telegram_chat_id: int,
        name: Optional[str] = None,
        type: str = "private",
        username: Optional[str] = None,
    ) -> ChatRoom:
        """
        채팅방 생성 또는 업데이트 (UPSERT)
        
        Args:
            session: AsyncSession 인스턴스
            telegram_chat_id: Telegram 채팅 ID
            name: 채팅방 이름
            type: 채팅 타입 (private, group, supergroup, channel)
            username: 채팅방 사용자명
            
        Returns:
            생성 또는 업데이트된 ChatRoom 인스턴스
        """
        # 먼저 기존 채팅방 조회
        stmt = select(ChatRoom).where(ChatRoom.telegram_chat_id == telegram_chat_id)
        result = await session.execute(stmt)
        existing_chat_room = result.scalar_one_or_none()
        
        if existing_chat_room:
            # 기존 채팅방 업데이트
            existing_chat_room.name = name
            existing_chat_room.type = type
            existing_chat_room.username = username
            await session.flush()
            await session.refresh(existing_chat_room)
            return existing_chat_room
        else:
            # 새 채팅방 생성
            new_chat_room = ChatRoom(
                telegram_chat_id=telegram_chat_id,
                name=name,
                type=type,
                username=username,
            )
            session.add(new_chat_room)
            await session.flush()
            await session.refresh(new_chat_room)
            return new_chat_room

    async def get_chat_room_by_id(self, session: AsyncSession, chat_room_id: Union[uuid.UUID, str]) -> Optional[ChatRoom]:
        """
        ID로 채팅방 조회
        
        Args:
            session: AsyncSession 인스턴스
            chat_room_id: 채팅방 ID (UUID 또는 UUID 문자열)
            
        Returns:
            ChatRoom 인스턴스 또는 None
        """
        # 문자열인 경우 UUID로 변환
        if isinstance(chat_room_id, str):
            chat_room_id = uuid.UUID(chat_room_id)
        result = await session.get(ChatRoom, chat_room_id)
        return result

    async def get_chat_room_by_telegram_id(
        self,
        session: AsyncSession,
        telegram_chat_id: int
    ) -> Optional[ChatRoom]:
        """
        Telegram 채팅 ID로 채팅방 조회
        
        Args:
            session: AsyncSession 인스턴스
            telegram_chat_id: Telegram 채팅 ID
            
        Returns:
            ChatRoom 인스턴스 또는 None
        """
        stmt = select(ChatRoom).where(ChatRoom.telegram_chat_id == telegram_chat_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_persona(
        self,
        session: AsyncSession,
        chat_room_id: Union[uuid.UUID, str],
        persona_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Optional[ChatRoom]:
        """
        채팅방에 Persona 설정
        
        Args:
            session: AsyncSession 인스턴스
            chat_room_id: 채팅방 ID (UUID 또는 UUID 문자열)
            persona_id: Persona ID (None이면 제거, UUID 또는 UUID 문자열)
            
        Returns:
            업데이트된 ChatRoom 인스턴스 또는 None
        """
        chat_room = await self.get_chat_room_by_id(session, chat_room_id)
        if not chat_room:
            return None
        
        # 문자열인 경우 UUID로 변환
        if persona_id is not None and isinstance(persona_id, str):
            persona_id = uuid.UUID(persona_id)
        
        chat_room.persona_id = persona_id
        await session.flush()
        await session.refresh(chat_room)
        return chat_room


# 싱글톤 인스턴스
_chat_room_repository = ChatRoomRepository()


async def upsert_chat_room(
    telegram_chat_id: int,
    name: Optional[str] = None,
    type: str = "private",
    username: Optional[str] = None,
) -> ChatRoom:
    """
    채팅방 생성 또는 업데이트 (편의 함수)
    
    Args:
        telegram_chat_id: Telegram 채팅 ID
        name: 채팅방 이름
        type: 채팅 타입 (private, group, supergroup, channel)
        username: 채팅방 사용자명
        
    Returns:
        생성 또는 업데이트된 ChatRoom 인스턴스
    """
    async with get_async_session() as session:
        return await _chat_room_repository.upsert_chat_room(
            session=session,
            telegram_chat_id=telegram_chat_id,
            name=name,
            type=type,
            username=username,
        )


async def get_chat_room_by_id(chat_room_id: Union[uuid.UUID, str]) -> Optional[ChatRoom]:
    """
    ID로 채팅방 조회 (편의 함수)
    
    Args:
        chat_room_id: 채팅방 ID (UUID 또는 UUID 문자열)
        
    Returns:
        ChatRoom 인스턴스 또는 None
    """
    async with get_async_session() as session:
        return await _chat_room_repository.get_chat_room_by_id(session, chat_room_id)


async def get_chat_room_by_telegram_id(telegram_chat_id: int) -> Optional[ChatRoom]:
    """
    Telegram 채팅 ID로 채팅방 조회 (편의 함수)
    
    Args:
        telegram_chat_id: Telegram 채팅 ID
        
    Returns:
        ChatRoom 인스턴스 또는 None
    """
    async with get_async_session() as session:
        return await _chat_room_repository.get_chat_room_by_telegram_id(session, telegram_chat_id)


async def set_chat_room_persona(
    chat_room_id: Union[uuid.UUID, str],
    persona_id: Optional[Union[uuid.UUID, str]] = None,
) -> Optional[ChatRoom]:
    """
    채팅방에 Persona 설정 (편의 함수)
    
    Args:
        chat_room_id: 채팅방 ID (UUID 또는 UUID 문자열)
        persona_id: Persona ID (None이면 제거, UUID 또는 UUID 문자열)
        
    Returns:
        업데이트된 ChatRoom 인스턴스 또는 None
    """
    async with get_async_session() as session:
        return await _chat_room_repository.set_persona(
            session=session,
            chat_room_id=chat_room_id,
            persona_id=persona_id,
        )

