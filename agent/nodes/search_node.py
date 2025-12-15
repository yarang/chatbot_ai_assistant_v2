from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm import get_llm
from tools.search_tool import get_search_tool
from tools.retrieval_tool import get_retrieval_tool
from tools.memory_tool import get_memory_tool
from tools.time_tool import get_time_tool
from repository.conversation_repository import get_history
from agent.state import ChatState

async def researcher_node(state: ChatState):
    llm = get_llm(state.get("model_name"))
    search_tool = get_search_tool()
    chat_room_id = state.get("chat_room_id")
    retrieval_tool = get_retrieval_tool(chat_room_id=str(chat_room_id) if chat_room_id else None)
    memory_tool = get_memory_tool()
    time_tool = get_time_tool()
    tools = [search_tool, retrieval_tool, memory_tool, time_tool]
    
    # Researcher agent
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a Researcher. You have access to search tools and a time tool."
                " Use them to find information requested by the user."
                " If you have found the information, summarize it and answer the user.\n"
                "IMPORTANT: If the user asks for ANY information, you MUST use the provided tools (search_internal_knowledge or search_google) to find it. Do not rely on your internal knowledge alone.\n"
                "IMPORTANT: When using the 'search_internal_knowledge' tool, you MUST cite the source of the information in your response. The tool output provides the source (e.g., 'Source: ...'). Append the source at the end of your answer.\n"
                "IMPORTANT: Do not simulate the user. Do not generate 'User:' or 'Human:' dialogue.\n"
                f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    
    # Determine forcing strategy (Method B)
    # If the last message is from the user, we FORCE the usage of the retrieval tool.
    # This prevents the AI from answering from memory.
    last_message = state["messages"][-1]
    force_retrieval = isinstance(last_message, HumanMessage)
    
    if force_retrieval:
        # Force the specific tool
        chain = prompt | llm.bind_tools(tools, tool_choice="search_internal_knowledge")
    else:
        # Auto mode for subsequent turns (e.g. after tool execution)
        chain = prompt | llm.bind_tools(tools)
    
    # Construct messages including history and summary
    messages = []
    if state.get("summary"):
        messages.append(SystemMessage(content=f"Previous conversation summary: {state['summary']}"))
        
    # Fetch recent history
    chat_room_id = state["chat_room_id"]
    history_tuples = await get_history(chat_room_id, limit=10)
    for role, content, name, _ in history_tuples:
        if role == "user":
            messages.append(HumanMessage(content=content, name=name))
        else:
            messages.append(AIMessage(content=content))
            
    messages.extend(state["messages"])
    
    response = await chain.ainvoke({"messages": messages})

    # Capture system prompt
    full_system_prompt = (
        "You are a Researcher. You have access to search tools and a time tool."
        " Use them to find information requested by the user."
        " If you have found the information, summarize it and answer the user.\n"
        "IMPORTANT: If the user asks for ANY information, you MUST use the provided tools (search_internal_knowledge or search_google) to find it. Do not rely on your internal knowledge alone.\n"
        "IMPORTANT: When using the 'search_internal_knowledge' tool, you MUST cite the source of the information in your response. The tool output provides the source (e.g., 'Source: ...'). Append the source at the end of your answer.\n"
        "IMPORTANT: Do not simulate the user. Do not generate 'User:' or 'Human:' dialogue.\n"
        f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Track token usage
    input_tokens = state.get("input_tokens_used", 0)
    output_tokens = state.get("output_tokens_used", 0)
    
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        input_tokens += response.usage_metadata.get('input_tokens', 0)
        output_tokens += response.usage_metadata.get('output_tokens', 0)
    
    return {
        "messages": [response],
        "input_tokens_used": input_tokens,
        "output_tokens_used": output_tokens,
        "applied_system_prompt": full_system_prompt
    }
