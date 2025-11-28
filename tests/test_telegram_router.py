import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.telegram_router import process_update
from telegram import Update, User, Chat, Message
from langchain_core.messages import AIMessage

@pytest.mark.asyncio
async def test_process_update_selective_response():
    # Mock dependencies
    with patch("api.telegram_router.bot") as mock_bot, \
         patch("api.telegram_router.upsert_user", new_callable=AsyncMock) as mock_upsert_user, \
         patch("api.telegram_router.upsert_chat_room", new_callable=AsyncMock) as mock_upsert_chat_room, \
         patch("api.telegram_router.graph") as mock_graph, \
         patch("api.telegram_router.settings") as mock_settings, \
         patch("api.telegram_router.BOT_USERNAME", None):
         
        # Setup Bot
        mock_bot_user = MagicMock(spec=User)
        mock_bot_user.username = "test_bot"
        mock_bot.get_me = AsyncMock(return_value=mock_bot_user)
        mock_bot.send_message = AsyncMock()
        
        # Setup Graph
        mock_graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="response")]})
        
        # Setup Settings
        mock_settings.telegram.bot_username = None
        
        # Setup Common Update Objects
        user = MagicMock(spec=User)
        user.id = 123
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"
        
        # Scenario 1: Private Chat (Should always process)
        chat_private = MagicMock(spec=Chat)
        chat_private.type = "private"
        chat_private.id = 1001
        chat_private.title = None
        chat_private.username = None
        
        message_private = MagicMock(spec=Message)
        message_private.text = "hello"
        message_private.reply_to_message = None
        message_private.photo = None
        message_private.entities = None
        
        update_private = MagicMock(spec=Update)
        update_private.effective_user = user
        update_private.effective_chat = chat_private
        update_private.message = message_private
        
        # Reset global BOT_USERNAME in router if needed, but we can't easily access it.
        # However, the first call will set it.
        
        await process_update(update_private)
        assert mock_upsert_user.called
        mock_upsert_user.reset_mock()
        
        # Scenario 2: Group Chat, No Mention (Should ignore)
        chat_group = MagicMock(spec=Chat)
        chat_group.type = "group"
        chat_group.id = 2001
        chat_group.title = "Test Group"
        chat_group.username = None
        
        message_group_ignore = MagicMock(spec=Message)
        message_group_ignore.text = "hello guys"
        message_group_ignore.reply_to_message = None
        message_group_ignore.photo = None
        message_group_ignore.entities = None
        
        update_group_ignore = MagicMock(spec=Update)
        update_group_ignore.effective_user = user
        update_group_ignore.effective_chat = chat_group
        update_group_ignore.message = message_group_ignore
        
        await process_update(update_group_ignore)
        assert not mock_upsert_user.called
        mock_upsert_user.reset_mock()
        
        # Scenario 3: Group Chat, Mention (Should process)
        message_group_mention = MagicMock(spec=Message)
        message_group_mention.text = "hello @test_bot"
        message_group_mention.reply_to_message = None
        message_group_mention.photo = None
        message_group_mention.entities = None
        
        update_group_mention = MagicMock(spec=Update)
        update_group_mention.effective_user = user
        update_group_mention.effective_chat = chat_group
        update_group_mention.message = message_group_mention
        
        await process_update(update_group_mention)
        assert mock_upsert_user.called
        mock_upsert_user.reset_mock()
        
        # Scenario 4: Group Chat, Reply to Bot (Should process)
        message_group_reply = MagicMock(spec=Message)
        message_group_reply.text = "replying to you"
        message_group_reply.photo = None
        message_group_reply.entities = None
        
        reply_to_user = MagicMock()
        reply_to_user.username = "test_bot"
        
        reply_to = MagicMock(spec=Message)
        reply_to.from_user = reply_to_user
        message_group_reply.reply_to_message = reply_to
        
        update_group_reply = MagicMock(spec=Update)
        update_group_reply.effective_user = user
        update_group_reply.effective_chat = chat_group
        update_group_reply.message = message_group_reply
        
        await process_update(update_group_reply)
        assert mock_upsert_user.called
        mock_upsert_user.reset_mock()

        # Scenario 5: Group Chat, Mention via Entity (Should process)
        message_group_entity = MagicMock(spec=Message)
        message_group_entity.text = "hello @test_bot"
        message_group_entity.reply_to_message = None
        message_group_entity.photo = None
        
        entity = MagicMock()
        entity.type = "mention"
        entity.offset = 6
        entity.length = 9
        message_group_entity.entities = [entity]
        
        update_group_entity = MagicMock(spec=Update)
        update_group_entity.effective_user = user
        update_group_entity.effective_chat = chat_group
        update_group_entity.message = message_group_entity
        
        # Ensure BOT_USERNAME is set correctly (it persists from previous calls in this test run)
        # But let's patch settings to verify it picks up from there if not set
        with patch("api.telegram_router.settings") as mock_settings:
            mock_settings.telegram.bot_username = "test_bot"
            # We need to reset BOT_USERNAME global in router to test initialization from settings
            # But it's hard to reset global variable in imported module without reloading.
            # However, since we already set it in previous calls via bot.get_me(), it should match.
            
            await process_update(update_group_entity)
            assert mock_upsert_user.called

    @patch("api.telegram_router.bot")
    async def test_process_update_commands(self, mock_bot):
        # Setup
        mock_bot.send_message = AsyncMock()
        
        user = MagicMock(spec=User)
        user.id = 123
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"
        
        chat = MagicMock(spec=Chat)
        chat.id = 1001
        chat.type = "private"
        chat.title = None
        chat.username = None
        
        # Test /help
        message = MagicMock(spec=Message)
        message.text = "/help"
        message.photo = None
        message.entities = None
        
        update = MagicMock(spec=Update)
        update.effective_user = user
        update.effective_chat = chat
        update.message = message
        
        with patch("api.telegram_router.upsert_user", new_callable=AsyncMock), \
             patch("api.telegram_router.upsert_chat_room", new_callable=AsyncMock):
            await process_update(update)
            
        assert mock_bot.send_message.called
        args, kwargs = mock_bot.send_message.call_args
        assert "commands" in kwargs["text"]

    @patch("api.telegram_router.bot")
    async def test_process_update_photo(self, mock_bot):
        # Setup
        mock_bot.get_file = AsyncMock()
        mock_file = MagicMock()
        mock_file.download_as_bytearray = AsyncMock(return_value=b"fake_image_bytes")
        mock_bot.get_file.return_value = mock_file
        mock_bot.send_message = AsyncMock()
        
        user = MagicMock(spec=User)
        user.id = 123
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"
        
        chat = MagicMock(spec=Chat)
        chat.id = 1001
        chat.type = "private"
        chat.title = None
        chat.username = None
        
        message = MagicMock(spec=Message)
        message.text = None
        message.caption = "Check this photo"
        message.photo = [MagicMock(file_id="file_123")]
        
        update = MagicMock(spec=Update)
        update.effective_user = user
        update.effective_chat = chat
        update.message = message
        
        with patch("api.telegram_router.upsert_user", new_callable=AsyncMock), \
             patch("api.telegram_router.upsert_chat_room", new_callable=AsyncMock), \
             patch("api.telegram_router.graph") as mock_graph:
            
            mock_graph.ainvoke = AsyncMock(return_value={"messages": [AIMessage(content="Nice photo!")]})
            
            await process_update(update)
            
            assert mock_bot.get_file.called
            assert mock_file.download_as_bytearray.called
            assert mock_graph.ainvoke.called
            
            # Verify input to graph contains image
            args, kwargs = mock_graph.ainvoke.call_args
            inputs = args[0]
            messages = inputs["messages"]
            assert isinstance(messages[0].content, list)
            assert messages[0].content[1]["type"] == "image_url"
            assert "data:image/jpeg;base64" in messages[0].content[1]["image_url"]["url"]
@pytest.mark.asyncio
async def test_group_chat_case_insensitive_mentions():
    """
    Test that bot responds to mentions and replies in group chats 
    even if the casing of the username doesn't match exactly.
    """
    # Mock dependencies
    with patch("api.telegram_router.bot") as mock_bot, \
         patch("api.telegram_router.upsert_user", new_callable=AsyncMock) as mock_upsert_user, \
         patch("api.telegram_router.upsert_chat_room", new_callable=AsyncMock) as mock_upsert_chat_room, \
         patch("api.telegram_router.graph") as mock_graph, \
         patch("api.telegram_router.settings") as mock_settings, \
         patch("api.telegram_router.BOT_USERNAME", None):
         
        # Setup Bot Username with mixed case
        mock_settings.telegram.bot_username = "MyBot"
        
        # Setup Common Update Objects
        user = MagicMock(spec=User)
        user.id = 123
        user.username = "test_user"
        user.first_name = "Test"
        user.last_name = "User"
        
        chat_group = MagicMock(spec=Chat)
        chat_group.type = "group"
        chat_group.id = 2001
        chat_group.title = "Test Group"
        chat_group.username = None

        # Scenario 1: Reply to Bot with casing mismatch
        # User replies to a message from "mybot" (lowercase), but bot is "MyBot"
        message_reply = MagicMock(spec=Message)
        message_reply.text = "replying to you"
        message_reply.photo = None
        message_reply.entities = None
        
        reply_to_user = MagicMock()
        reply_to_user.username = "mybot" # Lowercase from Telegram
        
        reply_to = MagicMock(spec=Message)
        reply_to.from_user = reply_to_user
        message_reply.reply_to_message = reply_to
        
        update_reply = MagicMock(spec=Update)
        update_reply.effective_user = user
        update_reply.effective_chat = chat_group
        update_reply.message = message_reply
        
        await process_update(update_reply)
        
        assert mock_upsert_user.called, "Reply with casing mismatch was ignored"
        mock_upsert_user.reset_mock()
        
        # Scenario 2: Text Mention with casing mismatch
        message_entity = MagicMock(spec=Message)
        message_entity.text = "hey bot"
        message_entity.reply_to_message = None
        message_entity.photo = None
        
        entity_user = MagicMock()
        entity_user.username = "mybot" # Lowercase
        
        entity = MagicMock()
        entity.type = "text_mention"
        entity.user = entity_user
        
        message_entity.entities = [entity]
        
        update_entity = MagicMock(spec=Update)
        update_entity.effective_user = user
        update_entity.effective_chat = chat_group
        update_entity.message = message_entity
        
        await process_update(update_entity)
        
        assert mock_upsert_user.called, "Text Mention with casing mismatch was ignored"
