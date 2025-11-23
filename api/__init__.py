from fastapi import APIRouter
from api.telegram_router import router as telegram_router
from api.qa_router import router as qa_router
from api.persona_router import router as persona_router


router = APIRouter()

router.include_router(telegram_router)
router.include_router(qa_router)
router.include_router(persona_router)