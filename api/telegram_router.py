from fastapi import APIRouter, Request, BackgroundTasks
from telegram import Update, Bot
from core.config import load_config
from core.graph import graph
from langchain_core.messages import HumanMessage, AIMessage
from repository.user_repository import upsert_user
from repository.chat_room_repository import upsert_chat_room, set_chat_room_persona
from repository.persona_repository import get_public_personas, get_persona_by_id

router = APIRouter()

config = load_config()
bot_token = config["telegram"]["bot_token"]
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

async def process_update(update: Update):
    user = update.effective_user
    chat = update.effective_chat
    message = update.message
    text = message.text
    
    if not text:
        return

    # 1. Ensure User exists
    # Email is required, so generate one
    email = f"telegram_{user.id}@telegram.placeholder"
    db_user = await upsert_user(
        email=email,
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # 2. Ensure ChatRoom exists
    db_chat_room = await upsert_chat_room(
        telegram_chat_id=chat.id,
        name=chat.title or user.first_name,
        type=chat.type,
        username=chat.username
    )
    
    # 3. Handle Commands
    if text.startswith("/start"):
        await bot.send_message(chat_id=chat.id, text="Hello! I am your AI assistant. You can set a persona using /persona.")
        return
        
    if text.startswith("/persona"):
        # List personas or set one
        parts = text.split()
        if len(parts) == 1:
            # List public personas
            personas = await get_public_personas()
            if not personas:
                await bot.send_message(chat_id=chat.id, text="No public personas available.")
            else:
                msg = "Available Personas:\n"
                for p in personas:
                    msg += f"- {p.name} (ID: {p.id})\n"
                msg += "\nUse `/persona <id>` to set."
                await bot.send_message(chat_id=chat.id, text=msg)
        else:
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

    # 4. Invoke Graph
    inputs = {
        "messages": [HumanMessage(content=text)],
        "user_id": str(db_user.id),
        "chat_room_id": str(db_chat_room.id),
        "model_name": None 
    }
    
    try:
        result = await graph.ainvoke(inputs)
        response_messages = result["messages"]
        # The last message should be the AI response
        ai_response = response_messages[-1]
        
        if isinstance(ai_response, AIMessage):
             await bot.send_message(chat_id=chat.id, text=ai_response.content)
        else:
             # Fallback if something weird happened
             await bot.send_message(chat_id=chat.id, text="I didn't get a response.")
        
    except Exception as e:
        print(f"Error processing message: {e}")
        await bot.send_message(chat_id=chat.id, text="Sorry, I encountered an error.")
