from agent.state import ChatState
from tools.search_tool import get_search_tool
from tools.retrieval_tool import get_retrieval_tool
from tools.memory_tool import get_memory_tool
from tools.time_tool import get_time_tool

# Define a custom tools node that lazily initializes tools
async def tools_node(state: ChatState):
    """
    Custom tools node that initializes tools at runtime to avoid
    database connection during module import.
    """
    from langgraph.prebuilt import ToolNode
    
    # Initialize tools at runtime
    search_tool = get_search_tool()
    retrieval_tool = get_retrieval_tool()
    memory_tool = get_memory_tool()
    time_tool = get_time_tool()
    
    # Create ToolNode with initialized tools
    tool_executor = ToolNode([search_tool, retrieval_tool, memory_tool, time_tool])
    
    # Execute the tools
    return await tool_executor.ainvoke(state)
