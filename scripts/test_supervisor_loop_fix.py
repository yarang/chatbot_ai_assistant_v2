
import asyncio
from langchain_core.messages import AIMessage, HumanMessage
from agent.nodes.router_node import supervisor_node

async def test_supervisor_loop_prevention():
    print("Testing Supervisor Loop Prevention...")
    
    # Simulate a state where the AI has just responded
    mock_state = {
        "messages": [
            HumanMessage(content="Hello"),
            AIMessage(content="Hello! How can I help you today?")
        ],
        "user_id": "test_user",
        "chat_room_id": "test_room",
        "model_name": "gemini-1.5-flash", 
        "summary": None
    }
    
    print("Invoking supervisor_node with an AIMessage as the last message...")
    result = await supervisor_node(mock_state)
    
    print(f"Result: {result}")
    
    if result.get("next") == "FINISH":
        print("SUCCESS: Supervisor correctly decided to FINISH.")
    else:
        print(f"FAILURE: Supervisor decided to route to {result.get('next')}. Fix not working.")

if __name__ == "__main__":
    asyncio.run(test_supervisor_loop_prevention())
