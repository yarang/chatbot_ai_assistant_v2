from datetime import datetime
import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from core.llm import get_llm
from repository.conversation_repository import get_history
from agent.state import ChatState, RouteDecision

from core.logger import get_logger

logger = get_logger(__name__)

# Define the agents
MEMBERS = ["Researcher", "GeneralAssistant", "NotionSearch"]
OPTIONS = ["FINISH"] + MEMBERS

async def supervisor_node(state: ChatState):
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
                logger.info("Last message was a text response from AI. Deciding FINISH to prevent loop.")
                return {"next": "FINISH"}

    
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
    for role, content, name in history_tuples:
        if role == "user":
            messages.append(HumanMessage(content=content, name=name))
        else:
            messages.append(AIMessage(content=content))
            
    messages.extend(state["messages"])

    # Hybrid Router Logic
    use_local = os.getenv("USE_LOCAL_ROUTER", "false").lower() == "true"
    local_url = os.getenv("LOCAL_LLM_BASE_URL", "http://172.16.1.101:11434")
    local_model = os.getenv("LOCAL_LLM_MODEL", "llama-3.1-8b")
    
    result_decision = None

    async def run_chain(llm_instance):
         structured = llm_instance.with_structured_output(RouteDecision)
         chain = prompt | structured
         return await chain.ainvoke({"messages": messages})

    if use_local:
        try:
            logger.info(f"Using Local Router: {local_url} ({local_model})")
            # Set a generic base_url for Ollama. 
            local_llm = ChatOllama(base_url=local_url, model=local_model, temperature=0, timeout=10.0) 
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
            print(f"Supervisor failed: {e}")
            return {"next": "GeneralAssistant"}

    next_step = result_decision.next_agent
    
    logger.info(f"Supervisor decided next step: {next_step} (Reason: {result_decision.reasoning})")
    
    # Debug Logging
    if state["messages"]:
        last_msg = state["messages"][-1]
        print(f"DEBUG: Last message content: {last_msg.content[:100]}...")
        print(f"DEBUG: Supervisor routing to: {next_step}")

        # ROBUST FAIL-SAFE:
        if next_step == "FINISH" and isinstance(last_msg, HumanMessage):
            logger.warning("Supervisor selected FINISH after User message. Overriding to Researcher to ensure response.")
            return {"next": "Researcher"}

    # Loop Detection Logic
    last_messages = state["messages"][-10:]
    ai_messages = [m.content for m in last_messages if isinstance(m, AIMessage)]
    
    if len(ai_messages) >= 3:
        # Check for exact matches
        if ai_messages[-1] == ai_messages[-2] == ai_messages[-3]:
            print("Loop detected: Last 3 AI messages are identical. Forcing FINISH.")
            return {"next": "FINISH"}

        # Check for Notion page creation loop
        if ("Successfully created Notion page" in ai_messages[-1] or "Successfully updated Notion page" in ai_messages[-1]) and next_step == "NotionSearch":
            print("Loop detected: Repeated Notion page operation attempt. Forcing FINISH.")
            return {"next": "FINISH"}
            
        if len(ai_messages) >= 4:
            if ai_messages[-1] == ai_messages[-3] and ai_messages[-2] == ai_messages[-4]:
                    print("Loop detected: Alternating messages detected. Forcing FINISH.")
                    return {"next": "FINISH"}

    return {"next": next_step}
