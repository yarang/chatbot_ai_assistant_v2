---
description: Rules for configuration and environment setup
---

# Configuration Rules

## Environment Variables (`.env`)
- You MUST use `.env` files for local configuration.
- You MUST NOT commit `.env` to version control.
- You MUST use `pydantic-settings` to load and validate configurations in `core/config.py`.

## `core/config.py`
- You MUST define a `Settings` class inheriting from `BaseSettings`.
- You MUST use type hints for all configuration fields.
- You MUST use `model_config = SettingsConfigDict(env_file=".env", ...)` to auto-load variables.

## Usage
- You MUST access configuration via a singleton dependency (e.g., `get_settings()`).
- You MUST NOT read `os.environ` directly in business logic; inject settings instead.