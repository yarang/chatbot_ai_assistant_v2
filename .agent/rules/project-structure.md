---
alwaysApply: true
description: Project structure and architecture rules
---

# Project Structure Rules

## Structure Enforcement
You MUST follow this exact project structure:

- **Root**: `main.py`, `.env` (not committed), `schema.sql`, `pyproject.toml`
- **Core Modules**:
  - `models/`: Database models (SQLAlchemy ORM)
  - `repository/`: Data access layer (persistence)
  - `services/`: Business logic and external integrations
  - `api/`: FastAPI routers and endpoints
  - `core/`: Core infrastructure (database, logger, middleware, exceptions, config, llm, vector_store)
- **AI/Agent Modules**:
  - `agent/`: LangGraph agent definitions
    - `graph.py`: Graph workflow definition
    - `state.py`: State schema (TypedDict)
    - `nodes/`: Agent node implementations
  - `tools/`: LangChain tools (search, retrieval, memory, etc.)
  - `llm/`: LLM-specific logic
    - `chains/`: LangChain chains and prompts
- **Web UI**:
  - `templates/`: Jinja2 HTML templates
  - `static/`: Static assets (CSS, JS, images)
- **Supporting**:
  - `scripts/`: Utility scripts (verification, ingestion, migration)
  - `tests/`: Test files (mirrors source structure)
  - `docs/`: Documentation files

You MUST NOT create an `app/` directory or move modules into subdirectories not listed above unless explicitly requested.

## Import Rules
You MUST use absolute imports starting from the root:
- Correct: `from core.database import ...`
- Incorrect: `from ..core.database import ...`

## Layered Architecture
You MUST respect the dependency flow:
```
api -> services -> repository -> models
 ↓       ↓           ↓
agent  tools      core
```

**Dependency Rules**:
- `api/`: Can use Services, Repositories, Agent graph, Core utilities
- `services/`: Can use Repositories, other Services, Tools, Core utilities
- `agent/`: Can use Tools, Services, Repositories, Core utilities
- `tools/`: Can use Services, Repositories, Core utilities (NO agent imports)
- `repository/`: Can use Models, Core utilities (NO higher-level imports)
- `models/`: Can ONLY use Core utilities (database, base classes)
- `core/`: MUST be self-contained (NO imports from other layers)
- `templates/`, `static/`: NO Python dependencies

**Strict Rules**:
- Models MUST NOT import from api, services, repository, agent, or tools layers
- Core MUST NOT import from any application layer
- Tools MUST NOT import from agent layer (to prevent circular dependencies)
- You MUST use dependency injection to break circular dependencies
- You MUST NOT create bidirectional imports between layers