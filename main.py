from fastapi import FastAPI
from core.config import load_config
from core.logger import configure_logging
from core.middleware import add_middlewares
from core.exceptions import install_exception_handlers

# Routers (will be implemented in api/)
from api.telegram_router import router as telegram_router
from api.qa_router import router as qa_router
from api.persona_router import router as persona_router


def create_app() -> FastAPI:
    config = load_config()
    configure_logging(config["log_level"])  # Set log level early

    app = FastAPI(title=config["app_name"])  # App instance

    add_middlewares(app)
    install_exception_handlers(app)

    # Include routers
    app.include_router(telegram_router, prefix="/api/telegram", tags=["telegram"])
    app.include_router(qa_router, prefix="/api/qa", tags=["qa"])
    app.include_router(persona_router, prefix="/api/personas", tags=["personas"])

    @app.on_event("startup")
    async def on_startup() -> None:
        # SQLAlchemy ORM을 사용하여 데이터베이스 초기화
        from core.database import init_db
        await init_db()

    return app


app = create_app()



