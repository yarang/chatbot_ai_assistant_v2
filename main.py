"""
Chatbot AI Assistant V2 - Main Application

라우터 구조:
- /api/*         : 모든 API 엔드포인트 (api/__init__.py에서 관리)
- /webhook       : Telegram Webhook
- /rag/*         : RAG 관리 웹 페이지
- /*             : 메인 웹 페이지
"""

import logging
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

# ==============================================================================
# 라우터 Import
# ==============================================================================
# Note: API 라우터는 api/__init__.py의 get_api_router()를 통해 포함됩니다.
# 여기서는 API가 아닌 라우터만 직접 import합니다.

from api.telegram_router import router as telegram_router
from api.web_router import router as web_router
from api.web_rag_router import router as web_rag_router

from core.config import get_settings
from core.database import init_db
from core.exceptions import install_exception_handlers
from core.logger import configure_logging
from core.middleware import add_middlewares
from core.metrics import MetricsMiddleware, get_metrics_summary, get_prometheus_metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Initialize database
    try:
        await init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("Continuing without database...")

    # Log configuration (safe)
    settings = get_settings()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting application with log level: {settings.log_level}")

    # Log Hybrid Router Configuration
    if settings.local_llm.enabled:
        logger.info("🚀 Hybrid Context-Aware Router: ENABLED (Prioritizing Local)")
        logger.info(f"   - Local Endpoint: {settings.local_llm.base_url}")
        logger.info(f"   - Local Model: {settings.local_llm.model}")
        logger.info(f"   - Fallback: {settings.llm_api}")
    else:
        logger.info("🌐 Hybrid Context-Aware Router: DISABLED (Using Cloud Only)")
        logger.info(f"   - Primary Agent: {settings.llm_api}")

    # Skip automatic webhook setup to avoid blocking
    if settings.telegram.bot_token and settings.telegram.webhook_url:
        logger.info(f"Telegram webhook URL configured: {settings.telegram.webhook_url}")
        logger.info(
            'Set webhook manually using: curl -F "url={settings.telegram.webhook_url}" https://api.telegram.org/bot{settings.telegram.bot_token}/setWebhook'
        )
    elif settings.telegram.bot_token:
        logger.warning("⚠️  TELEGRAM_WEBHOOK_URL not configured - webhook not set")

    if settings.telegram.webhook_url and "ngrok" in settings.telegram.webhook_url:
        logger.warning(
            "⚠️  Using ngrok? Ensure your BotFather 'Domain' setting matches: "
            + settings.telegram.webhook_url
        )

    yield
    # Shutdown (필요시 정리 작업 추가)


def create_app() -> FastAPI:
    """
    FastAPI 애플리케이션을 생성하고 설정합니다.

    라우터 포함 순서 (중요!):
    1. API 라우터 (/api/*) - 가장 구체적
    2. Telegram Webhook (/webhook) - 구체적 경로
    3. RAG 웹 페이지 (/rag/*) - 구체적 경로
    4. 메인 웹 페이지 (/*) - 가장 일반적 (catch-all)

    Returns:
        FastAPI: 설정된 애플리케이션 인스턴스
    """
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Chatbot AI Assistant",
        lifespan=lifespan,
        version="2.0.0",
        description="AI 어시스턴트 with RAG, Multi-Agent, Telegram integration",
    )

    # ======================================================================
    # Static Files
    # ======================================================================
    if os.path.exists("static"):
        app.mount("/static", StaticFiles(directory="static"), name="static")

    # ======================================================================
    # Middleware & Exception Handlers
    # ======================================================================
    add_middlewares(app)
    install_exception_handlers(app)

    # 메트릭 미들웨어 추가
    app.add_middleware(MetricsMiddleware)

    # ======================================================================
    # Metrics Endpoints
    # ======================================================================

    @app.get("/metrics")
    async def metrics_prometheus():
        """Prometheus 메트릭 엔드포인트"""
        return Response(content=await get_prometheus_metrics(), media_type="text/plain")

    @app.get("/metrics/summary")
    async def metrics_summary():
        """메트릭 요약 엔드포인트 (JSON)"""
        return await get_metrics_summary()

    # ======================================================================
    # Router Inclusion (순서가 중요합니다!)
    # ======================================================================
    # 1. API 라우터 (/api/*)
    #    모든 API 엔드포인트는 api/__init__.py에서 중앙 관리됩니다.
    #    - /api/qa/*        : 질문 응답
    #    - /api/persona/*   : 페르소나 관리
    #    - /api/files/*     : 파일 업로드
    #    - /api/rag/*       : RAG 검색
    from api import get_api_router

    api_router = get_api_router()
    app.include_router(api_router, prefix="/api")

    # 2. Telegram Webhook (/webhook)
    #    Telegram Bot에서 호출하는 엔드포인트
    #    - /webhook          : Webhook 엔드포인트
    #    - /telegram/test    : 테스트 엔드포인트
    app.include_router(telegram_router, tags=["Telegram"], include_in_schema=True)

    # 3. RAG 관리 웹 페이지 (/rag/*)
    #    RAG 파일 및 검색 관리를 위한 웹 인터페이스
    #    - /rag              : RAG 관리 홈
    #    - /rag/{id}         : 특정 채팅방 RAG 관리
    app.include_router(web_rag_router, tags=["Web RAG"])

    # 4. 메인 웹 페이지 (/*)
    #    사용자 인터페이스 및 대화 관리
    #    - /                 : 홈 (리다이렉트)
    #    - /login            : 로그인
    #    - /dashboard        : 대시보드
    #    - /personas         : 페르소나 관리
    #    etc.
    #    Note: 가장 마지막에 포함되어야 합니다 (catch-all 경로)
    app.include_router(web_router, tags=["Web"])

    return app


app = create_app()
