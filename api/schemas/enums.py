"""
Enum definitions for Pydantic schemas.

This module provides strongly-typed enums for consistent field values
across the application.
"""

from enum import StrEnum


class MessageRole(StrEnum):
    """
    Message role in a conversation.

    Attributes:
        USER: Message from the user
        ASSISTANT: Message from the AI assistant
        SYSTEM: System-level message
    """

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatType(StrEnum):
    """
    Telegram chat type.

    Attributes:
        PRIVATE: Private chat (1-on-1)
        GROUP: Group chat
        SUPERGROUP: Super group chat
        CHANNEL: Channel
    """

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class EvaluationScore(StrEnum):
    """
    Evaluation score levels.

    Attributes:
        VERY_POOR: Score of 1
        POOR: Score of 2
        FAIR: Score of 3
        GOOD: Score of 4
        EXCELLENT: Score of 5
    """

    VERY_POOR = "1"
    POOR = "2"
    FAIR = "3"
    GOOD = "4"
    EXCELLENT = "5"


class FileStatus(StrEnum):
    """
    File processing status.

    Attributes:
        PENDING: File uploaded, awaiting processing
        PROCESSING: File is being processed
        COMPLETED: File processing completed successfully
        FAILED: File processing failed
    """

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
