from typing import Annotated, List, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from core.llm import get_llm
from repository.conversation_repository import get_history, add_message
from repository.chat_room_repository import get_chat_room_by_id
from repository.persona_repository import get_persona_by_id
import uuid

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    user_id: str
    chat_room_id: str
    persona_content: Optional[str]
    model_name: Optional[str]

async def retrieve_data_node(state: ChatState):
    chat_room_id = state["chat_room_id"]
    chat_room = await get_chat_room_by_id(chat_room_id)
    
    persona_content = None
    if chat_room and chat_room.persona_id:
        persona = await get_persona_by_id(chat_room.persona_id)
        if persona:
            persona_content = persona.content
            
    return {"persona_content": persona_content}

async def generate_response_node(state: ChatState):
    llm = get_llm(state.get("model_name"))
    chat_room_id = state["chat_room_id"]
    
    # Construct messages
    messages = []
    
    # System Message (Persona)
    if state.get("persona_content"):
        messages.append(SystemMessage(content=state["persona_content"]))
        
    # History
    history_tuples = await get_history(chat_room_id, limit=20)
    for role, content in history_tuples:
        if role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))
            
    # Current Input
    # state['messages'] contains the input message(s) for this turn.
    # We assume the last message is the user's new input.
    input_message = state["messages"][-1]
    messages.append(input_message)
    
    response = await llm.ainvoke(messages)
    
    return {"messages": [response]}

async def save_conversation_node(state: ChatState):
    user_id = state["user_id"]
    chat_room_id = state["chat_room_id"]
    messages = state["messages"]
    
    # We expect the last message to be AI response, and the one before to be User input.
    if len(messages) >= 2:
        input_msg = messages[-2]
        output_msg = messages[-1]
        
        # Verify types to be safe
        if isinstance(output_msg, AIMessage):
             # Save User Message (if it's new)
             # Note: In a real robust system, we might want to ensure we don't save duplicates if retrying.
             # But here we assume simple flow.
             await add_message(user_id, chat_room_id, "user", input_msg.content)
             # Save AI Message
             await add_message(user_id, chat_room_id, "assistant", output_msg.content)
             
    return {}

workflow = StateGraph(ChatState)
workflow.add_node("retrieve_data", retrieve_data_node)
workflow.add_node("generate_response", generate_response_node)
workflow.add_node("save_conversation", save_conversation_node)

workflow.add_edge(START, "retrieve_data")
workflow.add_edge("retrieve_data", "generate_response")
workflow.add_edge("generate_response", "save_conversation")
workflow.add_edge("save_conversation", END)

graph = workflow.compile()
