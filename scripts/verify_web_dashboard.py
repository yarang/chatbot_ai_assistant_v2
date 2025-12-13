
import asyncio
import os
import sys
import uuid
from unittest.mock import AsyncMock, MagicMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock environment
os.environ["TELEGRAM_BOT_TOKEN"] = "test_token"
if "ADMIN_IDS" not in os.environ:
    os.environ["ADMIN_IDS"] = "12345,67890"

async def test_repository_logic():
    print("Testing Repo Logic...")
    from repository.chat_room_repository import ChatRoomRepository # Direct import
    
    repo = ChatRoomRepository()
    mock_session = AsyncMock()
    
    # Mock result for get_chat_rooms_by_user_id
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = ["room1", "room2"]
    mock_session.execute.return_value = mock_result
    
    rooms = await repo.get_chat_rooms_by_user_id(mock_session, uuid.uuid4())
    print(f"Rooms found: {rooms}")
    assert len(rooms) == 2
    
async def test_router_integration():
    print("\nTesting Router Integration (Simulation)...")
    # This is harder to test fully without a real DB, but we can verify imports and function calls
    from api.web_router import dashboard
    print("Dashboard endpoint imported successfully.")

if __name__ == "__main__":
    asyncio.run(test_repository_logic())
    asyncio.run(test_router_integration())
