"""
Pydantic schemas for API request/response validation.

This package provides type-safe data validation using Pydantic v2.
"""

from api.schemas.base import (
    BaseModel,
    PaginationParams,
    PaginatedResponse,
    RequestModel,
    ResponseModel,
    TimestampMixin,
    UUIDMixin,
)
from api.schemas.enums import (
    ChatType,
    EvaluationScore,
    FileStatus,
    MessageRole,
)
from api.schemas.user import UserCreate, UserResponse, UserUpdate
from api.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationsListResponse,
)
from api.schemas.chat_room import (
    ChatRoomCreate,
    ChatRoomResponse,
    ChatRoomsListResponse,
)
from api.schemas.persona import (
    PersonaCreate,
    PersonaResponse,
    PersonaUpdate,
    PersonasListResponse,
    ChatRoomPersonaSet,
    BulkOperationRequest,
    BulkOperationResponse,
    ExportRequest,
    ImportRequest,
)
from api.schemas.evaluation import (
    EvaluationCreate,
    EvaluationResponse,
)

__all__ = [
    # Base models
    "BaseModel",
    "RequestModel",
    "ResponseModel",
    "TimestampMixin",
    "UUIDMixin",
    "PaginationParams",
    "PaginatedResponse",
    # Enums
    "MessageRole",
    "ChatType",
    "EvaluationScore",
    "FileStatus",
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Conversation schemas
    "ConversationCreate",
    "ConversationResponse",
    "ConversationsListResponse",
    # ChatRoom schemas
    "ChatRoomCreate",
    "ChatRoomResponse",
    "ChatRoomsListResponse",
    # Persona schemas
    "PersonaCreate",
    "PersonaUpdate",
    "PersonaResponse",
    "PersonasListResponse",
    "ChatRoomPersonaSet",
    "BulkOperationRequest",
    "BulkOperationResponse",
    "ExportRequest",
    "ImportRequest",
    # Evaluation schemas
    "EvaluationCreate",
    "EvaluationResponse",
]
