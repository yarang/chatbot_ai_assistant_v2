from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.config import load_config
from repository.chat_room_repository import get_chat_room_by_telegram_id
from repository.conversation_repository import get_history
import hashlib
import hmac
import time
import json
from itsdangerous import URLSafeTimedSerializer

router = APIRouter()
templates = Jinja2Templates(directory="templates")
config = load_config()

# Secret key for session signing (should be in config/env, using bot token as fallback or random)
SECRET_KEY = config["telegram"]["bot_token"] or "temporary_secret_key"
serializer = URLSafeTimedSerializer(SECRET_KEY)

def get_current_user(request: Request):
    session = request.cookies.get("session")
    if not session:
        return None
    try:
        data = serializer.loads(session, max_age=86400) # 1 day
        return data
    except Exception:
        return None

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")

@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    # NOTE: You must replace 'YOUR_BOT_USERNAME' with your actual bot username (without @)
    # You can also add it to config.json and load it here.
    bot_username = "YOUR_BOT_USERNAME" 
    return templates.TemplateResponse("login.html", {"request": request, "bot_username": bot_username})

@router.get("/auth/telegram/callback")
async def telegram_callback(request: Request):
    params = dict(request.query_params)
    if not params:
         return RedirectResponse(url="/login")
         
    bot_token = config["telegram"]["bot_token"]
    if not bot_token:
        return HTMLResponse("Bot token not configured", status_code=500)
        
    if not check_telegram_authorization(params, bot_token):
        return HTMLResponse("Authorization failed", status_code=403)
        
    # Login successful
    user_data = {
        "id": params["id"],
        "first_name": params.get("first_name"),
        "username": params.get("username"),
        "photo_url": params.get("photo_url")
    }
    
    response = RedirectResponse(url="/dashboard", status_code=302)
    token = serializer.dumps(user_data)
    response.set_cookie("session", token, httponly=True, max_age=86400)
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    telegram_id = int(user_data["id"])
    
    # Fetch chat history
    # Assuming private chat
    chat_room = await get_chat_room_by_telegram_id(telegram_id)
    history = []
    if chat_room:
        history = await get_history(chat_room.id, limit=50)
        
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "user": user_data, 
        "history": history
    })

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    return response

def check_telegram_authorization(auth_data, bot_token):
    check_hash = auth_data.get('hash')
    if not check_hash:
        return False
    auth_data_copy = auth_data.copy()
    del auth_data_copy['hash']
    
    data_check_string = '\n'.join(sorted([f"{k}={v}" for k, v in auth_data_copy.items()]))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    
    if hash != check_hash:
        return False
    if time.time() - int(auth_data['auth_date']) > 86400:
        return False
    return True
