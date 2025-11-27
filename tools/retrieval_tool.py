from langchain_core.tools import Tool
from langchain_core.documents import Document
from core.vector_store import get_vector_store
from typing import List

def get_retrieval_tool():
    """
    Returns a tool that retrieves information from the vector store.
    """
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    
    async def retrieve_documents(query: str) -> str:
        """Retrieve documents from the vector store based on the query."""
        try:
            # Use the retriever to get relevant documents
            documents = await retriever.ainvoke(query)
            
            if not documents:
                return "No relevant information found in the knowledge base."
            
            # Format the documents into a readable string
            formatted_docs = []
            for i, doc in enumerate(documents, 1):
                content = doc.page_content
                # Include metadata if available
                metadata = doc.metadata
                source = metadata.get('source', 'Unknown') if metadata else 'Unknown'
                formatted_docs.append(f"Document {i} (Source: {source}):\n{content}")
            
            return "\n\n".join(formatted_docs)
        except Exception as e:
            return f"Error retrieving documents: {str(e)}"
    
    # Return a proper Tool instance
    return Tool(
        name="search_internal_knowledge",
        description="Searches for information in the internal knowledge base. Use this when asked about company policies, specific documents, or internal information.",
        func=lambda x: "",  # Sync version (not used in async context)
        coroutine=retrieve_documents  # Async version
    )
