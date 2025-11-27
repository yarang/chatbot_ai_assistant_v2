from typing import Annotated, List, Optional, Literal
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from core.llm import get_llm
from repository.conversation_repository import get_history, add_message
from repository.chat_room_repository import get_chat_room_by_id, update_chat_room_summary
from repository.persona_repository import get_persona_by_id
from tools.search_tool import get_search_tool
from tools.retrieval_tool import get_retrieval_tool
import functools
import operator

# Define the agents
MEMBERS = ["Researcher", "GeneralAssistant"]
OPTIONS = ["FINISH"] + MEMBERS

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    chat_room_id: str
    persona_content: Optional[str]
    model_name: Optional[str]
    summary: Optional[str]
    next: str
    input_tokens_used: Optional[int]
    output_tokens_used: Optional[int]

async def retrieve_data_node(state: ChatState):
    chat_room_id = state["chat_room_id"]
    chat_room = await get_chat_room_by_id(chat_room_id)
    
    persona_content = None
    summary = None
    if chat_room:
        if chat_room.persona_id:
            persona = await get_persona_by_id(chat_room.persona_id)
            if persona:
                persona_content = persona.content
        summary = chat_room.summary
            
    return {"persona_content": persona_content, "summary": summary}

async def supervisor_node(state: ChatState):
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        " following workers: {members}. Given the following user request,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with their results and status. When finished,"
        " respond with FINISH."
    )
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            (
                "system",
                "Given the conversation above, who should act next?"
                " Or should we FINISH? Select one of: {options}",
            ),
        ]
    ).partial(options=str(OPTIONS), members=", ".join(MEMBERS))
    
    llm = get_llm(state.get("model_name"))
    
    # Using function calling to enforce structured output for routing
    function_def = {
        "name": "route",
        "description": "Select the next role.",
        "parameters": {
            "title": "routeSchema",
            "type": "object",
            "properties": {
                "next": {
                    "title": "Next",
                    "type": "string",
                    "enum": OPTIONS,
                }
            },
            "required": ["next"],
        },
    }
    
    # Bind function and create chain
    # Note: Gemini supports function calling.
    supervisor_chain = (
        prompt
        | llm.bind_tools(tools=[function_def], tool_choice="route")
        | JsonOutputFunctionsParser()
    )
    
    # We need to construct messages including history and summary
    messages = []
    if state.get("summary"):
        messages.append(SystemMessage(content=f"Previous conversation summary: {state['summary']}"))
        
    # Fetch recent history
    chat_room_id = state["chat_room_id"]
    history_tuples = await get_history(chat_room_id, limit=10)
    for role, content in history_tuples:
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
            
    messages.extend(state["messages"])
    
    try:
        result = await supervisor_chain.ainvoke({"messages": messages})
        
        # Extract token usage from the last message if available
        # Note: supervisor_chain uses JsonOutputFunctionsParser, so we need to track tokens differently
        # For now, we'll skip supervisor token tracking as it's mainly for routing
        return {"next": result["next"]}
    except Exception as e:
        # Fallback if supervisor fails
        print(f"Supervisor failed: {e}")
        return {"next": "GeneralAssistant"}

async def researcher_node(state: ChatState):
    llm = get_llm(state.get("model_name"))
    search_tool = get_search_tool()
    retrieval_tool = get_retrieval_tool()
    tools = [search_tool, retrieval_tool]
    
    # Researcher agent
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a Researcher. You have access to search tools."
                " Use them to find information requested by the user."
                " If you have found the information, summarize it and answer the user."
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    
    chain = prompt | llm.bind_tools(tools)
    
    # Construct messages similar to supervisor but maybe less history?
    # For now, reuse the same message construction logic or pass state["messages"]
    # But state["messages"] only has current turn.
    # We should probably inject history into state["messages"] at the beginning of the graph?
    # Or just reconstruct here.
    messages = state["messages"]
    
    response = await chain.ainvoke({"messages": messages})
    
    # Track token usage
    input_tokens = state.get("input_tokens_used", 0)
    output_tokens = state.get("output_tokens_used", 0)
    
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        input_tokens += response.usage_metadata.get('input_tokens', 0)
        output_tokens += response.usage_metadata.get('output_tokens', 0)
    
    return {
        "messages": [response],
        "input_tokens_used": input_tokens,
        "output_tokens_used": output_tokens
    }

async def general_assistant_node(state: ChatState):
    llm = get_llm(state.get("model_name"))
    
    persona_content = state.get("persona_content") or "You are a helpful AI assistant."
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", persona_content),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    
    chain = prompt | llm
    
    messages = state["messages"]
    response = await chain.ainvoke({"messages": messages})
    
    # Track token usage
    input_tokens = state.get("input_tokens_used", 0)
    output_tokens = state.get("output_tokens_used", 0)
    
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        input_tokens += response.usage_metadata.get('input_tokens', 0)
        output_tokens += response.usage_metadata.get('output_tokens', 0)
    
    return {
        "messages": [response],
        "input_tokens_used": input_tokens,
        "output_tokens_used": output_tokens
    }

async def save_conversation_node(state: ChatState):
    user_id = state["user_id"]
    chat_room_id = state["chat_room_id"]
    messages = state["messages"]
    
    if not messages:
        return {}
        
    # Find the first user message in this turn
    user_message = None
    for msg in messages:
        if isinstance(msg, HumanMessage):
            user_message = msg
            break
            
    # Find the last AI message
    ai_message = messages[-1]
    
    if user_message and isinstance(ai_message, AIMessage) and not ai_message.tool_calls:
         # Handle multimodal content
        user_content = user_message.content
        if isinstance(user_content, list):
            text_parts = [item["text"] for item in user_content if item.get("type") == "text"]
            user_content_str = " ".join(text_parts)
            if any(item.get("type") == "image_url" for item in user_content):
                 user_content_str += " [Image]"
            user_content = user_content_str
        
        # Get token usage from state
        input_tokens = state.get("input_tokens_used", 0)
        output_tokens = state.get("output_tokens_used", 0)
        model_name = state.get("model_name", "gemini-pro")
        
        # Handle multimodal content for AI message
        ai_content = ai_message.content
        if isinstance(ai_content, list):
            text_parts = [item["text"] for item in ai_content if isinstance(item, dict) and item.get("type") == "text"]
            ai_content = " ".join(text_parts)
        
        await add_message(user_id, chat_room_id, "user", str(user_content))
        await add_message(
            user_id, 
            chat_room_id, 
            "assistant", 
            str(ai_content),
            model=model_name,
            input_tokens=input_tokens if input_tokens > 0 else None,
            output_tokens=output_tokens if output_tokens > 0 else None
        )
             
    return {}

async def summarize_conversation_node(state: ChatState):
    chat_room_id = state["chat_room_id"]
    
    # Check if we need to summarize
    # Logic: If history length > N (e.g. 10), summarize.
    # We need to fetch history to check length.
    history_tuples = await get_history(chat_room_id, limit=100) # Fetch more to check total
    
    if len(history_tuples) > 10:
        llm = get_llm(state.get("model_name"))
        
        # Create summary prompt
        # We summarize everything except the last few messages to keep context fresh
        to_summarize = history_tuples[:-4] # Keep last 4 messages
        if not to_summarize:
            return {}
            
        conversation_text = "\n".join([f"{role}: {content}" for role, content in to_summarize])
        current_summary = state.get("summary", "")
        
        prompt = f"""
        Summarize the following conversation concisely.
        Current Summary: {current_summary}
        
        New Conversation to add:
        {conversation_text}
        
        Update the summary to include the new information.
        """
        
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        new_summary = response.content
        
        # Track token usage for logging purposes (not saved to conversation)
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            from core.logger import get_logger
            logger = get_logger(__name__)
            logger.info(f"Summary generation used {response.usage_metadata.get('input_tokens', 0)} input tokens and {response.usage_metadata.get('output_tokens', 0)} output tokens")
        
        # Update DB
        await update_chat_room_summary(chat_room_id, new_summary)
        
        return {"summary": new_summary}
        
    return {}

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
    
    # Create ToolNode with initialized tools
    tool_executor = ToolNode([search_tool, retrieval_tool])
    
    # Execute the tools
    return await tool_executor.ainvoke(state)

# Define Graph
workflow = StateGraph(ChatState)

workflow.add_node("retrieve_data", retrieve_data_node)
workflow.add_node("Supervisor", supervisor_node)
workflow.add_node("Researcher", researcher_node)
workflow.add_node("GeneralAssistant", general_assistant_node)
workflow.add_node("tools", tools_node)  # Use custom tools node
workflow.add_node("save_conversation", save_conversation_node)
workflow.add_node("summarize_conversation", summarize_conversation_node)

# Edges
workflow.add_edge(START, "retrieve_data")
workflow.add_edge("retrieve_data", "Supervisor")

# Conditional edge from Supervisor
workflow.add_conditional_edges(
    "Supervisor",
    lambda x: x["next"],
    {
        "Researcher": "Researcher",
        "GeneralAssistant": "GeneralAssistant",
        "FINISH": "save_conversation",
    },
)

# Researcher flow
def route_researcher(state):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return "Supervisor"

workflow.add_conditional_edges("Researcher", route_researcher, {"tools": "tools", "Supervisor": "Supervisor"})
workflow.add_edge("tools", "Researcher")

# GeneralAssistant flow
workflow.add_edge("GeneralAssistant", "Supervisor")

# End flow
workflow.add_edge("save_conversation", "summarize_conversation")
workflow.add_edge("summarize_conversation", END)

graph = workflow.compile()
