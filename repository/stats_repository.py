from sqlalchemy import select, func
from core.database import get_async_session
from models.user_model import User
from models.conversation_model import Conversation
from models.persona_model import Persona

class StatsRepository:
    async def get_total_users(self, session):
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        return result.scalar()

    async def get_total_conversations(self, session):
        stmt = select(func.count(Conversation.id))
        result = await session.execute(stmt)
        return result.scalar()

    async def get_total_personas(self, session):
        stmt = select(func.count(Persona.id))
        result = await session.execute(stmt)
        return result.scalar()

    async def get_active_users_count(self, session):
        # Users with at least one conversation
        stmt = select(func.count(func.distinct(Conversation.user_id)))
        result = await session.execute(stmt)
        return result.scalar()

_stats_repository = StatsRepository()

async def get_system_stats():
    async with get_async_session() as session:
        return {
            "total_users": await _stats_repository.get_total_users(session),
            "total_conversations": await _stats_repository.get_total_conversations(session),
            "total_personas": await _stats_repository.get_total_personas(session),
            "active_users": await _stats_repository.get_active_users_count(session),
        }
