from typing import Optional, Dict, AsyncIterator
from langchain_core.messages import HumanMessage
from google.api_core import exceptions as google_exceptions

from agent.graph import graph
from core.logger import get_logger
from core.config import get_settings
from services.streaming_helper import StreamBuffer, stream_with_buffer

logger = get_logger(__name__)

async def ask_question(user_id: Optional[str], chat_room_id: str, question: str, system_prompt: Optional[str] = None) -> str:
    """질문 처리 및 답변 생성 (LangGraph 사용).

    사용자의 질문을 받아 LangGraph 워크플로우를 통해 답변을 생성합니다.

    Args:
        user_id (str, optional): 사용자 식별자. 없을 경우 'anonymous'로 처리됩니다.
        chat_room_id (str): 대화가 이루어지는 채팅방의 고유 ID.
        question (str): 사용자가 입력한 질문 텍스트.
        system_prompt (str, optional): AI에게 부여할 시스템 페르소나 또는 지침.

    Returns:
        str: 생성된 답변 텍스트.

    Raises:
        google_exceptions.ServiceUnavailable: Google GenAI 서비스가 사용 불가능할 때 발생.
        google_exceptions.RetryError: 요청 재시도 횟수를 초과했을 때 발생.
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
        except google_exceptions.ServiceUnavailable:
            logger.warning("Google GenAI Service Unavailable")
            return "죄송합니다. 현재 AI 서버가 매우 혼잡하여 응답할 수 없습니다. 잠시 후 다시 시도해 주세요."
        except google_exceptions.RetryError:
            logger.warning("Google GenAI Retry Error")
            return "죄송합니다. 요청 처리 중 최대 재배 횟수를 초과했습니다. 잠시 후 다시 시도해 주세요."
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
    system_prompt: Optional[str] = None,
    user_name: Optional[str] = None
) -> AsyncIterator[str]:
    """질문 처리 및 스트리밍 답변 생성 (LangGraph 사용).

    사용자의 질문을 받아 LangGraph 워크플로우를 통해 답변을 스트리밍 방식으로 생성합니다.

    Args:
        user_id (str, optional): 사용자 식별자. 없을 경우 'anonymous'로 처리됩니다.
        chat_room_id (str): 대화가 이루어지는 채팅방의 고유 ID.
        question (str): 사용자가 입력한 질문 텍스트.
        system_prompt (str, optional): AI에게 부여할 시스템 페르소나 또는 지침.
        user_name (str, optional): 사용자 이름. 질문 메시지에 포함됩니다.

    Yields:
        str: 생성된 답변의 텍스트 청크(chunk).

    Raises:
        google_exceptions.ServiceUnavailable: Google GenAI 서비스가 사용 불가능할 때 발생.
        google_exceptions.RetryError: 요청 재시도 횟수를 초과했을 때 발생.
    """
    if not user_id:
        user_id = "anonymous"
    
    try:
        # Initial State
        settings = get_settings()
        initial_state = {
            "messages": [HumanMessage(content=question, name=user_name)],
            "user_id": user_id,
            "chat_room_id": chat_room_id,
            "persona_content": system_prompt,
            "model_name": settings.gemini.model_name,
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
        except google_exceptions.ServiceUnavailable:
            logger.warning("Google GenAI Service Unavailable in stream")
            yield "죄송합니다. 현재 AI 서버가 매우 혼잡하여 응답할 수 없습니다. 잠시 후 다시 시도해 주세요."
        except google_exceptions.RetryError:
            logger.warning("Google GenAI Retry Error in stream")
            yield "죄송합니다. 요청 처리 중 최대 재시도 횟수를 초과했습니다. 잠시 후 다시 시도해 주세요."
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





from core.llm import get_llm
from repository.conversation_repository import get_history

async def summarize_chat_room(chat_room_id: str, user_id: str) -> str:
    """채팅방 대화 내용을 요약합니다.

    지정된 채팅방의 최근 대화 기록을 가져와 LLM을 사용하여 요약문을 생성합니다.

    Args:
        chat_room_id (str): 요약할 채팅방의 고유 ID.
        user_id (str): 요청한 사용자의 ID.

    Returns:
        str: 생성된 대화 요약문. 만약 대화 기록이 없으면 안내 메시지를 반환합니다.
    """
    try:
        # 대화 기록 가져오기 (최근 50개)
        history = await get_history(chat_room_id, limit=50)
        
        if not history:
            return "요약할 대화 내용이 없습니다."
            
        # 대화 내용 텍스트로 변환 (오래된 순)
        conversation_text = ""
        for role, message, name, _ in history:
            conversation_text += f"{name} ({role}): {message}\n"
            
        # 요약 요청 프롬프트
        llm = get_llm("gemini-2.5-flash") # Use 2.5 flash
        
        prompt = f"""
        다음 대화 내용을 간략하게 요약해주세요. 주요 주제와 결론 위주로 정리해주세요.
        
        대화 내용:
        {conversation_text}
        
        요약:
        """
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
        
    except Exception as e:
        logger.error(f"Error summarizing chat room: {e}", exc_info=True)
        return "대화 내용을 요약하는 중 오류가 발생했습니다."
