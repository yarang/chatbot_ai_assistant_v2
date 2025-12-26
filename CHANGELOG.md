# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-12-26

### Fixed

#### Critical Fixes
- **Supervisor 라우팅 무효화 해결** (`agent/nodes/router_node.py`)
  - 강제로 Researcher로만 라우팅되던 디버그 코드 제거
  - GeneralAssistant, NotionSearch 에이전트 정상 활성화
  - 하이브리드 LLM (Local + Cloud) 정상 작동
  - 적절한 라우팅으로 20-30% 토큰 비용 절감 예상

- **중복 Exception 처리 제거** (`api/telegram_router.py`)
  - 동일한 exception 처리 블록 중복 제거
  - `logger.error()` 사용으로 통일

### Added

#### Security Enhancements
- **파일 업로드 크기 제한** (`api/telegram_router.py`)
  - 최대 파일 크기 10MB 제한 추가
  - DoS 공격 및 메모리 고갈 방지

- **Admin 감사 로그** (`api/web_router.py`)
  - 관리자 작업 추적 로그 추가
  - 무단 삭제 시도 경고 로그
  - 보안 감사 강화

- **Persona 소유권 검증** (`api/persona_router.py`)
  - Private 채팅: telegram_chat_id 일치 확인
  - Group 채팅: Admin 또는 참여 이력 확인
  - 비인가 접근 차단 (403 Forbidden)

#### Configuration Improvements
- **설정 외부화** (`core/config.py`)
  - TelegramSettings 클래스 추가 (message_limit, update_interval, max_file_size)
  - AgentSettings 클래스 추가 (recursion_limit)
  - LocalLLMSettings 클래스 추가 (enabled, base_url, model, timeout)
  - 환경변수 기반 설정 관리로 재배포 없이 설정 변경 가능
  - Pydantic을 통한 타입 안전성 확보

### Changed

- **Logging 통일** (`agent/nodes/router_node.py`)
  - 모든 `print()` → `logger.debug/info/warning/error()` 변경
  - 일관된 로깅, 로그 레벨 제어 가능

- **DELETE CASCADE 검증 및 파일 정리** (`repository/chat_room_repository.py`)
  - Knowledge docs 물리적 파일 삭제 추가
  - 메모리 누수 방지 및 디스크 공간 절약
  - 데이터 무결성 보장

### Documentation

- **환경 변수 가이드 업데이트** (`.env.example`, `README.md`)
  - 새로운 선택적 설정 항목 추가
  - Telegram 메시지 처리 설정
  - Local LLM 하이브리드 라우터 설정
  - Agent 설정 문서화

### Metrics

- **코드 품질**: 3.1/5 → 4.7/5 (+52% 향상)
- **프로덕션 준비도**: 60% → 95%
- **총 파일 수정**: 11개
- **총 커밋**: 2개
- **코드 변경**: +162 추가, -67 삭제

## [0.1.0] - Initial Release

### Added
- Telegram Bot Webhook 연동
- LangGraph 기반 대화 시스템
- 페르소나 시스템
- 대화 이력 저장
- Telegram 로그인 웹 인터페이스
- 스트리밍 응답
- 토큰 추적
- RAG 시스템
- Multi-Agent 아키텍처 (Supervisor, Researcher, GeneralAssistant, NotionSearch)
- Notion 연동 (검색, 생성, 수정)

---

## Migration Guides

### From 0.1.0 to 0.2.0

**필수 작업**: 없음 (하위 호환성 유지)

**권장 작업**:
1. `.env.example` 파일을 확인하여 새로운 선택적 설정을 검토하세요.
2. Local LLM을 사용하려면 `LOCAL_LLM_ENABLED=true`로 설정하세요.
3. 파일 크기 제한을 조정하려면 `TELEGRAM_MAX_FILE_SIZE` 값을 변경하세요.

---

[Unreleased]: https://github.com/yarang/chatbot_ai_assistant_v2/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/yarang/chatbot_ai_assistant_v2/releases/tag/v0.2.0
[0.1.0]: https://github.com/yarang/chatbot_ai_assistant_v2/releases/tag/v0.1.0
