from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    name: str = "chatbot_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DATABASE_",
        extra="ignore"
    )


class TelegramSettings(BaseSettings):
    bot_token: str
    webhook_secret: Optional[str] = None
    bot_username: Optional[str] = None
    webhook_url: Optional[str] = None  # Full webhook URL (e.g., https://your-domain.com/webhook)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TELEGRAM_",
        extra="ignore"
    )


class GeminiSettings(BaseSettings):
    api_key: str
    model_name: str = "gemini-pro"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="GEMINI_",
        extra="ignore"
    )


class NotionSettings(BaseSettings):
    api_key: Optional[str] = None
    database_id: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NOTION_",
        extra="ignore"
    )


class Settings(BaseSettings):
    log_level: str = "INFO"
    admin_ids: List[int] = []
    tavily_api_key: Optional[str] = None
    
    # Nested settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    notion: NotionSettings = Field(default_factory=NotionSettings)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
