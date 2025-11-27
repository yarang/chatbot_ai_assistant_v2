from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_postgres import PGVector
from core.config import get_settings
from core.database import get_database_url

def get_embeddings():
    settings = get_settings()
    api_key = settings.gemini.api_key
    return GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=api_key
    )

def get_vector_store(collection_name: str = "chatbot_docs"):
    # Use sync connection string for PGVector initialization
    connection_string = get_database_url(async_driver=False)
    
    embeddings = get_embeddings()
    
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=connection_string,
        use_jsonb=True,
        create_extension=False,  # 일반 사용자 모드: vector extension은 관리자가 사전 설치 필요
    )
