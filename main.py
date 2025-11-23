from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import load_config
from core.logger import configure_logging
from core.middleware import add_middlewares
from core.exceptions import install_exception_handlers
from api import router
from core.database import get_engine

# Routers (will be implemented in api/)
from api.telegram_router import router as telegram_router
from api.qa_router import router as qa_router
from api.persona_router import router as persona_router
from api.web_router import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # await get_engine().connect() # connect() is not needed for async engine usually, but if we want to test connection:
    # engine = get_engine()
    # async with engine.begin() as conn:
    #     pass
    pass
    yield
    # Shutdown (필요시 정리 작업 추가)


def create_app() -> FastAPI:
    config = load_config()
    configure_logging(config["log_level"])  # Set log level early

    app = FastAPI(title=config["app_name"], lifespan=lifespan)  # App instance

    add_middlewares(app)
    install_exception_handlers(app)

    app.include_router(
        router,
        prefix="/api",
        tags=["api"],
    )
    
    app.include_router(web_router)

    return app


app = create_app()
