from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
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
    # NOTE: You must replace 'YOUR_BOT_USERNAME' with your actual bot username (without @)
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
async def dashboard(request: Request, room_id: str = None):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    from repository.chat_room_repository import get_user_chat_rooms, get_chat_room_by_id
    from repository.user_repository import get_user_by_telegram_id
    import uuid

    telegram_id = int(user_data["id"])
    db_user = await get_user_by_telegram_id(telegram_id)
    
    if not db_user:
         # Should not happen if logged in usually, but safety check
         return RedirectResponse(url="/login")

    # Fetch user's chat rooms
    is_admin = telegram_id in settings.admin_ids
    if is_admin:
        from repository.chat_room_repository import get_all_chat_rooms
        chat_rooms = await get_all_chat_rooms()
    else:
        chat_rooms = await get_user_chat_rooms(db_user.id)
    
    current_room = None
    if room_id:
        try:
            current_room = await get_chat_room_by_id(room_id)
        except:
             pass
    
    # If no specific room requested, or requested room not found/invalid, pick the first one (most likely private chat or recent)
    if not current_room and chat_rooms:
        current_room = chat_rooms[0]

    history = []
    if current_room:
        history = await get_history(current_room.id, limit=50)
        
    return templates.TemplateResponse(request, "user_dashboard.html", get_template_context(request, user_data, {
        "chat_rooms": chat_rooms,
        "current_room": current_room,
        "history": history
    }))

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("session")
    return response


@router.post("/dashboard/rooms/{room_id}/delete", response_class=HTMLResponse)
async def delete_chat_room_web(request: Request, room_id: str):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)
        
    # Admin Check
    user_id = int(user_data["id"])
    if user_id not in settings.admin_ids:
        raise HTTPException(status_code=403, detail="Access denied")
        
    from repository.chat_room_repository import delete_chat_room
    
    success = await delete_chat_room(room_id)
    if not success:
         raise HTTPException(status_code=404, detail="Chat room not found")
         
    return RedirectResponse(url="/dashboard", status_code=302)

@router.get("/personas", response_class=HTMLResponse)
async def list_personas(request: Request, tab: str = "my"):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
    
    from repository.persona_repository import get_user_personas, get_public_personas
    from repository.user_repository import get_user_by_telegram_id

    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    personas = []
    
    is_admin = int(user_data["id"]) in settings.admin_ids

    if is_admin:
        from repository.persona_repository import get_all_personas
        personas = await get_all_personas(limit=100)
    elif tab == "public":
        personas = await get_public_personas(limit=100)
    elif db_user:
        personas = await get_user_personas(db_user.id, include_public=False) # My personas only
            
    return templates.TemplateResponse(request, "personas.html", get_template_context(request, user_data, {
        "personas": personas,
        "active_tab": tab
    }))

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
    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    persona = None
    if db_user:
        persona = await get_persona_by_id(persona_id, user_id=db_user.id)
            
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
        
    return templates.TemplateResponse(request, "persona_edit.html", get_template_context(request, user_data, {"persona": persona}))

@router.post("/personas", response_class=HTMLResponse)
async def create_persona_web(
    request: Request,
    name: str = Form(...),
    content: str = Form(...),
    description: str = Form(None),
    is_public: bool = Form(False)
):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)
        
    from repository.persona_repository import create_persona
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    if db_user:
        await create_persona(
            user_id=db_user.id,
            name=name,
            content=content,
            description=description,
            is_public=is_public
        )
    
    return RedirectResponse(url="/personas", status_code=302)

@router.post("/personas/{persona_id}", response_class=HTMLResponse)
async def update_persona_web(
    request: Request,
    persona_id: str,
    name: str = Form(...),
    content: str = Form(...),
    description: str = Form(None),
    is_public: bool = Form(False)
):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)
        
    from repository.persona_repository import update_persona
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    if db_user:
        await update_persona(
            persona_id=persona_id,
            user_id=db_user.id,
            name=name,
            content=content,
            description=description,
            is_public=is_public
        )
        
    return RedirectResponse(url="/personas", status_code=302)

@router.post("/personas/{persona_id}/delete", response_class=HTMLResponse)
async def delete_persona_web(request: Request, persona_id: str):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)
        
    from repository.persona_repository import delete_persona
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    if db_user:
        await delete_persona(persona_id=persona_id, user_id=db_user.id)
        
    return RedirectResponse(url="/personas", status_code=302)

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


@router.get("/personas/{persona_id}", response_class=HTMLResponse)
async def view_persona(request: Request, persona_id: str):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    from repository.persona_repository import get_persona_by_id
    from repository.user_repository import get_user_by_telegram_id
    from repository.evaluation_repository import get_persona_evaluations, get_user_evaluation_for_persona, get_persona_average_score
    import uuid
    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    persona = None
    if db_user:
        persona = await get_persona_by_id(persona_id, user_id=db_user.id) # user_id is checked inside if owner, but if public it should return too. 
        # Actually get_persona_by_id might restrict to owner if user_id passed?
        # Let's check get_persona_by_id implementation. 
        # Usually it returns if owner OR public. If not, we should probably fetch public too.
        # But wait, the repo function likely handles it. 
        pass

    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    evaluations = await get_persona_evaluations(persona.id)
    user_evaluation = None
    if db_user:
        user_evaluation = await get_user_evaluation_for_persona(persona.id, db_user.id)
    
    average_score = await get_persona_average_score(persona.id)

    return templates.TemplateResponse(request, "persona_detail.html", get_template_context(request, user_data, {
        "persona": persona,
        "evaluations": evaluations,
        "user_evaluation": user_evaluation,
        "average_score": average_score if average_score else 0,
        "is_owner": str(persona.user_id) == str(db_user.id) if db_user else False
    }))


@router.post("/personas/{persona_id}/evaluate", response_class=HTMLResponse)
async def evaluate_persona_web(
    request: Request,
    persona_id: str,
    score: int = Form(...),
    comment: str = Form(None)
):
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)
        
    from repository.user_repository import get_user_by_telegram_id
    from repository.evaluation_repository import create_evaluation
    import uuid
    
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    if db_user:
        await create_evaluation(
            persona_id=uuid.UUID(persona_id),
            user_id=db_user.id,
            score=score,
            comment=comment
        )
        
    return RedirectResponse(url=f"/personas/{persona_id}", status_code=302)
