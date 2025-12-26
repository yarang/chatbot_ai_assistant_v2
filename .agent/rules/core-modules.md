---
globs: core/*.py
description: Rules for core modules (database, logger, middleware, exceptions, config, llm, vector_store)
---

# Core Module Rules

## Overview
The `core/` module contains foundational infrastructure that ALL other layers depend on. Core modules MUST be self-contained and MUST NOT import from application layers (api, services, repository, agent, tools).

## Database (`core/database.py`)
- You MUST use `sqlalchemy.ext.asyncio` for async database operations.
- You MUST use `AsyncSession` for all database interactions.
- You MUST provide `get_session()` function/dependency for session management.
- `DATABASE_URL` MUST be loaded from `core/config.py` (via `pydantic-settings`).
- You MUST implement connection pooling with appropriate limits.
- You SHOULD provide `init_db()` function for schema initialization.

**Required Exports**:
```python
# core/database.py
async_engine: AsyncEngine
AsyncSessionLocal: sessionmaker
async def get_session() -> AsyncSession
async def init_db() -> None
```

## Configuration (`core/config.py`)
- You MUST use `pydantic-settings` for configuration management.
- You MUST define a `Settings` class inheriting from `BaseSettings`.
- You MUST use type hints for all configuration fields.
- You MUST provide nested config classes for grouped settings (e.g., `GeminiSettings`, `DatabaseSettings`).
- You MUST load from `.env` file using `SettingsConfigDict`.
- You MUST provide a `get_settings()` function (singleton or dependency).
- You MUST validate required fields at startup.

**Example Structure**:
```python
class GeminiSettings(BaseModel):
    api_key: str
    model_name: str = "gemini-2.0-flash-exp"
    temperature: float = 0.7

class Settings(BaseSettings):
    gemini: GeminiSettings
    database_url: str
    tavily_api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__"
    )
```

## Logger (`core/logger.py`)
- You MUST use Python's standard `logging` module.
- You MUST provide a `get_logger(name: str)` factory function.
- You MUST configure log level from environment variable.
- You MUST format logs with timestamp, level, module name, and message.
- You SHOULD support both file and console logging.
- You MUST NOT log sensitive information (passwords, API keys, PII).

**Required Interface**:
```python
# core/logger.py
def get_logger(name: str) -> logging.Logger
def setup_logging(level: str = "INFO") -> None
```

## Middleware (`core/middleware.py`)
- You MUST implement request/response logging middleware.
- You MUST log processing time for all requests.
- You MUST include request ID for traceability.
- You MUST NOT log sensitive information (auth headers, request bodies with secrets).
- You SHOULD implement error tracking middleware.

**Example**:
```python
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time
        logger.info(
            f"request_id={request_id} "
            f"path={request.url.path} "
            f"method={request.method} "
            f"status={response.status_code} "
            f"duration={process_time:.3f}s"
        )
        return response
```

## Exception Handling (`core/exceptions.py`)
- You MUST define a base `AppException` class with status code support.
- You MUST inherit all custom exceptions from `AppException`.
- You MUST provide a `generic_exception_handler` for unexpected errors (500).
- You MUST provide an `app_exception_handler` for business errors (4xx).
- You MUST log all exceptions with appropriate context.
- You MUST NOT expose internal error details to end users.

**Required Classes**:
```python
class AppException(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

# Common exceptions
class NotFoundError(AppException):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} {id} not found", 404)

class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, 400)

class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)
```

## LLM Integration (`core/llm.py`)
- You MUST provide a factory function `get_llm(model_name: Optional[str])`.
- You MUST load API keys from `core/config.py`.
- You MUST support multiple LLM providers if needed (Gemini, Ollama, etc.).
- You SHOULD implement health check function for LLM availability.
- You MUST handle LLM initialization errors gracefully.
- You MUST log which model is being initialized.

**Required Interface**:
```python
# core/llm.py
def get_llm(model_name: Optional[str] = None) -> BaseChatModel
async def check_llm_health() -> bool
```

**Example**:
```python
from langchain_google_genai import ChatGoogleGenerativeAI

def get_llm(model_name: Optional[str] = None):
    settings = get_settings()
    if model_name is None:
        model_name = settings.gemini.model_name

    logger.info(f"Initializing LLM: {model_name}")
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=settings.gemini.api_key,
        temperature=settings.gemini.temperature
    )
```

## Vector Store (`core/vector_store.py`)
- You MUST provide functions for vector store initialization and access.
- You MUST support PGVector extension for PostgreSQL.
- You MUST use embeddings from LangChain providers.
- You MUST provide functions for document ingestion and retrieval.
- You SHOULD support metadata filtering for chat-room-specific knowledge.

**Required Interface**:
```python
# core/vector_store.py
def get_vector_store() -> VectorStore
async def ingest_documents(
    documents: List[Document],
    metadata: dict
) -> None
async def search_documents(
    query: str,
    filter: Optional[dict] = None,
    k: int = 5
) -> List[Document]
```

**Example**:
```python
from langchain_postgres import PGVector
from langchain_google_genai import GoogleGenerativeAIEmbeddings

def get_vector_store():
    settings = get_settings()
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=settings.gemini.api_key
    )

    return PGVector(
        connection_string=settings.database_url,
        embedding_function=embeddings,
        collection_name="documents"
    )
```

## Graph Management (`core/graph.py`) [OPTIONAL]
If you centralize LangGraph compilation:
- You MAY provide a function to get the compiled graph.
- You MUST ensure graph is compiled only once (singleton pattern).
- You SHOULD support graph reloading for development.

**Example**:
```python
# core/graph.py
from agent.graph import workflow

_compiled_graph = None

def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = workflow.compile()
    return _compiled_graph
```

## Dependency Injection Pattern
- Core modules SHOULD provide factory functions, not singletons.
- You SHOULD use FastAPI's `Depends()` for injection in API routes.
- You MAY implement singleton pattern for expensive resources (LLM, DB engine).

**Example**:
```python
# In API route
@router.get("/users")
async def get_users(
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings)
):
    # Use injected dependencies
    pass
```

## Testing Core Modules
- You MUST write unit tests for all core utilities.
- You MUST mock external dependencies (database, API calls).
- You SHOULD test error handling paths.
- You MUST test configuration loading with various scenarios.

## Module Initialization Order
When starting the application (in `main.py`):
1. Load configuration (`get_settings()`)
2. Setup logging (`setup_logging()`)
3. Initialize database (`init_db()`)
4. Register exception handlers
5. Add middleware
6. Include routers

## Anti-Patterns to Avoid
- DO NOT import from application layers (api, services, repository, agent, tools)
- DO NOT implement business logic in core modules
- DO NOT hardcode configuration values
- DO NOT create circular dependencies within core
- DO NOT expose internal implementation details
- DO NOT skip error handling in core utilities

## Best Practices
- Keep core modules simple and focused
- Document all public APIs with docstrings
- Use type hints consistently
- Implement proper error handling
- Log initialization and errors
- Provide sensible defaults for optional config
- Make core modules easily testable
- Version control breaking changes carefully