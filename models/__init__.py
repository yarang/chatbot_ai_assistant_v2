"""
모델 패키지

SQLAlchemy ORM 모델들을 export합니다.
"""

from models.user_model import User
from models.conversation_model import Conversation
from models.chat_room_model import ChatRoom
from models.persona_model import Persona
from models.evaluation_model import PersonaEvaluation
from models.knowledge_doc_model import KnowledgeDoc
from core.database import Base

# 테이블 생성 순서 지정
# Base.metadata.tables에 실제 존재하는 테이블만 순서 지정
table_orders = {
    "users": 1,
    "personas": 2,
    "chat_rooms": 3,
    "conversations": 4,
    "knowledge_docs": 5
}

for table_name, order in table_orders.items():
    if table_name in Base.metadata.tables:
        Base.metadata.tables[table_name].info["creation_order"] = order

__all__ = [
    "User",
    "Conversation",
    "ChatRoom",
    "Persona",
    "PersonaEvaluation",
    "KnowledgeDoc",
]
