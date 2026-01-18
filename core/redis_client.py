"""
Redis 클라이언트 모듈

애플리케이션의 Redis 연결을 관리하는 싱글톤 클라이언트입니다.
"""

import asyncio
import logging
from typing import Optional

import redis.asyncio as redis
from redis.asyncio import Redis

from core.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis 비동기 클라이언트 싱글톤

    Attributes:
        _instance: 싱글톤 인스턴스
        _client: Redis 연결 클라이언트
        _lock: 스레드 안전한 초기화를 위한 락
    """

    _instance: Optional["RedisClient"] = None
    _lock = asyncio.Lock()
    _client: Optional[Redis] = None

    def __init__(self):
        """초기화 (내부용)"""
        if RedisClient._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton instance")

    @classmethod
    async def get_instance(cls) -> "RedisClient":
        """
        싱글톤 인스턴스 반환 (스레드 안전)

        Returns:
            RedisClient: 싱글톤 인스턴스
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    logger.info("RedisClient 싱글톤 인스턴스 생성")
                    cls._instance = cls()
                    await cls._instance._connect()
        return cls._instance

    async def _connect(self) -> None:
        """Redis에 연결"""
        try:
            settings = get_settings()
            cache_settings = settings.cache

            # Check if caching is enabled
            if not cache_settings.enabled:
                logger.info("캐싱이 비활성화되어 있습니다. 인메모리 캐시를 사용합니다.")
                self._client = None
                return

            # Connect to Redis with cache settings
            self._client = redis.Redis(
                host=cache_settings.host,
                port=cache_settings.port,
                db=cache_settings.db,
                password=cache_settings.password,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            await self._client.ping()
            logger.info(
                f"Redis 연결 성공: {cache_settings.host}:{cache_settings.port}/{cache_settings.db}"
            )
        except Exception as e:
            logger.warning(f"Redis 연결 실패: {e}. 인메모리 캐시를 사용합니다.")
            self._client = None

    async def get_client(self) -> Optional[Redis]:
        """
        Redis 클라이언트 반환

        Returns:
            Redis 클라이언트 또는 None (연결 실패 시)
        """
        if self._client is None:
            await self._connect()
        return self._client

    async def close(self) -> None:
        """Redis 연결 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis 연결 종료")

    @property
    def is_connected(self) -> bool:
        """Redis 연결 상태"""
        return self._client is not None


# 전역 인스턴스
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> Optional[Redis]:
    """
    Redis 클라이언트 반환 (편의 함수)

    Returns:
        Redis 클라이언트 또는 None
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = await RedisClient.get_instance()
    return await _redis_client.get_client()


async def close_redis_client() -> None:
    """Redis 클라이언트 종료 (편의 함수)"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
