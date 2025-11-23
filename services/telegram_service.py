from typing import Any, Dict, Optional, List
import json
import aiohttp

from core.config import load_config
from core.logger import get_logger
from core.database import get_async_session
from models.chat_room_model import ChatRoom
from models.user_model import User
from models.persona_model import Persona
from repository.chat_room_repository import ChatRoomRepository
from repository.user_repository import UserRepository
from repository.persona_repository import PersonaRepository
from services.conversation_service import ask_question

logger = get_logger(__name__)

config = load_config()
TELEGRAM_BOT_TOKEN = config["telegram"]["bot_token"]
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


async def send_telegram_message(chat_id: str | int, text: str) -> bool:
    """텔레그램 메시지를 전송합니다."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{TELEGRAM_API_BASE}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "HTML"
                }
            ) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")
        return False


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
    # email은 telegram_id를 기반으로 생성
    email = f"telegram_{telegram_id}@telegram.local"
    
    user_repo = UserRepository()
    chat_room_repo = ChatRoomRepository()
    
    async with get_async_session() as session:
        user = await user_repo.upsert_user(
            session,
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
        
        chat_room = await chat_room_repo.upsert_chat_room(
            session,
            telegram_chat_id=telegram_chat_id,
            name=chat_title,
            type=chat_type,
            username=chat_username,
        )

    # Command handling
        if text.startswith('/'):
            return await handle_command(text, user.id, chat_room.id)

        # Generate answer using the current persona
        persona_repo = PersonaRepository()
        chat_room_repo = ChatRoomRepository()
        
        async with get_async_session() as session:
            chat_room = await chat_room_repo.get_chat_room_by_id(session, chat_room.id)
            if not chat_room.persona_id:
                # Create default persona if none exists
                persona = await persona_repo.create_persona(
                    session=session,
                    user_id=user.id,
                    name="기본 어시스턴트",
                    content="당신은 도움이 되는 AI 어시스턴트입니다. 사용자의 질문에 정중하고 도움이 되게 답변해주세요.",
                    description="기본 AI 어시스턴트"
                )
                chat_room.persona_id = persona.id
                await session.commit()
            else:
                persona = await persona_repo.get_persona_by_id(session, chat_room.persona_id)
    
        # Generate answer using the persona
        response = await ask_question(user.id, chat_room.id, text, system_prompt=persona.content)
        
        # Send response back via Telegram API
        await send_telegram_message(chat_id=telegram_chat_id, text=response)
        return True


async def handle_command(command: str, user_id: str, chat_room_id: str) -> bool:
    """
    Telegram 명령어를 처리합니다.
    
    Available commands:
    /start - 시작 메시지와 도움말을 표시합니다
    /help - 사용 가능한 명령어 목록을 표시합니다
    /persona - 현재 사용 중인 페르소나 정보를 표시합니다
    /personas - 사용 가능한 페르소나 목록을 표시합니다
    /create_persona - 새로운 페르소나를 생성합니다
    /select_persona {id} - 특정 페르소나를 선택합니다
    """
    
    cmd_parts = command.split()
    cmd = cmd_parts[0].lower()
    args = cmd_parts[1:] if len(cmd_parts) > 1 else []
    
    persona_repo = PersonaRepository()
    chat_room_repo = ChatRoomRepository()
    
        if cmd == '/login':
            async with get_async_session() as session:
                user = await user_repo.get_user_by_id(session, user_id)
            if user:
                user_info = f"""
    if cmd == '/start' or cmd == '/help':
        help_text = """
안녕하세요! 저는 AI 챗봇 어시스턴트입니다. 다음 명령어를 사용할 수 있습니다:

/help - 이 도움말을 표시합니다
/persona - 현재 사용 중인 페르소나 정보를 표시합니다
/personas - 사용 가능한 페르소나 목록을 표시합니다
/create_persona - 새로운 페르소나를 생성합니다
                await send_telegram_message(chat_id=chat_room_id, text=user_info)
                return True
            else:
                await send_telegram_message(chat_id=chat_room_id, text="사용자 정보를 찾을 수 없습니다.")
                return True
/select_persona {id} - 특정 페르소나를 선택합니다

자유롭게 대화를 시작해보세요!
"""
        await send_telegram_message(chat_id=chat_room_id, text=help_text)
        return True

    elif cmd == '/persona':
        async with get_async_session() as session:
            chat_room = await chat_room_repo.get_chat_room_by_id(session, chat_room_id)
            if not chat_room or not chat_room.persona_id:
                await send_telegram_message(chat_id=chat_room_id, text="현재 선택된 페르소나가 없습니다.")
                return True
                
            persona = await persona_repo.get_persona_by_id(session, chat_room.persona_id)
            if not persona:
                await send_telegram_message(chat_id=chat_room_id, text="페르소나를 찾을 수 없습니다.")
                return True
                
            persona_info = f"""
현재 페르소나 정보:
이름: {persona.name}
설명: {persona.description or '설명 없음'}
"""
            await send_telegram_message(chat_id=chat_room_id, text=persona_info)
            return True

    elif cmd == '/personas':
        async with get_async_session() as session:
            personas = await persona_repo.get_user_personas(session, user_id, include_public=True)
        
        if not personas:
            await send_telegram_message(chat_id=chat_room_id, text="사용 가능한 페르소나가 없습니다.")
            return True
            
        personas_list = "사용 가능한 페르소나 목록:\n\n"
        for p in personas:
            personas_list += f"ID: {p.id}\n이름: {p.name}\n설명: {p.description or '설명 없음'}\n\n"
        
        await send_telegram_message(chat_id=chat_room_id, text=personas_list)
        return True

    elif cmd == '/create_persona':
        # Implement persona creation logic
        create_text = """
새로운 페르소나를 생성하려면 다음 형식으로 입력해주세요:

/create_persona
{
    "name": "페르소나 이름",
    "content": "페르소나 시스템 프롬프트",
    "description": "페르소나 설명 (선택사항)",
    "is_public": false
}
"""
        if len(args) == 0:
            await send_telegram_message(chat_id=chat_room_id, text=create_text)
            return True
            
        try:
            persona_data = json.loads(" ".join(args))
            async with get_async_session() as session:
                persona = await persona_repo.create_persona(
                    session=session,
                    user_id=user_id,
                    **persona_data
                )
                await session.commit()
                
            await send_telegram_message(
                chat_id=chat_room_id,
                text=f"페르소나가 생성되었습니다!\nID: {persona.id}\n이름: {persona.name}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to create persona: {e}")
            await send_telegram_message(
                chat_id=chat_room_id,
                text="페르소나 생성에 실패했습니다. 형식을 확인해주세요."
            )
            return True

    elif cmd == '/select_persona':
        if len(args) == 0:
            await send_telegram_message(
                chat_id=chat_room_id,
                text="사용할 페르소나의 ID를 입력해주세요.\n예: /select_persona {persona_id}"
            )
            return True
            
        persona_id = args[0]
        async with get_async_session() as session:
            # Persona 조회
            persona = await persona_repo.get_persona_by_id(session, persona_id)
            if not persona:
                await send_telegram_message(chat_id=chat_room_id, text="페르소나를 찾을 수 없습니다.")
                return True
            
            # 채팅방 업데이트
            chat_room = await chat_room_repo.get_chat_room_by_id(session, chat_room_id)
            if not chat_room:
                await send_telegram_message(chat_id=chat_room_id, text="채팅방을 찾을 수 없습니다.")
                return True
                
            chat_room.persona_id = persona_id
            await session.commit()
            
            await send_telegram_message(
                chat_id=chat_room_id,
                text=f"페르소나가 변경되었습니다!\n이름: {persona.name}"
            )
            return True

    return False
    await ask_question(user_id=user.id, chat_room_id=chat_room.id, question=text)
    return True



