import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import get_async_session, init_db
from models.user_model import User
from models.chat_room_model import ChatRoom
from models.conversation_model import Conversation
from repository.stats_repository import get_system_stats

async def verify_token_stats():
    print("Initializing database...")
    await init_db()

    async with get_async_session() as session:
        # 1. Create Test User and Chat Room
        user_id = uuid.uuid4()
        telegram_id = 55555
        user = User(
            id=user_id,
            email=f"token_test_{user_id}@example.com",
            telegram_id=telegram_id,
            username="token_tester"
        )
        session.add(user)
        
        chat_room_id = uuid.uuid4()
        chat_room = ChatRoom(
            id=chat_room_id,
            telegram_chat_id=telegram_id,
            type="private",
            username="token_tester"
        )
        session.add(chat_room)
        
        # 2. Add Conversations with Token Usage
        models_data = [
            ("gpt-4", 100, 50),
            ("gpt-4", 200, 100),
            ("gpt-3.5-turbo", 50, 20),
            ("claude-3-opus", 300, 150)
        ]
        
        for model, input_t, output_t in models_data:
            conv = Conversation(
                user_id=user_id,
                chat_room_id=chat_room_id,
                role="assistant",
                message="Test response",
                model=model,
                input_tokens=input_t,
                output_tokens=output_t
            )
            session.add(conv)
            
        try:
            await session.commit()
            print("Created test data.")
        except Exception as e:
            await session.rollback()
            print(f"Failed to create test data: {e}")
            return

    # 3. Verify Stats
    print("Verifying stats...")
    stats = await get_system_stats()
    token_usage = stats.get("token_usage", [])
    
    print("Token Usage Stats:")
    for usage in token_usage:
        print(f"Model: {usage['model']}, Input: {usage['input_tokens']}, Output: {usage['output_tokens']}, Total: {usage['total_tokens']}")

    # Assertions
    gpt4_stats = next((u for u in token_usage if u['model'] == 'gpt-4'), None)
    assert gpt4_stats is not None
    assert gpt4_stats['input_tokens'] >= 300 # >= because other tests might add data
    assert gpt4_stats['output_tokens'] >= 150
    
    claude_stats = next((u for u in token_usage if u['model'] == 'claude-3-opus'), None)
    assert claude_stats is not None
    assert claude_stats['total_tokens'] >= 450

    print("Verification Passed!")

    # Clean up
    async with get_async_session() as session:
        from sqlalchemy import delete
        await session.execute(delete(Conversation).where(Conversation.user_id == user_id))
        await session.execute(delete(ChatRoom).where(ChatRoom.id == chat_room_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()
        print("Cleanup complete.")

if __name__ == "__main__":
    asyncio.run(verify_token_stats())
