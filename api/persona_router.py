from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from core.security import get_current_user_required
from repository.chat_room_repository import set_chat_room_persona
from repository.persona_repository import (
    bulk_delete_personas,
    bulk_toggle_public,
    create_persona,
    delete_persona,
    duplicate_persona,
    export_personas,
    get_persona_by_id,
    get_public_personas,
    get_user_personas,
    import_personas,
    update_persona,
)

router = APIRouter()


# Request/Response 모델
class PersonaCreate(BaseModel):
    name: str
    content: str
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: bool = False


class PersonaUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class PersonaResponse(BaseModel):
    id: str
    user_id: str
    name: str
    content: str
    description: Optional[str]
    category: Optional[str]
    tags: Optional[List[str]]
    is_public: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ChatRoomPersonaSet(BaseModel):
    persona_id: Optional[str] = None  # None이면 Persona 제거


class EvaluationCreate(BaseModel):
    score: int
    comment: Optional[str] = None


class EvaluationResponse(BaseModel):
    id: str
    persona_id: str
    user_id: str
    score: int
    comment: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class BulkOperationRequest(BaseModel):
    persona_ids: List[str]
    action: str  # 'delete', 'make_public', 'make_private'


class BulkOperationResponse(BaseModel):
    success: int
    failed: int
    errors: List[str]


class ExportRequest(BaseModel):
    persona_ids: List[str]


class ImportRequest(BaseModel):
    personas: List[dict]
    overwrite_names: bool = False


@router.post("/", response_model=PersonaResponse)
async def create_persona_endpoint(
    persona: PersonaCreate = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """Create a new Persona.

    Args:
        persona (PersonaCreate): The persona creation data.
        current_user (Dict[str, Any]): The authenticated user.

    Returns:
        PersonaResponse: The created persona details.

    Raises:
        HTTPException: If the user is not found or other errors occur.
    """
    try:
        # Telegram ID를 사용하여 User ID를 찾거나 생성해야 함.
        # 현재 세션에는 telegram_id가 "id" 필드에 있음.
        # 하지만 Persona는 UUID user_id를 사용함.
        # 따라서 세션의 telegram_id로 DB User를 조회해야 함.
        # 편의상 여기서는 repository가 telegram_id를 처리할 수 있도록 하거나,
        # security에서 DB User를 가져오도록 개선해야 함.
        # Convert Telegram ID to User UUID
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
            category=persona.category,
            tags=persona.tags,
            is_public=persona.is_public,
        )
        return PersonaResponse(
            id=str(created.id),
            user_id=str(created.user_id),
            name=created.name,
            content=created.content,
            description=created.description,
            category=created.category,
            tags=created.tags,
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
    """Retrieve a Persona by ID.

    Args:
        persona_id (str): The unique identifier of the persona.
        current_user (Dict[str, Any]): The authenticated user.

    Returns:
        PersonaResponse: The persona details.

    Raises:
        HTTPException: If the persona is not found.
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
        category=persona.category,
        tags=persona.tags,
        is_public=persona.is_public,
        created_at=persona.created_at.isoformat(),
        updated_at=persona.updated_at.isoformat(),
    )


@router.get("/user/me", response_model=List[PersonaResponse])
async def get_my_personas_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """Retrieve the current user's Personas.

    Args:
        current_user (Dict[str, Any]): The authenticated user.

    Returns:
        List[PersonaResponse]: A list of personas owned by the user.
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
            category=p.category,
            tags=p.tags,
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
        category=persona_update.category,
        tags=persona_update.tags,
        is_public=persona_update.is_public,
    )

    if not updated:
        raise HTTPException(
            status_code=404, detail="Persona not found or permission denied"
        )

    return PersonaResponse(
        id=str(updated.id),
        user_id=str(updated.user_id),
        name=updated.name,
        content=updated.content,
        description=updated.description,
        category=updated.category,
        tags=updated.tags,
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
        raise HTTPException(
            status_code=404, detail="Persona not found or permission denied"
        )

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
            category=p.category,
            tags=p.tags,
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
    # Verify chat room ownership
    from core.config import get_settings
    from repository.chat_room_repository import get_chat_room_by_id
    from repository.conversation_repository import get_history

    settings = get_settings()
    user_telegram_id = int(current_user["id"])

    # Get chat room
    chat_room = await get_chat_room_by_id(chat_room_id)
    if not chat_room:
        raise HTTPException(status_code=404, detail="Chat room not found")

    # Check ownership
    # For private chats, telegram_chat_id equals user's telegram_id
    # For groups, check if user is admin or has sent messages in this room
    is_owner = False

    if chat_room.type == "private":
        # Private chat: telegram_chat_id should match user's telegram_id
        is_owner = chat_room.telegram_chat_id == user_telegram_id
    else:
        # Group/Channel: check if user is admin or has participated
        if user_telegram_id in settings.admin_ids:
            is_owner = True
        else:
            # Check if user has participated in this chat room
            from repository.chat_room_repository import get_chat_room_participants
            from repository.user_repository import get_user_by_telegram_id

            db_user = await get_user_by_telegram_id(user_telegram_id)
            if db_user:
                participants = await get_chat_room_participants(chat_room_id)
                if any(p.id == db_user.id for p in participants):
                    is_owner = True

    if not is_owner:
        raise HTTPException(
            status_code=403, detail="You don't have permission to modify this chat room"
        )

    # Set persona
    chat_room = await set_chat_room_persona(
        chat_room_id=chat_room_id,
        persona_id=request.persona_id,
    )

    return {
        "message": "Persona set successfully",
        "chat_room_id": str(chat_room.id),
        "persona_id": str(chat_room.persona_id) if chat_room.persona_id else None,
    }


@router.post("/{persona_id}/evaluate", response_model=EvaluationResponse)
async def create_evaluation_endpoint(
    persona_id: str,
    evaluation: EvaluationCreate = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """
    Persona 평가 생성
    """
    import uuid

    from repository.evaluation_repository import create_evaluation
    from repository.user_repository import get_user_by_telegram_id

    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        created = await create_evaluation(
            persona_id=uuid.UUID(persona_id),
            user_id=db_user.id,
            score=evaluation.score,
            comment=evaluation.comment,
        )
        return EvaluationResponse(
            id=str(created.id),
            persona_id=str(created.persona_id),
            user_id=str(created.user_id),
            score=created.score,
            comment=created.comment,
            created_at=created.created_at.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{persona_id}/evaluations", response_model=List[EvaluationResponse])
async def get_evaluations_endpoint(
    persona_id: str,
):
    """
    Persona 평가 목록 조회
    """
    import uuid

    from repository.evaluation_repository import get_persona_evaluations

    evaluations = await get_persona_evaluations(uuid.UUID(persona_id))
    return [
        EvaluationResponse(
            id=str(e.id),
            persona_id=str(e.persona_id),
            user_id=str(e.user_id),
            score=e.score,
            comment=e.comment,
            created_at=e.created_at.isoformat(),
        )
        for e in evaluations
    ]


@router.post("/{persona_id}/duplicate", response_model=PersonaResponse)
async def duplicate_persona_endpoint(
    persona_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """Persona 복제"""
    from repository.user_repository import get_user_by_telegram_id

    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_uuid = db_user.id

    duplicated = await duplicate_persona(persona_id=persona_id, user_id=user_uuid)
    if not duplicated:
        raise HTTPException(
            status_code=404, detail="Persona not found or permission denied"
        )

    return PersonaResponse(
        id=str(duplicated.id),
        user_id=str(duplicated.user_id),
        name=duplicated.name,
        content=duplicated.content,
        description=duplicated.description,
        category=duplicated.category,
        tags=duplicated.tags,
        is_public=duplicated.is_public,
        created_at=duplicated.created_at.isoformat(),
        updated_at=duplicated.updated_at.isoformat(),
    )


@router.post("/bulk", response_model=BulkOperationResponse)
async def bulk_operation_endpoint(
    request: BulkOperationRequest = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """일괄 작업 처리"""
    from repository.user_repository import get_user_by_telegram_id

    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_uuid = db_user.id

    if request.action == "delete":
        result = await bulk_delete_personas(
            persona_ids=request.persona_ids, user_id=user_uuid
        )
    elif request.action == "make_public":
        result = await bulk_toggle_public(
            persona_ids=request.persona_ids, user_id=user_uuid, is_public=True
        )
    elif request.action == "make_private":
        result = await bulk_toggle_public(
            persona_ids=request.persona_ids, user_id=user_uuid, is_public=False
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

    return BulkOperationResponse(**result)


@router.post("/export")
async def export_personas_endpoint(
    request: ExportRequest = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """Persona 내보내기 (JSON 다운로드)"""
    from datetime import datetime
    from fastapi.responses import JSONResponse

    from repository.user_repository import get_user_by_telegram_id

    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_uuid = db_user.id

    exported = await export_personas(persona_ids=request.persona_ids, user_id=user_uuid)

    return JSONResponse(
        content={
            "personas": exported,
            "exported_at": datetime.now().isoformat(),
            "count": len(exported),
        },
        headers={"Content-Disposition": 'attachment; filename="personas_export.json"'},
    )


@router.post("/import", response_model=dict)
async def import_personas_endpoint(
    request: ImportRequest = Body(...),
    current_user: Dict[str, Any] = Depends(get_current_user_required),
):
    """Persona 가져오기 (JSON 업로드)"""
    from repository.user_repository import get_user_by_telegram_id

    db_user = await get_user_by_telegram_id(int(current_user["id"]))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_uuid = db_user.id

    result = await import_personas(
        personas_data=request.personas,
        user_id=user_uuid,
        overwrite_names=request.overwrite_names,
    )

    return result
