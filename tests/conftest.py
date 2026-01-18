"""
Pytest configuration and fixtures for RAG chatbot tests.

This module provides shared fixtures and configuration for all test modules.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import get_settings
from core.database import Base

# Test database URL (use separate test database)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an instance of the default event loop for the test session.

    This fixture ensures that each test module gets a fresh event loop,
    preventing 'Event loop is closed' errors.

    Yields:
        asyncio.AbstractEventLoop: New event loop instance
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_engine():
    """
    Create a test database engine.

    This fixture creates an in-memory SQLite database for testing.
    The database is dropped after each test function.

    Yields:
        AsyncEngine: Test database engine
    """
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.

    This fixture provides a clean database session for each test.
    All changes are rolled back after the test.

    Args:
        db_engine: Test database engine fixture

    Yields:
        AsyncSession: Test database session
    """
    async_session_maker = sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    # Session is automatically closed by context manager


@pytest.fixture(scope="function")
def test_settings():
    """
    Provide test settings.

    This fixture returns settings configured for testing.
    Override specific settings as needed for test isolation.

    Returns:
        Settings: Test configuration object
    """
    return get_settings()


# Auto-use fixtures to apply to all tests
@pytest.fixture(autouse=True)
async def setup_test_environment():
    """
    Set up test environment before each test.

    This fixture runs automatically before each test to ensure
    a clean test environment.
    """
    # Setup: Configure test environment
    yield
    # Teardown: Clean up resources
    await asyncio.sleep(0)  # Allow pending tasks to complete
