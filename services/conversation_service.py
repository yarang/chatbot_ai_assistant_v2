from typing import Optional, Dict, AsyncIterator
from langchain_core.messages import HumanMessage

from core.graph import graph
from core.logger import get_logger
from services.streaming_helper import StreamBuffer, stream_with_buffer

logger = get_logger(__name__)

async def ask_question(user_id: Optional[str], chat_room_id: str, question: str, system_prompt: Optional[str] = None) -> str:
    """
    질문 처리 및 답변 생성 (LangGraph 사용)
    
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
        
    try:
        # Initial State
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "user_id": user_id,
            "chat_room_id": chat_room_id,
            "persona_content": system_prompt
        }
        
        # Invoke Graph
        config = {"recursion_limit": 20}
        try:
            final_state = await graph.ainvoke(initial_state, config=config)
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                logger.warning(f"Rate limit exceeded: {e}")
                return "죄송합니다. API 사용량을 초과했습니다. 나중에 다시 시도해 주세요."
            raise e
        
        # Extract Response
        messages = final_state["messages"]
        last_message = messages[-1]
        
        return last_message.content
        
    except Exception as e:
        logger.error(f"Error in ask_question: {e}")
        return "죄송합니다. 오류가 발생했습니다."


async def ask_question_stream(
    user_id: Optional[str],
    chat_room_id: str,
    question: str,
    system_prompt: Optional[str] = None
) -> AsyncIterator[str]:
    """
    질문 처리 및 스트리밍 답변 생성 (LangGraph 사용)
    
    Args:
        user_id: 사용자 ID
        chat_room_id: 채팅방 ID
        question: 질문 내용
        system_prompt: 시스템 프롬프트 (선택)
        
    Yields:
        답변 텍스트 청크
    """
    if not user_id:
        user_id = "anonymous"
    
    try:
        # Initial State
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "user_id": user_id,
            "chat_room_id": chat_room_id,
            "persona_content": system_prompt,
            "next": ""
        }
        
        # Stream from graph
        buffer = StreamBuffer(time_threshold_sec=0.5, char_threshold=50)
        # Stream from graph

        config = {"recursion_limit": 20}
        
        try:
            stream = graph.astream(initial_state, config=config, stream_mode="updates")
            
            async for chunk in stream_with_buffer(stream, buffer):
                yield chunk
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                logger.warning(f"Rate limit exceeded in stream: {e}")
                yield "죄송합니다. API 사용량을 초과했습니다. 나중에 다시 시도해 주세요."
            else:
                logger.error(f"Error in stream: {e}")
                yield "죄송합니다. 오류가 발생했습니다."
            
    except Exception as e:
        logger.error(f"Error in ask_question_stream: {e}")
        yield "죄송합니다. 오류가 발생했습니다."




