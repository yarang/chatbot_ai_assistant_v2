"""
모델 패키지

SQLAlchemy ORM 모델들을 export합니다.
"""

from models.user_model import User
from models.conversation_model import Conversation
from models.chat_room_model import ChatRoom
from models.persona_model import Persona
from core.database import Base

# 테이블 생성 순서 지정
Base.metadata.tables["users"].info["creation_order"] = 1
Base.metadata.tables["personas"].info["creation_order"] = 2
Base.metadata.tables["chat_rooms"].info["creation_order"] = 3
Base.metadata.tables["conversations"].info["creation_order"] = 4
Base.metadata.tables["usage_logs"].info["creation_order"] = 5

__all__ = [
    "User",
    "Conversation",
    "ChatRoom",
    "Persona",
]
