import os
import sqlite3
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Iterator

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text
from core.config import load_config


class Base(DeclarativeBase):
    """SQLAlchemy Base 클래스"""
    pass


# SQLAlchemy Async Engine 및 Session 설정
_engine = None
_async_session_maker = None


def _get_database_url() -> str:
    """데이터베이스 URL 생성"""
    config = load_config()
    db_config = config["database"]
    driver = db_config.get("driver", "postgresql")
    
    if driver == "sqlite":
        db_path = db_config["path"]
        # aiosqlite를 위한 URL 형식: sqlite+aiosqlite:///경로
        return f"sqlite+aiosqlite:///{db_path}"
    elif driver == "postgresql":
        # PostgreSQL URL 형식: postgresql+asyncpg://user:password@host:port/database
        user = db_config.get("user", "postgres")
        password = db_config.get("password", "")
        host = db_config.get("host", "localhost")
        port = db_config.get("port", 5432)
        database = db_config.get("database", "chatbot_db")
        
        # 환경변수에서 비밀번호 가져오기 (보안)
        password = os.getenv("DATABASE_PASSWORD", password)
        user = os.getenv("DATABASE_USER", user)
        host = os.getenv("DATABASE_HOST", host)
        port = int(os.getenv("DATABASE_PORT", port))
        database = os.getenv("DATABASE_NAME", database)
        
        if password:
            return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql+asyncpg://{user}@{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database driver: {driver}")


def get_engine():
    """SQLAlchemy async engine 반환 (싱글톤)"""
    global _engine
    if _engine is None:
        database_url = _get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False,
            connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
        )
    return _engine


def get_async_session_maker():
    """AsyncSessionMaker 반환 (싱글톤)"""
    global _async_session_maker
    if _async_session_maker is None:
        _async_session_maker = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_maker


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """비동기 세션 컨텍스트 매니저"""
    async_session = get_async_session_maker()
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    engine = get_engine()
    config = load_config()
    driver = config["database"].get("driver", "postgresql")
    
    async with engine.begin() as conn:
        # SQLite 전용 설정
        if driver == "sqlite":
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA foreign_keys=ON;"))
        
        # PostgreSQL은 외래키가 기본적으로 활성화되어 있음
        # 모든 테이블 생성
        await conn.run_sync(Base.metadata.create_all)


# 하위 호환성을 위한 기존 함수 (deprecated)
def _connect():
    """기존 코드 호환성을 위한 함수 (deprecated)"""
    config = load_config()
    db_path = config["database"]["path"]
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """기존 코드 호환성을 위한 함수 (deprecated)"""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()



