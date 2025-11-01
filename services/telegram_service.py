from typing import Any, Dict

from core.config import load_config
from repository.user_repository import upsert_user
from repository.chat_room_repository import upsert_chat_room
from services.conversation_service import ask_question


async def handle_update(update: Dict[str, Any], secret_header: str | None) -> bool:
    config = load_config()
    expected = config["telegram"].get("webhook_secret")
    if expected and secret_header != expected:
        return False

    message = update.get("message") or update.get("edited_message")
    if not message:
        return True

    chat = message.get("chat", {})
    from_user = message.get("from", {})
    text = message.get("text", "")

    # Upsert user
    # Telegram 사용자는 email이 없을 수 있으므로, telegram_id를 기반으로 식별
    telegram_id = from_user.get("id")
    # email은 telegram_id를 기반으로 생성 (또는 다른 방식으로 처리)
    email = f"telegram_{telegram_id}@telegram.local"
    
    user = await upsert_user(
        email=email,
        telegram_id=telegram_id,
        username=from_user.get("username"),
        first_name=from_user.get("first_name"),
        last_name=from_user.get("last_name"),
    )

    # Upsert chat room
    telegram_chat_id = chat.get("id")
    chat_type = chat.get("type", "private")  # private, group, supergroup, channel
    chat_title = chat.get("title") or chat.get("first_name")  # 그룹/채널 제목 또는 개인 채팅 이름
    chat_username = chat.get("username")
    
    chat_room = await upsert_chat_room(
        telegram_chat_id=telegram_chat_id,
        name=chat_title,
        type=chat_type,
        username=chat_username,
    )

    # Generate answer and (optionally) send back via Telegram API later
    await ask_question(user_id=user.id, chat_room_id=chat_room.id, question=text)
    return True



