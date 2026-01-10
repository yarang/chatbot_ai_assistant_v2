from fastapi import APIRouter

from api.persona_router import router as persona_router
from api.qa_router import router as qa_router
from api.telegram_router import router as telegram_router

router = APIRouter()

router.include_router(telegram_router, prefix="/telegram", tags=["telegram"])
router.include_router(qa_router, prefix="/qa", tags=["qa"])
router.include_router(persona_router, prefix="/persona", tags=["persona"])