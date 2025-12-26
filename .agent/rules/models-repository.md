---
globs: models/*.py,repository/*.py
description: Rules for Models and Repository pattern
---

# Model and Repository Rules

## Models (`models/`)
- You MUST use SQLAlchemy 2.0 style (`Mapped`, `mapped_column`).
- You MUST use UUIDs for primary keys.
- You MUST include `created_at` timestamps for all entities.

## Repositories (`repository/`)
- You MUST implement one repository per aggregate/model.
- You MUST use `AsyncSession` passed from the service/caller.
- You MUST return ORM models or Pydantic schemas, not raw tuples (unless specific aggregation).
- You MUST handle database-level exceptions (like UniqueConstraint violation) and wrap them if necessary.