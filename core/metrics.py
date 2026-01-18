"""
성능 모니터링 모듈

애플리케이션의 주요 성능 지표를 추적하고 모니터링합니다.
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Callable

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Prometheus 메트릭
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

rag_search_duration_seconds = Histogram(
    "rag_search_duration_seconds",
    "RAG search latency",
    ["chat_room_id"],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "type"],  # type: input, output
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request latency",
    ["model"],
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_type", "hit"],  # hit: true, false
)

active_connections = Gauge(
    "active_connections",
    "Active database connections",
)

embedding_cache_size = Gauge(
    "embedding_cache_size",
    "Current embedding cache size",
)


# 인메모리 메트릭
class MetricsStore:
    """인메모리 메트릭 저장소"""

    def __init__(self):
        self.request_times: dict = defaultdict(list)
        self.error_counts: dict = defaultdict(int)
        self._lock = asyncio.Lock()

    async def record_request(self, endpoint: str, duration: float) -> None:
        """요청 시간 기록"""
        async with self._lock:
            self.request_times[endpoint].append(duration)
            # 최근 100개만 유지
            if len(self.request_times[endpoint]) > 100:
                self.request_times[endpoint].pop(0)

    async def record_error(self, endpoint: str) -> None:
        """에러 기록"""
        async with self._lock:
            self.error_counts[endpoint] += 1

    async def get_stats(self) -> dict:
        """통계 반환"""
        async with self._lock:
            stats = {}
            for endpoint, times in self.request_times.items():
                if times:
                    stats[endpoint] = {
                        "count": len(times),
                        "avg": sum(times) / len(times),
                        "min": min(times),
                        "max": max(times),
                        "errors": self.error_counts.get(endpoint, 0),
                    }
            return stats


# 전역 메트릭 저장소
metrics_store = MetricsStore()


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    HTTP 요청 메트릭 수집 미들웨어

    모든 HTTP 요청의 시간, 상태 코드 등을 수집합니다.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """요청 처리 및 메트릭 수집"""
        start_time = time.time()
        endpoint = request.url.path

        try:
            response = await call_next(request)
            duration = time.time() - start_time

            # Prometheus 메트릭
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).inc()
            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint,
            ).observe(duration)

            # 인메모리 메트릭
            await metrics_store.record_request(endpoint, duration)

            return response

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Request error: {endpoint} - {e}")

            # 에러 메트릭
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=500,
            ).inc()
            await metrics_store.record_error(endpoint)

            raise


def track_llm_request(model: str):
    """
    LLM 요청 추적 데코레이터

    Args:
        model: 모델 이름

    Example:
        @track_llm_request("gemini-2.5-flash")
        async def generate_response(prompt: str) -> str:
            ...
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                llm_request_duration_seconds.labels(model=model).observe(duration)

                # 토큰 사용량 추출 (있는 경우)
                if hasattr(result, "usage_metadata") and result.usage_metadata:
                    input_tokens = result.usage_metadata.get("input_tokens", 0)
                    output_tokens = result.usage_metadata.get("output_tokens", 0)

                    llm_tokens_total.labels(model=model, type="input").inc(input_tokens)
                    llm_tokens_total.labels(model=model, type="output").inc(
                        output_tokens
                    )

                return result

            except Exception:
                duration = time.time() - start_time
                llm_request_duration_seconds.labels(model=model).observe(duration)
                raise

        return wrapper

    return decorator


def track_rag_search(chat_room_id: str):
    """
    RAG 검색 추적 데코레이터

    Args:
        chat_room_id: 채팅방 ID

    Example:
        @track_rag_search("room-123")
        async def search(query: str) -> list:
            ...
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                rag_search_duration_seconds.labels(chat_room_id=chat_room_id).observe(
                    duration
                )

                return result

            except Exception:
                duration = time.time() - start_time
                rag_search_duration_seconds.labels(chat_room_id=chat_room_id).observe(
                    duration
                )
                raise

        return wrapper

    return decorator


def track_cache_hit(cache_type: str, hit: bool):
    """
    캐시 적중 추적

    Args:
        cache_type: 캐시 타입 (embedding, rag, query)
        hit: 적중 여부
    """
    cache_hits_total.labels(cache_type=cache_type, hit=str(hit)).inc()


async def update_cache_metrics() -> None:
    """캐시 메트릭 업데이트"""
    try:
        from core.cache import embedding_cache

        embedding_cache_size.set(embedding_cache.size)
    except Exception as e:
        logger.debug(f"Failed to update cache metrics: {e}")


async def get_metrics_summary() -> dict:
    """
    메트릭 요약 반환

    Returns:
        성능 지표 요약
    """
    stats = await metrics_store.get_stats()
    summary = {
        "endpoints": stats,
        "cache": {},
        "llm": {},
    }

    # 캐시 통계 추가
    try:
        from core.cache import embedding_cache, rag_result_cache

        summary["cache"]["embedding"] = embedding_cache.get_stats()
        summary["cache"]["rag"] = rag_result_cache.get_stats()
    except Exception:
        pass

    return summary


async def get_prometheus_metrics() -> bytes:
    """
    Prometheus 메트릭 반환

    Returns:
        Prometheus 텍스트 포맷 메트릭
    """
    await update_cache_metrics()
    return generate_latest(REGISTRY)
