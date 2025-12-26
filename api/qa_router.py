from fastapi import APIRouter
from services.conversation_service import ask_question


router = APIRouter()


@router.post("/ask")
async def ask(payload: dict):
    """Answers a question using the RAG-based assistant.

    This endpoint delegates the question to the conversational AI service, 
    which may use internal knowledge, web search, or memory to generate an answer.

    Args:
        payload (dict):
            - question (str): The user's question. (Required)
            - user_id (str, optional): The user's ID.
            - chat_room_id (str): The chat room ID. (Required)

    Returns:
        dict: A dictionary containing the "answer" key with the generated response.
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



