import logging
import sys
import os

# Monkeypatch fix for ModelProfile missing in langchain_core
import langchain_core.language_models
if not hasattr(langchain_core.language_models, 'ModelProfile'):
    class ModelProfile(dict): pass
    langchain_core.language_models.ModelProfile = ModelProfile
if not hasattr(langchain_core.language_models, 'ModelProfileRegistry'):
    class ModelProfileRegistry(dict): pass
    langchain_core.language_models.ModelProfileRegistry = ModelProfileRegistry
if not hasattr(langchain_core.language_models, 'is_openai_data_block'):
    langchain_core.language_models.is_openai_data_block = lambda *args: False

# Monkeypatch for messages.content
import langchain_core.messages
if not hasattr(langchain_core.messages, 'content'):
    from types import ModuleType
    content_mod = ModuleType('langchain_core.messages.content')
    class Citation: pass
    content_mod.Citation = Citation
    class ContentBlock: pass
    content_mod.ContentBlock = ContentBlock
    sys.modules['langchain_core.messages.content'] = content_mod
    
    # Also attach to langchain_core.messages module itself if not present
    if not hasattr(langchain_core.messages, 'content'):
        langchain_core.messages.content = content_mod

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core.config import get_settings
from core.logger import configure_logging
from core.middleware import add_middlewares
from core.exceptions import install_exception_handlers
from api import router as api_router
from core.database import get_engine, init_db

# Routers (will be implemented in api/)
from api.telegram_router import router as telegram_router
from api.qa_router import router as qa_router
from api.persona_router import router as persona_router
from api.web_router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Initialize database
    await init_db()
    
    # Log configuration (safe)
    settings = get_settings()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting application with log level: {settings.log_level}")
    
    # Set up Telegram webhook if configured
    if settings.telegram.bot_token and settings.telegram.webhook_url:
        try:
            import httpx
            bot_token = settings.telegram.bot_token
            webhook_url = settings.telegram.webhook_url
            
            logger.info(f"Setting Telegram webhook to: {webhook_url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/setWebhook",
                    json={"url": webhook_url}
                )
                result = response.json()
                
                if result.get("ok"):
                    logger.info("✅ Telegram webhook set successfully")
                else:
                    logger.error(f"❌ Failed to set webhook: {result.get('description')}")
        except Exception as e:
            logger.error(f"Error setting Telegram webhook: {e}")
    elif settings.telegram.bot_token:
        logger.warning("⚠️  TELEGRAM_WEBHOOK_URL not configured - webhook not set")
    
    if settings.telegram.webhook_url and "ngrok" in settings.telegram.webhook_url:
        logger.warning("⚠️  Using ngrok? Ensure your BotFather 'Domain' setting matches: " + settings.telegram.webhook_url)

    
    yield
    # Shutdown (필요시 정리 작업 추가)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Chatbot AI Assistant", lifespan=lifespan, version="2.0.0")

    # Mount static files
    app.mount("/static", StaticFiles(directory="static"), name="static")

    add_middlewares(app)
    install_exception_handlers(app)

    # Include routers
    app.include_router(
        api_router,
        prefix="/api",
        tags=["api"],
    )
    
    app.include_router(web_router)
    app.include_router(telegram_router)
    app.include_router(qa_router)
    # app.include_router(persona_router) # Removed to prevent conflict with web_router and catch-all behavior. It is already included in api_router.
    
    from api.web_rag_router import router as web_rag_router
    app.include_router(web_rag_router)

    return app


app = create_app()
