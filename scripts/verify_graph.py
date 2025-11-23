import asyncio
import uuid
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.graph import graph
from langchain_core.messages import HumanMessage
from repository.user_repository import upsert_user
from repository.chat_room_repository import upsert_chat_room
from core.database import get_engine, Base
from models.user_model import User
from models.persona_model import Persona
from models.chat_room_model import ChatRoom
from models.conversation_model import Conversation

# Set creation order for init_db (Optional if using create_all)
User.__table__.info["creation_order"] = 1
Persona.__table__.info["creation_order"] = 2
ChatRoom.__table__.info["creation_order"] = 3
Conversation.__table__.info["creation_order"] = 4

async def verify_graph():
    print("Initializing DB...")
    engine = get_engine()
    async with engine.begin() as conn:
        # Warning: This drops all tables!
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    print("Creating test user and chat room...")
    user = await upsert_user(
        email="test_graph@example.com",
        telegram_id=123456789,
        username="test_user",
        first_name="Test",
        last_name="User"
    )
    
    chat_room = await upsert_chat_room(
        telegram_chat_id=123456789,
        name="Test Chat",
        type="private",
        username="test_user"
    )
    
    print(f"User ID: {user.id}")
    print(f"Chat Room ID: {chat_room.id}")
    
    print("Invoking Graph...")
    inputs = {
        "messages": [HumanMessage(content="Hello, who are you?")],
        "user_id": str(user.id),
        "chat_room_id": str(chat_room.id),
        "model_name": "gemini-1.5-flash" # Use a valid model name if needed
    }
    
    try:
        result = await graph.ainvoke(inputs)
        print("Graph Result:")
        for msg in result["messages"]:
            print(f"[{type(msg).__name__}]: {msg.content}")
            
        print("Verification Successful!")
    except Exception as e:
        print(f"Verification Failed: {e}")

if __name__ == "__main__":
    asyncio.run(verify_graph())
