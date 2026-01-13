#!/usr/bin/env python3
"""Zhipu AI 연결 테스트 스크립트"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.llm import get_llm
from core.logger import get_logger

logger = get_logger(__name__)

def test_zhipu_ai():
    """Zhipu AI 연결 테스트"""
    print("="*60)
    print("Zhipu AI 연결 테스트")
    print("="*60)

    try:
        # LLM 초기화
        print("\n1. LLM 초기화 중...")
        llm = get_llm()
        print(f"✅ LLM 초기화 성공")
        print(f"   모델: {llm.model}")
        print(f"   타입: {type(llm).__name__}")

        # 간단한 테스트 프롬프트
        print("\n2. 테스트 프롬프트 실행 중...")
        test_prompt = "안녕하세요? 한 글자로만 답변해주세요."
        response = llm.invoke(test_prompt)
        print(f"✅ 응답 수신 성공")
        print(f"   프롬프트: {test_prompt}")
        print(f"   응답: {response.content}")

        print("\n" + "="*60)
        print("✅ 모든 테스트 통과!")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_zhipu_ai()
    sys.exit(0 if success else 1)
