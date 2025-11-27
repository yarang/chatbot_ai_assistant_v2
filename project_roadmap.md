# Project Roadmap: Chatbot AI Assistant V2

이 문서는 Chatbot AI Assistant V2 프로젝트의 장기적인 개발 계획을 기술합니다. 현재 코드베이스 분석을 바탕으로 기능 확장, 안정성 확보, 사용자 경험 개선을 위한 로드맵을 제시합니다.

## 1. 기능 목록 (Feature List)

### 핵심 기능 (Core)
- [x] Telegram Bot Webhook 연동
- [x] 기본 대화 기능 (LangGraph 기반)
- [x] 페르소나 시스템 (기본 구현)
- [x] 대화 내용 저장 (DB)
- [ ] **[개선]** 에러 핸들링 및 로깅 강화
- [ ] **[신규]** Docker 및 배포 환경 구성

### 웹 인터페이스 (Web Interface)
- [x] Telegram 로그인 연동
- [x] 대시보드 (대화 이력 조회)
- [ ] **[신규]** 페르소나 관리자 페이지 (생성/수정/삭제)
- [ ] **[보류]** 웹 채팅 인터페이스 (실시간 대화)
- [ ] **[신규]** 관리자 대시보드 (사용자 통계)

### AI 및 대화 지능 (AI Intelligence)
- [ ] **[신규]** 장기 기억 (Vector DB / RAG) 도입
- [ ] **[신규]** 도구 사용 (Tool Use) - 웹 검색, 날씨 등
- [ ] **[신규]** 멀티모달 지원 (이미지 인식, 음성 처리)
- [ ] **[개선]** 스트리밍 응답 (Streaming Response)
- [ ] **[신규]** 대화 자동 요약 (Auto Summarization)
- [ ] **[신규]** 멀티 에이전트 협업 (Multi-Agent Collaboration) - 챗봇 간 대화
- [ ] **[신규]** 그룹 채팅 모드 (Selective Response) - 호출 시에만 응답

---

## 2. 우선순위 지정 (Prioritization)

| 우선순위 | 항목 | 설명 | 비고 |
| :--- | :--- | :--- | :--- |
| **P0 (Critical)** | 배포 환경 및 안정성 | Docker라이징, 환경변수 관리, 에러 핸들링 | 서비스 운영 필수 |
| **P0 (Critical)** | 웹 페르소나 관리 | 텔레그램 명령어보다 편리한 웹 UI 제공 | UX 핵심 |
| **P1 (High)** | RAG / 장기 기억 | 단순 대화 이력을 넘어선 문맥 파악 능력 | AI 성능 차별화 |
| **P1 (High)** | 도구 사용 (Tools) | 외부 정보 검색 및 기능 수행 | 확장성 |
| **P2 (Medium)** | 웹 실시간 채팅 | 텔레그램 외의 채널 확장 | 접근성 |
| **P3 (Low)** | 멀티모달 | 이미지/음성 지원 | 부가 기능 |

---

## 3. Sprint 계획 (Sprint Plan)

각 Sprint는 2주 단위로 가정합니다.

### Sprint 1: Foundation & Stability (기반 다지기)
**목표**: 안정적인 배포 환경 구성 및 코드 품질 개선
- **Tasks**:
  - Dockerfile 및 docker-compose 작성
  - 환경 변수 및 설정 파일 구조 개선
  - `main.py` 및 Router 에러 핸들링 미들웨어 강화
  - 기본 Unit Test 작성 (Router, Service)
- **산출물**: Docker 이미지, 테스트 리포트, 안정화된 서버

### Sprint 2: Web Experience Upgrade (웹 경험 개선)
**목표**: 웹에서 페르소나를 관리하고 대화 이력을 편리하게 볼 수 있도록 개선
- **Tasks**:
  - 페르소나 CRUD 웹 페이지 구현 (Frontend + Backend API)
  - 대화 이력 UI 개선 (가독성 향상)
  - 관리자 대시보드 구현 (사용자 통계)
  - Telegram 로그인 위젯 설정 가이드 문서화
- **산출물**: 페르소나 관리 페이지, 개선된 대시보드, 관리자 페이지

### Sprint 3: Intelligence Expansion (지능 확장)
**목표**: AI가 더 똑똑하게 대답하고 외부 정보를 활용하도록 개선
- **Tasks**:
  - LangGraph 노드 확장: Tool Node 추가
  - Google Search 또는 Tavily Search 연동
  - Vector DB (예: Chroma or PGVector) 연동 설계
  - RAG 파이프라인 구축 (문서 업로드 및 임베딩)
  - 대화 요약 기능 구현 (LangGraph State 관리)
- **산출물**: 검색 가능한 챗봇, 지식 베이스 연동 기능, 요약된 대화 컨텍스트

### Sprint 4: Interaction & Multi-Agent (상호작용 및 멀티 에이전트)
**목표**: 다양한 방식의 소통 지원 및 에이전트 간 협업 구현
- **Tasks**:
  - 그룹 채팅 멘션 감지 및 필터링 구현 (Selective Response)
  - 멀티 페르소나 오케스트레이션 (LangGraph Subgraph)
  - 챗봇 간 자율 대화 모드 구현
  - 이미지 입력 처리 (Vision Model 연동)
  - 음성 메시지 처리 (STT/TTS)
- **산출물**: 멀티모달 지원 챗봇, 멀티 에이전트 협업 시스템

---

## 4. Task List (종합 작업 목록)

이 리스트는 향후 작업 관리를 위한 체크리스트입니다.

### Phase 1: Infrastructure
- [ ] Dockerfile 작성 및 빌드 테스트
- [ ] docker-compose.yml 작성 (App + DB)
- [ ] Logging 설정 고도화 (File rotation 등)
- [ ] Exception Handler 전역 설정 보완

### Phase 2: Web Features
- [ ] `GET /personas` API 구현 (Web용)
- [ ] `POST /personas` API 구현 (Web용)
- [ ] `PUT /personas/{id}` API 구현
- [ ] `DELETE /personas/{id}` API 구현
- [ ] 페르소나 관리 HTML 템플릿 작성 (Jinja2)
- [ ] 페르소나 생성/수정 Form 핸들링

### Phase 3: AI Logic
- [ ] LangGraph Tool Node 추가
- [ ] Search Tool 구현
- [ ] PGVector 설정 및 Migration
- [ ] 문서 임베딩 로직 구현 (`ingest_docs`)
- [ ] Retrieve Node 개선 (Vector Search 포함)

### Phase 4: Advanced
- [ ] Telegram Photo Message 핸들링 로직 추가
- [ ] Telegram Voice Message 핸들링 로직 추가
- [ ] Streaming Response Handler 구현
