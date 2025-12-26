---
globs: services/*.py
description: Rules for Service layer and business logic
---

# Service Layer Rules

## Service Responsibilities
- You MUST verify that this layer serves as the boundary for transactions.
- You MUST handle `AsyncSession` management (passing it to repositories).
- You MUST implement all business logic here, not in API routers.

## External Integrations
- You MUST wrap external API calls (Gemini, Telegram) in dedicated service methods.
- You MUST handle timeouts and errors from external services gracefully.

## Naming Conventions
- Services MUST be named `SomethingService`.
- Methods SHOULD be verb-noun (e.g., `handle_question`, `create_user`).