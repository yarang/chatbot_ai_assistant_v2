# Chatbot AI Assistant V2

텔레그램 봇과 웹 인터페이스를 통해 제공되는 LangGraph 기반의 AI 챗봇 어시스턴트입니다. 페르소나 시스템, 대화 이력 관리, RAG(Retrieval-Augmented Generation), 토큰 추적, 스트리밍 응답 등의 기능을 제공합니다.

## 주요 기능

### 핵심 기능
- **LangGraph 기반 대화**: 상태 관리가 가능한 고급 대화 플로우
- **페르소나 시스템**: 다양한 AI 캐릭터를 생성하고 관리
- **스트리밍 응답**: 실시간으로 AI 응답을 받아볼 수 있는 스트리밍 기능
- **토큰 추적**: 대화별 토큰 사용량 모니터링
- **RAG (검색 증강 생성)**: 벡터 DB를 활용한 문서 검색 및 답변 생성
- **Multi-Agent 협업**: Supervisor, Researcher, GeneralAssistant, NotionSearch 등 여러 에이전트가 협력
- **Notion 연동**: Notion 페이지 검색, 생성(Create), 수정(Update) 기능 지원

### 텔레그램 봇
- Webhook 기반 메시지 처리
- `/start`, `/help`, `/persona` 등의 명령어 지원
- 대화 이력 저장 및 컨텍스트 유지

### 웹 인터페이스
- Telegram 로그인 인증
- 대화 이력 조회 대시보드
- 페르소나 관리 (CRUD)
- 사용 통계 및 모니터링

## 기술 스택

- **Language**: Python 3.12+
- **Framework**: FastAPI
- **AI/ML**: 
  - LangChain
  - LangGraph
  - Google Gemini API
- **Database**: PostgreSQL with pgvector
- **API Integration**:
  - Telegram Bot API
  - Tavily Search API
- **Development**:
  - uv (패키지 관리)
  - pytest (테스트)
  - Docker (컨테이너화)

## 설치 및 실행

### 사전 요구사항

- Python 3.12 이상
- PostgreSQL 15+ (pgvector 확장 필요)
- [uv](https://github.com/astral-sh/uv) (권장)

### 1. 저장소 클론

```bash
git clone <repository-url>
cd chatbot_ai_assistant_v2
```

### 2. 환경 변수 설정

`.env.example` 파일을 `.env`로 복사하고 필요한 값을 설정합니다:

```bash
cp .env.example .env
```

`.env` 파일 필수 설정 예시:
```env
# App
LOG_LEVEL=INFO

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL_NAME=gemini-2.0-flash-exp

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_WEBHOOK_URL=https://your-domain.ngrok-free.app/webhook

# Search
TAVILY_API_KEY=your_tavily_api_key

# Access Control (Admin telegram IDs)
ADMIN_IDS=[12345678, 87654321]

# Notion (Optional)
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id

# Database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
DATABASE_NAME=chatbot_db
```

**선택적 고급 설정**:
```env
# Telegram 메시지 처리 설정 (기본값 사용 가능)
TELEGRAM_MESSAGE_LIMIT=4000          # 메시지 길이 제한 (기본: 4000)
TELEGRAM_UPDATE_INTERVAL=0.5         # 메시지 업데이트 간격 (기본: 0.5초)
TELEGRAM_MAX_FILE_SIZE=10485760      # 파일 업로드 크기 제한 (기본: 10MB)

# Local LLM 하이브리드 라우터 (선택)
LOCAL_LLM_ENABLED=false              # Local LLM 사용 여부 (기본: false)
LOCAL_LLM_BASE_URL=http://172.16.1.101:11434
LOCAL_LLM_MODEL=llama-3.1-8b
LOCAL_LLM_TIMEOUT=10.0

# Agent 설정
AGENT_RECURSION_LIMIT=20             # LangGraph 재귀 깊이 제한 (기본: 20)
```

### 3. 의존성 설치

```bash
uv sync
```

### 4. 데이터베이스 초기화

#### 4.1 데이터베이스 관리자 작업 (한 번만 실행)

데이터베이스와 필수 extension을 생성합니다. **이 작업은 PostgreSQL 슈퍼유저 권한이 필요합니다.**

```bash
# PostgreSQL 슈퍼유저로 접속
psql -U postgres

# 데이터베이스 생성
CREATE DATABASE chatbot_db;

# chatbot_db에 연결
\c chatbot_db

# 필수 extension 설치 (RAG 기능에 필요)
CREATE EXTENSION IF NOT EXISTS vector;

# 종료
\q
```

#### 4.2 일반 사용자 작업

**방법 1: 스키마 파일 수동 적용**

```bash
psql -h <DATABASE_HOST> -U <DATABASE_USER> -d chatbot_db -f schema.sql
```

**방법 2: 애플리케이션 시작 시 자동 생성 (권장)**

애플리케이션을 시작하면 `init_db()` 함수가 자동으로 필요한 테이블을 생성합니다:

```bash
uvicorn main:app --reload
```

> **참고**: 기존 데이터를 모두 삭제하고 초기화하려면 `python scripts/reset_db.py`를 실행할 수 있습니다 (주의: 데이터 손실).

### 5. 애플리케이션 실행

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

애플리케이션은 `http://localhost:8000`에서 실행됩니다.

## Docker로 실행

### Docker Compose 사용

```bash
docker-compose up -d
```

이 명령어는 애플리케이션과 PostgreSQL 데이터베이스를 함께 실행합니다.

### 로컬 개발 시 Ngrok 사용 (필수)

텔레그램 봇의 Webhook은 **HTTPS**만 지원하므로, 로컬에서 실행 중인 서버(`localhost:8000`)를 외부에서 접속 가능하게 하려면 [ngrok](https://ngrok.com/)과 같은 터널링 프로그램이 필요합니다.

1. Ngrok 설치 및 실행:
   ```bash
   ngrok http 8000
   ```
2. 생성된 HTTPS URL (예: `https://abcd-123.ngrok-free.app`)을 복사회여 `.env` 파일의 `TELEGRAM_WEBHOOK_URL`에 설정합니다.

### 개별 Docker 빌드

```bash
docker build -t chatbot-ai-assistant-v2 .
docker run -p 8000:8000 --env-file .env chatbot-ai-assistant-v2
```

## 프로젝트 구조

```
chatbot_ai_assistant_v2/
├── api/                    # API 라우터
│   ├── persona_router.py   # 페르소나 관리 API
│   ├── qa_router.py        # QA 및 RAG API
│   ├── telegram_router.py  # 텔레그램 webhook
│   └── web_router.py       # 웹 UI 라우터
│   ├── telegram_router.py  # 텔레그램 webhook
│   └── web_router.py       # 웹 UI 라우터
├── agent/                  # AI 에이전트 노드
│   ├── nodes/
│   │   ├── router_node.py  # Supervisor (라우팅)
│   │   ├── notion_node.py  # Notion 작업
│   │   ├── search_node.py  # 웹 검색
│   │   └── chat_node.py    # 일반 대화
│   ├── graph.py            # LangGraph 정의
│   └── state.py            # 상태 정의
├── core/                   # 핵심 모듈
│   ├── config.py           # 설정 관리
│   ├── database.py         # DB 연결
│   ├── graph.py            # LangGraph 정의
│   ├── llm.py              # LLM 초기화
│   ├── vector_store.py     # Vector DB 관리
│   └── middleware.py       # 미들웨어
├── models/                 # 데이터 모델
│   ├── user_model.py
│   ├── persona_model.py
│   ├── conversation_model.py
│   ├── chat_room_model.py
│   └── usage_model.py
├── repository/             # 데이터 액세스 레이어
│   ├── user_repository.py
│   ├── persona_repository.py
│   ├── conversation_repository.py
│   └── stats_repository.py
├── services/               # 비즈니스 로직
│   ├── conversation_service.py
│   ├── gemini_service.py
│   └── streaming_helper.py
├── tools/                  # LangGraph 도구
│   ├── search_tool.py
│   └── retrieval_tool.py
├── templates/              # Jinja2 HTML 템플릿
├── static/                 # 정적 파일 (CSS, JS)
├── tests/                  # 테스트 코드
├── scripts/                # 유틸리티 스크립트
├── docs/                   # 문서
├── schema.sql              # DB 스키마
├── main.py                 # 애플리케이션 진입점
└── pyproject.toml          # 프로젝트 메타데이터
```

## 사용 방법

### 텔레그램 봇 사용

1. 텔레그램에서 봇을 검색하거나 봇 토큰으로 생성한 봇에 접속
2. `/start` 명령어로 시작
3. `/persona` 명령어로 사용 가능한 페르소나 확인
4. 메시지를 보내 대화 시작

### 웹 인터페이스 사용

1. 브라우저에서 `http://localhost:8000` 접속
2. Telegram 로그인으로 인증
3. 대시보드에서 대화 이력 확인
4. 페르소나 관리 페이지에서 AI 캐릭터 생성/수정

## 테스트

전체 테스트 실행:

```bash
pytest
```

특정 테스트 실행:

```bash
pytest tests/test_graph.py
pytest tests/test_streaming.py
pytest tests/test_token_tracking.py
```

## 유틸리티 스크립트

프로젝트에는 여러 유틸리티 스크립트가 포함되어 있습니다:

- `scripts/verify_db.py` - 데이터베이스 연결 및 스키마 확인
- `scripts/verify_graph.py` - LangGraph 구성 검증
- `scripts/verify_token_tracking.py` - 토큰 추적 기능 테스트
- `scripts/verify_web.py` - 웹 서버 동작 확인
- `scripts/ingest_docs.py` - 문서를 벡터 DB에 임베딩
- `scripts/reset_db.py` - 데이터베이스 초기화 (주의: 데이터 삭제)

예시:
```bash
python scripts/verify_db.py
python scripts/ingest_docs.py --docs-dir ./documents
```

## API 사용 가이드

본 프로젝트는 RESTful API를 제공하여 외부 시스템과의 연동을 지원합니다. 모든 API 요청에는 기본적으로 `Authorization` 헤더 또는 쿠키 세션이 필요할 수 있습니다 (개발 환경에서는 일부 완화됨).

### 1. QA (질의응답) API

RAG 기반의 AI 어시스턴트에게 질문하고 답변을 받을 수 있습니다.

**Endpoint:** `POST /api/qa/ask`

**Curl 예시:**

```bash
curl -X POST "http://localhost:8000/api/qa/ask" \
     -H "Content-Type: application/json" \
     -d '{
           "question": "이번 프로젝트의 아키텍처에 대해 설명해줘",
           "chat_room_id": "YOUR_CHAT_ROOM_ID",
           "user_id": "YOUR_USER_ID"
         }'
```

**응답 예시:**

```json
{
  "answer": "본 프로젝트는 LangGraph를 기반으로 한 Multi-Agent 아키텍처를 채택하고 있습니다..."
}
```

### 2. 페르소나(Persona) API

AI 캐릭터(페르소나)를 관리하는 API입니다.

#### 페르소나 생성

**Endpoint:** `POST /api/persona/`

**Curl 예시:**

```bash
curl -X POST "http://localhost:8000/api/persona/" \
     -H "Content-Type: application/json" \
     -H "Cookie: session=YOUR_SESSION_COOKIE" \
     -d '{
           "name": "친절한 수학 선생님",
           "content": "당신은 초등학생에게 수학을 친절하게 가르쳐주는 선생님입니다.",
           "description": "수학 개념을 쉽게 설명해주는 페르소나",
           "is_public": true
         }'
```

#### 페르소나 조회

**Endpoint:** `GET /api/persona/{persona_id}`

**Curl 예시:**

```bash
curl -X GET "http://localhost:8000/api/persona/123e4567-e89b-12d3-a456-426614174000" \
     -H "Cookie: session=YOUR_SESSION_COOKIE"
```

#### 내 페르소나 목록 조회

**Endpoint:** `GET /api/persona/user/me`

**Curl 예시:**

```bash
curl -X GET "http://localhost:8000/api/persona/user/me" \
     -H "Cookie: session=YOUR_SESSION_COOKIE"
```

### 3. Telegram Webhook

텔레그램 봇의 업데이트를 수신하는 엔드포인트입니다. (직접 호출보다는 텔레그램 서버에 의해 호출됩니다.)

**Endpoint:** `POST /telegram/webhook`

## 개발 로드맵

자세한 개발 계획은 [project_roadmap.md](./project_roadmap.md)를 참조하세요.

### 완료된 기능
- ✅ 텔레그램 봇 Webhook 연동
- ✅ LangGraph 기반 대화 시스템
- ✅ 페르소나 시스템
- ✅ 대화 이력 저장
- ✅ Telegram 로그인 웹 인터페이스
- ✅ 스트리밍 응답
- ✅ 토큰 추적
- ✅ RAG 시스템
- ✅ Multi-Agent 아키텍처 (Supervisor, Researcher, NotionSearch)
- ✅ Notion 연동 (검색, 생성, 수정)

### 진행 예정 기능
- 🔄 웹 페르소나 관리 UI 개선
- 🔄 멀티 에이전트 협업 기능 확장
- 🔄 그룹 채팅 지원
- 🔄 멀티모달 지원 (이미지, 음성)

## 기여하기

기여를 환영합니다! Pull Request를 제출하기 전에:

1. 새로운 기능은 관련 이슈를 먼저 생성해주세요
2. 코드 스타일 가이드를 따라주세요
3. 테스트를 추가하고 모든 테스트가 통과하는지 확인해주세요
4. 커밋 메시지는 명확하고 설명적으로 작성해주세요

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 문의

문제가 발생하거나 질문이 있으시면 GitHub Issues를 통해 문의해주세요.
