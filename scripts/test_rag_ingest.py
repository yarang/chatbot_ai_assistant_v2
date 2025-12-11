import asyncio
import os
from uuid import uuid4
from reportlab.pdfgen import canvas
from services.knowledge_service import process_uploaded_file
from repository.user_repository import upsert_user
from repository.chat_room_repository import upsert_chat_room
from core.database import get_async_session
from tools.retrieval_tool import get_retrieval_tool
from fastapi import UploadFile

# Mock UploadFile
class MockUploadFile(UploadFile):
    def __init__(self, filename, content):
        self.filename = filename
        self.content = content
        self.file = None

    async def read(self):
        return self.content

async def create_test_pdf(filename, text):
    c = canvas.Canvas(filename)
    c.drawString(100, 750, text)
    c.save()
    
    with open(filename, "rb") as f:
        content = f.read()
    return content

async def test_rag_flow():
    print("--- Starting RAG Ingestion Test ---")
    
    # 1. Setup Test Data
    user_id = str(uuid4())
    chat_room_id_1 = str(uuid4())
    chat_room_id_2 = str(uuid4())
    
    print(f"Test User ID: {user_id}")
    print(f"Test Chat Room 1 (Source): {chat_room_id_1}")
    print(f"Test Chat Room 2 (Isolation): {chat_room_id_2}")
    
    # Create DB entries
    db_user = await upsert_user(email="test@example.com", telegram_id=12345, username="tester", first_name="Test", last_name="User")
    # We need to manually insert chat rooms or upsert them. upsert_chat_room uses telegram_chat_id (int).
    # Let's just use the repo functions.
    
    # Mock telegram IDs
    tg_chat_1 = 11111
    tg_chat_2 = 22222
    
    room1 = await upsert_chat_room(telegram_chat_id=tg_chat_1, name="Room 1", type="private")
    room2 = await upsert_chat_room(telegram_chat_id=tg_chat_2, name="Room 2", type="private")
    
    chat_room_id_1 = str(room1.id)
    chat_room_id_2 = str(room2.id)
    
    # 2. Create Test PDF
    pdf_filename = "test_doc.pdf"
    unique_keyword = f"SECRET_CODE_{uuid4().hex[:8]}"
    pdf_content = await create_test_pdf(pdf_filename, f"This is a confidential document for Room 1. {unique_keyword}")
    
    print(f"Created PDF with keyword: {unique_keyword}")
    
    mock_file = MockUploadFile(filename=pdf_filename, content=pdf_content)
    
    # 3. Ingest File into Room 1
    print("Ingesting file into Room 1...")
    success, msg = await process_uploaded_file(chat_room_id_1, str(db_user.id), mock_file)
    print(f"Ingestion Result: {success}, {msg}")
    
    if not success:
        print("Ingestion failed. Aborting.")
        return

    # Wait a bit for indexing (though local vector store is usually fast/sync-ish)
    await asyncio.sleep(2)
    
    # 4. Test Retrieval in Room 1 (Should Find)
    print("\n[Test 1] Searching in Room 1...")
    tool_room1 = get_retrieval_tool(chat_room_id_1)
    result1 = await tool_room1.coroutine(f"What is the secret code? {unique_keyword}")
    print(f"Result 1: {result1[:200]}...") # Truncate for display
    
    if unique_keyword in result1:
        print("✅ SUCCESS: Found keyword in Room 1.")
    else:
        print("❌ FAILURE: Did not find keyword in Room 1.")
        
    # 5. Test Retrieval in Room 2 (Should NOT Find)
    print("\n[Test 2] Searching in Room 2 (Isolation Check)...")
    tool_room2 = get_retrieval_tool(chat_room_id_2)
    result2 = await tool_room2.coroutine(f"What is the secret code? {unique_keyword}")
    print(f"Result 2: {result2[:200]}...")
    
    if unique_keyword not in result2:
        print("✅ SUCCESS: Did NOT find keyword in Room 2 (Isolation working).")
    else:
        print("❌ FAILURE: Found keyword in Room 2 (Isolation BROKEN).")

    # 6. Test Listing Documents
    print("\n[Test 3] Listing Documents in Room 1...")
    from services.knowledge_service import get_chat_room_documents
    docs = await get_chat_room_documents(chat_room_id_1)
    if docs and len(docs) > 0 and docs[0].filename == pdf_filename:
        print(f"✅ SUCCESS: Listing returned {len(docs)} documents. Found {docs[0].filename}.")
        doc_id_to_delete = str(docs[0].id)
    else:
        print(f"❌ FAILURE: Listing returned {len(docs) if docs else 0} documents.")
        return

    # 7. Test Deletion
    print(f"\n[Test 4] Deleting Document {doc_id_to_delete}...")
    from services.knowledge_service import delete_document
    delete_success = await delete_document(doc_id_to_delete, chat_room_id_1)
    if delete_success:
        print("✅ SUCCESS: Document deletion reported success.")
    else:
        print("❌ FAILURE: Document deletion failed.")
        
    # Wait for deletion propagation if async
    await asyncio.sleep(1)
    
    # 8. Test Retrieval after Deletion (Should NOT Find)
    print("\n[Test 5] Searching in Room 1 after Deletion...")
    result3 = await tool_room1.coroutine(f"What is the secret code? {unique_keyword}")
    print(f"Result 3: {result3[:200]}...")
    
    if unique_keyword not in result3 and "No relevant information" in result3:
        print("✅ SUCCESS: Keyword NOT found after deletion.")
    else:
        # Note: PGVector might still return old chunks if not deleted correctly.
        print("❓ RESULT: Check if deletion effectively removed context.")
        if unique_keyword in result3:
             print("❌ FAILURE: Keyword STILL found after deletion.")
        else:
             print("✅ SUCCESS: Keyword NOT found.")

    # Cleanup
    # Cleanup
    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)
    
    # Clean up uploads dir for test
    import shutil
    upload_dir = f"uploads/{chat_room_id_1}"
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir)
        
if __name__ == "__main__":
    asyncio.run(test_rag_flow())
