#!/usr/bin/env python3
"""
Add missing summary column to chat_rooms table
"""

import os
import sys
import asyncio

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy import text
from core.database import get_engine

# Load environment variables
load_dotenv()


async def run_migration():
    """Add summary column to chat_rooms table"""
    
    engine = get_engine()
    
    migration_sql = "ALTER TABLE chat_rooms ADD COLUMN IF NOT EXISTS summary TEXT"
    
    print("=" * 60)
    print("Chat Rooms Migration: Add summary column")
    print("=" * 60)
    print("\nApplying migration...")
    
    try:
        async with engine.begin() as conn:
            print(f"  - Adding summary column to chat_rooms...")
            await conn.execute(text(migration_sql))
        
        print("\n✅ Migration completed successfully!")
        print("\nAdded column:")
        print("  - chat_rooms.summary: TEXT (nullable)")
        print("\n" + "=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 60)
        return False
    finally:
        await engine.dispose()


def main():
    success = asyncio.run(run_migration())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
