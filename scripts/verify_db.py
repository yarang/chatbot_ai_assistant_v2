import asyncio
import os
import sys

# Add project root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from core.config import get_settings
from core.database import Base, get_engine
from models.chat_room_model import ChatRoom
from models.conversation_model import Conversation
from models.persona_model import Persona
from models.usage_model import UsageLog

# Import all models to ensure they are registered with Base
from models.user_model import User


async def verify_database():
    print("🔍 Verifying database connection...")
    
    try:
        settings = get_settings()
        db_config = settings.database
        print(f"   Configured Host: {db_config.host}:{db_config.port}")
        print(f"   Configured Database: {db_config.name}")
        
        engine = get_engine()
        
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
            print("\n🔍 Verifying schema compatibility...")
            
            # Check if tables exist
            result = await conn.execute(
                text("""
                    SELECT tablename 
                    FROM pg_catalog.pg_tables 
                    WHERE schemaname = 'public'
                """)
            )
            existing_tables = {row[0] for row in result.fetchall()}
            print(f"   Found tables: {', '.join(existing_tables)}")
            
            expected_tables = {"users", "personas", "chat_rooms", "conversations"}
            missing_tables = expected_tables - existing_tables
            
            if missing_tables:
                print(f"⚠️  Missing tables: {', '.join(missing_tables)}")
                print("   You may need to run the schema creation script or let the app initialize.")
            else:
                print("✅ All core tables found.")

            # Inspect users table columns if it exists
            if "users" in existing_tables:
                print("\n🔍 Inspecting 'users' table columns...")
                result = await conn.execute(
                    text("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = 'users'
                    """)
                )
                columns = {row[0]: row[1] for row in result.fetchall()}
                print(f"   Columns: {columns}")

    except Exception as e:
        print(f"❌ Database verification failed: {e}")
        print("\nPossible causes:")
        print("1. Database server is not running")
        print("2. Incorrect credentials in environment variables")
        print("3. Database 'chatbot_db' does not exist")

if __name__ == "__main__":
    asyncio.run(verify_database())
