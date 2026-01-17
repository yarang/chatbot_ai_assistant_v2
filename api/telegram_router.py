import asyncio
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException, status
from langchain_core.messages import AIMessage, HumanMessage
from telegram import Bot, Update

from agent.graph import graph
from core.config import get_settings
from core.logger import get_logger
from services.streaming_helper import TelegramMarkdownFormatter
from repository.chat_room_repository import set_chat_room_persona, upsert_chat_room
from repository.persona_repository import (
    create_persona,
    get_persona_by_id,
    get_public_personas,
    get_user_personas,
)
from repository.user_repository import upsert_user

logger = get_logger(__name__)

# Create router with explicit settings for OpenAPI documentation
router = APIRouter(
    tags=["Telegram"],
    responses={
        200: {"description": "Success"},
        401: {"description": "Unauthorized - Invalid webhook secret"},
        429: {"description": "Too Many Requests - IP blocked due to failed attempts"},
    },
)

settings = get_settings()
bot_token = settings.telegram.bot_token
# Initialize Bot only if token is present to avoid errors during startup if not configured
bot = None  # Lazy initialization
bot_initialized = False

# Rate limiting and anomaly detection for webhook security
FAILED_AUTH_ATTEMPTS: Dict[str, List[float]] = defaultdict(list)
MAX_FAILED_ATTEMPTS = 10  # Maximum failed attempts before blocking
BLOCK_DURATION = 300  # Block duration in seconds (5 minutes)


def is_ip_blocked(client_ip: str) -> bool:
    """
    Check if an IP address is currently blocked due to too many failed attempts.

    Args:
        client_ip: Client IP address

    Returns:
        bool: True if IP is blocked, False otherwise
    """
    current_time = time.time()

    # Clean up old entries
    if client_ip in FAILED_AUTH_ATTEMPTS:
        # Remove attempts older than block duration
        FAILED_AUTH_ATTEMPTS[client_ip] = [
            attempt_time
            for attempt_time in FAILED_AUTH_ATTEMPTS[client_ip]
            if current_time - attempt_time < BLOCK_DURATION
        ]

        # If still too many attempts, block
        if len(FAILED_AUTH_ATTEMPTS[client_ip]) >= MAX_FAILED_ATTEMPTS:
            return True

    return False


def record_failed_attempt(client_ip: str) -> int:
    """
    Record a failed authentication attempt for an IP address.

    Args:
        client_ip: Client IP address

    Returns:
        int: Number of failed attempts in the current time window
    """
    current_time = time.time()
    FAILED_AUTH_ATTEMPTS[client_ip].append(current_time)

    # Clean up old entries
    FAILED_AUTH_ATTEMPTS[client_ip] = [
        attempt_time
        for attempt_time in FAILED_AUTH_ATTEMPTS[client_ip]
        if current_time - attempt_time < BLOCK_DURATION
    ]

    return len(FAILED_AUTH_ATTEMPTS[client_ip])


async def get_bot():
    global bot, bot_initialized
    if not bot_initialized and bot_token:
        bot = Bot(token=bot_token)
        bot_initialized = True
    return bot


def verify_webhook_secret(request: Request) -> bool:
    """
    Verify Telegram webhook secret token.

    Telegram sends the secret token in the X-Telegram-Bot-Api-Secret-Token header.
    This must match the TELEGRAM_WEBHOOK_SECRET environment variable.

    Args:
        request: FastAPI Request object

    Returns:
        bool: True if secret is valid or not configured, False otherwise
    """
    webhook_secret = settings.telegram.webhook_secret

    # If no secret is configured, skip verification (not recommended for production)
    if not webhook_secret:
        logger.warning("Webhook secret not configured. Skipping verification.")
        return True

    # Get the secret token from the request header
    received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")

    if not received_secret:
        logger.warning("Webhook request missing secret token header")
        return False

    # Compare secrets
    if received_secret != webhook_secret:
        logger.warning(
            f"Invalid webhook secret token received: {received_secret[:10]}..."
        )
        return False

    return True


def extract_request_info(request: Request) -> Dict[str, str]:
    """
    Extract useful information from request for logging.

    Args:
        request: FastAPI Request object

    Returns:
        Dict with request information
    """
    return {
        "client_host": request.client.host if request.client else "unknown",
        "user_agent": request.headers.get("user-agent", "unknown"),
        "content_type": request.headers.get("content-type", "unknown"),
        "x_forwarded_for": request.headers.get("x-forwarded-for", "unknown"),
    }


@router.post(
    "/webhook",
    tags=["Telegram"],
    summary="Telegram Webhook",
    description="Telegram Bot에서 업데이트를 수신하는 Webhook 엔드포인트입니다. 보안 검증 및 Rate Limiting이 포함되어 있습니다.",
    responses={
        200: {"description": "Update received and queued for processing"},
        401: {"description": "Unauthorized - Invalid webhook secret token"},
        429: {
            "description": "Too Many Requests - IP blocked due to failed authentication attempts"
        },
    },
    include_in_schema=True,
)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Telegram Webhook endpoint - receives updates from Telegram.

    Security features:
    - IP-based rate limiting and blocking
    - Secret token verification (if TELEGRAM_WEBHOOK_SECRET is set)
    - Request logging with client information
    - Error handling with detailed logging
    """
    # Extract request information for logging
    req_info = extract_request_info(request)
    client_ip = req_info["client_host"]

    # Check if IP is blocked due to too many failed attempts
    if is_ip_blocked(client_ip):
        logger.warning(
            f"Webhook request from blocked IP. "
            f"Client: {client_ip}, "
            f"Failed attempts: {len(FAILED_AUTH_ATTEMPTS[client_ip])}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed authentication attempts. Please try again later.",
        )

    # Verify webhook secret token
    if not verify_webhook_secret(request):
        # Record failed attempt
        failed_count = record_failed_attempt(client_ip)

        # Log the failed attempt with request details
        logger.warning(
            f"Webhook authentication failed. "
            f"Client: {client_ip}, "
            f"Failed attempts: {failed_count}/{MAX_FAILED_ATTEMPTS}, "
            f"User-Agent: {req_info['user_agent']}, "
            f"X-Forwarded-For: {req_info['x_forwarded_for']}"
        )

        # Return 401 Unauthorized to reject the request
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook secret token",
        )

    bot_instance = await get_bot()

    try:
        # Parse Telegram update from request body
        data = await request.json()
        update = Update.de_json(data, bot_instance)

        logger.info(
            f"Received webhook update. "
            f"Update ID: {update.update_id}, "
            f"Client: {client_ip}"
        )

        # Process update in background to avoid blocking webhook response
        background_tasks.add_task(process_update, update)

    except HTTPException:
        # Re-raise HTTP exceptions (authentication failures)
        raise

    except Exception as e:
        # Log error with request context
        logger.error(
            f"Error processing webhook. Client: {client_ip}, Error: {e}", exc_info=True
        )
        # Still return 200 to avoid Telegram retries
        # (The error is logged, so we can monitor it)

    return {"status": "ok"}


# Global cache for bot username
BOT_USERNAME = None

# Global lock per user to prevent concurrent processing
USER_LOCKS: Dict[int, asyncio.Lock] = {}


def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in USER_LOCKS:
        USER_LOCKS[user_id] = asyncio.Lock()
    return USER_LOCKS[user_id]


async def edit_message_with_retry(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
) -> bool:
    """
    Edit a Telegram message with retry logic and exponential backoff.

    Args:
        bot: Telegram Bot instance
        chat_id: Chat ID
        message_id: Message ID to edit
        text: New text content
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (will be doubled each retry)

    Returns:
        bool: True if successful, False otherwise
    """
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
            )
            return True

        except Exception as e:
            error_str = str(e)

            # Don't retry if error is not retryable
            if "message is not modified" in error_str.lower():
                # Message content same as before, treat as success
                return True
            elif "message to edit not found" in error_str.lower():
                # Message was deleted, can't retry
                logger.warning(f"Message {message_id} not found for editing")
                return False
            elif "429" in error_str or "Too Many Requests" in error_str:
                # Rate limit - apply backoff
                logger.warning(
                    f"Rate limit hit on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                else:
                    return False
            elif "Bad Request" in error_str:
                # Bad request (e.g., invalid markdown), don't retry
                logger.debug(f"Bad request editing message: {e}")
                return False
            else:
                # Other errors - log and retry
                logger.debug(
                    f"Error editing message (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                    continue
                else:
                    return False

    return False


async def send_with_typing_indicator(
    bot: Bot,
    chat_id: int,
    text: str,
) -> None:
    """
    Send a message with typing indicator before sending.

    Args:
        bot: Telegram Bot instance
        chat_id: Chat ID
        text: Text to send
    """
    try:
        # Send typing action
        await bot.send_chat_action(chat_id=chat_id, action="typing")
        # Small delay to make it visible
        await asyncio.sleep(0.3)
        # Send the message
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.error(f"Error sending message with typing indicator: {e}")
        # Fallback: just send the message
        try:
            await bot.send_message(chat_id=chat_id, text=text)
        except Exception as e2:
            logger.error(f"Error sending fallback message: {e2}")


def escape_for_telegram(text: str) -> str:
    """
    Escape text for safe Telegram message sending (without Markdown).
    This is a fallback when Markdown formatting fails.

    Args:
        text: Text to escape

    Returns:
        Escaped text safe for plain text messages
    """
    # For plain text messages, we mainly need to escape special characters
    # that could be interpreted as Markdown or other formatting
    return TelegramMarkdownFormatter.escape_markdown(text)


@router.get(
    "/telegram/test",
    tags=["Telegram"],
    summary="Telegram Test Endpoint",
    description="Telegram router가 제대로 로드되었는지 테스트하는 엔드포인트입니다.",
)
async def telegram_test():
    """Test endpoint to verify telegram router is working."""
    return {
        "status": "ok",
        "message": "Telegram router is working!",
        "router": "telegram_router",
    }


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

        logger.info(
            f"Processing message from chat_id={chat.id}, chat_type={chat.type}, user_id={user.id}, text_preview={text[:50] if text else 'photo/doc'}"
        )

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
            last_name=user.last_name,
        )
        logger.debug(f"User upserted: db_user_id={db_user.id}")

        # 2. Ensure ChatRoom exists
        logger.debug(f"Upserting chat room with telegram_chat_id={chat.id}")
        db_chat_room = await upsert_chat_room(
            telegram_chat_id=chat.id,
            name=chat.title or user.first_name,
            type=chat.type,
            username=chat.username,
        )
        logger.debug(f"Chat room upserted: db_chat_room_id={db_chat_room.id}")

        # 3. Handle Commands
        if text and (text.startswith("/start") or text.startswith("/help")):
            help_text = """👋 안녕하세요! AI 어시스턴트입니다.

📋 **대화 관리**
• `/help` 또는 `/start` - 이 도움말 표시
• `/summary` - 현재 대화 내용 요약

🎭 **페르소나 (AI 성격)**
• `/persona` - 현재 설정된 페르소나 확인
• `/personas` - 사용 가능한 페르소나 목록
• `/select_persona <id>` - 페르소나 변경 (예: `/select_persona 6d7ba44a-a3eb-432c-adaf-9b0b9330bc`)
• `/create_persona {"name": "이름", "content": "프롬프트"}` - 새 페르소나 생성

📚 **문서 관리 (RAG)**
• 파일 전송 - PDF/TXT 파일 업로드 (최대 10MB)
• `/files` - 업로드된 문서 목록 확인
• `/delete_file <id>` - 문서 삭제

💡 **팁**
• 파일을 업로드하면 자동으로 분석되어 대화에 활용됩니다
• 페르소나를 변경하면 AI의 응답 스타일이 바뀝니다
• 언제든지 메시지를 보내서 대화를 시작하세요!

---
도움이 필요하시면 `/help`를 입력하세요."""
            await bot.send_message(
                chat_id=chat.id, text=help_text, parse_mode="Markdown"
            )
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
                        text='Please provide persona data in JSON format.\nExample: /create_persona {"name": "My Persona", "content": "You are a helpful assistant."}',
                    )
                    return

                data = json.loads(json_str)
                name = data.get("name")
                content = data.get("content")
                description = data.get("description")
                is_public = data.get("is_public", False)

                if not name or not content:
                    await bot.send_message(
                        chat_id=chat.id, text="Name and content are required."
                    )
                    return

                new_persona = await create_persona(
                    user_id=db_user.id,
                    name=name,
                    content=content,
                    description=description,
                    is_public=is_public,
                )
                await bot.send_message(
                    chat_id=chat.id,
                    text=f"Persona created: {new_persona.name} (ID: {new_persona.id})",
                )
            except json.JSONDecodeError:
                await bot.send_message(chat_id=chat.id, text="Invalid JSON format.")
            except Exception as e:
                await bot.send_message(
                    chat_id=chat.id, text=f"Error creating persona: {e}"
                )
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
                        msg += (
                            f"- {p.name}\n  ID: `{p.id}`\n  {p.description or ''}\n\n"
                        )
                    msg += "Use `/select_persona <id>` to set."
                    await bot.send_message(
                        chat_id=chat.id, text=msg, parse_mode="Markdown"
                    )
            except Exception as e:
                await bot.send_message(
                    chat_id=chat.id, text=f"Error fetching personas: {e}"
                )
            return

        if text and text.startswith("/select_persona"):
            parts = text.split()
            if len(parts) < 2:
                await bot.send_message(
                    chat_id=chat.id, text="Usage: /select_persona <id>"
                )
                return

            persona_id = parts[1]
            try:
                # Verify persona exists
                persona = await get_persona_by_id(persona_id)
                if persona:
                    await set_chat_room_persona(db_chat_room.id, persona.id)
                    await bot.send_message(
                        chat_id=chat.id, text=f"Persona set to: {persona.name}"
                    )
                else:
                    await bot.send_message(chat_id=chat.id, text="Persona not found.")
            except Exception as e:
                await bot.send_message(
                    chat_id=chat.id, text=f"Error setting persona: {e}"
                )
            return

        if text and text.startswith("/persona"):
            # Show current persona
            if db_chat_room.persona_id:
                persona = await get_persona_by_id(db_chat_room.persona_id)
                if persona:
                    await bot.send_message(
                        chat_id=chat.id,
                        text=f"Current Persona: {persona.name}\n{persona.description or ''}",
                    )
                else:
                    await bot.send_message(
                        chat_id=chat.id,
                        text="Current persona ID not found (maybe deleted).",
                    )
            else:
                await bot.send_message(
                    chat_id=chat.id, text="No persona set. Using default."
                )
            return

        if text and text.startswith("/summary"):
            await bot.send_message(
                chat_id=chat.id,
                text="대화 내용을 요약하고 있습니다. 잠시만 기다려주세요...",
            )
            try:
                from telegram.helpers import escape_markdown

                from services.conversation_service import summarize_chat_room

                summary = await summarize_chat_room(
                    chat_room_id=db_chat_room.id, user_id=db_user.id
                )
                # Use MarkdownV2 for better stability, escape the LLM output
                safe_summary = escape_markdown(summary, version=2)
                # Header "📋 대화 요약" in bold. Note: emojis don't strictly need escaping but good practice to be safe or just string format
                header = escape_markdown("📋 대화 요약", version=2)

                await bot.send_message(
                    chat_id=chat.id,
                    text=f"*{header}*\n\n{safe_summary}",
                    parse_mode="MarkdownV2",
                )
            except Exception as e:
                logger.error(f"Error executing summary command: {e}")
                await bot.send_message(
                    chat_id=chat.id, text="대화 요약 중 오류가 발생했습니다."
                )
            return

        if text and text.startswith("/files"):
            # List known documents
            try:
                from telegram.helpers import escape_markdown

                from services.knowledge_service import get_chat_room_documents

                logger.info(f"Listing files for chat_room_id={db_chat_room.id}")
                docs = await get_chat_room_documents(str(db_chat_room.id))

                if not docs:
                    logger.info("No docs returned from service.")
                    await bot.send_message(
                        chat_id=chat.id,
                        text="No uploaded documents found in this room.",
                    )
                else:
                    msg = "📚 *Uploaded Documents*:\n\n"
                    for doc in docs:
                        # Escape filename for Markdown (v1 legacy used here since parse_mode="Markdown")
                        # Version 1 escapes are minimal but we need to be careful.
                        # Actually let's just use explicit replacements or safe text.
                        # Using MarkdownV2 is better but requires escaping everything.
                        # Let's stick to v1 but escape common chars.
                        safe_filename = (
                            doc.filename.replace("_", "\\_")
                            .replace("*", "\\*")
                            .replace("`", "\\`")
                            .replace("[", "\\[")
                        )

                        sub_text = f"Method: {doc.processing_method}, Size: {doc.size or 0} bytes"
                        # Escape sub_text chars too just in case
                        sub_text = (
                            sub_text.replace("_", "\\_")
                            .replace("*", "\\*")
                            .replace("`", "\\`")
                        )

                        msg += f"📄 *{safe_filename}*\n   ID: `{doc.id}`\n   {sub_text}\n\n"

                    msg += "Use `/delete_file <id>` to remove."
                    await bot.send_message(
                        chat_id=chat.id, text=msg, parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error(f"Error fetching files: {e}")
                await bot.send_message(
                    chat_id=chat.id, text="Failed to retrieve file list."
                )
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
                    await bot.send_message(
                        chat_id=chat.id,
                        text=f"✅ Document `{doc_id}` deleted successfully.",
                        parse_mode="Markdown",
                    )
                else:
                    await bot.send_message(
                        chat_id=chat.id,
                        text=f"❌ Failed to delete document. Check ID and Permissions.",
                    )
            except Exception as e:
                logger.error(f"Error deleting file: {e}")
                await bot.send_message(
                    chat_id=chat.id, text=f"Error deleting file: {e}"
                )
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
                b64_str = base64.b64encode(image_bytes).decode("utf-8")
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

                # Check file size limit
                if doc.file_size and doc.file_size > settings.telegram.max_file_size:
                    await bot.send_message(
                        chat_id=chat.id,
                        text=f"❌ File too large. Maximum size: 10MB (Your file: {doc.file_size / 1024 / 1024:.1f}MB)",
                    )
                    return

                # Check for supported types
                if (
                    "pdf" in mime_type.lower()
                    or "text/plain" in mime_type.lower()
                    or file_name.lower().endswith(".pdf")
                    or file_name.lower().endswith(".txt")
                ):
                    await bot.send_message(
                        chat_id=chat.id,
                        text=f"📥 Processing document: {file_name}...\nThis may take a moment.",
                    )

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

                    success, msg = await process_uploaded_file(
                        str(db_chat_room.id), str(db_user.id), upload_file
                    )

                    if success:
                        await bot.send_message(chat_id=chat.id, text=f"✅ {msg}")
                    else:
                        # Truncate error message if too long
                        error_msg = str(msg)
                        if len(error_msg) > 3000:
                            error_msg = error_msg[:3000] + "... (truncated)"
                        await bot.send_message(
                            chat_id=chat.id, text=f"❌ Ingestion failed: {error_msg}"
                        )
                    return
                else:
                    await bot.send_message(
                        chat_id=chat.id,
                        text="Unsupported file type. Please upload PDF or TXT files.",
                    )
                    return

            except Exception as e:
                logger.error(f"Error processing document: {e}", exc_info=True)
                await bot.send_message(
                    chat_id=chat.id, text="Failed to process document."
                )
                return

        message_content = text
        if image_data:
            message_content = [
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": image_data}},
            ]

        # For now, streaming doesn't support multimodal (image) due to complexity
        # Fall back to non-streaming for images
        if image_data:
            inputs = {
                "messages": [HumanMessage(content=message_content)],
                "user_id": str(db_user.id),
                "chat_room_id": str(db_chat_room.id),
                "model_name": "gemini-1.5-flash",
            }

            try:
                result = await graph.ainvoke(inputs)
                response_messages = result["messages"]
                ai_response = response_messages[-1]

                if isinstance(ai_response, AIMessage):
                    await bot.send_message(chat_id=chat.id, text=ai_response.content)
                else:
                    await bot.send_message(
                        chat_id=chat.id, text="I didn't get a response."
                    )

            except Exception as e:
                print(f"Error processing message: {e}")
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    await bot.send_message(
                        chat_id=chat.id,
                        text="죄송합니다. API 사용량을 초과했습니다. 나중에 다시 시도해 주세요.",
                    )
                else:
                    await bot.send_message(
                        chat_id=chat.id, text="Sorry, I encountered an error."
                    )
            return

        # Streaming response for text-only messages
        logger.info(
            f"Starting streaming response for user_id={db_user.id}, chat_room_id={db_chat_room.id}"
        )
        try:
            # Send typing indicator before starting stream
            await bot.send_chat_action(chat_id=chat.id, action="typing")
            await asyncio.sleep(0.2)  # Brief pause to show typing

            # Send initial message
            sent_msg = await bot.send_message(chat_id=chat.id, text="...")
            logger.debug(f"Sent initial message: message_id={sent_msg.message_id}")

            full_response = ""
            chunk_count = 0

            # List of sent messages to handle pagination
            sent_messages: List[Update] = [sent_msg]
            sent_texts: Dict[int, str] = {sent_msg.message_id: "..."}
            MESSAGE_LIMIT = settings.telegram.message_limit

            # Determine user name for context
            user_name = db_user.first_name or db_user.username or "Unknown"

            async for chunk in ask_question_stream(
                user_id=str(db_user.id),
                chat_room_id=str(db_chat_room.id),
                question=text,
                user_name=user_name,
            ):
                # Smart update logic to handle both deltas and snapshots
                if chunk.startswith(full_response) and len(chunk) >= len(full_response):
                    # It's a snapshot (extended version of previous)
                    full_response = chunk
                else:
                    # It's a delta (or a new independent chunk)
                    full_response += chunk
                chunk_count += 1

                # Update message with retry logic
                # StreamBuffer now handles timing, so we update every chunk
                try:
                    # Calculate how many messages we need
                    num_needed = (len(full_response) // MESSAGE_LIMIT) + 1

                    # If we need more messages than we have
                    if num_needed > len(sent_messages):
                        # First, finalize the current last message (fill it up and remove "...")
                        prev_last_msg = sent_messages[-1]
                        prev_last_idx = len(sent_messages) - 1
                        prev_text = full_response[
                            prev_last_idx * MESSAGE_LIMIT : (prev_last_idx + 1)
                            * MESSAGE_LIMIT
                        ]

                        if sent_texts.get(prev_last_msg.message_id) != prev_text:
                            success = await edit_message_with_retry(
                                bot=bot,
                                chat_id=chat.id,
                                message_id=prev_last_msg.message_id,
                                text=prev_text,
                            )
                            if success:
                                sent_texts[prev_last_msg.message_id] = prev_text

                        # Add new messages
                        while len(sent_messages) < num_needed:
                            new_msg = await bot.send_message(
                                chat_id=chat.id, text="..."
                            )
                            sent_messages.append(new_msg)
                            sent_texts[new_msg.message_id] = "..."

                    # Now update the (possibly new) last message
                    last_msg_index = len(sent_messages) - 1
                    start_idx = last_msg_index * MESSAGE_LIMIT
                    current_chunk_text = full_response[start_idx:]
                    new_text = current_chunk_text + "..."

                    if sent_texts.get(sent_messages[-1].message_id) != new_text:
                        success = await edit_message_with_retry(
                            bot=bot,
                            chat_id=chat.id,
                            message_id=sent_messages[-1].message_id,
                            text=new_text,
                        )
                        if success:
                            sent_texts[sent_messages[-1].message_id] = new_text

                except Exception as e:
                    logger.debug(f"Error in streaming update loop: {e}")

            logger.info(
                f"Streaming complete: received {chunk_count} chunks, total length={len(full_response)}"
            )

            # Safety check: If response is too huge, truncate or warn
            if len(sent_messages) > 20:
                logger.warning(
                    f"Too many messages generated ({len(sent_messages)}). Stopping updates."
                )
                await bot.send_message(
                    chat_id=chat.id, text="[Response truncated due to length limit]"
                )
                return

            # Final update with retry logic
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
                        success = await edit_message_with_retry(
                            bot=bot,
                            chat_id=chat.id,
                            message_id=msg.message_id,
                            text=final_text,
                        )
                        if success:
                            sent_texts[msg.message_id] = final_text
                logger.debug(f"Final message edit successful")
            except Exception as e:
                logger.error(f"Final edit error: {e}")

        except Exception as e:
            logger.error(
                f"Error processing message in streaming block: {e}", exc_info=True
            )
            await bot.send_message(
                chat_id=chat.id, text="Sorry, I encountered an error."
            )

    except Exception as e:
        logger.error(f"Error in process_update: {e}", exc_info=True)
        try:
            await bot.send_message(
                chat_id=chat.id,
                text="Sorry, I encountered an error processing your message.",
            )
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
