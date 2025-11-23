from typing import Optional, Dict

from core.database import get_async_session
from repository.conversation_repository import ConversationRepository
from repository.chat_room_repository import ChatRoomRepository
from services.gemini_service import generate_answer


async def ask_question(user_id: Optional[str], chat_room_id: str, question: str, system_prompt: Optional[str] = None) -> str:
    """
    질문 처리 및 답변 생성
    
    Args:
        user_id: 사용자 ID
        chat_room_id: 채팅방 ID
        question: 질문 내용
        system_prompt: 시스템 프롬프트 (선택)
        
    Returns:
        생성된 답변
    """
    if not user_id:
        user_id = "anonymous"
        
    conv_repo = ConversationRepository()
    chat_room_repo = ChatRoomRepository()
    
    async with get_async_session() as session:
        # 사용자 메시지 저장 (토큰 정보 없음)
        await conv_repo.add_message(
            session,
            user_id=user_id, 
            chat_room_id=chat_room_id, 
            role="user", 
            message=question
        )
        
        # 채팅방 정보 조회 (Persona 포함)
        chat_room = await chat_room_repo.get_chat_room_by_id(session, chat_room_id)
        system_instruction = system_prompt
        if not system_instruction and chat_room and chat_room.persona:
            system_instruction = chat_room.persona.content
        
        # 대화 이력 조회
        history = await conv_repo.get_history(session, chat_room_id=chat_room_id, limit=20)
        
        # AI 답변 생성 (토큰 정보 포함, Persona 적용)
        answer_result = await generate_answer(
            history=history, 
            question=question,
            system_instruction=system_instruction
        )
        
        # Assistant 메시지 저장 (토큰 정보 포함)
        await conv_repo.add_message(
            session,
            user_id=user_id,
            chat_room_id=chat_room_id,
            role="assistant",
            message=answer_result["text"],
            model=answer_result["model"],
            input_tokens=answer_result["input_tokens"],
            output_tokens=answer_result["output_tokens"]
        )
        
        return answer_result["text"]




