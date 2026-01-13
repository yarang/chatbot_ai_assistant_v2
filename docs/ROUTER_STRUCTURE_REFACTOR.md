# 라우터 구조 개선 제안

## 현재 문제점

1. **중복 포함**: `qa_router`가 `api_router` 내부와 `main.py`에서 두 번 포함됨
2. **불필요한 Import**: `persona_router`를 import하지만 사용하지 않음
3. **구조 모호함**: 어떤 라우터가 어디에 포함되는지 명확하지 않음
4. **순서 문제**: 일반 경로 라우터보다 구체적 경로가 먼저 포함되어야 함

## 제안된 개선 구조

### 1단계: 라우터 분류

#### API 라우터 (/api prefix)
- `file_upload_router` - 파일 업로드 API
- `rag_search_router` - RAG 검색 API
- `persona_router` - 페르소나 관리 API
- `qa_router` - 질문 응답 API

#### 웹 라우터 (no prefix - HTML 페이지)
- `web_router` - 메인 웹 페이지 (/login, /dashboard, etc.)
- `web_rag_router` - RAG 관리 웹 페이지 (/rag, etc.)

#### 특수 라우터 (no prefix - 외부 연동)
- `telegram_router` - Telegram Webhook (/webhook)

### 2단계: 개선된 api/__init__.py

```python
from fastapi import APIRouter

def get_api_router():
    """
    API 라우터를 모두 포함하는 라우터를 생성합니다.

    Returns:
        APIRouter: /api prefix를 가진 라우터
    """
    from api.persona_router import router as persona_router
    from api.qa_router import router as qa_router
    from api.file_upload_router import router as file_upload_router
    from api.rag_search_router import router as rag_search_router

    router = APIRouter()

    # 개별 기능별로 prefix 분리
    router.include_router(qa_router, prefix="/qa", tags=["qa"])
    router.include_router(persona_router, prefix="/persona", tags=["persona"])
    router.include_router(file_upload_router, prefix="/files", tags=["files"])
    router.include_router(rag_search_router, prefix="/rag", tags=["rag"])

    return router

# 빈 라우터 (호환성용)
router = APIRouter()
```

### 3단계: 개선된 main.py

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# 필요한 라우터만 import
from api.telegram_router import router as telegram_router
from api.web_router import router as web_router
from api.web_rag_router import router as web_rag_router
# 다른 라우터들은 api/__init__.py에서 관리

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Chatbot AI Assistant", lifespan=lifespan, version="2.0.0")

    # Static files
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")

    add_middlewares(app)
    install_exception_handlers(app)

    # ========================================================================
    # 라우터 포함 순서 (중요!)
    # ========================================================================
    # 1. API 라우터 (/api/*) - 가장 구체적
    from api import get_api_router
    api_router = get_api_router()
    app.include_router(api_router, prefix="/api", tags=["API"])

    # 2. Telegram Webhook (/webhook) - 구체적 경로
    app.include_router(
        telegram_router,
        tags=["Telegram"],
        include_in_schema=True
    )

    # 3. 웹 페이지 (/rag/*) - web_rag 관련
    app.include_router(web_rag_router, tags=["Web RAG"])

    # 4. 메인 웹 페이지 (/*) - 가장 일반적 (catch-all)
    app.include_router(web_router, tags=["Web"])

    return app
```

## 개선된 경로 구조

```
API 라우터 (/api):
├─ /api/qa/ask              - 질문 응답
├─ /api/persona/            - 페르소나 관리
│  ├─ /                     (GET: 목록, POST: 생성)
│  ├─ /{id}                 (GET: 조회)
│  ├─ /user/me              (GET: 내 페르소나)
│  └─ ...
├─ /api/files/              - 파일 업로드
│  ├─ /{chat_room_id}/files (POST: 업로드)
│  └─ ...
└─ /api/rag/                - RAG 검색
   └─ /search               (POST: 검색)

Telegram 라우터:
└─ /webhook                 (POST) - Telegram Webhook
   └─ /telegram/test        (GET) - 테스트

웹 페이지:
├─ /rag                     - RAG 관리 페이지
├─ /rag/{id}                - 특정 채팅방 RAG
├─ /                        - 홈 (/login 또는 /dashboard로 리다이렉트)
├─ /login                   - 로그인 페이지
├─ /dashboard               - 대시보드
├─ /personas                - 페르소나 목록
└─ ...                      - 기타 웹 페이지
```

## 이점

1. **명확한 구분**: API, Web, Telegram이 명확히 분리됨
2. **중복 제거**: 각 라우터가 한 번만 포함됨
3. **확장성**: 새로운 API를 추가하려면 `api/__init__.py`에만 추가하면 됨
4. **일관성**: 모든 API는 `/api` prefix를 가짐
5. **순서 최적화**: 구체적 경로가 일반적 경로보다 먼저 포함됨

## migration 단계

1. api/__init__.py 수정
2. main.py에서 불필요한 import 제거
3. main.py 라우터 포함 순서 재조정
4. 테스트로 경로 확인
