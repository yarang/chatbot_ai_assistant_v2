from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.state import ChatState
from core.llm import get_llm


async def general_assistant_node(state: ChatState):
    llm = get_llm(state.get("model_name"))
    
    persona_content = state.get("persona_content") or "You are a helpful AI assistant."
    messages = state["messages"]
    
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", persona_content + f"\nIMPORTANT: Do not simulate the user. Do not generate 'User:' or 'Human:' dialogue.\nIMPORTANT: Keep your answers CONCISE. Limit response length to max 1 page. Avoid excessive verbosity.\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    
    chain = prompt | llm
    
    prompt_val = prompt.format(messages=messages)
    # Check if prompt_val is a list of messages or a string (it should be list of messages)
    system_prompt_str = ""
    if isinstance(prompt_val, list):
         for m in prompt_val:
             if m.type == "system":
                 system_prompt_str += m.content + "\n"
    elif hasattr(prompt_val, "to_messages"):
         for m in prompt_val.to_messages():
             if m.type == "system":
                 system_prompt_str += m.content + "\n"
    
    # We can also just use the persona_content constructed above + instruction
    full_system_prompt = persona_content + f"\nIMPORTANT: Do not simulate the user. Do not generate 'User:' or 'Human:' dialogue.\nIMPORTANT: Keep your answers CONCISE and to the point. Even when detailed information is requested, limit the response length to appropriately summary level (max 1 page equivalent). Avoid excessive verbosity.\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

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
        "output_tokens_used": output_tokens,
        "applied_system_prompt": full_system_prompt
    }
