---
alwaysApply: true
description: Modularization and software design best practices
---

# Module Design and Modularization Rules

## Core Design Principles

### SOLID Principles
You MUST follow SOLID principles in all code:

**S - Single Responsibility Principle**
- Each module/class/function MUST have ONE clear responsibility.
- If you can describe a module's purpose with "and", it's doing too much.
- Split modules when they exceed ~300 lines or handle multiple concerns.

**O - Open/Closed Principle**
- Modules MUST be open for extension but closed for modification.
- Use dependency injection, interfaces, and plugins for extensibility.
- You MUST NOT modify core modules to add new features; extend them instead.

**L - Liskov Substitution Principle**
- Subclasses MUST be substitutable for their base classes.
- You MUST NOT break base class contracts in derived classes.

**I - Interface Segregation Principle**
- Clients MUST NOT depend on interfaces they don't use.
- Create focused, specific interfaces rather than large general ones.

**D - Dependency Inversion Principle**
- High-level modules MUST NOT depend on low-level modules.
- Both MUST depend on abstractions (interfaces, protocols).
- Use dependency injection throughout the application.

### DRY (Don't Repeat Yourself)
- You MUST extract repeated code into reusable functions/classes.
- You MUST use inheritance or composition to avoid code duplication.
- You MUST NOT copy-paste code; refactor instead.
- Exceptions: You MAY duplicate code if it serves different business purposes.

### KISS (Keep It Simple, Stupid)
- You MUST choose the simplest solution that works.
- You MUST NOT over-engineer for hypothetical future requirements.
- You MUST avoid unnecessary abstractions.
- Complexity MUST be justified by actual requirements.

### YAGNI (You Aren't Gonna Need It)
- You MUST NOT implement features before they're needed.
- You MUST NOT add "just in case" abstractions.
- You MUST focus on current requirements, not speculation.

## Module Cohesion and Coupling

### High Cohesion
- Module elements MUST be closely related and work toward a single purpose.
- Functions in a module SHOULD operate on the same data structures.
- You SHOULD be able to describe module purpose in one sentence.

**Good Example:**
```python
# user_repository.py - High cohesion
class UserRepository:
    async def create_user(self, ...): pass
    async def get_user_by_id(self, ...): pass
    async def update_user(self, ...): pass
    async def delete_user(self, ...): pass
```

**Bad Example:**
```python
# utils.py - Low cohesion (grab bag)
def hash_password(...): pass
def send_email(...): pass
def calculate_distance(...): pass
def format_date(...): pass
```

### Low Coupling
- Modules MUST have minimal dependencies on other modules.
- You MUST depend on abstractions, not concrete implementations.
- You SHOULD use dependency injection to reduce coupling.
- Changes in one module SHOULD NOT require changes in many others.

**Good Example:**
```python
# Depends on abstraction
class ConversationService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

# Can swap implementations
service = ConversationService(PostgresUserRepository())
service = ConversationService(MockUserRepository())
```

**Bad Example:**
```python
# Tightly coupled to concrete implementation
class ConversationService:
    def __init__(self):
        from repository.user_repository import UserRepository
        self.repository = UserRepository()  # Hardcoded dependency
```

## Module Organization

### Module Size
- Modules SHOULD be 100-500 lines (excluding tests and docs).
- Modules exceeding 500 lines MUST be refactored into smaller modules.
- You MUST split large modules by responsibility or domain.

### Module Naming
- Module names MUST be lowercase with underscores: `user_repository.py`.
- Module names MUST clearly indicate their purpose.
- You MUST avoid generic names like `utils.py`, `helpers.py`, `common.py`.
- Prefer specific names: `date_utils.py`, `string_helpers.py`, `auth_validators.py`.

### Package Structure
- You MUST group related modules into packages (directories with `__init__.py`).
- Packages MUST represent bounded contexts or layers.
- You MUST use `__init__.py` to define package public API.

Example:
```python
# repository/__init__.py
from repository.user_repository import UserRepository
from repository.conversation_repository import ConversationRepository

__all__ = ["UserRepository", "ConversationRepository"]
```

## Dependency Management

### Dependency Injection
- You MUST use dependency injection for all external dependencies.
- You MUST inject dependencies via constructor or function parameters.
- You MUST NOT use global state or singletons for dependencies.

**Good Example:**
```python
class ConversationService:
    def __init__(
        self,
        user_repo: UserRepository,
        llm_client: LLMClient,
        logger: Logger
    ):
        self.user_repo = user_repo
        self.llm_client = llm_client
        self.logger = logger
```

### Dependency Direction
- Dependencies MUST flow in ONE direction: top to bottom.
- Higher-level layers CAN depend on lower-level layers.
- Lower-level layers MUST NOT depend on higher-level layers.

```
api -> services -> repository -> models
 ↓       ↓           ↓           ↓
NO  ← NO       ← NO         ← NO
```

### Circular Dependencies
- You MUST NOT create circular dependencies.
- If circular dependency is detected, refactor to extract common interface.
- Use forward references (TYPE_CHECKING) only for type hints, not runtime.

**Fixing Circular Dependencies:**
```python
# Before: Circular dependency
# user_service.py imports conversation_service.py
# conversation_service.py imports user_service.py

# After: Extract shared interface or use events
# user_service.py
from domain.events import UserCreatedEvent

class UserService:
    def create_user(self):
        # ...
        self.event_bus.publish(UserCreatedEvent(...))

# conversation_service.py listens to events
class ConversationService:
    def on_user_created(self, event: UserCreatedEvent):
        # Handle event
```

## Interface Design

### Function Signatures
- Functions MUST have clear, descriptive names (verb-noun format).
- Functions SHOULD have 0-5 parameters; more indicates poor design.
- You MUST use Pydantic models for complex parameter groups.
- You MUST use type hints for ALL parameters and return values.

**Good Example:**
```python
async def create_conversation(
    user_id: UUID,
    chat_room_id: UUID,
    message: str,
    persona_id: Optional[UUID] = None
) -> Conversation:
    pass
```

**Bad Example:**
```python
# Too many parameters, unclear purpose
async def process(a, b, c, d, e, f, g, h):
    pass
```

### Return Values
- Functions MUST have predictable return types.
- You SHOULD return domain objects, not primitive types or tuples.
- You MUST use Optional[T] for nullable returns.
- You MUST use exceptions for error cases, not error codes.

### Error Handling
- You MUST define custom exception classes for domain errors.
- Exceptions MUST inherit from a base `AppException` class.
- You MUST NOT use exceptions for control flow.
- You MUST handle exceptions at appropriate boundaries.

Example:
```python
# core/exceptions.py
class AppException(Exception):
    """Base exception for application errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class UserNotFoundError(AppException):
    def __init__(self, user_id: UUID):
        super().__init__(
            f"User {user_id} not found",
            status_code=404
        )
```

## Code Organization Patterns

### Repository Pattern
- You MUST implement repositories for all data access.
- Repositories MUST work with domain models, not raw queries.
- You MUST NOT leak database implementation details.

```python
class UserRepository:
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Returns User domain object, not SQLAlchemy model."""
        pass
```

### Service Pattern
- You MUST encapsulate business logic in service classes.
- Services MUST orchestrate repositories and external integrations.
- You MUST NOT put business logic in API handlers or repositories.

### Factory Pattern
- You MUST use factories for complex object creation.
- Factories SHOULD handle dependency wiring.

```python
def create_llm_client(settings: Settings) -> LLMClient:
    """Factory for LLM client with proper configuration."""
    return GeminiClient(
        api_key=settings.gemini.api_key,
        model=settings.gemini.model_name,
        timeout=settings.gemini.timeout
    )
```

### Strategy Pattern
- You SHOULD use strategies for interchangeable algorithms.
- Example: Different LLM providers, different storage backends.

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

class GeminiProvider(LLMProvider):
    async def generate(self, prompt: str) -> str:
        # Gemini implementation
        pass

class OpenAIProvider(LLMProvider):
    async def generate(self, prompt: str) -> str:
        # OpenAI implementation
        pass
```

## Async/Await Best Practices

### Async Function Design
- You MUST use `async def` for I/O-bound operations.
- You MUST use `await` for all async operations.
- You MUST NOT use blocking operations in async functions.
- You SHOULD use `asyncio.gather()` for concurrent operations.

### Sync vs Async
- Pure computation SHOULD remain synchronous.
- Database operations MUST be async.
- External API calls MUST be async.
- File I/O SHOULD be async (use `aiofiles`).

### Error Handling in Async
- You MUST wrap async operations in try-except.
- You MUST properly propagate exceptions from async tasks.
- You SHOULD use `asyncio.create_task()` for fire-and-forget operations.

## Type Hints and Validation

### Type Annotations
- You MUST provide type hints for ALL functions, parameters, and returns.
- You MUST use `Optional[T]` for nullable types.
- You SHOULD use `Union` sparingly; prefer specific types.
- You MUST use `Protocol` or `ABC` for interfaces.

### Pydantic Models
- You MUST use Pydantic models for:
  - API request/response schemas
  - Configuration settings
  - Data transfer objects (DTOs)
  - Structured LLM outputs
- You MUST add field descriptions for clarity.
- You SHOULD add validators for business rules.

```python
from pydantic import BaseModel, Field, validator

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")

    @validator("username")
    def username_alphanumeric(cls, v):
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric")
        return v
```

## Testing and Testability

### Test Structure
- You MUST write tests for all business logic.
- Test files MUST mirror source structure: `test_user_service.py` for `user_service.py`.
- You MUST use descriptive test names: `test_create_user_with_valid_data()`.

### Mocking and Fixtures
- You MUST mock external dependencies in unit tests.
- You SHOULD use pytest fixtures for common test data.
- You MUST NOT hit real databases/APIs in unit tests.

### Testable Design
- Functions MUST be testable in isolation.
- You MUST avoid hard dependencies (use injection).
- You SHOULD keep functions pure when possible.

## Documentation

### Docstrings
- You MUST provide docstrings for all public functions and classes.
- You SHOULD use Google-style or NumPy-style docstrings.
- Docstrings MUST include parameter descriptions and return types.

```python
async def create_user(
    username: str,
    email: str,
    session: AsyncSession
) -> User:
    """
    Creates a new user in the system.

    Args:
        username: The desired username (3-50 chars, alphanumeric)
        email: User's email address
        session: Database session for transaction

    Returns:
        The created User object with generated ID

    Raises:
        UserAlreadyExistsError: If username or email already taken
        ValidationError: If input data is invalid
    """
    pass
```

### Code Comments
- You MUST comment complex algorithms or non-obvious logic.
- You MUST NOT comment obvious code.
- Comments MUST explain "why", not "what".

**Good:**
```python
# Use exponential backoff to avoid overwhelming the API
await asyncio.sleep(2 ** retry_count)
```

**Bad:**
```python
# Increment counter
counter += 1
```

## Performance Considerations

### Database Optimization
- You MUST use database indexes for frequently queried fields.
- You MUST implement pagination for large result sets.
- You SHOULD use select_related/prefetch for N+1 query prevention.
- You MUST use connection pooling.

### Caching Strategy
- You SHOULD cache expensive computations.
- You MUST implement cache invalidation logic.
- You SHOULD use TTL-based caching for time-sensitive data.

### Resource Management
- You MUST close resources properly (use context managers).
- You MUST implement connection limits for external services.
- You SHOULD implement circuit breakers for flaky services.

## Security Best Practices

### Input Validation
- You MUST validate ALL user inputs.
- You MUST sanitize inputs to prevent injection attacks.
- You MUST use Pydantic or similar for automatic validation.

### Authentication and Authorization
- You MUST verify authentication on all protected endpoints.
- You MUST implement proper authorization checks.
- You MUST NOT trust client-side data for security decisions.

### Secret Management
- You MUST load secrets from environment variables or secret managers.
- You MUST NOT hardcode secrets in code.
- You MUST NOT log sensitive data.

## Monitoring and Observability

### Logging
- You MUST log significant business events.
- You MUST include context in log messages (user_id, request_id).
- You MUST use structured logging when possible.
- You MUST NOT log PII or sensitive data.

### Metrics
- You SHOULD track key performance indicators (response time, error rate).
- You SHOULD implement health check endpoints.

### Error Tracking
- You MUST capture and report unhandled exceptions.
- You SHOULD include stack traces and context in error reports.

## Anti-Patterns to Avoid

### DO NOT:
- Create God objects (classes that do everything)
- Use global mutable state
- Hardcode configuration values
- Mix concerns (business logic in API handlers)
- Use magic numbers or strings
- Ignore exceptions or errors
- Create deep inheritance hierarchies (prefer composition)
- Premature optimization
- Over-engineer simple solutions
- Create circular dependencies
- Bypass the layered architecture
- Use `except: pass` without logging
- Modify parameters in-place without documenting
- Return different types from the same function

## Refactoring Guidelines

### When to Refactor
- Code duplication appears (3+ instances)
- Function exceeds 50 lines
- Module exceeds 500 lines
- Complexity metrics are high (cyclomatic complexity > 10)
- Code is difficult to test
- Code smells are detected

### How to Refactor
- Write tests first (if they don't exist)
- Make small, incremental changes
- Run tests after each change
- Commit working states frequently
- Document breaking changes

### Common Refactorings
- Extract method (long function → smaller functions)
- Extract class (large class → multiple focused classes)
- Introduce parameter object (many params → single object)
- Replace conditional with polymorphism
- Pull up/push down methods in hierarchy
- Replace magic numbers with named constants

## Code Review Checklist

Before committing, verify:
- [ ] All functions have type hints
- [ ] All public APIs have docstrings
- [ ] No hardcoded configuration values
- [ ] Error handling is implemented
- [ ] Tests are written and passing
- [ ] No circular dependencies
- [ ] Follows layered architecture
- [ ] Uses dependency injection
- [ ] Logging is appropriate
- [ ] No sensitive data in logs
- [ ] Resource cleanup is handled
- [ ] Performance is acceptable
- [ ] Security best practices followed
