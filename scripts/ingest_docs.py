import asyncio
from langchain_core.documents import Document
from core.vector_store import get_vector_store

async def ingest_docs():
    print("Initializing Vector Store...")
    vector_store = get_vector_store()
    
    # Sample Documents
    docs = [
        Document(
            page_content="The company policy on remote work allows employees to work from home up to 3 days a week. Approval from the manager is required.",
            metadata={"source": "policy_manual", "topic": "remote_work"}
        ),
        Document(
            page_content="Annual leave entitlement is 20 days per year. Unused leave can be carried over up to 5 days.",
            metadata={"source": "policy_manual", "topic": "leave"}
        ),
        Document(
            page_content="The office is located at 123 AI Boulevard, Tech City. It is open from 9 AM to 6 PM.",
            metadata={"source": "office_info", "topic": "location"}
        ),
        Document(
            page_content="To reset your password, visit the IT support portal and click on 'Forgot Password'.",
            metadata={"source": "it_support", "topic": "password"}
        ),
    ]
    
    print(f"Adding {len(docs)} documents...")
    # PGVector.add_documents is sync or async?
    # langchain-postgres PGVector usually has async methods or we run in executor if sync.
    # But wait, we initialized it with sync connection string.
    # So we should call it synchronously?
    # But we are in async function.
    # Let's check if we can run it.
    
    # Actually, langchain-postgres PGVector add_documents is synchronous if using psycopg3 sync connection.
    vector_store.add_documents(docs)
    
    print("Ingestion Complete!")

if __name__ == "__main__":
    # Since add_documents might be sync, we might not need asyncio run if we don't use await.
    # But get_vector_store uses get_settings which is fine.
    # Let's just run it.
    asyncio.run(ingest_docs())
