from fastapi import APIRouter
from services.conversation_service import ask_question


router = APIRouter()


@router.post("/ask")
async def ask(payload: dict):
    """
    질문 및 답변 API
    
    Payload:
        - question: 질문 내용 (필수)
        - user_id: 사용자 ID (선택)
        - chat_room_id: 채팅방 ID (필수)
    """
    question = payload.get("question", "").strip()
    user_id = payload.get("user_id")
    chat_room_id = payload.get("chat_room_id")
    
    if not question:
        return {"error": "question is required"}
    
    if not chat_room_id:
        return {"error": "chat_room_id is required"}
    
    answer = await ask_question(user_id=user_id, chat_room_id=chat_room_id, question=question)
    return {"answer": answer}



