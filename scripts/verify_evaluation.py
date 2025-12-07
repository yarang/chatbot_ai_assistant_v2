import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_async_session, init_db
from models.user_model import User
from models.persona_model import Persona
from repository.evaluation_repository import create_evaluation, get_persona_evaluations, get_persona_average_score

async def verify_evaluation():
    print("Initializing database...")
    await init_db()

    async with get_async_session() as session:
        # 1. Create Test User
        user_id = uuid.uuid4()
        telegram_id = 123456789
        user = User(
            id=user_id,
            email=f"test_eval_{user_id}@example.com",
            telegram_id=telegram_id,
            username="test_eval_user"
        )
        session.add(user)
        try:
            await session.commit()
            print(f"Created user: {user_id}")
        except Exception as e:
            await session.rollback()
            # Try to get existing user if unique constraint fails (likely from previous runs)
            # using clean select
            from sqlalchemy import select
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one()
            user_id = user.id
            print(f"Using existing user: {user_id}")

        # 2. Create Test Persona
        persona_id = uuid.uuid4()
        persona = Persona(
            id=persona_id,
            user_id=user_id,
            name="Test Persona for Evaluation",
            content="You are a test persona.",
            is_public=True
        )
        session.add(persona)
        await session.commit()
        print(f"Created persona: {persona_id}")

    # 3. Create Evaluation
    print("Creating evaluation...")
    score = 5
    comment = "Excellent persona!"
    try:
        eval1 = await create_evaluation(persona_id, user_id, score, comment)
        print(f"Created evaluation: Score={eval1.score}, Comment={eval1.comment}")
    except Exception as e:
        print(f"Failed to create evaluation: {e}")
        return

    # 4. Verify Retrieval
    print("Verifying retrieval...")
    evaluations = await get_persona_evaluations(persona_id)
    assert len(evaluations) == 1
    assert evaluations[0].score == score
    assert evaluations[0].comment == comment
    print("Retrieval verified.")

    # 5. Verify Average Score
    print("Verifying average score...")
    avg = await get_persona_average_score(persona_id)
    assert avg == 5.0
    print(f"Average score verified: {avg}")

    # Clean up (optional, but good for repeatability)
    async with get_async_session() as session:
        from sqlalchemy import delete
        # Delete persona (cascades to evaluations)
        await session.execute(delete(Persona).where(Persona.id == persona_id))
        # Delete user
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(verify_evaluation())
