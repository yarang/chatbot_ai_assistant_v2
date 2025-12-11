# Implementation Plan - Chat-Specific RAG Ingestion

## Goal Description
Allow users to upload files (PDF, TXT, etc.) via Telegram to a specific chat room. These files will be ingested into a vector database to act as "Internal Knowledge" (RAG) specific to that chat room. Searching for information should only yield results from files uploaded to the current chat room.

## User Review Required
> [!IMPORTANT]
> **Storage Policy**: Original files will be stored in `uploads/{chat_id}/`. If the server disk is ephemeral, these will be lost on restart unless persistent storage is configured. For now, we assume local disk persistence.
> **File Types**: Initial support will be for **PDF** and **TXT** files.
> **Image-Based PDFs**: We will implement a "Smart Ingestion" logic. If a PDF yields no text (scanned/image-only), we will use **Gemini 1.5 Flash** to visually analyze and extract information from the file (requiring `pypdfium2` for rendering).

## Proposed Changes

### Database Layer
#### [NEW] `knowledge_docs` Table in `schema.sql`
- `id` (UUID, PK)
- `chat_room_id` (UUID, FK)
- `user_id` (UUID, FK)
- `filename` (VARCHAR)
- `file_path` (VARCHAR)
- `file_type` (VARCHAR)
- `processing_method` (VARCHAR) -- 'text' or 'vision'
- `size` (INTEGER)
- `created_at` (TIMESTAMP)

### API Layer
#### [MODIFY] `app/api/telegram_router.py`
- Update request handling logic to accept `message.document`.
- Implement file download and save logic.
- Call ingestion service to process the file.

### Service Layer
#### [NEW] `app/services/knowledge_service.py`
- `process_uploaded_file(chat_room_id, user_id, file_obj, filename)`:
  1. Save file to disk.
  2. **Text Extraction**: Attempt to extract text using `pypdf`.
  3. **Quality Check**: If text length is low (e.g. < 50 chars) but file size is large, verify if it's an image PDF.
  4. **Vision Fallback**:
     - Use `pypdfium2` to convert PDF pages to images.
     - Send images to Gemini 1.5 Flash with prompt: "Transcribe and summarize the detailed content of this document."
     - Use the **Gemini generated text** as the document content.
  5. **Embedding**: Split text (extracted or generated) and save to PGVector metadata `{"chat_room_id": ...}`.
- `delete_document(doc_id)`: Removes file and vector embeddings.

### Core Layer
#### [MODIFY] `app/core/vector_store.py`
- Create `ingest_file(file_path, metadata)` function.

### RAG / Tools Layer
#### [MODIFY] `app/tools/retrieval_tool.py`
- Update `get_retrieval_tool` to accept `chat_room_id` (via state or tool argument).
- Modify search logic to apply metadata filter: `filter={"chat_room_id": str(chat_room_id)}`.

## Verification Plan

### Automated Tests
- Create a test script `scripts/test_rag_upload.py` to simulate file upload and verification of ingestion.
- Test retrieval with and without correct `chat_room_id` filter to ensure isolation.

### Manual Verification
1. Open Telegram bot.
2. Send a PDF file (e.g., a dummy menu or policy).
3. Bot should reply "File uploaded and processed."
4. Ask a question about the PDF content.
5. Bot should answer correctly.
6. Ask the same question in a *different* chat room (if possible to test) -> Bot should NOT know the answer.
