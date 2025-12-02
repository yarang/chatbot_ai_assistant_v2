from fastapi import APIRouter, Request, BackgroundTasks
import asyncio
from telegram import Update, Bot
from core.config import get_settings
from core.graph import graph
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
        if update.message and update.message.text:
            background_tasks.add_task(process_update, update)
    except Exception as e:
        print(f"Error parsing update: {e}")
        
    return {"status": "ok"}


# Global cache for bot username
BOT_USERNAME = None

async def process_update(update: Update):
    global BOT_USERNAME
    
    try:
        user = update.effective_user
        chat = update.effective_chat
        message = update.message
        
        # Handle edited messages or other updates that might not have a message
        if not message:
            logger.debug("Update has no message, skipping")
            return

        text = message.text or message.caption
        
        if not text and not message.photo:
            logger.debug("Message has no text or photo, skipping")
            return
        
        logger.info(f"Processing message from chat_id={chat.id}, chat_type={chat.type}, user_id={user.id}, text_preview={text[:50] if text else 'photo'}")

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


        # Group Chat Selective Response Logic
        if chat.type in ["group", "supergroup"]:
            logger.debug(f"Group chat detected, checking for mentions or replies")
            is_mentioned = False
            is_reply_to_bot = False
            
            # Check for mention using entities
            if message.entities:
                for entity in message.entities:
                    if entity.type == "mention":
                        # Extract username from text
                        mention_text = text[entity.offset:entity.offset + entity.length]
                        if BOT_USERNAME and mention_text.lower() == f"@{BOT_USERNAME.lower()}":
                            is_mentioned = True
                            logger.info(f"Bot mentioned via @mention in group chat")
                            break
                    elif entity.type == "text_mention":
                        # Check if it mentions the bot user
                        if BOT_USERNAME and entity.user and entity.user.username and entity.user.username.lower() == BOT_USERNAME.lower():
                            is_mentioned = True
                            logger.info(f"Bot mentioned via text_mention in group chat")
                            break
            
            # Fallback: Check for mention in text if entities didn't catch it (or if checking text is preferred)
            if not is_mentioned and BOT_USERNAME and f"@{BOT_USERNAME}" in text:
                is_mentioned = True
                logger.info(f"Bot mentioned via text search in group chat")

            # Check for reply
            if message.reply_to_message and message.reply_to_message.from_user:
                # We need to know bot's ID to check if reply is to bot.
                # bot.get_me() returns User object which has ID.
                # We can cache BOT_ID as well if needed, but let's assume we can check username or ID.
                # If we have BOT_USERNAME, we can check if reply user is us.
                if BOT_USERNAME and message.reply_to_message.from_user.username and message.reply_to_message.from_user.username.lower() == BOT_USERNAME.lower():
                    is_reply_to_bot = True
                    logger.info(f"Message is a reply to bot in group chat")
                    
            if not (is_mentioned or is_reply_to_bot):
                # Ignore message
                logger.debug(f"Ignoring group message - not mentioned or replied to")
                return
        else:
            logger.debug(f"Non-group chat (type={chat.type}), processing message")

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
        if text.startswith("/start") or text.startswith("/help"):
            help_text = """
Hello! I am your AI assistant. You can use the following commands:

/help - Show this help message
/persona - Show current persona
/personas - List available personas
/create_persona - Create a new persona
/select_persona <id> - Select a persona
"""
            await bot.send_message(chat_id=chat.id, text=help_text)
            return

        if text.startswith("/create_persona"):
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

        if text.startswith("/personas"):
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

        if text.startswith("/select_persona"):
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
            
        if text.startswith("/persona"):
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
                print(f"Error processing photo: {e}")
                await bot.send_message(chat_id=chat.id, text="Failed to process image.")
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
            
            async for chunk in ask_question_stream(
                user_id=str(db_user.id),
                chat_room_id=str(db_chat_room.id),
                question=text
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

