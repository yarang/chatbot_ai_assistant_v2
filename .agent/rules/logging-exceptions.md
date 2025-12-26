---
globs: core/logger.py,core/middleware.py,core/exceptions.py
description: Rules for logging and exception handling
---

# Logging and Exception Rules

## Logging Standards
- You MUST log entry and exit of critical business flows.
- You MUST use levels correctly:
  - `INFO`: Business events, request logs.
  - `WARNING`: Handled expectations, business errors.
  - `ERROR`: System failures, unhandled exceptions.
- You MUST NOT use `print()` statements; use `logger`.

## Exception Handling
- You MUST raise `AppException(message, status_code)` for known error states.
- You MUST ensure all async DB sessions are closed even when exceptions occur (use `async with` or try/finally).