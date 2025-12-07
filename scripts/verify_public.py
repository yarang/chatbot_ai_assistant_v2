import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_async_session, init_db
from models.user_model import User
from models.persona_model import Persona
from repository.evaluation_repository import create_evaluation, get_persona_evaluations
from repository.persona_repository import get_public_personas, create_persona

async def verify_public_persona():
    print("Initializing database...")
    await init_db()

    async with get_async_session() as session:
        # 1. Create Test User
        user_id = uuid.uuid4()
        telegram_id = 987654321
        user = User(
            id=user_id,
            email=f"test_public_{user_id}@example.com",
            telegram_id=telegram_id,
            username="public_test_user",
            first_name="Public",
            last_name="Tester"
        )
        session.add(user)
        try:
            await session.commit()
            print(f"Created user: {user.username}")
        except Exception:
            await session.rollback()
            from sqlalchemy import select
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one()
            user_id = user.id
            print(f"Using existing user: {user.username}")

        # 2. Create Public Persona
        persona = await create_persona(
            user_id=user_id,
            name="Public Test Persona",
            content="I am public.",
            is_public=True
        )
        print(f"Created public persona: {persona.name}")

        # 3. Create Private Persona
        private_persona = await create_persona(
            user_id=user_id,
            name="Private Test Persona",
            content="I am private.",
            is_public=False
        )
        print(f"Created private persona: {private_persona.name}")

    # 4. Verify Public List
    print("Verifying public list...")
    public_personas = await get_public_personas(limit=10)
    public_ids = [p.id for p in public_personas]
    assert persona.id in public_ids
    assert private_persona.id not in public_ids
    print("Public list verified.")

    # 5. Verify Evaluation with User Info
    print("Verifying evaluation user info...")
    await create_evaluation(persona.id, user_id, 5, "Great!")
    
    evaluations = await get_persona_evaluations(persona.id)
    assert len(evaluations) > 0
    # Check if user is loaded and accessible
    eval_user = evaluations[0].user
    print(f"Evaluation by: {eval_user.username}")
    assert eval_user.username == "public_test_user"
    print("Evaluation user info verified.")

    # Clean up
    async with get_async_session() as session:
        from sqlalchemy import delete
        await session.execute(delete(Persona).where(Persona.user_id == user_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(verify_public_persona())
