from langchain_core.tools import Tool
from langchain_core.documents import Document
from core.vector_store import get_vector_store
from typing import List

def get_memory_tool():
    """
    Returns a tool that retrieves information from the conversation history.
    """
    # Use a separate collection for conversation history
    vector_store = get_vector_store(collection_name="conversation_history")
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    
    async def retrieve_memory(query: str) -> str:
        """Retrieve past conversation details based on the query."""
        try:
            # Use the retriever to get relevant documents
            documents = await retriever.ainvoke(query)
            
            if not documents:
                return "No relevant past conversation found."
            
            # Format the documents into a readable string
            formatted_docs = []
            for i, doc in enumerate(documents, 1):
                content = doc.page_content
                # Include metadata if available
                metadata = doc.metadata
                role = metadata.get('role', 'unknown')
                timestamp = metadata.get('timestamp', 'unknown')
                formatted_docs.append(f"Memory {i} ({role} at {timestamp}):\n{content}")
            
            return "\n\n".join(formatted_docs)
        except Exception as e:
            return f"Error retrieving memory: {str(e)}"
    
    # Return a proper Tool instance
    return Tool(
        name="search_conversation_history",
        description="Searches for information in the past conversation history. Use this when the user refers to something discussed in the past or when you need to recall specific details from previous interactions.",
        func=lambda x: "",  # Sync version (not used in async context)
        coroutine=retrieve_memory  # Async version
    )
