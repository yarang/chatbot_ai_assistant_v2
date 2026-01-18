"""
캐시 모듈

임베딩 결과와 RAG 검색 결과를 캐싱하여 중복 연산을 방지합니다.
Redis와 인메모리 캐시를 모두 지원하는 하이브리드 아키텍처입니다.
"""

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)


class MemoryCache:
    """
    인메모리 LRU 캐시

    TTL 기반 만료와 LRU eviction을 지원합니다.

    Attributes:
        max_size: 최대 캐시 항목 수
        ttl: 캐시 항목의 기본 TTL (초)
        cache: 캐시 저장소 {key: (value, timestamp)}
        lock: 스레드 안전한 접근을 위한 락

    Example:
        >>> cache = MemoryCache(max_size=1000, ttl=300)
        >>> await cache.set("query:hello", [0.1, 0.2, ...])
        >>> value = await cache.get("query:hello")
    """

    def __init__(self, max_size: int = 1000, ttl: int = 300):
        """
        캐시 초기화

        Args:
            max_size: 최대 캐시 항목 수 (기본값: 1000)
            ttl: 캐시 항목의 기본 TTL (초, 기본값: 300)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None (만료되었거나 없는 경우)
        """
        async with self.lock:
            if key in self.cache:
                value, timestamp = self.cache[key]
                if time.time() - timestamp < self.ttl:
                    self._hits += 1
                    return value
                # 만료된 항목 삭제
                del self.cache[key]
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 캐시할 값
            ttl: 이 항목의 TTL (None인 경우 기본 TTL 사용)
        """
        async with self.lock:
            # 용량 초과 시 LRU 삭제
            if len(self.cache) >= self.max_size:
                await self._evict_lru()

            self.cache[key] = (value, time.time())

    async def delete(self, key: str) -> bool:
        """
        캐시 항목 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    async def clear(self) -> None:
        """모든 캐시 항목 삭제"""
        async with self.lock:
            self.cache.clear()
            self._hits = 0
            self._misses = 0

    async def _evict_lru(self) -> None:
        """가장 오래된 항목 삭제 (LRU eviction)"""
        if not self.cache:
            return

        oldest_key = min(self.cache.items(), key=lambda x: x[1][1])[0]
        del self.cache[oldest_key]

    @property
    def hit_rate(self) -> float:
        """캐시 적중률"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def size(self) -> int:
        """현재 캐시 항목 수"""
        return len(self.cache)

    def get_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 반환

        Returns:
            통계 정보 딕셔너리
        """
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


def generate_cache_key(prefix: str, *args: Any) -> str:
    """
    캐시 키 생성

    Args:
        prefix: 키 접두사
        *args: 키에 포함할 값들

    Returns:
        해시된 캐시 키

    Example:
        >>> generate_cache_key("embedding", "hello world", 768)
        'embedding:a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e'
    """
    key_str = ":".join(str(arg) for arg in args)
    key_hash = hashlib.sha256(key_str.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


# 전역 캐시 인스턴스
embedding_cache = MemoryCache(max_size=2000, ttl=3600)  # 1시간 TTL
rag_result_cache = MemoryCache(max_size=500, ttl=300)  # 5분 TTL
query_cache = MemoryCache(max_size=1000, ttl=1800)  # 30분 TTL


class HybridCache:
    """
    하이브리드 캐시 (Redis L1 + Memory L2)

    Redis를 1차 캐시로 사용하고, Redis 연결 실패 시 인메모리 캐시를 2차 백업으로 사용합니다.

    Attributes:
        redis_enabled: Redis 사용 가능 여부
        fallback_cache: Redis 실패시 사용할 인메모리 캐시

    Example:
        >>> cache = HybridCache("embedding", ttl=3600)
        >>> await cache.set("key", [0.1, 0.2, ...])
        >>> value = await cache.get("key")
    """

    def __init__(self, prefix: str, ttl: int = 300):
        """
        하이브리드 캐시 초기화

        Args:
            prefix: 캐시 키 접두사 (예: "embedding", "rag", "query")
            ttl: 기본 TTL (초)
        """
        self.prefix = prefix
        self.ttl = ttl
        self.redis_enabled = False
        self._redis_client = None
        self.fallback_cache = MemoryCache(max_size=2000, ttl=ttl)

    async def _ensure_redis(self) -> None:
        """Redis 연결 확인"""
        if self._redis_client is None:
            try:
                from core.redis_client import get_redis_client

                self._redis_client = await get_redis_client()
                self.redis_enabled = self._redis_client is not None
                if self.redis_enabled:
                    logger.debug(f"{self.prefix} 캐시: Redis 사용")
            except Exception as e:
                logger.warning(
                    f"{self.prefix} 캐시: Redis 연결 실패, 인메모리 사용 - {e}"
                )
                self.redis_enabled = False

    async def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Redis를 먼저 시도하고, 실패 시 인메모리 캐시를 사용합니다.

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        await self._ensure_redis()

        # Redis 시도
        if self.redis_enabled and self._redis_client:
            try:
                full_key = f"{self.prefix}:{key}"
                value = await self._redis_client.get(full_key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.debug(f"Redis get 실패, 인메모리 사용: {e}")
                self.redis_enabled = False

        # 인메모리 캐시 백업
        return await self.fallback_cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        캐시에 값 저장

        Redis와 인메모리 캐시에 모두 저장합니다.

        Args:
            key: 캐시 키
            value: 캐시할 값
            ttl: TTL (None인 경우 기본 TTL 사용)
        """
        await self._ensure_redis()

        actual_ttl = ttl if ttl is not None else self.ttl

        # Redis 시도
        if self.redis_enabled and self._redis_client:
            try:
                full_key = f"{self.prefix}:{key}"
                serialized = json.dumps(value, ensure_ascii=False)
                await self._redis_client.setex(full_key, actual_ttl, serialized)
            except Exception as e:
                logger.debug(f"Redis set 실패, 인메모리만 사용: {e}")
                self.redis_enabled = False

        # 인메모리 캐시 백업
        await self.fallback_cache.set(key, value, actual_ttl)

    async def delete(self, key: str) -> bool:
        """
        캐시 항목 삭제

        Args:
            key: 캐시 키

        Returns:
            삭제 성공 여부
        """
        await self._ensure_redis()

        # Redis 시도
        if self.redis_enabled and self._redis_client:
            try:
                full_key = f"{self.prefix}:{key}"
                await self._redis_client.delete(full_key)
            except Exception:
                pass

        # 인메모리 캐시 백업
        return await self.fallback_cache.delete(key)

    async def clear(self) -> None:
        """모든 캐시 항목 삭제"""
        await self._ensure_redis()

        # Redis 시도 (패턴 매칭으로 모든 키 삭제)
        if self.redis_enabled and self._redis_client:
            try:
                pattern = f"{self.prefix}:*"
                keys = []
                async for key in self._redis_client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await self._redis_client.delete(*keys)
            except Exception:
                pass

        # 인메모리 캐시 백업
        await self.fallback_cache.clear()

    @property
    def stats(self) -> Dict[str, Any]:
        """캐시 통계"""
        return {
            "redis_enabled": self.redis_enabled,
            "fallback_stats": self.fallback_cache.get_stats(),
        }
