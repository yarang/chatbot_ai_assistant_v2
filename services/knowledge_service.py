import os
import aiofiles
import pypdf
import pydantic_core
from datetime import datetime
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy import select, delete
from core.database import get_async_session
from core.config import get_settings
from core.vector_store import get_vector_store
from core.logger import get_logger
from core.llm import get_llm
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

logger = get_logger(__name__)

async def save_upload_file(file: UploadFile, chat_room_id: str) -> str:
    """Save uploaded file to disk.

    Args:
        file (UploadFile): The file object uploaded via FastAPI.
        chat_room_id (str): The ID of the chat room associated with the file.

    Returns:
        str: The absolute path to the saved file.
    """
    upload_dir = f"uploads/{chat_room_id}"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, file.filename)
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
        
    logger.info(f"File saved to: {file_path}")
    return file_path

async def process_pdf_smart(file_path: str) -> str:
    """Process PDF with Smart Ingestion logic.

    Attempts standard text extraction first. If the quality is low (e.g., scanned PDF),
    it switches to a vision-based approach using Gemini 1.5 Flash to transcribe images.

    Args:
        file_path (str): Path to the PDF file.

    Returns:
        str: Extracted text content from the PDF.
    """
    text_content = ""
    
    # 1. Try standard extraction
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            ctx = page.extract_text()
            if ctx:
                text_content += ctx + "\n"
    except Exception as e:
        logger.warning(f"Standard PDF extraction failed: {e}")

    # Check quality (heuristic: < 100 chars per page on average, or total very low)
    is_low_quality = len(text_content.strip()) < 100
    
    if is_low_quality:
        logger.info(f"PDF text content low ({len(text_content)} chars). Switching to Smart Ingestion (Vision).")
        try:
            import pypdfium2 as pdfium
            import base64
            
            pdf = pdfium.PdfDocument(file_path)
            vision_text = []
            
            llm = get_llm("gemini-1.5-flash") # Use Flash for speed/cost
            
            for i, page in enumerate(pdf):
                # Render page to image
                bitmap = page.render(scale=2) # 2x scale for better OCR
                pil_image = bitmap.to_pil()
                
                # Convert to base64 for Gemini
                from io import BytesIO
                buffered = BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                # Call Gemini
                message = HumanMessage(
                    content=[
                        {"type": "text", "text": "Transcribe and summarize the detailed content of this document page. Preserve key information, tables, and lists accurately."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}
                    ]
                )
                
                response = await llm.ainvoke([message])
                vision_text.append(f"--- Page {i+1} (Vision Extracted) ---\n{response.content}")
                
            text_content = "\n".join(vision_text)
            
        except Exception as e:
            logger.error(f"Smart Ingestion failed: {e}")
            # Fallback to whatever we had or empty
            if not text_content:
                text_content = "Failed to extract content from this file."

    return text_content

async def process_uploaded_file(
    chat_room_id: str, 
    user_id: str, 
    file: UploadFile
):
    """Main entry point for processing an uploaded file.

    Handles file saving, content extraction (text or vision), database recording,
    and vector store ingestion.

    Args:
        chat_room_id (str): The ID of the chat room.
        user_id (str): The ID of the user uploading the file.
        file (UploadFile): The file object to process.

    Returns:
        tuple[bool, str]: A tuple containing success status (bool) and a message (str).
    """
    filename = file.filename
    file_type = "pdf" if filename.lower().endswith(".pdf") else "txt"
    
    # 1. Save File
    file_path = await save_upload_file(file, chat_room_id)
    file_size = os.path.getsize(file_path)
    
    # 2. Extract Content
    content = ""
    processing_method = "text"
    
    if file_type == "pdf":
        content = await process_pdf_smart(file_path)
        if "Vision Extracted" in content:
            processing_method = "vision"
    else:
        # TXT file
        async with aiofiles.open(file_path, 'r') as f:
            content = await f.read()

    # 3. Create DB Record (knowledge_docs)
    # We need to use raw SQL or SQLAlchemy Core if we don't have a model defined in ORM yet.
    # But checking schema.sql, we created the table. Let's use raw insert for now to avoid creating model file if not needed.
    # Actually, better to define model or use text().
    
    # 3. Create DB Record (knowledge_docs)
    from models.knowledge_doc_model import KnowledgeDoc
    
    async with get_async_session() as session:
        logger.info(f"Creating DB record for file {filename} in room {chat_room_id}")
        doc = KnowledgeDoc(
            chat_room_id=UUID(chat_room_id),
            user_id=UUID(user_id),
            filename=filename,
            file_path=file_path,
            file_type=file_type,
            processing_method=processing_method,
            size=file_size
        )
        session.add(doc)
        await session.commit()
        logger.info(f"DB record created. ID: {doc.id}")

    # 4. Ingest into Vector Store
    try:
        vector_store = get_vector_store()
        
        # Split text?
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = splitter.split_text(content)
        
        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "chat_room_id": str(chat_room_id),
                    "source": filename,
                    "type": "internal_knowledge"
                }
            )
            for chunk in chunks
        ]
        
        # Add to vector store
        # Use async method since we enabled async_mode
        await vector_store.aadd_documents(docs)
        
        logger.info(f"Successfully ingested {len(docs)} chunks for file {filename}")
        return True, f"Successfully processed {filename} ({processing_method} mode)."
        
    except Exception as e:
        logger.error(f"Vector ingestion failed: {e}")
        return False, f"Processed file but failed to index: {e}"

async def get_chat_room_documents(chat_room_id: str):
    """Retrieve all knowledge documents for a specific chat room.

    Args:
        chat_room_id (str): The ID of the chat room.

    Returns:
        list[KnowledgeDoc]: A list of knowledge document records.
    """
    from models.knowledge_doc_model import KnowledgeDoc
    
    logger.info(f"Fetching documents for chat_room_id: {chat_room_id}")
    async with get_async_session() as session:
        stmt = select(KnowledgeDoc).where(KnowledgeDoc.chat_room_id == UUID(chat_room_id)).order_by(KnowledgeDoc.created_at.desc())
        result = await session.execute(stmt)
        docs = result.scalars().all()
        logger.info(f"Found {len(docs)} documents.")
        return docs

async def delete_document(doc_id: str, chat_room_id: str) -> bool:
    """Delete a document by ID.

    Removes the document record from the database, deletes the file from the filesystem,
    and removes associated embeddings from the vector store.

    Args:
        doc_id (str): The UUID of the document to delete.
        chat_room_id (str): The ID of the chat room owning the document.

    Returns:
        bool: True if deletion was successful, False if the document was not found.
    """
    from models.knowledge_doc_model import KnowledgeDoc
    
    async with get_async_session() as session:
        # 1. Get document info first to have file path and filename
        stmt = select(KnowledgeDoc).where(KnowledgeDoc.id == UUID(doc_id)).where(KnowledgeDoc.chat_room_id == UUID(chat_room_id))
        result = await session.execute(stmt)
        doc = result.scalar_one_or_none()
        
        if not doc:
            logger.warning(f"Document {doc_id} not found in room {chat_room_id}")
            return False
            
        file_path = doc.file_path
        filename = doc.filename
        
        # 2. Delete from DB
        await session.delete(doc)
        await session.commit()
        
        # 3. Delete from File System
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to remove file {file_path}: {e}")
                
        # 4. Delete from Vector Store
        # Currently PGVector doesn't support easy "delete by metadata" in LangChain interface efficiently without ID approach.
        # But we added "source" metadata.
        # A workaround is to delete the collection data if possible or ignore it.
        # Ideally, we should fetch IDs by metadata and delete.
        # For now, let's try to delete if possible.
        try:
            vector_store = get_vector_store()
            # Note: This is a bit tricky with langchan-postgres. 
            # We can use the underlying connection to delete from langchain_pg_embedding table.
            # But let's check if the vector store object has a delete method supported.
            # PGVector interface: delete(ids: Optional[List[str]] = None, **kwargs: Any)
            # We don't have the chunk IDs.
            
            # Alternative: direct SQL delete from embedding table.
            # Table name is typically: `langchain_pg_embedding`
            # Metadata is in `cmetadata` column (JSONB).
            
            # Use raw SQL to delete vector embeddings
            from sqlalchemy import text
            # Assuming default collection id logic. We need to be careful.
            
            # Safest way for now: Skip precise vector deletion or implement custom SQL.
            # Let's implement custom SQL deletion for robustness.
            delete_vectors_sql = text("""
                DELETE FROM langchain_pg_embedding
                WHERE cmetadata ->> 'source' = :filename
                AND cmetadata ->> 'chat_room_id' = :chat_room_id
            """)
            
            await session.execute(delete_vectors_sql, {"filename": filename, "chat_room_id": str(chat_room_id)})
            await session.commit()
            
            logger.info(f"Deleted document {doc_id} and its vector embeddings.")
            
        except Exception as e:
            logger.error(f"Failed to delete vector embeddings for {doc_id}: {e}")
            
        return True
