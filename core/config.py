import json
import os
from functools import lru_cache
from typing import Any, Dict


CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))


@lru_cache(maxsize=1)
def load_config() -> Dict[str, Any]:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Environment overrides
    if os.getenv("LOG_LEVEL"):
        config["log_level"] = os.getenv("LOG_LEVEL")
    if os.getenv("GEMINI_API_KEY"):
        config["gemini"]["api_key"] = os.getenv("GEMINI_API_KEY")
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        config["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")

    # Database configuration
    db = config.get("database", {})
    
    # PostgreSQL: 환경변수로 설정 오버라이드 가능
    if os.getenv("DATABASE_HOST"):
        db["host"] = os.getenv("DATABASE_HOST")
    if os.getenv("DATABASE_PORT"):
        db["port"] = int(os.getenv("DATABASE_PORT"))
    if os.getenv("DATABASE_USER"):
        db["user"] = os.getenv("DATABASE_USER")
    if os.getenv("DATABASE_NAME"):
        db["database"] = os.getenv("DATABASE_NAME")
    # password는 보안상 환경변수로만 설정 (database.py에서 처리)
    
    config["database"] = db

    return config



