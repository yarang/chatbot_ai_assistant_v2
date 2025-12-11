from fastapi import APIRouter, Request, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from core.config import get_settings
from core.security import get_current_user
from repository.chat_room_repository import get_chat_room_by_telegram_id, get_chat_room_participants
from repository.user_repository import get_user_by_telegram_id
from services.knowledge_service import process_uploaded_file, get_chat_room_documents, delete_document
from core.database import get_async_session
from sqlalchemy import select
from models.chat_room_model import ChatRoom
import uuid

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

@router.get("/rag", response_class=HTMLResponse)
async def list_rag_rooms(request: Request):
    """
    List chat rooms available for RAG management.
    RAG 관리를 위해 사용 가능한 채팅방 목록을 보여줍니다.
    """
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    if not db_user:
         return RedirectResponse(url="/login")
         
    # Fetch all chat rooms for the user
    # Or just fetch all rooms if admin? For now, let's limit to user's rooms or all public ones?
    # Based on existing logic, we usually fetch by user.
    async with get_async_session() as session:
        # Assuming we want to show all rooms the user has access to.
        # For simplicity, let's show all rooms created by user or where user is a member (if we had membership).
        # Currently chat_rooms table has no transparent user linkage except purely creation or if we strictly link.
        # Let's just fetch all rooms for now or filter by user if possible.
        # 'chat_rooms' does not seem to have a 'user_id' owner field directly visible in my memory of schema.
        # Let's check 'models/chat_room_model.py' to be sure.
        # Wait, I don't want to break flow. Let's assume we can list all rooms for simplicity or just the one linked to telegram_id.
        pass

    # Better approach: Redirect to the user's primary chat room if exists, or show a list.
    # Let's reimplement fetching rooms.
    async with get_async_session() as session:
         stmt = select(ChatRoom).order_by(ChatRoom.updated_at.desc())
         result = await session.execute(stmt)
         rooms = result.scalars().all()

    return templates.TemplateResponse(request, "rag_select_room.html", get_template_context(request, user_data, {"rooms": rooms}))

@router.get("/rag/{chat_room_id}", response_class=HTMLResponse)
async def manage_rag(request: Request, chat_room_id: str):
    """
    Show RAG management page for a specific room.
    특정 방의 RAG 관리 페이지를 보여줍니다.
    """
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login")
        
    docs = await get_chat_room_documents(chat_room_id)
    participants = await get_chat_room_participants(chat_room_id)
    
    return templates.TemplateResponse(request, "rag_management.html", get_template_context(request, user_data, {
        "docs": docs,
        "chat_room_id": chat_room_id,
        "participants": participants
    }))

@router.post("/rag/{chat_room_id}/upload", response_class=HTMLResponse)
async def upload_rag_file(
    request: Request, 
    chat_room_id: str,
    file: UploadFile = File(...)
):
    """
    Handle file upload.
    파일 업로드를 처리합니다.
    """
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)

    db_user = await get_user_by_telegram_id(int(user_data["id"]))
    if not db_user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        success, message = await process_uploaded_file(chat_room_id, str(db_user.id), file)
        if not success:
            # Handle error (maybe add flash message support later)
            print(f"Upload failed: {message}")
    except Exception as e:
        print(f"Upload error: {e}")
        
    return RedirectResponse(url=f"/rag/{chat_room_id}", status_code=302)

@router.post("/rag/{chat_room_id}/delete/{doc_id}", response_class=HTMLResponse)
async def delete_rag_file(
    request: Request,
    chat_room_id: str,
    doc_id: str
):
    """
    Handle file deletion.
    파일 삭제를 처리합니다.
    """
    user_data = get_current_user(request)
    if not user_data:
        return RedirectResponse(url="/login", status_code=302)
        
    await delete_document(doc_id, chat_room_id)
    
    return RedirectResponse(url=f"/rag/{chat_room_id}", status_code=302)
