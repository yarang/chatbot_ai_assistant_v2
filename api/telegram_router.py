from fastapi import APIRouter, Request, BackgroundTasks
import asyncio
from typing import Dict
from telegram import Update, Bot
from core.config import get_settings
from agent.graph import graph
from core.logger import get_logger
from langchain_core.messages import HumanMessage, AIMessage
from repository.user_repository import upsert_user
from repository.chat_room_repository import upsert_chat_room, set_chat_room_persona
from repository.persona_repository import get_public_personas, get_persona_by_id, create_persona, get_user_personas

logger = get_logger(__name__)

router = APIRouter()

settings = get_settings()
bot_token = settings.telegram.bot_token
# Initialize Bot only if token is present to avoid errors during startup if not configured
bot = Bot(token=bot_token) if bot_token else None

@router.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    if not bot:
        return {"status": "error", "message": "Bot token not configured"}
        
    data = await request.json()
    try:
        update = Update.de_json(data, bot)
        if update.message and (update.message.text or update.message.document or update.message.photo):
            background_tasks.add_task(process_update, update)
    except Exception as e:
        print(f"Error parsing update: {e}")
        
    return {"status": "ok"}


# Global cache for bot username
BOT_USERNAME = None

# Global lock per user to prevent concurrent processing
USER_LOCKS: Dict[int, asyncio.Lock] = {}

def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in USER_LOCKS:
        USER_LOCKS[user_id] = asyncio.Lock()
    return USER_LOCKS[user_id]

async def _process_update_impl(update: Update):
    global BOT_USERNAME
    
    try:
        user = update.effective_user
        chat = update.effective_chat
        message = update.message
        
        # Handle edited messages or other updates that might not have a message
        if not message:
            logger.debug("Update has no message, skipping")
            return

        if user.is_bot:
            logger.debug(f"Ignoring message from bot user_id={user.id}")
            return

        text = message.text or message.caption
        
        if not text and not message.photo and not message.document:
            logger.debug("Message has no text, photo, or document, skipping")
            return
        
        logger.info(f"Processing message from chat_id={chat.id}, chat_type={chat.type}, user_id={user.id}, text_preview={text[:50] if text else 'photo/doc'}")

        # Lazy load bot username
        if BOT_USERNAME is None:
            if settings.telegram.bot_username:
                 BOT_USERNAME = settings.telegram.bot_username
            elif bot:
                try:
                    me = await bot.get_me()
                    BOT_USERNAME = me.username
                except Exception as e:
                    print(f"Failed to fetch bot username: {e}")


        # 1. Ensure User exists
        # Email is required, so generate one
        logger.debug(f"Upserting user with telegram_id={user.id}")
        email = f"telegram_{user.id}@telegram.placeholder"
        db_user = await upsert_user(
            email=email,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        logger.debug(f"User upserted: db_user_id={db_user.id}")
        
        # 2. Ensure ChatRoom exists
        logger.debug(f"Upserting chat room with telegram_chat_id={chat.id}")
        db_chat_room = await upsert_chat_room(
            telegram_chat_id=chat.id,
            name=chat.title or user.first_name,
            type=chat.type,
            username=chat.username
        )
        logger.debug(f"Chat room upserted: db_chat_room_id={db_chat_room.id}")
        
        # 3. Handle Commands
        if text and (text.startswith("/start") or text.startswith("/help")):
            help_text = """
Hello! I am your AI assistant. You can use the following commands:

/help - Show this help message
/summary - Summarize the conversation
/persona - Show current persona
/personas - List available personas
/select_persona <id> - Select a persona
/create_persona <json> - Create a new persona (e.g. /create_persona {"name": "Name", "content": "Prompt"})
"""
            await bot.send_message(chat_id=chat.id, text=help_text)
            return

        if text and text.startswith("/create_persona"):
            # Expected format: /create_persona {"name": "...", "content": "..."}
            try:
                import json
                # Extract JSON part
                json_str = text.replace("/create_persona", "", 1).strip()
                if not json_str:
                    await bot.send_message(
                        chat_id=chat.id, 
                        text="Please provide persona data in JSON format.\nExample: /create_persona {\"name\": \"My Persona\", \"content\": \"You are a helpful assistant.\"}"
                    )
                    return

                data = json.loads(json_str)
                name = data.get("name")
                content = data.get("content")
                description = data.get("description")
                is_public = data.get("is_public", False)

                if not name or not content:
                    await bot.send_message(chat_id=chat.id, text="Name and content are required.")
                    return

                new_persona = await create_persona(
                    user_id=db_user.id,
                    name=name,
                    content=content,
                    description=description,
                    is_public=is_public
                )
                await bot.send_message(chat_id=chat.id, text=f"Persona created: {new_persona.name} (ID: {new_persona.id})")
            except json.JSONDecodeError:
                await bot.send_message(chat_id=chat.id, text="Invalid JSON format.")
            except Exception as e:
                await bot.send_message(chat_id=chat.id, text=f"Error creating persona: {e}")
            return

        if text and text.startswith("/personas"):
            # List user's personas + public personas
            try:
                user_personas = await get_user_personas(db_user.id, include_public=True)
                if not user_personas:
                    await bot.send_message(chat_id=chat.id, text="No personas found.")
                else:
                    msg = "Available Personas:\n\n"
                    for p in user_personas:
                        msg += f"- {p.name}\n  ID: `{p.id}`\n  {p.description or ''}\n\n"
                    msg += "Use `/select_persona <id>` to set."
                    await bot.send_message(chat_id=chat.id, text=msg, parse_mode="Markdown")
            except Exception as e:
                await bot.send_message(chat_id=chat.id, text=f"Error fetching personas: {e}")
            return

        if text and text.startswith("/select_persona"):
            parts = text.split()
            if len(parts) < 2:
                await bot.send_message(chat_id=chat.id, text="Usage: /select_persona <id>")
                return
                
            persona_id = parts[1]
            try:
                # Verify persona exists
                persona = await get_persona_by_id(persona_id)
                if persona:
                    await set_chat_room_persona(db_chat_room.id, persona.id)
                    await bot.send_message(chat_id=chat.id, text=f"Persona set to: {persona.name}")
                else:
                    await bot.send_message(chat_id=chat.id, text="Persona not found.")
            except Exception as e:
                await bot.send_message(chat_id=chat.id, text=f"Error setting persona: {e}")
            return
            
        if text and text.startswith("/persona"):
            # Show current persona
            if db_chat_room.persona_id:
                persona = await get_persona_by_id(db_chat_room.persona_id)
                if persona:
                    await bot.send_message(chat_id=chat.id, text=f"Current Persona: {persona.name}\n{persona.description or ''}")
                else:
                    await bot.send_message(chat_id=chat.id, text="Current persona ID not found (maybe deleted).")
            else:
                await bot.send_message(chat_id=chat.id, text="No persona set. Using default.")
            return

        if text and text.startswith("/summary"):
            await bot.send_message(chat_id=chat.id, text="대화 내용을 요약하고 있습니다. 잠시만 기다려주세요...")
            try:
                from services.conversation_service import summarize_chat_room
                from telegram.helpers import escape_markdown
                
                summary = await summarize_chat_room(chat_room_id=db_chat_room.id, user_id=db_user.id)
                # Use MarkdownV2 for better stability, escape the LLM output
                safe_summary = escape_markdown(summary, version=2)
                # Header "📋 대화 요약" in bold. Note: emojis don't strictly need escaping but good practice to be safe or just string format
                header = escape_markdown("📋 대화 요약", version=2)
                
                await bot.send_message(
                    chat_id=chat.id, 
                    text=f"*{header}*\n\n{safe_summary}", 
                    parse_mode="MarkdownV2"
                )
            except Exception as e:
                logger.error(f"Error executing summary command: {e}")
                await bot.send_message(chat_id=chat.id, text="대화 요약 중 오류가 발생했습니다.")
            return

        if text and text.startswith("/files"):
            # List known documents
            try:
                from services.knowledge_service import get_chat_room_documents
                from telegram.helpers import escape_markdown
                
                logger.info(f"Listing files for chat_room_id={db_chat_room.id}")
                docs = await get_chat_room_documents(str(db_chat_room.id))
                
                if not docs:
                    logger.info("No docs returned from service.")
                    await bot.send_message(chat_id=chat.id, text="No uploaded documents found in this room.")
                else:
                    msg = "📚 *Uploaded Documents*:\n\n"
                    for doc in docs:
                        # Escape filename for Markdown (v1 legacy used here since parse_mode="Markdown")
                        # Version 1 escapes are minimal but we need to be careful.
                        # Actually let's just use explicit replacements or safe text.
                        # Using MarkdownV2 is better but requires escaping everything.
                        # Let's stick to v1 but escape common chars.
                        safe_filename = doc.filename.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
                        
                        sub_text = f"Method: {doc.processing_method}, Size: {doc.size or 0} bytes"
                        # Escape sub_text chars too just in case
                        sub_text = sub_text.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
                        
                        msg += f"📄 *{safe_filename}*\n   ID: `{doc.id}`\n   {sub_text}\n\n"
                    
                    msg += "Use `/delete_file <id>` to remove."
                    await bot.send_message(chat_id=chat.id, text=msg, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Error fetching files: {e}")
                await bot.send_message(chat_id=chat.id, text="Failed to retrieve file list.")
            return

        if text and text.startswith("/delete_file"):
            # Delete a document
            parts = text.split()
            if len(parts) < 2:
                await bot.send_message(chat_id=chat.id, text="Usage: /delete_file <id>")
                return
            
            doc_id = parts[1]
            try:
                from services.knowledge_service import delete_document
                success = await delete_document(doc_id, str(db_chat_room.id))
                
                if success:
                    await bot.send_message(chat_id=chat.id, text=f"✅ Document `{doc_id}` deleted successfully.", parse_mode="Markdown")
                else:
                    await bot.send_message(chat_id=chat.id, text=f"❌ Failed to delete document. Check ID and Permissions.")
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                await bot.send_message(chat_id=chat.id, text=f"Error deleting file: {e}")
            return

        # 4. Invoke Graph with Streaming
        import base64
        from services.conversation_service import ask_question_stream
        
        # Check for photo
        image_data = None
        if message.photo:
            try:
                # Get largest photo
                photo = message.photo[-1]
                file_obj = await bot.get_file(photo.file_id)
                image_bytes = await file_obj.download_as_bytearray()
                b64_str = base64.b64encode(image_bytes).decode('utf-8')
                image_data = f"data:image/jpeg;base64,{b64_str}"
                
                # If no text caption, use default text
                if not text:
                    text = "Describe this image."
            except Exception as e:
                logger.error(f"Error processing photo: {e}")
                await bot.send_message(chat_id=chat.id, text="Failed to process image.")
                return

        # Check for Document (PDF/TXT)
        if message.document:
            try:
                doc = message.document
                file_name = doc.file_name or "unknown_file"
                mime_type = doc.mime_type or ""

                # Check file size limit (10MB)
                MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
                if doc.file_size and doc.file_size > MAX_FILE_SIZE:
                    await bot.send_message(
                        chat_id=chat.id,
                        text=f"❌ File too large. Maximum size: 10MB (Your file: {doc.file_size / 1024 / 1024:.1f}MB)"
                    )
                    return

                # Check for supported types
                if "pdf" in mime_type.lower() or "text/plain" in mime_type.lower() or file_name.lower().endswith(".pdf") or file_name.lower().endswith(".txt"):

                    await bot.send_message(chat_id=chat.id, text=f"📥 Processing document: {file_name}...\nThis may take a moment.")
                    
                    file_obj = await bot.get_file(doc.file_id)
                    
                    # Convert Telegram file to UploadFile-like object or byte stream
                    # knowledge_service expects UploadFile but we can adapt it or change service to accept bytes.
                    # Adapting here:
                    from io import BytesIO
                    from fastapi import UploadFile
                    
                    file_bytes = await file_obj.download_as_bytearray()
                    byte_stream = BytesIO(file_bytes)
                    
                    # Mock UploadFile
                    upload_file = UploadFile(file=byte_stream, filename=file_name)
                    
                    from services.knowledge_service import process_uploaded_file
                    success, msg = await process_uploaded_file(str(db_chat_room.id), str(db_user.id), upload_file)
                    
                    if success:
                         await bot.send_message(chat_id=chat.id, text=f"✅ {msg}")
                    else:
                         # Truncate error message if too long
                         error_msg = str(msg)
                         if len(error_msg) > 3000:
                             error_msg = error_msg[:3000] + "... (truncated)"
                         await bot.send_message(chat_id=chat.id, text=f"❌ Ingestion failed: {error_msg}")
                    return
                else:
                    await bot.send_message(chat_id=chat.id, text="Unsupported file type. Please upload PDF or TXT files.")
                    return

            except Exception as e:
                logger.error(f"Error processing document: {e}", exc_info=True)
                await bot.send_message(chat_id=chat.id, text="Failed to process document.")
                return

        message_content = text
        if image_data:
            message_content = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]

        # For now, streaming doesn't support multimodal (image) due to complexity
        # Fall back to non-streaming for images
        if image_data:
            inputs = {
                "messages": [HumanMessage(content=message_content)],
                "user_id": str(db_user.id),
                "chat_room_id": str(db_chat_room.id),
                "model_name": "gemini-1.5-flash"
            }
            
            try:
                result = await graph.ainvoke(inputs)
                response_messages = result["messages"]
                ai_response = response_messages[-1]
                
                if isinstance(ai_response, AIMessage):
                     await bot.send_message(chat_id=chat.id, text=ai_response.content)
                else:
                     await bot.send_message(chat_id=chat.id, text="I didn't get a response.")
                
            except Exception as e:
                print(f"Error processing message: {e}")
                if "429" in str(e) or "ResourceExhausted" in str(e):
                     await bot.send_message(chat_id=chat.id, text="죄송합니다. API 사용량을 초과했습니다. 나중에 다시 시도해 주세요.")
                else:
                     await bot.send_message(chat_id=chat.id, text="Sorry, I encountered an error.")
            return
        
        # Streaming response for text-only messages
        logger.info(f"Starting streaming response for user_id={db_user.id}, chat_room_id={db_chat_room.id}")
        try:
            # Send initial message with typing indicator
            sent_msg = await bot.send_message(chat_id=chat.id, text="...")
            logger.debug(f"Sent initial message: message_id={sent_msg.message_id}")
            
            full_response = ""
            last_update_time = 0
            update_interval = 0.5  # Seconds between updates
            chunk_count = 0
            
            # List of sent messages to handle pagination
            sent_messages = [sent_msg]
            sent_texts = {sent_msg.message_id: "..."}
            MESSAGE_LIMIT = 4000 # Telegram limit is 4096, keep buffer
            
            # Determine user name for context
            user_name = db_user.first_name or db_user.username or "Unknown"

            async for chunk in ask_question_stream(
                user_id=str(db_user.id),
                chat_room_id=str(db_chat_room.id),
                question=text,
                user_name=user_name
            ):
                # Smart update logic to handle both deltas and snapshots
                if chunk.startswith(full_response) and len(chunk) >= len(full_response):
                    # It's a snapshot (extended version of previous)
                    full_response = chunk
                else:
                    # It's a delta (or a new independent chunk)
                    full_response += chunk
                chunk_count += 1
                
                # Rate limit message updates
                import time
                current_time = time.time()
                if current_time - last_update_time >= update_interval:
                    try:
                        # Calculate how many messages we need
                        num_needed = (len(full_response) // MESSAGE_LIMIT) + 1
                        
                        # If we need more messages than we have
                        if num_needed > len(sent_messages):
                            # First, finalize the current last message (fill it up and remove "...")
                            prev_last_msg = sent_messages[-1]
                            prev_last_idx = len(sent_messages) - 1
                            prev_text = full_response[prev_last_idx * MESSAGE_LIMIT : (prev_last_idx + 1) * MESSAGE_LIMIT]
                            
                            if sent_texts.get(prev_last_msg.message_id) != prev_text:
                                try:
                                    await bot.edit_message_text(
                                        chat_id=chat.id,
                                        message_id=prev_last_msg.message_id,
                                        text=prev_text
                                    )
                                    sent_texts[prev_last_msg.message_id] = prev_text
                                except Exception as e:
                                    logger.debug(f"Error finalizing previous message: {e}")
                            
                            # Add new messages
                            while len(sent_messages) < num_needed:
                                new_msg = await bot.send_message(chat_id=chat.id, text="...")
                                sent_messages.append(new_msg)
                                sent_texts[new_msg.message_id] = "..."
                        
                        # Now update the (possibly new) last message
                        last_msg_index = len(sent_messages) - 1
                        start_idx = last_msg_index * MESSAGE_LIMIT
                        current_chunk_text = full_response[start_idx:]
                        new_text = current_chunk_text + "..."
                        
                        if sent_texts.get(sent_messages[-1].message_id) != new_text:
                            await bot.edit_message_text(
                                chat_id=chat.id,
                                message_id=sent_messages[-1].message_id,
                                text=new_text
                            )
                            sent_texts[sent_messages[-1].message_id] = new_text
                        last_update_time = current_time
                    except Exception as e:
                        # Ignore edit errors (message might be the same, or rate limited)
                        if "429" in str(e) or "Too Many Requests" in str(e):
                             logger.warning(f"Rate limit hit during edit: {e}")
                             # Backoff slightly
                             await asyncio.sleep(2)
                        else:
                             logger.debug(f"Edit message error: {e}")
            
            logger.info(f"Streaming complete: received {chunk_count} chunks, total length={len(full_response)}")
            
            # Safety check: If response is too huge, truncate or warn
            if len(sent_messages) > 20:
                 logger.warning(f"Too many messages generated ({len(sent_messages)}). Stopping updates.")
                 await bot.send_message(chat_id=chat.id, text="[Response truncated due to length limit]")
                 return
            
            # Final update
            try:
                # Ensure we have enough messages for the final text
                num_needed = (len(full_response) // MESSAGE_LIMIT) + 1
                while len(sent_messages) < num_needed:
                    new_msg = await bot.send_message(chat_id=chat.id, text="...")
                    sent_messages.append(new_msg)
                    sent_texts[new_msg.message_id] = "..."
                
                # Update all messages to ensure they are clean (no "...")
                for i, msg in enumerate(sent_messages):
                    start_idx = i * MESSAGE_LIMIT
                    end_idx = (i + 1) * MESSAGE_LIMIT
                    text_chunk = full_response[start_idx:end_idx]
                    
                    # Only update if it's the last one OR if we want to remove "..." from previous ones
                    # To be safe and clean, update all.
                    
                    final_text = text_chunk
                    if i == len(sent_messages) - 1 and not final_text:
                         final_text = "I didn't get a response."

                    if sent_texts.get(msg.message_id) != final_text:
                        await bot.edit_message_text(
                            chat_id=chat.id,
                            message_id=msg.message_id,
                            text=final_text
                        )
                        sent_texts[msg.message_id] = final_text
                logger.debug(f"Final message edit successful")
            except Exception as e:
                logger.error(f"Final edit error: {e}")
            
        except Exception as e:
            logger.error(f"Error processing message in streaming block: {e}", exc_info=True)
            await bot.send_message(chat_id=chat.id, text="Sorry, I encountered an error.")
    
    except Exception as e:
        logger.error(f"Error in process_update: {e}", exc_info=True)
        try:
            await bot.send_message(chat_id=chat.id, text="Sorry, I encountered an error processing your message.")
        except Exception as send_error:
            logger.error(f"Failed to send error message to user: {send_error}")


async def process_update(update: Update):
    """
    Wrapper around _process_update_impl to enforce sequential processing per user.
    """
    user = update.effective_user
    if not user:
        await _process_update_impl(update)
        return

    lock = get_user_lock(user.id)
    async with lock:
        await _process_update_impl(update)


