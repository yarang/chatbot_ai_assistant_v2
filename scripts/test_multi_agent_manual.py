"""
Manual test script for Multi-Agent Orchestration.
This script performs a simple test by invoking the graph with different queries
to see how the Supervisor routes to different agents.
"""

import asyncio
from core.graph import graph
from langchain_core.messages import HumanMessage
import uuid

async def test_general_query():
    """Test a general conversational query."""
    print("\n=== Testing General Query ===")
    user_id = str(uuid.uuid4())
    chat_room_id = str(uuid.uuid4())
    
    state = {
        "messages": [HumanMessage(content="안녕하세요!")],
        "user_id": user_id,
        "chat_room_id": chat_room_id,
        "persona_content": None,
        "model_name": None,
        "summary": None,
        "next": ""
    }
    
    try:
        result = await graph.ainvoke(state)
        print(f"User: 안녕하세요!")
        print(f"Assistant: {result['messages'][-1].content}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_research_query():
    """Test a query that should trigger the Researcher agent."""
    print("\n=== Testing Research Query ===")
    user_id = str(uuid.uuid4())
    chat_room_id = str(uuid.uuid4())
    
    state = {
        "messages": [HumanMessage(content="Can you search for the latest news on AI?")],
        "user_id": user_id,
        "chat_room_id": chat_room_id,
        "persona_content": None,
        "model_name": None,
        "summary": None,
        "next": ""
    }
    
    try:
        result = await graph.ainvoke(state)
        print(f"User: Can you search for the latest news on AI?")
        print(f"Assistant: {result['messages'][-1].content}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("Starting Manual Multi-Agent Tests...")
    
    # Test 1: General query
    success1 = await test_general_query()
    
    # Test 2: Research query
    success2 = await test_research_query()
    
    print("\n=== Test Summary ===")
    print(f"General Query: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Research Query: {'✓ PASS' if success2 else '✗ FAIL'}")

if __name__ == "__main__":
    asyncio.run(main())
