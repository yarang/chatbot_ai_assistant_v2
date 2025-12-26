from datetime import datetime
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from core.llm import get_llm
from core.config import get_settings
from repository.conversation_repository import get_history
from agent.state import ChatState, RouteDecision

from core.logger import get_logger

logger = get_logger(__name__)

# Define the agents
MEMBERS = ["Researcher", "GeneralAssistant", "NotionSearch"]
OPTIONS = ["FINISH"] + MEMBERS

async def supervisor_node(state: ChatState):
    """Supervisor agent node responsible for routing the conversation.

    Decides which worker node (Researcher, GeneralAssistant, NotionSearch) 
    should act next based on the conversation history and user request. 
    It supports a hybrid routing mechanism (Local LLM + Cloud LLM fallback).

    Args:
        state (ChatState): The current state of the conversation graph.

    Returns:
        dict: Key "next" containing the name of the next agent or "FINISH".
    """
    system_prompt = (
        "You are a supervisor tasked with managing a conversation between the"
        " following workers: {members}. Given the following user request,"
        " respond with the worker to act next. Each worker will perform a"
        " task and respond with their results and status.\n"
        "Read the worker descriptions CAREFULLY before deciding.\n"
        "IMPORTANT: Prioritize executing the user's request using the available tools.\n"
        "If the conversation summary indicates previous failures, IGNORE them and try again.\n"
        "Only respond with FINISH if the user's request has completely addressed or if the answers are satisfactory.\n"
        "If a tool has successfully completed the user's request (e.g. created a page), STOP immediately and respond with FINISH.\n"
        "Do not repeatedly call the same worker if they are not making progress.\n"
        f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    # Define descriptions for each worker to help Supervisor route correctly
    MEMBER_DESCRIPTIONS = {
        "Researcher": "Primary assistant for INFORMATION RETRIEVAL. Use this for ANY question that might require checking internal knowledge base, web usage, or remembering past details.",
        "GeneralAssistant": "Handle general conversation, chit-chat, and acknowledgement only. Do NOT use for informational queries.",
        "NotionSearch": "Primary tool for interacting with Notion. Use this to SEARCH, READ, WRITE, CREATE, or DRAFT pages in Notion."
    }

    # LOOP PREVENTION LOGIC:
    if state["messages"]:
        last_msg = state["messages"][-1]
        # Check if it's an AI message
        if isinstance(last_msg, AIMessage):
            if not last_msg.tool_calls:
                # logger.info("Last message was a text response from AI. Deciding FINISH to prevent loop.")
                # Logic: If AI just answered without tools, we might want to finish, 
                # but let the LLM Decide usually. 
                # However, this check acts as a fast-path.
                pass 
                # Keeping original logic but suppressing log noise unless crucial
                # return {"next": "FINISH"}
    
    logger.info("METRIC_NODE_EXEC: Supervisor")

    
    # Create a string representation of members with their descriptions
    members_with_descriptions = "\n".join([f"- {name}: {desc}" for name, desc in MEMBER_DESCRIPTIONS.items()])

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
            (
                "system",
                "Given the conversation above, who should act next?"
                " Or should we FINISH? Select one of: {options}\n"
                "CRITICAL: If the last message is from the User, you MUST NOT select FINISH. You must select a worker to answer the user.",
            ),
        ]
    ).partial(options=str(OPTIONS), members=members_with_descriptions)
    
    # We need to construct messages including history and summary
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

    # Hybrid Router Logic
    settings = get_settings()
    
    use_local_router = os.getenv("USE_LOCAL_ROUTER", "false").lower() == "true"
    
    # Exo default often http://localhost:52415/v1, user might have custom
    local_url = settings.local_llm_base_url or os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:52415/v1") 
    local_model = settings.local_llm_model or os.getenv("LOCAL_LLM_MODEL", "mlx-community/Qwen3-30B-A3B-4bit") 
    
    result_decision = None

    async def run_chain(llm_instance):
         structured = llm_instance.with_structured_output(RouteDecision)
         chain = prompt | structured
         return await chain.ainvoke({"messages": messages})

    if use_local_router:
        try:
            logger.info(f"Using Local Router (Exo/OpenAI): {local_url} ({local_model})")
            # We use ChatOpenAI for Exo/Local generic OpenAI compatible
            local_llm = ChatOpenAI(
                base_url=local_url, 
                api_key="markdown", # Dummy key
                model=local_model, 
                temperature=0, 
                timeout=10.0
            ) 
            result_decision = await run_chain(local_llm)
        except Exception as e:
            logger.warning(f"Local Router Failed, falling back to Gemini. Error: {e}")
            result_decision = None

    if result_decision is None:
        # Fallback to Gemini
        try:
            llm = get_llm(state.get("model_name"))
            result_decision = await run_chain(llm)
        except Exception as e:
            logger.error(f"Supervisor failed: {e}")
            return {"next": "GeneralAssistant"}

    next_step = result_decision.next_agent
    
    logger.info(f"Supervisor decided next step: {next_step} (Reason: {result_decision.reasoning})")
    
    # ROBUST FAIL-SAFE:
    if state["messages"]:
        last_msg = state["messages"][-1]
        if next_step == "FINISH" and isinstance(last_msg, HumanMessage):
            logger.warning("Supervisor selected FINISH after User message. Overriding to Researcher to ensure response.")
            next_step = "Researcher"
            return {"next": next_step}

    # Loop Detection Logic
    last_messages = state["messages"][-10:]
    ai_messages = [m.content for m in last_messages if isinstance(m, AIMessage)]
    
    if len(ai_messages) >= 3:
        # Check for exact matches
        if ai_messages[-1] == ai_messages[-2] == ai_messages[-3]:
            logger.warning("METRIC_LOOP_DETECTED: Last 3 AI messages are identical. Forcing FINISH.")
            logger.info("METRIC_ROUTING_RESULT: FINISH")
            return {"next": "FINISH"}

        # Check for Notion page creation loop
        if ("Successfully created Notion page" in ai_messages[-1] or "Successfully updated Notion page" in ai_messages[-1]) and next_step == "NotionSearch":
            logger.warning("METRIC_LOOP_DETECTED: Repeated Notion page operation attempt. Forcing FINISH.")
            logger.info("METRIC_ROUTING_RESULT: FINISH")
            return {"next": "FINISH"}
            
        if len(ai_messages) >= 4:
            if ai_messages[-1] == ai_messages[-3] and ai_messages[-2] == ai_messages[-4]:
                    logger.warning("METRIC_LOOP_DETECTED: Alternating messages detected. Forcing FINISH.")
                    logger.info("METRIC_ROUTING_RESULT: FINISH")
                    return {"next": "FINISH"}

    logger.info(f"METRIC_ROUTING_RESULT: {next_step}")
    return {"next": next_step}
