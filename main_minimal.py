import logging

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(override=True)

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api import router as api_router
from api.qa_router import router as qa_router
from api.telegram_router import router as telegram_router
from api.web_router import router as web_router
from api.file_upload_router import router as file_upload_router
from core.config import get_settings
# from core.database import get_engine, init_db  # Skip DB init
# from core.exceptions import install_exception_handlers  # Skip exception handlers
# from core.logger import configure_logging  # Skip logger
# from core.middleware import add_middlewares  # Skip middlewares


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - minimal configuration
    settings = get_settings()
    logger = logging.getLogger(__name__)
    logger.info(f"Starting application with log level: {settings.log_level}")

    yield
    # Shutdown


def create_app() -> FastAPI:
    get_settings()
    # configure_logging(settings.log_level)  # Skip for now

    app = FastAPI(title="Chatbot AI Assistant", lifespan=lifespan, version="2.0.0")

    # Skip static files for now
    # app.mount("/static", StaticFiles(directory="static"), name="static")

    # Skip middlewares and exception handlers for now
    # add_middlewares(app)
    # install_exception_handlers(app)

    # Include routers
    app.include_router(
        api_router,
        prefix="/api",
        tags=["api"],
    )
    app.include_router(file_upload_router, prefix="/api", tags=["file-upload"])
    app.include_router(web_router)
    app.include_router(telegram_router)
    app.include_router(qa_router)

    from api.web_rag_router import router as web_rag_router
    app.include_router(web_rag_router)

    return app


app = create_app()
