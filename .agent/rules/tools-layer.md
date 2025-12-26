---
globs: tools/*.py
description: Rules for LangChain/LangGraph tools and external integrations
---

# Tools Layer Rules

## Tools Directory Structure
You MUST follow this structure for tool-related code:
```
tools/
├── __init__.py           # Tool exports and registry
├── search_tool.py        # Web search integration (Tavily)
├── retrieval_tool.py     # RAG/Vector DB retrieval
├── memory_tool.py        # Long-term memory access
├── time_tool.py          # Time/date utilities
└── {domain}_tool.py      # Domain-specific tools
```

## Tool Design Principles

### Single Responsibility
- Each tool file MUST focus on ONE external integration or capability.
- You MUST NOT combine unrelated tools in a single file.
- Tool functions MUST be focused and do one thing well.

### Naming Conventions
- Tool files MUST be named `{functionality}_tool.py`.
- Tool factory functions MUST be named `get_{name}_tool()`.
- Tool classes SHOULD be named `{Name}Tool` if implementing custom tools.

## Tool Implementation

### Factory Pattern
- You MUST provide a factory function that returns a configured tool instance.
- Factory functions MUST handle configuration loading from `core.config`.
- Factory functions MUST validate required environment variables/settings.
- You MUST provide meaningful error messages if configuration is missing.

Example:
```python
from langchain_core.tools import Tool
from core.config import get_settings

def get_search_tool():
    """Returns a configured Tavily search tool."""
    settings = get_settings()
    api_key = settings.tavily_api_key

    if not api_key:
        raise ValueError("TAVILY_API_KEY not configured")

    return TavilySearch(
        max_results=3,
        tavily_api_key=api_key
    )
```

### Tool Metadata
- You MUST provide a clear `name` for each tool (kebab-case).
- You MUST provide a descriptive `description` explaining what the tool does.
- Descriptions MUST be detailed enough for the LLM to understand when to use the tool.
- You SHOULD include parameter descriptions in the tool schema.

### Tool Parameters
- Tool functions MUST use type-annotated parameters.
- You SHOULD use Pydantic models for complex input schemas.
- You MUST validate inputs within the tool function.
- You MUST provide default values for optional parameters.

## External API Integration

### API Key Management
- You MUST load API keys from `core.config.get_settings()`.
- You MUST NOT hardcode API keys in tool files.
- You MUST provide fallback to environment variables if config fails.
- You SHOULD log warnings if API keys are missing (but don't log the keys).

### Error Handling
- You MUST wrap external API calls in try-except blocks.
- You MUST handle common errors (timeout, rate limit, auth failure).
- You MUST return user-friendly error messages, not raw exceptions.
- You MUST log errors using `core.logger` with appropriate context.

Example:
```python
from core.logger import get_logger

logger = get_logger(__name__)

async def search_web(query: str) -> str:
    try:
        result = await external_api.search(query)
        return result
    except TimeoutError:
        logger.error(f"Search timeout for query: {query}")
        return "Search timed out. Please try again."
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return "Search failed due to an error."
```

### Timeout Configuration
- You SHOULD set reasonable timeouts for all external API calls.
- You MUST make timeouts configurable via settings when possible.
- Default timeouts SHOULD be between 10-30 seconds depending on the operation.

### Rate Limiting
- You SHOULD implement rate limiting for frequently called APIs.
- You MUST respect API provider rate limits.
- You SHOULD implement exponential backoff for retries.

## Tool Types

### Search Tools (`search_tool.py`)
- You MUST use the Tavily Search API for web searches.
- You MUST limit search results to a reasonable number (3-5).
- You SHOULD filter or summarize results if they're too verbose.
- You MUST include source URLs in search results.

### Retrieval Tools (`retrieval_tool.py`)
- You MUST use `core.vector_store` for RAG operations.
- You MUST filter results by `chat_room_id` for chat-specific knowledge.
- You MUST use `as_retriever()` pattern for LangChain integration.
- You SHOULD implement hybrid search (vector + keyword) if available.
- You MUST handle empty results gracefully.

Example:
```python
from core.vector_store import get_vector_store

def get_retrieval_tool(chat_room_id: str):
    """Returns a retrieval tool scoped to a specific chat room."""
    vector_store = get_vector_store()

    retriever = vector_store.as_retriever(
        search_kwargs={
            "filter": {"chat_room_id": str(chat_room_id)},
            "k": 5
        }
    )

    return retriever
```

### Memory Tools (`memory_tool.py`)
- You MUST access conversation history via `repository.conversation_repository`.
- You MUST NOT implement database access directly in tools.
- You SHOULD provide tools for:
  - Retrieving past conversation summaries
  - Searching conversation history
  - Retrieving user preferences/context

### Utility Tools (`time_tool.py`, etc.)
- You MUST implement pure utility functions as simple tools.
- You SHOULD use the `@tool` decorator for simple functions.
- You MUST NOT add unnecessary complexity to utility tools.

Example:
```python
from langchain_core.tools import tool
from datetime import datetime

@tool
def get_current_time() -> str:
    """Returns the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

## Tool Registration and Export

### Tool Registry (`__init__.py`)
- You SHOULD maintain a central registry of available tools.
- You MUST export tool factory functions from `__init__.py`.
- You MAY provide a `get_all_tools()` function for bulk tool loading.

Example:
```python
# tools/__init__.py
from tools.search_tool import get_search_tool
from tools.retrieval_tool import get_retrieval_tool
from tools.time_tool import get_current_time

def get_all_tools(chat_room_id: str = None):
    """Returns all available tools."""
    tools = [
        get_search_tool(),
        get_current_time,
    ]

    if chat_room_id:
        tools.append(get_retrieval_tool(chat_room_id))

    return tools
```

### Dynamic Tool Loading
- You MAY implement dynamic tool loading based on persona or context.
- You MUST validate tool availability before binding to LLM.
- You SHOULD log which tools are being loaded.

## Tool Execution in Agents

### Binding Tools to LLM
- You MUST use `.bind_tools(tools)` to attach tools to LLM instances.
- You MUST NOT manually construct tool call schemas (let LangChain handle it).

### Tool Call Detection
- You MUST check for `message.tool_calls` to detect when tools are invoked.
- You MUST route to a dedicated `tools_node` for execution.

### Tool Execution Node
- You MUST implement tool execution in `agent/nodes/tools_node.py`.
- You MUST use `ToolMessage` to wrap tool results.
- You MUST handle tool execution errors and return error messages.
- You MUST preserve the original `tool_call_id` in `ToolMessage`.

Example:
```python
from langchain_core.messages import ToolMessage

async def tools_node(state: ChatState):
    """Executes tools requested by the LLM."""
    messages = state["messages"]
    last_message = messages[-1]

    tool_calls = last_message.tool_calls
    tool_messages = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        tool_id = tool_call["id"]

        try:
            # Execute the tool
            result = await execute_tool(tool_name, tool_input)
            tool_messages.append(
                ToolMessage(
                    content=str(result),
                    tool_call_id=tool_id
                )
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            tool_messages.append(
                ToolMessage(
                    content=f"Error: {str(e)}",
                    tool_call_id=tool_id
                )
            )

    return {"messages": tool_messages}
```

## Testing Tools

### Unit Tests
- You MUST write unit tests for all custom tools.
- You MUST mock external API calls in tests.
- You MUST test error handling paths.
- You SHOULD test with invalid inputs.

### Integration Tests
- You SHOULD write integration tests with real APIs in a test environment.
- You MUST use test API keys, not production keys.
- You SHOULD skip integration tests if API keys are not available.

## Performance Considerations

### Caching
- You SHOULD cache expensive tool results when appropriate.
- You MUST implement cache invalidation logic.
- You SHOULD use TTL-based caching for time-sensitive data.

### Async Operations
- You MUST implement tools as async functions when they perform I/O.
- You MUST use `await` for all async operations.
- You SHOULD use `asyncio.gather()` for parallel tool calls if safe.

### Resource Cleanup
- You MUST close connections/sessions properly.
- You SHOULD use context managers (`async with`) for resource management.

## Security Considerations

### Input Validation
- You MUST validate and sanitize all tool inputs.
- You MUST prevent injection attacks (SQL, command, etc.).
- You MUST limit input size to prevent DoS.

### Output Sanitization
- You MUST sanitize tool outputs before returning to LLM.
- You MUST NOT expose internal system paths or secrets.
- You SHOULD truncate excessively long outputs.

### API Security
- You MUST use HTTPS for all external API calls.
- You MUST NOT log sensitive data (API keys, user PII).
- You SHOULD implement request signing if required by the API.

## Anti-Patterns to Avoid

### DO NOT:
- Implement business logic in tools (delegate to services)
- Create tools that modify global state
- Use synchronous blocking calls in async tools
- Hardcode configuration values
- Ignore errors or exceptions
- Return raw exception messages to users
- Create overly complex tools (split them up)
- Bypass the factory pattern
- Access database directly (use repositories)
- Implement authentication logic in tools

## Best Practices

### DO:
- Keep tools simple and focused
- Provide clear, detailed descriptions
- Handle errors gracefully
- Log tool usage for debugging
- Use type hints consistently
- Implement timeouts for all I/O
- Cache results when appropriate
- Write comprehensive tests
- Document complex tool behavior
- Version your tool schemas
- Monitor tool performance and usage
- Implement proper retry logic
- Use configuration for all external dependencies
