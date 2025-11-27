# Token Usage Tracking Implementation

## 목표 (Goal)

현재 코드베이스에 토큰 사용량 추적 기능을 추가하여 모든 대화에서 LLM 호출 시 사용된 토큰을 기록하도록 수정합니다. 이를 통해 사용자는 각 대화마다 얼마나 많은 토큰이 사용되었는지 확인할 수 있습니다.

### 현재 상태 분석

1. **데이터베이스**: `conversations` 테이블에 이미 `input_tokens`과 `output_tokens` 필드가 존재하지만 현재는 사용되지 않음
2. **LLM 통합**: LangChain의 `ChatGoogleGenerativeAI`를 사용하며, 응답 메시지(`AIMessage`)에 `usage_metadata` 속성이 포함됨
3. **그래프 구조**: LangGraph를 사용한 멀티 에이전트 시스템으로 Supervisor, Researcher, GeneralAssistant 노드에서 LLM 호출이 발생

### 해결 방법

LangChain의 `AIMessage.usage_metadata` 속성을 활용하여 각 LLM 호출 후 토큰 정보를 추출하고, 이를 `ChatState`에 누적하여 대화 저장 시 데이터베이스에 기록합니다.

## Proposed Changes

### Core Graph Module

#### [MODIFY] [graph.py](file:///Users/yarang/workspaces/privates/chatbot_ai_assistant_v2/core/graph.py)

**ChatState 클래스 수정** (Lines 22-29):
- `input_tokens_used: Optional[int]` 필드 추가
- `output_tokens_used: Optional[int]` 필드 추가
- 대화 턴에서 사용된 토큰을 누적하기 위한 필드

**supervisor_node 함수 수정** (Lines 46-118):
- LLM 응답에서 `usage_metadata` 추출
- `state`의 토큰 카운터 업데이트
- 기존 로직은 유지하되 토큰 정보만 추가로 추적

**researcher_node 함수 수정** (Lines 120-149):
- LLM 응답에서 `usage_metadata` 추출
- `state`의 토큰 카운터 업데이트

**general_assistant_node 함수 수정** (Lines 151-167):
- LLM 응답에서 `usage_metadata` 추출
- `state`의 토큰 카운터 업데이트

**save_conversation_node 함수 수정** (Lines 169-200):
- `add_message` 호출 시 `state`에서 누적된 토큰 정보를 전달
- assistant 메시지 저장 시 `model`, `input_tokens`, `output_tokens` 포함

**summarize_conversation_node 함수 수정** (Lines 202-240):
- summary 생성 시에도 토큰 사용량 추적
- 단, summary는 대화 기록에 저장하지 않으므로 로깅만 수행

---

### Verification Plan

#### Automated Tests

기존 테스트 구조를 활용하여 토큰 추적 기능 검증:

```bash
# 모든 테스트 실행
uv run pytest tests/ -v

# 특정 테스트만 실행
uv run pytest tests/test_graph.py -v
uv run pytest tests/test_multi_agent.py -v
```

새로운 테스트 추가 계획:
- `tests/test_token_tracking.py`: 토큰 추적 로직을 검증하는 단위 테스트 작성
  - 각 노드에서 토큰 정보가 정확히 추출되는지 확인
  - ChatState에 토큰이 올바르게 누적되는지 확인
  - save_conversation_node에서 데이터베이스에 토큰이 저장되는지 확인

#### Manual Verification

1. **Telegram Bot을 통한 실제 대화 테스트**
   ```bash
   # 개발 서버 시작
   uv run uvicorn main:app --reload
   ```
   - Telegram으로 봇과 대화
   - 간단한 질문과 복잡한 질문(Researcher가 필요한)을 모두 테스트
   
2. **데이터베이스 확인**
   ```sql
   -- 최근 대화 기록의 토큰 정보 확인
   SELECT id, role, model, input_tokens, output_tokens, 
          LEFT(message, 50) as message_preview, created_at
   FROM conversations
   ORDER BY created_at DESC
   LIMIT 20;
   ```
   - assistant 메시지에 `input_tokens`와 `output_tokens`이 0이 아닌 값으로 저장되어 있는지 확인
   - `model` 필드에 사용된 모델명이 기록되어 있는지 확인

3. **Web UI를 통한 확인**
   ```bash
   # 웹 인터페이스 접속
   open http://localhost:8000
   ```
   - 로그인 후 대화 기록 확인
   - 토큰 정보가 표시되는지 확인 (필요 시 UI 수정)

4. **로그 확인**
   ```bash
   # 애플리케이션 로그에서 토큰 정보 확인
   tail -f logs/*.log | grep -i token
   ```

#### 검증 성공 기준

- [ ] 모든 기존 테스트가 통과
- [ ] 새로운 토큰 추적 테스트가 통과
- [ ] Telegram을 통한 대화 후 데이터베이스에 토큰 정보가 정확히 저장됨
- [ ] supervisor, researcher, general_assistant 모든 경로에서 토큰 추적이 동작함
- [ ] 토큰 사용량이 0이 아닌 실제 값으로 기록됨
