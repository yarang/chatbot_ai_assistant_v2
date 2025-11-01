from fastapi import APIRouter, Depends, Header, HTTPException
from services.telegram_service import handle_update


router = APIRouter()


@router.post("/webhook")
async def telegram_webhook(
    payload: dict,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    # Optional: verify secret header if configured
    result = await handle_update(payload, x_telegram_bot_api_secret_token)
    if not result:
        raise HTTPException(status_code=400, detail="Invalid update")
    return {"ok": True}



