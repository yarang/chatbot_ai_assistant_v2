from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel

from repository.persona_repository import (
    create_persona,
    get_persona_by_id,
    get_user_personas,
    update_persona,
    delete_persona,
    get_public_personas,
)
from repository.chat_room_repository import set_chat_room_persona
from core.security import get_current_user_required


router = APIRouter()


# Request/Response 모델
class PersonaCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    is_public: bool = False


class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class PersonaResponse(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    description: Optional[str]
    is_public: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ChatRoomPersonaSet(BaseModel):
    persona_id: Optional[str] = None  # None이면 Persona 제거


@router.post("/", response_model=PersonaResponse)
async def create_persona_endpoint(
    persona: PersonaCreate = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    Persona 생성
    """
    try:
        # Telegram ID를 사용하여 User ID를 찾거나 생성해야 함.
        # 현재 세션에는 telegram_id가 "id" 필드에 있음.
        # 하지만 Persona는 UUID user_id를 사용함.
        # 따라서 세션의 telegram_id로 DB User를 조회해야 함.
        # 편의상 여기서는 repository가 telegram_id를 처리할 수 있도록 하거나,
        # security에서 DB User를 가져오도록 개선해야 함.
        # 일단은 repository가 telegram_id (str) 처리를 지원하는지 확인 필요.
        # repository는 uuid 변환을 시도하므로, telegram_id(숫자형 문자열)는 UUID가 아님.
        # User Repository를 통해 UUID를 조회해야 함.
        
        # TODO: Security에서 DB User 조회 로직 추가 필요.
        # 임시로 세션의 id를 그대로 사용하지만, 이는 Telegram ID임.
        # Persona Model의 user_id는 UUID 타입임.
        # 해결책: UserRepository를 사용하여 Telegram ID로 User UUID 조회.
        
        from repository.user_repository import get_user_by_telegram_id
        
        db_user = await get_user_by_telegram_id(int(current_user["id"]))
        if not db_user:
            raise HTTPException(status_code=400, detail="User not found in database")
        user_uuid = db_user.id

        created = await create_persona(
            user_id=user_uuid,
            name=persona.name,
            content=persona.content,
            description=persona.description,
            is_public=persona.is_public,
        )
        return PersonaResponse(
            id=str(created.id),
            user_id=str(created.user_id),
            name=created.name,
            content=created.content,
            description=created.description,
            is_public=created.is_public,
            created_at=created.created_at.isoformat(),
            updated_at=created.updated_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona_endpoint(
    persona_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    Persona 조회
    """
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    user_uuid = db_user.id if db_user else None

    persona = await get_persona_by_id(persona_id=persona_id, user_id=user_uuid)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    return PersonaResponse(
        id=str(persona.id),
        user_id=str(persona.user_id),
        name=persona.name,
        content=persona.content,
        description=persona.description,
        is_public=persona.is_public,
        created_at=persona.created_at.isoformat(),
        updated_at=persona.updated_at.isoformat(),
    )


@router.get("/user/me", response_model=List[PersonaResponse])
async def get_my_personas_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    내 Persona 목록 조회
    """
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
        return []
    user_uuid = db_user.id

    personas = await get_user_personas(user_id=user_uuid, include_public=True)
    return [
        PersonaResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            name=p.name,
            content=p.content,
            description=p.description,
            is_public=p.is_public,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in personas
    ]


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona_endpoint(
    persona_id: str,
    persona_update: PersonaUpdate = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    Persona 수정 (소유자만 가능)
    """
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
         raise HTTPException(status_code=404, detail="User not found")
    user_uuid = db_user.id

    updated = await update_persona(
        persona_id=persona_id,
        user_id=user_uuid,
        name=persona_update.name,
        content=persona_update.content,
        description=persona_update.description,
        is_public=persona_update.is_public,
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Persona not found or permission denied")
    
    return PersonaResponse(
        id=str(updated.id),
        user_id=str(updated.user_id),
        name=updated.name,
        content=updated.content,
        description=updated.description,
        is_public=updated.is_public,
        created_at=updated.created_at.isoformat(),
        updated_at=updated.updated_at.isoformat(),
    )


@router.delete("/{persona_id}")
async def delete_persona_endpoint(
    persona_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    Persona 삭제 (소유자만 가능)
    """
    from repository.user_repository import get_user_by_telegram_id
    
    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
         raise HTTPException(status_code=404, detail="User not found")
    user_uuid = db_user.id

    success = await delete_persona(persona_id=persona_id, user_id=user_uuid)
    if not success:
        raise HTTPException(status_code=404, detail="Persona not found or permission denied")
    
    return {"message": "Persona deleted successfully"}


@router.get("/public/list", response_model=List[PersonaResponse])
async def get_public_personas_endpoint(limit: int = 50):
    """
    공개 Persona 목록 조회
    """
    personas = await get_public_personas(limit=limit)
    return [
        PersonaResponse(
            id=str(p.id),
            user_id=str(p.user_id),
            name=p.name,
            content=p.content,
            description=p.description,
            is_public=p.is_public,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in personas
    ]


@router.post("/chat-room/{chat_room_id}/persona")
async def set_chat_room_persona_endpoint(
    chat_room_id: str,
    request: ChatRoomPersonaSet = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    채팅방에 Persona 설정
    """
    # TODO: 채팅방 소유권 확인 로직 추가 필요
    
    chat_room = await set_chat_room_persona(
        chat_room_id=chat_room_id,
        persona_id=request.persona_id,
    )
    
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    return {
        "message": "Persona set successfully",
        "chat_room_id": str(chat_room.id),
        "persona_id": str(chat_room.persona_id) if chat_room.persona_id else None,
    }

