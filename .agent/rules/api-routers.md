---
globs: api/*.py,main.py
description: Rules for API Routers and FastAPI structure
---

# API Router Rules

## Router Design
- Each router MUST be defined in its own file in `api/`.
- You MUST use `APIRouter()` for grouping endpoints.
- You MUST inject dependencies (Services, Repositories) into route handlers or instantiate them within the handler using `SessionLocal` context.

## Route Handler Rules
- You MUST use `async def` for all route handlers.
- You MUST validate incoming JSON using Pydantic models or explicit checks.
- You MUST return standardized JSON responses.
- You MUST NOT put complex business logic in routers; delegate to `services/`.

## Main App (`main.py`)
- You MUST include all routers in `main.py` using `app.include_router()`.
- You MUST add `LoggingMiddleware` and global exception handlers in `main.py`.