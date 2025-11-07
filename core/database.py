import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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
    """데이터베이스 URL 생성 (PostgreSQL만 지원)"""
    config = load_config()
    db_config = config["database"]
    
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


def get_engine():
    """SQLAlchemy async engine 반환 (싱글톤)"""
    global _engine
    if _engine is None:
        database_url = _get_database_url()
        _engine = create_async_engine(
            database_url,
            echo=False
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


from sqlalchemy import text

async def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    engine = get_engine()
    
    async with engine.begin() as conn:
        # 존재하는 테이블 목록 조회
        result = await conn.execute(
            text("""
                SELECT tablename 
                FROM pg_catalog.pg_tables 
                WHERE schemaname = 'public'
            """)
        )
        existing_tables = {row[0] for row in result.fetchall()}
        
        # 테이블을 생성 순서대로 정렬
        sorted_tables = sorted(
            Base.metadata.tables.values(),
            key=lambda t: t.info.get("creation_order", 999)
        )
        
        # 누락된 테이블만 생성
        for table in sorted_tables:
            if table.name not in existing_tables:
                await conn.run_sync(lambda: table.create(engine))
                print(f"테이블 생성됨: {table.name}")
            else:
                print(f"테이블이 이미 존재함: {table.name}")

