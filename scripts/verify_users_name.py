import asyncio
import os
import sys
import uuid

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import get_async_session, init_db
from repository.user_repository import upsert_user
from repository.chat_room_repository import upsert_chat_room
from repository.conversation_repository import add_message, get_history

async def verify_user_names():
    print("🔍 Verifying retrieving user names in history...")
    
    # Initialize DB (creates tables if needed)
    await init_db()

    # Create dummy data
    test_email = f"test_{uuid.uuid4()}@example.com"
    test_user_name = "TestAlice"
    test_chat_room_id = str(uuid.uuid4())
    
    async with get_async_session() as session:
        # Create User
        print(f"Creating user {test_user_name}...")
        user = await upsert_user(
            email=test_email,
            first_name=test_user_name,
            username="alice123"
        )
        
        # Create Chat Room
        print("Creating chat room...")
        chat_room = await upsert_chat_room(
            telegram_chat_id=123456789,
            name="Test Room",
            type="group"
        )
        
        # Add Message
        print("Adding message...")
        await add_message(
            user_id=user.id,
            chat_room_id=chat_room.id,
            role="user",
            message="Hello, I am Alice!"
        )
        
        # Get History
        print("Fetching history...")
        history = await get_history(chat_room.id, limit=5)
        
        print("\nChecking results:")
        found = False
        for item in history:
            # Expecting tuple (role, message, name, applied_system_prompt)
            if len(item) == 4:
                role, message, name, _ = item
                print(f"Role: {role}, Message: {message}, Name: {name}")
                if name == test_user_name:
                    found = True
            else:
                print(f"❌ Unexpected item format: {item}")
        
        if found:
            print("\n✅ Verification SUCCESS: Retrieved correct user name!")
        else:
            print("\n❌ Verification FAILED: User name not found in history.")

if __name__ == "__main__":
    asyncio.run(verify_user_names())
