from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.config import get_settings
from core.security import get_current_user, check_telegram_authorization, create_session_token
from repository.chat_room_repository import get_chat_room_by_telegram_id
from repository.conversation_repository import get_history
from repository.persona_repository import get_user_personas, get_persona_by_id
from repository.user_repository import get_user_by_telegram_id
from core.database import get_async_session
from repository.stats_repository import get_system_stats

router = APIRouter()
templates = Jinja2Templates(directory="templates")

settings = get_settings()

def get_template_context(request: Request, user_data: dict, extra: dict = None) -> dict:
    context = {
        "request": request,
        "user": user_data,
        "is_admin": int(user_data["id"]) in settings.admin_ids
    }
    if extra:
        context.update(extra)
    return context

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
    bot_username = settings.telegram.bot_username or "YOUR_BOT_USERNAME" 
    return templates.TemplateResponse(request, "login.html", {"bot_username": bot_username})

@router.get("/auth/telegram/callback")
async def telegram_callback(request: Request):
    params = dict(request.query_params)
    if not params:
         return RedirectResponse(url="/login")
         
    # Admin Check
    # In a real app, we would check the session user.
    # For now, we assume local dev or basic auth (not implemented here).
    # Let's just check if we have admin IDs configured.
    if not settings.admin_ids:
        return HTMLResponse("Admin not configured", status_code=403)
        
    bot_token = settings.telegram.bot_token
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
    token = create_session_token(user_data)
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
        
    return templates.TemplateResponse(request, "dashboard.html", get_template_context(request, user_data, {"history": history}))

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    return response

@router.get("/personas", response_class=HTMLResponse)
async def list_personas(request: Request):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
    
    from repository.persona_repository import get_user_personas
    from repository.user_repository import get_user_by_telegram_id
    from core.database import get_async_session
    
    async with get_async_session() as session:
        db_user = await get_user_by_telegram_id(session, int(user_data["id"]))
        personas = []
        if db_user:
            personas = await get_user_personas(session, db_user.id, include_public=True)
            
    return templates.TemplateResponse(request, "personas.html", get_template_context(request, user_data, {"personas": personas}))

@router.get("/personas/new", response_class=HTMLResponse)
async def new_persona(request: Request):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    return templates.TemplateResponse(request, "persona_edit.html", get_template_context(request, user_data, {"persona": None}))

@router.get("/personas/{persona_id}/edit", response_class=HTMLResponse)
async def edit_persona(request: Request, persona_id: str):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    from repository.persona_repository import get_persona_by_id
    from repository.user_repository import get_user_by_telegram_id
    from core.database import get_async_session
    
    async with get_async_session() as session:
        db_user = await get_user_by_telegram_id(session, int(user_data["id"]))
        persona = None
        if db_user:
            persona = await get_persona_by_id(session, persona_id, user_id=db_user.id)
            
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
        
    return templates.TemplateResponse(request, "persona_edit.html", get_template_context(request, user_data, {"persona": persona}))

@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    # Check if user is admin
    user_id = int(user_data["id"])
    if user_id not in settings.admin_ids:
        raise HTTPException(status_code=403, detail="Access denied")
        
    from repository.stats_repository import get_system_stats
    stats = await get_system_stats()
    
    return templates.TemplateResponse(request, "admin_dashboard.html", get_template_context(request, user_data, {"stats": stats}))
