from typing import List, Tuple, Dict, Optional
import google.generativeai as genai
from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)

class GeminiService:
    def __init__(self):
        settings = get_settings()
        api_key = settings.gemini.api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in config")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        

async def generate_answer(
    history: List[Tuple[str, str]], 
    question: str,
    system_instruction: Optional[str] = None
) -> Dict[str, any]:
    """
    AI 답변 생성
    
    Args:
        history: 대화 이력 [(role, message), ...]
        question: 질문 내용
        system_instruction: 시스템 프롬프트 (Persona 내용)
        
    Returns:
        {
            "text": 답변 텍스트,
            "model": 사용한 모델,
            "input_tokens": 입력 토큰 수,
            "output_tokens": 출력 토큰 수
        }
    """
    # Placeholder for Gemini API integration. Keeps interface ready.
    settings = get_settings()
    model = settings.gemini.model_name
    # For now, echo a simple deterministic response for local testing
    context = "\n".join([f"{role}: {msg}" for role, msg in history[-6:]])
    
    # TODO: 실제 Gemini API 호출 시 system_instruction을 적용하고 토큰 정보를 받아서 반환
    # 현재는 Mock 데이터
    persona_info = f"[Persona: {system_instruction}]\n" if system_instruction else ""
    answer_text = f"{persona_info}[model={model}] 답변: {question}\n(문맥: {context})"
    
    # Mock 토큰 계산 (실제로는 API 응답에서 받아야 함)
    # 간단한 추정: 대략적으로 문자 수 기반
    input_tokens = len(question) + len(context) // 4
    if system_instruction:
        input_tokens += len(system_instruction) // 4
    output_tokens = len(answer_text) // 4  # 대략적인 추정
    
    return {
        "text": answer_text,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens
    }



