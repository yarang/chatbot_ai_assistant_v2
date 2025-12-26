---
globs: agent/**/*.py
description: Rules for LangGraph agent nodes and graph design
---

# LangGraph Agent Rules

## Agent Directory Structure
You MUST follow this structure for agent-related code:
```
agent/
├── graph.py              # Graph definition and compilation
├── state.py              # State definition (TypedDict)
└── nodes/                # Agent node implementations
    ├── common_nodes.py   # Shared nodes (retrieve, save, summarize)
    ├── router_node.py    # Supervisor/Router node
    ├── chat_node.py      # General conversation node
    ├── search_node.py    # Research/Search node
    ├── notion_node.py    # Notion integration node
    └── tools_node.py     # Tool execution node
```

## State Management

### State Definition (`agent/state.py`)
- You MUST define state using `TypedDict` from `typing_extensions`.
- You MUST use `Annotated[List[BaseMessage], add_messages]` for message handling.
- You MUST include these minimum fields:
  ```python
  class ChatState(TypedDict):
      messages: Annotated[List[BaseMessage], add_messages]
      user_id: str
      chat_room_id: str
      next: str  # Routing control
  ```
- You MAY add optional fields but MUST mark them as `Optional[Type]`.
- You MUST NOT modify the state schema without updating all dependent nodes.

### State Modification Rules
- Nodes MUST return a dict with only the fields they want to update.
- You MUST NOT mutate the state object directly.
- You MUST use proper reducers (e.g., `add_messages`) for list fields.

## Graph Definition (`agent/graph.py`)

### Graph Construction
- You MUST use `StateGraph` with the defined `ChatState`.
- You MUST compile the graph with `workflow.compile()`.
- You MUST define clear entry point using `START` and exit point using `END`.

### Node Registration
- You MUST register all nodes using `workflow.add_node(name, function)`.
- Node names SHOULD be descriptive (e.g., "Supervisor", "Researcher").
- You MUST NOT duplicate node names.

### Edge Rules
- You MUST use `add_edge()` for deterministic transitions.
- You MUST use `add_conditional_edges()` for dynamic routing.
- Conditional edges MUST provide a mapping for all possible return values.
- You MUST handle the "FINISH" routing case explicitly.

### Routing Logic
- Router functions MUST be pure functions (no side effects).
- Router functions MUST return a string matching one of the defined edge targets.
- You MUST validate router return values match defined edges.

## Node Implementation

### Node Function Signature
- All nodes MUST be async functions: `async def node_name(state: ChatState) -> dict`
- Nodes MUST accept `ChatState` as the only parameter.
- Nodes MUST return a dict with state updates (not the full state).
- You MUST use type hints for all node functions.

### Router/Supervisor Node Rules (`router_node.py`)
- You MUST define available agents/workers as a list.
- You MUST use structured output for routing decisions (Pydantic model).
- You MUST include reasoning in routing decisions for debugging.
- You MUST implement loop detection to prevent infinite cycles:
  - Check for repeated identical AI messages
  - Check for alternating message patterns
  - Force "FINISH" if loop detected
- You MUST implement fail-safe logic:
  - Never select "FINISH" immediately after a user message
  - Fall back to a default agent if routing fails
- You SHOULD include worker descriptions to improve routing accuracy.

### Worker Node Rules
- Worker nodes MUST focus on a single responsibility.
- Worker nodes MUST log their decisions using `core.logger`.
- Worker nodes MUST handle errors gracefully and log them.
- Worker nodes MUST return meaningful responses in `messages`.

### Tool-Calling Nodes
- Nodes that call tools MUST check for `tool_calls` in the last message.
- You MUST route to a dedicated `tools` node for tool execution.
- You MUST NOT execute tools directly in worker nodes.
- Tool results MUST be appended to messages using `ToolMessage`.

### Common Nodes (`common_nodes.py`)
- You MUST implement these standard nodes:
  - `retrieve_data_node`: Load conversation history and context
  - `save_conversation_node`: Persist conversation to database
  - `summarize_conversation_node`: Generate conversation summary
- Common nodes MUST be reusable across different graphs.
- You MUST use repository layer for database operations (no direct DB access).

## LLM Integration

### Model Selection
- You MUST use `core.llm.get_llm()` to obtain LLM instances.
- You MUST respect the `model_name` from state if provided.
- You MUST implement fallback logic if a model is unavailable.

### Hybrid Router Support
- You SHOULD support local LLM routing via environment variables:
  - `USE_LOCAL_ROUTER=true/false`
  - `LOCAL_LLM_BASE_URL`
  - `LOCAL_LLM_MODEL`
- You MUST fall back to Gemini if local routing fails.
- You MUST log which router is being used.

### Structured Output
- You MUST use Pydantic models for structured LLM outputs.
- You MUST validate structured outputs before using them.
- You MUST handle parsing errors gracefully.

## Prompt Engineering

### System Prompts
- You MUST provide clear, specific instructions in system prompts.
- You MUST include current timestamp if time-sensitive operations are involved.
- You SHOULD include worker descriptions in supervisor prompts.
- You MUST use `MessagesPlaceholder` for dynamic message injection.

### Prompt Templates
- You MUST use `ChatPromptTemplate.from_messages()`.
- You MUST use `.partial()` for static variables (e.g., available options).
- You MUST NOT hardcode dynamic values in prompts.

## Message Handling

### Message Types
- You MUST use appropriate LangChain message types:
  - `HumanMessage`: User input
  - `AIMessage`: Assistant responses
  - `SystemMessage`: System/context information
  - `ToolMessage`: Tool execution results
- You MUST include `name` field for multi-user conversations.

### Message Construction
- You MUST build message history from database before processing.
- You MUST include conversation summary if available.
- You MUST limit history to recent messages (e.g., last 10-20).
- You MUST preserve message order (chronological).

## Error Handling

### Exception Management
- You MUST wrap LLM calls in try-except blocks.
- You MUST log all exceptions using `logger.error()`.
- You MUST provide fallback behavior on errors (don't crash the graph).
- You MUST NOT expose internal errors to users.

### Timeout Handling
- You SHOULD set timeouts for external API calls.
- You MUST handle timeout exceptions gracefully.

## Performance Optimization

### Async/Await
- You MUST use `async`/`await` for all I/O operations.
- You MUST NOT use blocking operations in nodes.
- You SHOULD use `asyncio.gather()` for parallel operations when safe.

### Token Management
- You SHOULD track token usage in state (`input_tokens_used`, `output_tokens_used`).
- You SHOULD limit context window size to prevent token overflow.

## Testing and Debugging

### Logging
- You MUST log key decisions (e.g., routing choices, tool calls).
- You SHOULD log state transitions for debugging.
- You MUST use appropriate log levels (INFO, WARNING, ERROR).
- You MUST NOT log sensitive user data.

### Debug Output
- You MAY include temporary `print()` statements for debugging.
- You MUST remove or comment out debug prints before committing.
- You SHOULD use environment variables for debug flags.

## Integration with Other Layers

### Service Layer Integration
- Nodes MAY call service layer functions for complex operations.
- You MUST NOT bypass the service layer to access repositories directly.

### Repository Layer Integration
- You MUST use repository functions for all database operations.
- You MUST pass `AsyncSession` from service layer if needed.
- You MUST NOT create database sessions in node functions.

### Tools Layer Integration
- You MUST import tools from `tools/` directory.
- You MUST bind tools to LLMs using `.bind_tools()`.
- You MUST handle tool execution in a dedicated node.

## Anti-Patterns to Avoid

### DO NOT:
- Create circular dependencies between nodes
- Modify global state within nodes
- Use synchronous blocking calls (use async)
- Hardcode user IDs or chat room IDs
- Skip error handling "because it works locally"
- Create deep nesting in conditional edges (>3 levels)
- Ignore type hints or bypass type checking
- Mix business logic with routing logic
- Store large objects in state (use references/IDs)
- Create nodes that do multiple unrelated things

## Best Practices

### DO:
- Keep nodes focused and single-purpose
- Use descriptive names for nodes and edges
- Document complex routing logic with comments
- Test edge cases (empty messages, missing fields)
- Implement graceful degradation on errors
- Use structured logging with context
- Profile performance for slow nodes
- Version control your graph changes carefully
- Write unit tests for individual nodes
- Use dependency injection for external services
