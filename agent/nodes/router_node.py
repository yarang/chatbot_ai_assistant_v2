from datetime import datetime
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from core.llm import get_llm
from repository.conversation_repository import get_history
from agent.state import ChatState

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
        "Only respond with FINISH if the user's request has been completely addressed or if the answers are satisfactory.\n"
        "If a tool has successfully completed the user's request (e.g. created a page), STOP immediately and respond with FINISH.\n"
        "Do not repeatedly call the same worker if they are not making progress.\n"
        f"Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    


    # Define descriptions for each worker to help Supervisor route correctly
    MEMBER_DESCRIPTIONS = {
        "Researcher": "Perform web searches and gather information.",
        "GeneralAssistant": "Handle general conversation, chit-chat, and queries not related to specific tools.",
        "NotionSearch": "Primary tool for interacting with Notion. Use this to SEARCH, READ, WRITE, CREATE, or DRAFT pages in Notion."
    }

    # LOOP PREVENTION LOGIC:
    # If the last message is from an AI and it's NOT a tool call, we assume the assistant has answered.
    # We should stop here to prevent the Supervisor from looping back to GeneralAssistant endlessly.
    if state["messages"]:
        last_msg = state["messages"][-1]
        # Check if it's an AI message
        if isinstance(last_msg, AIMessage):
            # Check if it has tool calls (if so, we might need to continue to 'tools' node)
            # Note: LangChain usually handles tool_calls routing *before* hitting supervisor again if using standard prebuilt nodes,
            # but if Researcher/Notion returns to Supervisor with a tool call, we might need to handle it.
            # However, in this graph, 'tools' node usually goes back to the calling node or Supervisor.
            # If the AI message has NO tool calls, it's a text response. We should FINISH.
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
                " Or should we FINISH? Select one of: {options}",
            ),
        ]
    ).partial(options=str(OPTIONS), members=members_with_descriptions)
    
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
        next_step = result["next"]
        
        logger.info(f"Supervisor decided next step: {next_step}")
        
        # Debug Logging
        if state["messages"]:
            last_msg = state["messages"][-1]
            print(f"DEBUG: Last message content: {last_msg.content[:100]}...")
            print(f"DEBUG: Supervisor routing to: {next_step}")
        
        # Loop Detection Logic
        last_messages = state["messages"][-10:]
        ai_messages = [m.content for m in last_messages if isinstance(m, AIMessage)]
        
        if len(ai_messages) >= 3:
            # Check for exact matches
            if ai_messages[-1] == ai_messages[-2] == ai_messages[-3]:
                print("Loop detected: Last 3 AI messages are identical. Forcing FINISH.")
                return {"next": "FINISH"}

            # Check for Notion page creation loop (messages differ by URL)
            # If the last message was a successful creation, and the Supervisor is trying to schedule NotionSearch again,
            # it means we are in a loop (unless user explicitly asked for multiple, but Supervisor should handle that).
            if ("Successfully created Notion page" in ai_messages[-1] or "Successfully updated Notion page" in ai_messages[-1]) and next_step == "NotionSearch":
                print("Loop detected: Repeated Notion page operation attempt. Forcing FINISH.")
                return {"next": "FINISH"}
                
            if len(ai_messages) >= 4:
                if ai_messages[-1] == ai_messages[-3] and ai_messages[-2] == ai_messages[-4]:
                     print("Loop detected: Alternating messages detected. Forcing FINISH.")
                     return {"next": "FINISH"}

        return {"next": next_step}
    except Exception as e:
        print(f"Supervisor failed: {e}")
        return {"next": "GeneralAssistant"}
