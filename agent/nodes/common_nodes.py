from datetime import datetime
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
from core.llm import get_llm
from repository.conversation_repository import get_history, add_message
from repository.chat_room_repository import get_chat_room_by_id, update_chat_room_summary
from repository.persona_repository import get_persona_by_id
from core.vector_store import get_vector_store
from agent.state import ChatState

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

        # Index messages into vector store for RAG
        try:
            vector_store = get_vector_store(collection_name="conversation_history")
            
            # Index user message
            user_doc = Document(
                page_content=str(user_content),
                metadata={
                    "user_id": str(user_id),
                    "chat_room_id": str(chat_room_id),
                    "role": "user",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Index AI message
            ai_doc = Document(
                page_content=str(ai_content),
                metadata={
                    "user_id": str(user_id),
                    "chat_room_id": str(chat_room_id),
                    "role": "assistant",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Use run_in_executor to avoid async_mode error with GoogleGenerativeAIEmbeddings
            # The async implementation of embeddings might be trying to use async client incorrectly
            import asyncio
            await asyncio.to_thread(vector_store.add_documents, [user_doc, ai_doc])
        except Exception as e:
            print(f"Error indexing conversation: {e}")
             
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
        
        try:
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
        except Exception as e:
            if "429" in str(e) or "ResourceExhausted" in str(e):
                print(f"Skipping summary generation due to rate limit: {e}")
                return {}
            raise e
        
    return {}
