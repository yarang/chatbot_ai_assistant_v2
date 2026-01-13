from typing import Any, Optional

from langchain_core.tools import Tool

from core.logger import get_logger
from core.vector_store import get_vector_store

logger = get_logger(__name__)


def get_retrieval_tool(chat_room_id: Optional[str] = None) -> Tool:
    """
    Returns a tool that retrieves information from the vector store.
    """
    vector_store = get_vector_store()

    # Configure search arguments
    search_kwargs: dict[str, Any] = {"k": 3}
    if chat_room_id:
        # Filter by chat_room_id in metadata
        search_kwargs["filter"] = {"chat_room_id": chat_room_id}  # type: ignore[assignment]

    retriever = vector_store.as_retriever(search_kwargs=search_kwargs)

    async def retrieve_documents(query: str) -> str:
        """Retrieve documents from the vector store based on the query.

        Implements chat room isolation and relevance score filtering.
        """
        try:
            # SECURITY: Log chat room ID for audit trail
            if chat_room_id:
                logger.info(
                    f"[SECURITY] Retrieving documents for chat_room_id={chat_room_id}, query={query}"
                )
            else:
                logger.warning(
                    f"[SECURITY] Retrieving documents WITHOUT chat room filter (global search), query={query}"
                )

            # Use the retriever to get relevant documents
            documents = await retriever.ainvoke(query)

            if not documents:
                logger.info(
                    f"No relevant documents found for chat_room_id={chat_room_id}"
                )
                return "No relevant information found in the knowledge base."

            logger.info(
                f"Found {len(documents)} raw documents for chat_room_id={chat_room_id}"
            )

            # Filter by relevance score (>= 0.7)
            MIN_RELEVANCE_SCORE = 0.7
            filtered_docs = []
            filtered_count = 0

            for doc in documents:
                metadata = doc.metadata or {}
                score = metadata.get("score", 1.0)  # Default to 1.0 if no score

                if score >= MIN_RELEVANCE_SCORE:
                    filtered_docs.append(doc)
                else:
                    filtered_count += 1
                    logger.debug(
                        f"Filtered out document with score {score:.2f} < {MIN_RELEVANCE_SCORE}"
                    )

            # Log filtering results
            if filtered_count > 0:
                logger.info(
                    f"[SECURITY] Filtered {filtered_count} low-relevance documents (score < {MIN_RELEVANCE_SCORE}) for chat_room_id={chat_room_id}"
                )

            if not filtered_docs:
                logger.info(
                    f"No documents passed relevance threshold (>= {MIN_RELEVANCE_SCORE}) for chat_room_id={chat_room_id}"
                )
                return "No relevant information found in the knowledge base."

            logger.info(
                f"Returning {len(filtered_docs)} relevant documents for chat_room_id={chat_room_id}"
            )

            # Format the documents into a readable string
            formatted_docs = []
            for i, doc in enumerate(filtered_docs, 1):
                content = doc.page_content
                # Include metadata if available
                metadata = doc.metadata
                source = metadata.get("source", "Unknown") if metadata else "Unknown"
                score = metadata.get("score", "N/A")

                # Include score in output for transparency
                if score != "N/A":
                    formatted_docs.append(
                        f"Document {i} (Source: {source}, Relevance: {score:.2f}):\n{content}"
                    )
                else:
                    formatted_docs.append(
                        f"Document {i} (Source: {source}):\n{content}"
                    )

            return "\n\n".join(formatted_docs)
        except Exception as e:
            logger.error(
                f"Error retrieving documents for chat_room_id={chat_room_id}: {str(e)}"
            )
            return f"Error retrieving documents: {str(e)}"

    # Return a proper Tool instance
    return Tool(
        name="search_internal_knowledge",
        description="Searches for information in the internal knowledge base. Use this when asked about company policies, specific documents, or internal information.",
        func=lambda x: "",  # Sync version (not used in async context)
        coroutine=retrieve_documents,  # Async version
    )
