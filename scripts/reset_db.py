import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.database import get_engine, init_db
from sqlalchemy import text
import models  # Import models to register them with Base

async def reset_db():
    print("Resetting DB...")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS users, personas, chat_rooms, conversations, usage_logs, token_usage, messages, knowledge_docs, persona_evaluations CASCADE"))
    
    print("Tables dropped.")
    print("Recreating tables...")
    await init_db()
    
    print("DB Reset Complete.")

if __name__ == "__main__":
    asyncio.run(reset_db())
