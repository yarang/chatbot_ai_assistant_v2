# Token Usage Tracking Implementation

## 코드베이스 검토 및 분석
- [x] 현재 데이터베이스 스키마 검토
- [x] LLM 호출 지점 파악
- [x] 토큰 사용량 추적 로직 위치 확인
- [x] 대화 저장 프로세스 이해

## 기존 시스템 분석
- [x] conversations 테이블의 token 필드 확인 (이미 존재)
- [x] LangChain/LangGraph의 토큰 콜백 메커니즘 조사 (usage_metadata)
- [x] 현재 Gemini 서비스 구현 검토

## 구현 계획 작성
- [x] 토큰 사용량 추적 방법 설계
- [x] 필요한 코드 수정 사항 계획
- [x] 데이터베이스 스키마 변경 필요 여부 확인 (변경 불필요)

## 구현
- [x] ChatState에 토큰 정보 필드 추가
- [x] supervisor_node에서 토큰 추적
- [x] researcher_node에서 토큰 추적
- [x] general_assistant_node에서 토큰 추적
- [x] save_conversation_node에서 토큰 정보 저장
- [x] summarize_conversation_node에서 토큰 추적

## 검증
- [x] 토큰 추적이 정상 작동하는지 확인
- [x] 데이터베이스에 토큰 정보가 저장되는지 확인
