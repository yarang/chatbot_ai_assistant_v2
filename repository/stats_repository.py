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

    async def get_token_usage_stats(self, session):
        """
        모델별 토큰 사용량을 집계하여 반환합니다.
        Returns:
            List[dict]: [{'model': 'gpt-4', 'input_tokens': 100, 'output_tokens': 50, 'total_tokens': 150}, ...]
        """
        stmt = select(
            Conversation.model,
            func.sum(Conversation.input_tokens).label("input_tokens"),
            func.sum(Conversation.output_tokens).label("output_tokens")
        ).where(
            Conversation.model.isnot(None)
        ).group_by(
            Conversation.model
        ).order_by(
            func.sum(Conversation.input_tokens + Conversation.output_tokens).desc()
        )
        
        result = await session.execute(stmt)
        stats = []
        for row in result:
            input_tokens = row.input_tokens or 0
            output_tokens = row.output_tokens or 0
            stats.append({
                "model": row.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            })
        return stats

_stats_repository = StatsRepository()

async def get_system_stats():
    async with get_async_session() as session:
        return {
            "total_users": await _stats_repository.get_total_users(session),
            "total_conversations": await _stats_repository.get_total_conversations(session),
            "total_personas": await _stats_repository.get_total_personas(session),
            "active_users": await _stats_repository.get_active_users_count(session),
            "token_usage": await _stats_repository.get_token_usage_stats(session),
        }
