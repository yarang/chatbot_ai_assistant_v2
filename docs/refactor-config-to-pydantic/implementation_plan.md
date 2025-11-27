# Streaming Response Implementation Plan

## Goal
Implement streaming responses to improve user experience by showing LLM output progressively instead of waiting for the complete response. This provides immediate feedback and makes the bot feel more responsive.

## User Review Required
> [!IMPORTANT]
> **Telegram API Rate Limits**: Telegram allows editing messages but has rate limits (~30 edits/second per chat). We'll implement a buffer strategy to avoid hitting these limits.

## Proposed Changes

### Core Logic

#### [MODIFY] [conversation_service.py](file:///Users/yarang/workspaces/privates/chatbot_ai_assistant_v2/services/conversation_service.py)
- **Add `ask_question_stream` function**: New async generator that yields chunks of the response
- Uses `graph.astream()` instead of `graph.ainvoke()`
- Yields intermediate state updates as they arrive from LangGraph
- Extracts text from streaming messages (handles both AIMessage content and tool outputs)

#### [MODIFY] [telegram_router.py](file:///Users/yarang/workspaces/privates/chatbot_ai_assistant_v2/api/telegram_router.py)
- **Update `process_update` function**: Replace direct graph invocation with streaming logic
- Send initial "typing" indicator or placeholder message
- Stream response chunks and update message using `bot.edit_message_text()`
- Implement buffer strategy:
  - Buffer chunks for ~500ms or until 50 characters accumulated
  - This reduces edit calls while still feeling responsive
- Handle final message (save to DB, remove "..." indicator)

---

### Helper Functions

#### [NEW] [services/streaming_helper.py](file:///Users/yarang/workspaces/privates/chatbot_ai_assistant_v2/services/streaming_helper.py)
- `StreamBuffer` class: Accumulates text chunks and decides when to flush
- `extract_text_from_stream_event`: Parses LangGraph stream events to extract displayable text

---

### Error Handling
- If streaming fails mid-way, send error message
- Fallback to non-streaming if Telegram edit fails repeatedly
- Log streaming errors for debugging

## Verification Plan

### Automated Tests
- Create `tests/test_streaming.py`:
  - Test `ask_question_stream` yields chunks correctly
  - Test `StreamBuffer` accumulates and flushes at right thresholds
  - Mock Telegram API to verify edit_message calls

### Manual Verification
- Test with PostgreSQL running
- Send message to Telegram bot
- Observe:
  1. Initial message appears quickly (with "...")
  2. Message updates as LLM generates response
  3. Final message is complete and saved to chat history
  4. Check Telegram doesn't rate limit (watch for errors)
