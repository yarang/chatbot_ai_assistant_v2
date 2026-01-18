"""
문서 지식 서비스

파일 업로드, 텍스트 추출, 청킹, 임베딩을 처리합니다.
sentence-transformers (all-mpnet-base-v2)를 사용하여 로컬에서 768차원 벡터를 생성합니다.
"""

import os
import pathlib
from uuid import UUID

import aiofiles
from fastapi import UploadFile
from langchain_core.messages import HumanMessage

from core.config import get_settings
from core.database import get_async_session
from core.llm import get_llm
from core.logger import get_logger
from repository.file_repository import FileCreate, FileRepository
from services.embedding_service import EmbeddingService
from services.text_chunking_service import TextChunkingService
from services.text_extraction_service import ExtractedText

logger = get_logger(__name__)
settings = get_settings()


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

    # Security: Extract only the filename to prevent path traversal attacks
    safe_filename = pathlib.Path(file.filename).name
    file_path = os.path.join(upload_dir, safe_filename)

    async with aiofiles.open(file_path, "wb") as out_file:
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
        import pypdf

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
        logger.info(
            f"PDF text content low ({len(text_content)} chars). Switching to Smart Ingestion (Vision)."
        )
        try:
            import base64

            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(file_path)
            vision_text = []

            llm = get_llm("gemini-1.5-flash")  # Use Flash for speed/cost

            for i, page in enumerate(pdf):
                # Render page to image
                bitmap = page.render(scale=2)  # 2x scale for better OCR
                pil_image = bitmap.to_pil()

                # Convert to base64 for Gemini
                from io import BytesIO

                buffered = BytesIO()
                pil_image.save(buffered, format="JPEG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                # Call Gemini
                message = HumanMessage(
                    content=[
                        {
                            "type": "text",
                            "text": "Transcribe and summarize the detailed content of this document page. Preserve key information, tables, and lists accurately.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                        },
                    ]
                )

                response = await llm.ainvoke([message])
                vision_text.append(
                    f"--- Page {i + 1} (Vision Extracted) ---\n{response.content}"
                )

            text_content = "\n".join(vision_text)

        except Exception as e:
            logger.error(f"Smart Ingestion failed: {e}")
            # Fallback to whatever we had or empty
            if not text_content:
                text_content = "Failed to extract content from this file."

    return text_content


async def process_uploaded_file(
    chat_room_id: str, user_id: str, file: UploadFile
) -> tuple[bool, str]:
    """Main entry point for processing an uploaded file.

    Handles file saving, content extraction (text or vision), database recording,
    and embedding ingestion using sentence-transformers.

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
        async with aiofiles.open(file_path, "r") as f:
            content = await f.read()

    # 3. Create File record in rag_files table
    async with get_async_session() as session:
        file_repo = FileRepository(session)

        # Check for duplicates
        if await file_repo.check_duplicate(UUID(chat_room_id), filename):
            logger.warning(f"Duplicate file detected: {filename}")
            return False, f"File '{filename}' already exists in this chat room."

        # Create file record
        file_data = FileCreate(
            chat_room_id=UUID(chat_room_id),
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            content_type=file_type,
        )
        db_file = await file_repo.create(file_data)
        file_id = db_file.id

        logger.info(f"File record created: ID={file_id}, filename={filename}")

        # 4. Extract text and create chunks
        try:
            # TextExtractionService instantiation removed - using ExtractedText directly
            extracted_text = ExtractedText(
                content=content,
                metadata={
                    "source": filename,
                    "file_type": file_type,
                    "processing_method": processing_method,
                },
            )

            # Chunk the text
            chunking_service = TextChunkingService()
            chunks = chunking_service.chunk_text(
                extracted_text=extracted_text,
                file_id=file_id,
                max_chunk_size=500,
                overlap_size=50,
            )

            logger.info(f"Created {len(chunks)} chunks for file {filename}")

            # 5. Embed and store chunks
            embedding_service = EmbeddingService(session)
            result = await embedding_service.embed_chunks(
                chunks=chunks,
                chat_room_id=UUID(chat_room_id),
                file_id=file_id,
            )

            # Update file status to completed
            await file_repo.update_status(file_id, status="completed")

            logger.info(
                f"Successfully processed {filename}: {result.successful_chunks} chunks embedded"
            )
            return (
                True,
                f"Successfully processed {filename} ({processing_method} mode, {result.successful_chunks} chunks).",
            )

        except Exception as e:
            # Update file status to failed
            await file_repo.update_status(
                file_id, status="failed", error_message=str(e)
            )
            logger.error(f"Failed to process file {filename}: {e}", exc_info=True)
            return False, f"Failed to process file: {str(e)}"


async def get_chat_room_documents(chat_room_id: str):
    """Retrieve all knowledge documents for a specific chat room.

    Args:
        chat_room_id (str): The ID of the chat room.

    Returns:
        list[File]: A list of file records from rag_files table.
    """
    logger.info(f"Fetching documents for chat_room_id: {chat_room_id}")
    async with get_async_session() as session:
        file_repo = FileRepository(session)
        docs = await file_repo.get_by_chat_room_id(UUID(chat_room_id))
        logger.info(f"Found {len(docs)} documents.")
        return docs


async def delete_document(doc_id: str, chat_room_id: str) -> bool:
    """Delete a document by ID.

    Removes the document record from the database, deletes the file from the filesystem,
    and removes associated embeddings from rag_chunks.

    Args:
        doc_id (str): The ID of the document to delete.
        chat_room_id (str): The ID of the chat room owning the document.

    Returns:
        bool: True if deletion was successful, False if the document was not found.
    """
    from sqlalchemy import text

    async with get_async_session() as session:
        # 1. Get document info first
        file_repo = FileRepository(session)
        db_file = await file_repo.get_by_id(int(doc_id))

        if not db_file:
            logger.warning(f"Document {doc_id} not found in room {chat_room_id}")
            return False

        file_path = db_file.file_path
        filename = db_file.filename

        # 2. Delete embeddings from rag_chunks
        delete_chunks_sql = text("""
            DELETE FROM rag_chunks
            WHERE file_id = :file_id
        """)
        await session.execute(delete_chunks_sql, {"file_id": int(doc_id)})
        await session.commit()
        logger.info(f"Deleted chunks for file {doc_id}")

        # 3. Delete file record from rag_files
        await file_repo.delete(int(doc_id))

        # 4. Delete from File System
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Failed to remove file {file_path}: {e}")

        logger.info(f"Deleted document {doc_id} ({filename})")
        return True
