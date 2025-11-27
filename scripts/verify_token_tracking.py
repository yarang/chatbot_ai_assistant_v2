"""
Manual Token Tracking Verification Script

This script tests the token tracking functionality with the actual graph and LLM.
Run this after starting the application to verify token tracking works correctly.
"""

import asyncio
import uuid
from langchain_core.messages import HumanMessage
from core.graph import graph
from repository.conversation_repository import get_history
from repository.chat_room_repository import create_chat_room, get_chat_room_by_telegram_id
from repository.user_repository import create_or_update_user
from sqlalchemy import select, desc
from core.database import get_async_session
from models.conversation_model import Conversation


async def test_token_tracking():
    """Test token tracking end-to-end"""
    
    print("=" * 60)
    print("Token Tracking Verification Test")
    print("=" * 60)
    
    # Create test user and chat room
    telegram_user_id = 999999
    telegram_chat_id = -999999
    
    async with get_async_session() as session:
        # Create user
        user = await create_or_update_user(
            session=session,
            telegram_id=telegram_user_id,
            username="test_token_tracking",
            first_name="Token",
            last_name="Test"
        )
        await session.commit()
        
        # Create chat room
        chat_room = await create_chat_room(
            session=session,
            telegram_chat_id=telegram_chat_id,
            name="Token Test Room",
            type="private",
            username="test_token_tracking"
        )
        await session.commit()
        
        print(f"\n✓ Created test user: {user.id}")
        print(f"✓ Created test chat room: {chat_room.id}")
        
        # Test 1: Simple question to GeneralAssistant
        print("\n" + "-" * 60)
        print("Test 1: Simple question (GeneralAssistant)")
        print("-" * 60)
        
        state = {
            "messages": [HumanMessage(content="Hello, how are you?")],
            "user_id": str(user.id),
            "chat_room_id": str(chat_room.id),
            "persona_content": "You are a helpful AI assistant.",
            "model_name": "gemini-pro",
            "summary": None,
            "next": "",
            "input_tokens_used": 0,
            "output_tokens_used": 0
        }
        
        result = await graph.ainvoke(state)
        
        print(f"\n✓ Graph executed successfully")
        print(f"  Input tokens: {result.get('input_tokens_used', 'N/A')}")
        print(f"  Output tokens: {result.get('output_tokens_used', 'N/A')}")
        
        # Check database
        stmt = (
            select(Conversation)
            .where(Conversation.chat_room_id == chat_room.id)
            .where(Conversation.role == "assistant")
            .order_by(desc(Conversation.created_at))
            .limit(1)
        )
        result_db = await session.execute(stmt)
        conversation = result_db.scalar_one_or_none()
        
        if conversation:
            print(f"\n✓ Conversation saved to database:")
            print(f"  Model: {conversation.model}")
            print(f"  Input tokens: {conversation.input_tokens}")
            print(f"  Output tokens: {conversation.output_tokens}")
            print(f"  Message: {conversation.message[:100]}...")
            
            if conversation.input_tokens and conversation.input_tokens > 0:
                print("\n✅ SUCCESS: Token tracking is working!")
            else:
                print("\n⚠️  WARNING: Tokens are 0 or None")
        else:
            print("\n❌ ERROR: No conversation found in database")
        
        # Test 2: Question that triggers Researcher
        print("\n" + "-" * 60)
        print("Test 2: Research question (Researcher)")
        print("-" * 60)
        
        state2 = {
            "messages": [HumanMessage(content="What is the latest news about AI?")],
            "user_id": str(user.id),
            "chat_room_id": str(chat_room.id),
            "persona_content": None,
            "model_name": "gemini-pro",
            "summary": None,
            "next": "",
            "input_tokens_used": 0,
            "output_tokens_used": 0
        }
        
        result2 = await graph.ainvoke(state2)
        
        print(f"\n✓ Graph executed successfully")
        print(f"  Input tokens: {result2.get('input_tokens_used', 'N/A')}")
        print(f"  Output tokens: {result2.get('output_tokens_used', 'N/A')}")
        
        # Check last conversation
        stmt = (
            select(Conversation)
            .where(Conversation.chat_room_id == chat_room.id)
            .where(Conversation.role == "assistant")
            .order_by(desc(Conversation.created_at))
            .limit(1)
        )
        result_db = await session.execute(stmt)
        conversation2 = result_db.scalar_one_or_none()
        
        if conversation2 and conversation2.id != conversation.id:
            print(f"\n✓ New conversation saved to database:")
            print(f"  Model: {conversation2.model}")
            print(f"  Input tokens: {conversation2.input_tokens}")
            print(f"  Output tokens: {conversation2.output_tokens}")
            print(f"  Message: {conversation2.message[:100]}...")
            
            if conversation2.input_tokens and conversation2.input_tokens > 0:
                print("\n✅ SUCCESS: Token tracking is working for research queries!")
            else:
                print("\n⚠️  WARNING: Tokens are 0 or None")
        
        # Show summary of all conversations
        print("\n" + "=" * 60)
        print("All Conversations in Test Chat Room")
        print("="  * 60)
        
        stmt = (
            select(Conversation)
            .where(Conversation.chat_room_id == chat_room.id)
            .order_by(Conversation.created_at)
        )
        result_all = await session.execute(stmt)
        all_conversations = result_all.scalars().all()
        
        for conv in all_conversations:
            tokens_str = f"[{conv.input_tokens or 0}in + {conv.output_tokens or 0}out]" if conv.role == "assistant" else ""
            print(f"\n{conv.role}: {conv.message[:80]}... {tokens_str}")
            if conv.model:
                print(f"  Model: {conv.model}")
        
        print("\n" + "=" * 60)
        print("Verification Complete")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_token_tracking())
