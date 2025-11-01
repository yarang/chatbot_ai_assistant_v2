from typing import List, Optional
from fastapi import APIRouter, HTTPException, Body
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
    user_id: str = Body(...),
    persona: PersonaCreate = Body(...),
):
    """
    Persona 생성
    
    Args:
        user_id: 사용자 ID
        persona: Persona 정보
    """
    try:
        created = await create_persona(
            user_id=user_id,
            name=persona.name,
            content=persona.content,
            description=persona.description,
            is_public=persona.is_public,
        )
        return PersonaResponse(
            id=created.id,
            user_id=created.user_id,
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
    user_id: Optional[str] = None,
):
    """
    Persona 조회
    
    Args:
        persona_id: Persona ID
        user_id: 조회하는 사용자 ID (선택, 소유자 또는 공개 Persona만 조회 가능)
    """
    persona = await get_persona_by_id(persona_id=persona_id, user_id=user_id)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    return PersonaResponse(
        id=persona.id,
        user_id=persona.user_id,
        name=persona.name,
        content=persona.content,
        description=persona.description,
        is_public=persona.is_public,
        created_at=persona.created_at.isoformat(),
        updated_at=persona.updated_at.isoformat(),
    )


@router.get("/user/{user_id}", response_model=List[PersonaResponse])
async def get_user_personas_endpoint(
    user_id: str,
    include_public: bool = True,
):
    """
    사용자의 Persona 목록 조회
    
    Args:
        user_id: User ID
        include_public: 공개 Persona 포함 여부
    """
    personas = await get_user_personas(user_id=user_id, include_public=include_public)
    return [
        PersonaResponse(
            id=p.id,
            user_id=p.user_id,
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
    user_id: str = Body(...),
    persona_update: PersonaUpdate = Body(...),
):
    """
    Persona 수정 (소유자만 가능)
    
    Args:
        persona_id: Persona ID
        user_id: 수정하는 사용자 ID
        persona_update: 수정할 정보
    """
    updated = await update_persona(
        persona_id=persona_id,
        user_id=user_id,
        name=persona_update.name,
        content=persona_update.content,
        description=persona_update.description,
        is_public=persona_update.is_public,
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="Persona not found or permission denied")
    
    return PersonaResponse(
        id=updated.id,
        user_id=updated.user_id,
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
    user_id: str = Body(...),
):
    """
    Persona 삭제 (소유자만 가능)
    
    Args:
        persona_id: Persona ID
        user_id: 삭제하는 사용자 ID
    """
    success = await delete_persona(persona_id=persona_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Persona not found or permission denied")
    
    return {"message": "Persona deleted successfully"}


@router.get("/public/list", response_model=List[PersonaResponse])
async def get_public_personas_endpoint(limit: int = 50):
    """
    공개 Persona 목록 조회
    
    Args:
        limit: 조회할 최대 개수
    """
    personas = await get_public_personas(limit=limit)
    return [
        PersonaResponse(
            id=p.id,
            user_id=p.user_id,
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
):
    """
    채팅방에 Persona 설정
    
    Args:
        chat_room_id: 채팅방 ID
        request: Persona ID (None이면 제거)
    """
    chat_room = await set_chat_room_persona(
        chat_room_id=chat_room_id,
        persona_id=request.persona_id,
    )
    
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")
    
    return {
        "message": "Persona set successfully",
        "chat_room_id": chat_room.id,
        "persona_id": chat_room.persona_id,
    }

