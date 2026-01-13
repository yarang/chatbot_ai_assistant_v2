from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.state import ChatState
from core.llm import get_llm


async def general_assistant_node(state: ChatState):
    llm = get_llm(state.get("model_name"))

    persona_content = state.get("persona_content") or "You are a helpful AI assistant."
    retrieved_context = state.get("retrieved_context")
    summary = state.get("summary")
    messages = state["messages"]

    # RAG 컨텍스트가 있는 경우 시스템 프롬프트에 추가
    system_content = persona_content

    if retrieved_context:
        system_content += f"\n\n# 검색된 문서 컨텍스트\n{retrieved_context}\n\n위 문서 내용을 참고하여 질문에 답변해주세요."

    if summary:
        system_content += f"\n\n# 대화 요약\n{summary}\n\n이전 대화 내용을 참고하여 맥락을 유지해주세요."

    system_content += f"\n\nIMPORTANT: Do not simulate the user. Do not generate 'User:' or 'Human:' dialogue.\nIMPORTANT: Keep your answers CONCISE. Limit response length to max 1 page. Avoid excessive verbosity.\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_content),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    chain = prompt | llm

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
        "applied_system_prompt": system_content
    }
