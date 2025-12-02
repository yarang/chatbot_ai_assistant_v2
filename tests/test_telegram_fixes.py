import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.telegram_router import process_update
from telegram import Update, User, Chat, Message

@pytest.mark.asyncio
async def test_process_update_streaming_redundant_edits():
    # Mock dependencies
    with patch("api.telegram_router.bot") as mock_bot, \
         patch("api.telegram_router.upsert_user", new_callable=AsyncMock), \
         patch("api.telegram_router.upsert_chat_room", new_callable=AsyncMock), \
         patch("api.telegram_router.graph") as mock_graph, \
         patch("api.telegram_router.settings") as mock_settings, \
         patch("api.telegram_router.settings") as mock_settings, \
         patch("services.conversation_service.ask_question_stream") as mock_ask_stream, \
         patch("time.time") as mock_time:
         
        # Setup Bot
        mock_bot.send_message = AsyncMock()
        mock_bot.edit_message_text = AsyncMock()
        
        # Setup initial message return
        sent_msg = MagicMock(spec=Message)
        sent_msg.message_id = 999
        mock_bot.send_message.return_value = sent_msg
        
        # Setup Update
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
        message.text = "hello"
        message.photo = None
        
        update = MagicMock(spec=Update)
        update.effective_user = user
        update.effective_chat = chat
        update.message = message
        
        # Mock stream to yield chunks that result in same text
        # 1. "Hello" -> New text "Hello..."
        # 2. "Hello" (snapshot) -> Same text "Hello..." -> Should NOT edit
        # 3. " World" (delta) -> New text "Hello World..." -> Should edit
        
        # Mock time to advance
        mock_time.side_effect = [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009]
        
        async def mock_stream_gen(*args, **kwargs):
            print("Mock stream yielding Hello")
            yield "Hello"
            print("Mock stream yielding Hello (snapshot)")
            yield "Hello" 
            print("Mock stream yielding World")
            yield " World"
            
        mock_ask_stream.side_effect = mock_stream_gen
        
        # Run
        print("Calling process_update")
        await process_update(update)
        print("Finished process_update")
        
        # Verify
        print(f"ask_stream called: {mock_ask_stream.called}")
        # send_message called once for "..."
        assert mock_bot.send_message.call_count >= 1
        
        # edit_message_text calls:
        # 1. "Hello..."
        # 2. "Hello World..."
        # 3. "Hello World" (Final)
        # Total 3 calls. 
        # Without fix, it would be 4 calls (extra one for the second "Hello")
        
        # Let's check the calls
        edits = mock_bot.edit_message_text.call_args_list
        texts = [call.kwargs['text'] for call in edits]
        
        print(f"Edit texts: {texts}")
        
        # Filter out "..." if any (though logic appends ...)
        # We expect: "Hello...", "Hello World...", "Hello World"
        
        assert "Hello..." in texts
        assert "Hello World..." in texts
        assert "Hello World" in texts
        
        # Check for duplicates
        # If fix works, "Hello..." should appear only once (or maybe twice if timing allows, but with our mock it's sequential)
        # Actually, the loop logic:
        # Chunk 1: "Hello" -> full="Hello". Edit "Hello..."
        # Chunk 2: "Hello" -> full="Hello". New text "Hello...". Same as last sent. NO EDIT.
        # Chunk 3: " World" -> full="Hello World". Edit "Hello World..."
        # Final: Edit "Hello World"
        
        # So we expect exactly 3 edits.
        assert len(edits) == 3
        assert texts[0] == "Hello..."
        assert texts[1] == "Hello World..."
        assert texts[2] == "Hello World"
