import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

async def mock_impl(update):
    user_id = update.effective_user.id
    print(f"Start processing for user {user_id}")
    await asyncio.sleep(1.0)
    print(f"End processing for user {user_id}")

async def main():
    print("Verifying Concurrency Control...")
    
    # Patch the implementation to sleep
    with patch("api.telegram_router._process_update_impl", side_effect=mock_impl) as mock_method:
        from api.telegram_router import process_update
        
        # Scenario 1: Same User (Sequential)
        print("\n--- Scenario 1: Same User (Should take ~2.0s) ---")
        user1 = MagicMock()
        user1.id = 111
        update1 = MagicMock()
        update1.effective_user = user1
        
        start_time = time.time()
        await asyncio.gather(
            process_update(update1),
            process_update(update1)
        )
        duration = time.time() - start_time
        print(f"Duration: {duration:.2f}s")
        if 1.9 <= duration <= 2.2:
            print("✅ PASS: Sequential processing enforced")
        else:
            print("❌ FAIL: Concurrent processing detected (or too slow)")

        # Scenario 2: Different Users (Parallel)
        print("\n--- Scenario 2: Different Users (Should take ~1.0s) ---")
        user2 = MagicMock()
        user2.id = 222
        update2 = MagicMock()
        update2.effective_user = user2
        
        user3 = MagicMock()
        user3.id = 333
        update3 = MagicMock()
        update3.effective_user = user3
        
        start_time = time.time()
        await asyncio.gather(
            process_update(update2),
            process_update(update3)
        )
        duration = time.time() - start_time
        print(f"Duration: {duration:.2f}s")
        if 0.9 <= duration <= 1.2:
            print("✅ PASS: Parallel processing allowed")
        else:
            print("❌ FAIL: Sequential processing for different users (or too slow)")

if __name__ == "__main__":
    asyncio.run(main())
