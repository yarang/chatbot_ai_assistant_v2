import json
from datetime import datetime
from typing import Dict, Any
from agent.state import ChatState
from llm.chains.notion_chain import notion_search_chain
from langchain_core.messages import AIMessage
from core.config import get_settings
from core.notion_client import NotionClient
from core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from core.logger import get_logger

logger = get_logger(__name__)

from langchain_core.messages import AIMessage, HumanMessage

async def notion_node(state: ChatState) -> Dict[str, Any]:
    """
    Node that searches Notion or creates a page based on user intent.
    """
    logger.debug(f"NotionNode invoked with state keys: {list(state.keys())}")
    messages = state["messages"]
    
    # Find the last HumanMessage to understand the user's intent
    last_user_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_user_message = msg.content
            break
            
    if not last_user_message:
        # Fallback if no human message found (unlikely)
        logger.warning("No HumanMessage found in state, using last message content.")
        last_user_message = messages[-1].content

    model_name = state.get("model_name")
    
    llm = get_llm(model_name)
    
    # 1. Classify Intent and Extract Data
    system_prompt = (
        "You are a smart assistant interacting with Notion.\n"
        "Analyze the user's request and determine if they want to SEARCH, CREATE, or UPDATE a page.\n"
        "If CREATE, extract the potential 'title' and 'content' for the page.\n"
        "If UPDATE, you MUST provide the 'page_id'. If you don't know the 'page_id', SEARCH for the page first using 'search_notion'.\n"
        "If SEARCH, extract the 'query'.\n"
        "Current Time: {time}"
    )
    
    tools = [
        {
            "name": "search_notion",
            "description": "Search for pages in Notion",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "create_page",
            "description": "Create a new page in Notion",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the page"},
                    "content": {"type": "string", "description": "Content of the page (markdown supported)"}
                },
                "required": ["title", "content"]
            }
        },
        {
            "name": "update_page",
            "description": "Update an existing Notion page (title or append content). REQUIRES valid page_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "The exact ID of the page to update (e.g. 1b511319-56a4...)"},
                    "title": {"type": "string", "description": "New title for the page (optional)"},
                    "content": {"type": "string", "description": "Text content to append to the page (optional)"}
                },
                "required": ["page_id"]
            }
        }
    ]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "{input}")
    ]).partial(time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    
    chain = prompt | llm.bind_tools(tools)
    
    try:
        result = await chain.ainvoke({"input": last_user_message})
        tool_calls = result.tool_calls
        
        response_text = "I couldn't understand your request regarding Notion."
        
        if tool_calls:
            tool_call = tool_calls[0]
            function_name = tool_call["name"]
            logger.info(f"Notion intent classified: {function_name}")
            args = tool_call["args"]
            
            client = NotionClient()
            
            if function_name == "search_notion":
                query = args.get("query")
                logger.debug(f"Executing Notion search for: {query}")
                # Use existing chain logic or call client directly
                # Re-using the chain logic here for consistency
                response_text = await notion_search_chain(query, model_name)
                
            elif function_name == "create_page":
                title = args.get("title")
                content = args.get("content")
                logger.debug(f"Executing Notion page creation: title='{title}'")
                
                res = await client.create_page(title, content)
                if res:
                    logger.info("Notion page creation successful")
                    response_text = f"Successfully created Notion page: [{title}]({res.get('url')})"
                else:
                    logger.error("Notion page creation failed (client returned None)")
                    response_text = "Failed to create Notion page. Please check logs."

            elif function_name == "update_page":
                page_id = args.get("page_id")
                title = args.get("title")
                content = args.get("content")
                logger.debug(f"Executing Notion page update: id='{page_id}'")

                success = await client.update_page(page_id, title, content)
                if success:
                    logger.info("Notion page update successful")
                    response_text = f"Successfully updated Notion page {page_id}."
                else:
                    logger.error("Notion page update failed")
                    response_text = "Failed to update Notion page. Please check logs."
        else:
            # Fallback to search if no tool selected (default behavior)
            logger.info("No explicit tool selected, defaulting to Notion search")
            response_text = await notion_search_chain(str(last_user_message), model_name)

    except Exception as e:
        logger.error(f"Notion Node Error: {e}", exc_info=True)
        response_text = "An error occurred while accessing Notion."
    
    return {
        "messages": [AIMessage(content=response_text)]
    }
