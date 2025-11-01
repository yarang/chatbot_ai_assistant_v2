from typing import Optional

from repository.conversation_repository import add_message, get_history
from repository.chat_room_repository import get_chat_room_by_id
from services.gemini_service import generate_answer


async def ask_question(user_id: Optional[str], chat_room_id: str, question: str) -> str:
    """
    질문 처리 및 답변 생성
    
    Args:
        user_id: 사용자 ID
        chat_room_id: 채팅방 ID
        question: 질문 내용
        
    Returns:
        생성된 답변
    """
    if not user_id:
        user_id = "anonymous"

    # 사용자 메시지 저장 (토큰 정보 없음)
    await add_message(user_id=user_id, chat_room_id=chat_room_id, role="user", message=question)
    
    # 채팅방 정보 조회 (Persona 포함)
    chat_room = await get_chat_room_by_id(chat_room_id)
    system_instruction = None
    if chat_room and chat_room.persona:
        system_instruction = chat_room.persona.content
    
    # 대화 이력 조회
    history = await get_history(chat_room_id=chat_room_id, limit=20)
    
    # AI 답변 생성 (토큰 정보 포함, Persona 적용)
    answer_result = await generate_answer(
        history=history, 
        question=question,
        system_instruction=system_instruction
    )
    
    # Assistant 메시지 저장 (토큰 정보 포함)
    await add_message(
        user_id=user_id,
        chat_room_id=chat_room_id,
        role="assistant",
        message=answer_result["text"],
        model=answer_result["model"],
        input_tokens=answer_result["input_tokens"],
        output_tokens=answer_result["output_tokens"]
    )
    
    return answer_result["text"]



