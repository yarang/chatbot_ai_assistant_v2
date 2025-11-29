import pytest
import asyncio
from datetime import datetime
from tools.time_tool import get_time_tool
from core.graph import graph
from langchain_core.messages import HumanMessage

def test_time_tool():
    tool = get_time_tool()
    result = tool.invoke("")
    print(f"Time tool result: {result}")
    assert isinstance(result, str)
    # Check format roughly
    assert datetime.strptime(result, "%Y-%m-%d %H:%M:%S")

@pytest.mark.asyncio
async def test_graph_streaming_updates():
    """
    Verify that graph.astream with stream_mode="updates" 
    yields events in the expected format (dict with node name keys).
    """
    import uuid
    initial_state = {
        "messages": [HumanMessage(content="What time is it?")],
        "user_id": str(uuid.uuid4()),
        "chat_room_id": str(uuid.uuid4()),
        "model_name": "gemini-1.5-flash"
    }
    
    print("\nStarting stream test...")
    chunk_count = 0
    async for event in graph.astream(initial_state, stream_mode="updates"):
        print(f"Event received: {event.keys()}")
        chunk_count += 1
        
        # Verify event structure
        for node_name, node_output in event.items():
            assert isinstance(node_output, dict)
            # We expect 'messages' in the output for most nodes
            if "messages" in node_output:
                print(f"Node {node_name} produced messages")
                
    print(f"Total chunks: {chunk_count}")
    assert chunk_count > 0

if __name__ == "__main__":
    # Manual run if executed directly
    test_time_tool()
    asyncio.run(test_graph_streaming_updates())
