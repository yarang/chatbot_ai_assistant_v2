"""
Gemini AI Service

Google Gemini API를 사용하여 AI 답변 생성을 제공합니다.

참고: 현재는 Mock 데이터를 반환합니다.
실제 Gemini API 통합이 필요합니다.
"""

from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)


class GeminiService:
    """
    Google Gemini AI 서비스

    Attributes:
        model: Gemini GenerativeModel 인스턴스

    Raises:
        ValueError: GEMINI_API_KEY가 설정되지 않은 경우
    """

    def __init__(self):
        """GeminiService 초기화 및 API 설정"""
        settings = get_settings()
        api_key = settings.gemini.api_key
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in config")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-pro")
        logger.info("GeminiService initialized")


async def generate_answer(
    history: List[Tuple[str, str]],
    question: str,
    system_instruction: Optional[str] = None,
) -> Dict[str, Any]:
    """
    AI 답변 생성 (현재 Mock 구현)

    경고: 이 함수는 현재 Mock 데이터를 반환합니다.
    실제 Gemini API 통합이 필요합니다.

    Args:
        history: 대화 이력 [(role, message), ...]
            - role: "user" 또는 "assistant"
            - message: 메시지 내용
        question: 사용자 질문
        system_instruction: 시스템 프롬프트 (Persona 내용)

    Returns:
        Dict[str, Any]: AI 응답 정보
            - text (str): 답변 텍스트
            - model (str): 사용한 모델명
            - input_tokens (int): 입력 토큰 수 (현재 추정치)
            - output_tokens (int): 출력 토큰 수 (현재 추정치)

    Note:
        현재 구현은 Mock 데이터를 반환하며,
        토큰 수는 문자 수 기반의 대략적인 추정치입니다.

    Future Work:
        - 실제 Gemini API 호출 구현
        - system_instruction 적용
        - 정확한 토큰 수 반환 (usage_metadata)

    Example:
        >>> history = [("user", "안녕"), ("assistant", "반갑습니다")]
        >>> result = await generate_answer(history, "오늘 날씨 어때?")
        >>> print(result["text"])
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

    logger.debug(f"Generated mock answer: {len(answer_text)} chars, "
                f"tokens: in={input_tokens}, out={output_tokens}")

    return {
        "text": answer_text,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }