from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_postgres import PGVector

from core.database import get_database_url


def get_embeddings():
    """Get sentence-transformers embeddings for RAG."""
    # Use sentence-transformers all-mpnet-base-v2 (768 dimensions)
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-mpnet-base-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_vector_store(collection_name: str = "chatbot_docs"):
    # Use async connection string for PGVector initialization
    connection_string = get_database_url(async_driver=True)

    embeddings = get_embeddings()

    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
        create_extension=False,
        async_mode=True,
    )
