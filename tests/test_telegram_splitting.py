import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.telegram_router import process_update

@pytest.mark.asyncio
async def test_telegram_message_splitting():
    """
    Test that long messages are split into multiple Telegram messages.
    We will mock the bot and the stream to simulate a long response.
    """
    # Mock dependencies
    mock_update = MagicMock()
    mock_update.effective_user.id = 123
    mock_update.effective_chat.id = 456
    mock_update.effective_chat.type = "private"
    mock_update.message.text = "Tell me a long story"
    mock_update.message.photo = None
    
    mock_bot = AsyncMock()
    # Mock send_message to return a mock message object
    def create_mock_msg(chat_id, text):
        msg = MagicMock()
        msg.message_id = len(mock_bot.sent_messages_log) + 1
        mock_bot.sent_messages_log.append(msg)
        return msg
    
    mock_bot.sent_messages_log = []
    mock_bot.send_message.side_effect = create_mock_msg
    
    # Mock settings
    with patch("api.telegram_router.bot", mock_bot), \
         patch("api.telegram_router.upsert_user") as mock_upsert_user, \
         patch("api.telegram_router.upsert_chat_room") as mock_upsert_chat_room, \
         patch("services.conversation_service.ask_question_stream") as mock_stream:
        
        # Setup mocks
        mock_upsert_user.return_value.id = "user_123"
        mock_upsert_chat_room.return_value.id = "room_456"
        
        # Simulate a stream that yields chunks accumulating to > 4000 chars
        # We'll use a smaller limit in the code for testing if possible, 
        # but since we can't easily change the constant inside the function without more mocking,
        # we will generate enough data.
        # MESSAGE_LIMIT is 4000.
        
        async def stream_generator(*args, **kwargs):
            # Yield 3 chunks of 2000 chars each -> 6000 chars total
            # This should result in 2 messages (4000 + 2000)
            chunk1 = "a" * 2000
            yield chunk1
            
            chunk2 = "b" * 2000 # Total 4000
            yield chunk2
            
            chunk3 = "c" * 2000 # Total 6000
            yield chunk3
            
        mock_stream.side_effect = stream_generator
        
        # Run the function
        await process_update(mock_update)
        
        # Verification
        # 1. Check that send_message was called multiple times
        # Initial "..." + at least one more for the split
        assert mock_bot.send_message.call_count >= 2
        
        # 2. Check edit_message_text calls
        # We expect edits to happen.
        assert mock_bot.edit_message_text.called
        
        # Check the final state of edits
        # The first message should have been edited to have 4000 chars eventually
        # The second message should have the rest
        
        # Get all calls to edit_message_text
        edit_calls = mock_bot.edit_message_text.call_args_list
        
        # Find the last edit for the first message
        first_msg_id = mock_bot.sent_messages_log[0].message_id
        edits_to_first = [call for call in edit_calls if call.kwargs['message_id'] == first_msg_id]
        last_edit_to_first = edits_to_first[-1]
        
        # The text in the last edit to the first message should be 4000 chars (chunk1 + chunk2)
        # Wait, chunk1 is 2000 'a'. chunk2 is 2000 'b'. Total 4000.
        # So first message should be "a"*2000 + "b"*2000
        assert len(last_edit_to_first.kwargs['text']) == 4000
        assert last_edit_to_first.kwargs['text'].startswith("aaaa")
        assert last_edit_to_first.kwargs['text'].endswith("bbbb")
        
        # Find the last edit for the second message
        second_msg_id = mock_bot.sent_messages_log[1].message_id
        edits_to_second = [call for call in edit_calls if call.kwargs['message_id'] == second_msg_id]
        last_edit_to_second = edits_to_second[-1]
        
        # The text in the last edit to the second message should be 2000 chars ("c"*2000)
        assert len(last_edit_to_second.kwargs['text']) == 2000
        assert last_edit_to_second.kwargs['text'].startswith("cccc")
