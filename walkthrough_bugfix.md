# Bug Fix: Async Mode Error & Rate Limit Investigation

## 1. Async Mode Error Fix
**Issue**: The application was crashing with `Error indexing conversation: This method must be called with async_mode`. This was caused by `GoogleGenerativeAIEmbeddings` failing when called asynchronously via `vector_store.aadd_documents`.

**Fix**: Modified `core/graph.py` to run the synchronous `vector_store.add_documents` method in a separate thread using `asyncio.to_thread`. This bypasses the problematic async implementation of the embeddings client.

**File Changed**: `core/graph.py`

```python
# Before
await vector_store.aadd_documents([user_doc, ai_doc])

# After
import asyncio
await asyncio.to_thread(vector_store.add_documents, [user_doc, ai_doc])
```

**Test Update**: Updated `tests/test_memory.py` to mock `add_documents` instead of `aadd_documents` to reflect this change.

## 2. Rate Limit (ResourceExhausted)
**Issue**: The user reported `ResourceExhausted: 429` errors.
**Cause**: The application is hitting the Google Gemini API Free Tier limit (2 requests per minute). The LangGraph workflow (Supervisor -> Researcher -> etc.) makes multiple LLM calls per user request, quickly exhausting the quota.
**Mitigation**: The library `langchain_google_genai` automatically retries with exponential backoff (as seen in the logs: "Retrying ... in 32.0 seconds").
**Recommendation**:
- For development/testing: Be patient with the retries or run fewer tests at a time.
- For production: Upgrade to a paid plan to increase the quota.

## 3. Verification
- `tests/reproduce_issue.py`: **PASSED**. The "bug" mentioned in the file comments (result being a string representation of a list) is NOT reproducing. The function `extract_text_from_stream_event` works correctly.
- `tests/test_memory.py`: **PASSED**. Validated the fix for the vector store interaction.
