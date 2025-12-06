from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.notion_client import NotionClient
from core.llm import get_llm

async def notion_search_chain(query: str, model_name: str = None) -> str:
    """
    Search Notion and return a summarized answer.
    """
    client = NotionClient()
    results = await client.search(query)
    
    if not results:
        return "Notion에서 관련 정보를 찾을 수 없습니다."
        
    # Format results for the LLM
    context = "\n".join([f"- [{item['title']}]({item['url']})" for item in results])
    
    llm = get_llm(model_name)
    
    prompt = ChatPromptTemplate.from_template(
        """
        사용자의 질문에 대해 아래 Notion 검색 결과를 바탕으로 답변해 주세요.
        
        질문: {query}
        
        Notion 검색 결과:
        {context}
        
        답변:
        """
    )
    
    chain = prompt | llm | StrOutputParser()
    
    return await chain.ainvoke({"query": query, "context": context})
