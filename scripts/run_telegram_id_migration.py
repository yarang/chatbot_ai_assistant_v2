#!/usr/bin/env python3
"""
Apply database migration to fix telegram_id integer overflow
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
    """Run the migration to change telegram_id columns to BIGINT"""
    
    engine = get_engine()
    
    migrations = [
        ("users.telegram_id", "ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT"),
        ("chat_rooms.telegram_chat_id", "ALTER TABLE chat_rooms ALTER COLUMN telegram_chat_id TYPE BIGINT"),
    ]
    
    print("=" * 60)
    print("Telegram ID Migration: INTEGER -> BIGINT")
    print("=" * 60)
    print("\nApplying migration...")
    
    try:
        async with engine.begin() as conn:
            for column_name, sql in migrations:
                print(f"  - Altering {column_name}...")
                await conn.execute(text(sql))
        
        print("\n✅ Migration completed successfully!")
        print("\nChanged columns:")
        print("  - users.telegram_id: INTEGER -> BIGINT")
        print("  - chat_rooms.telegram_chat_id: INTEGER -> BIGINT")
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
