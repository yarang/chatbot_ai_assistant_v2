"""
임베딩 모델 싱글톤 관리자

애플리케이션 전체에서 SentenceTransformer 모델을 공유하여
메모리 사용량을 최적화하고 초기화 시간을 단축합니다.
GPU 가속을 지원하며, 사용 가능한 장치를 자동으로 감지합니다.
"""

import asyncio
import logging
from typing import Optional

import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def _detect_device() -> str:
    """
    사용 가능한 디바이스 감지

    우선순위: CUDA > MPS (Apple Silicon) > CPU

    Returns:
        str: 사용할 디바이스 ('cuda', 'mps', 'cpu')
    """
    # CUDA (NVIDIA GPU)
    if torch.cuda.is_available():
        device_count = torch.cuda.device_count()
        logger.info(f"CUDA 감지됨: {device_count}개 GPU")
        return "cuda"

    # MPS (Apple Silicon GPU)
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("Apple Silicon MPS 감지됨")
        return "mps"

    # Vulkan/ROCm (AMD GPU) - 실험적 지원
    try:
        if torch.version.hip:
            logger.info("AMD ROCm (HIP) 감지됨")
            return "cuda"  # ROCm uses CUDA interface
    except Exception:
        pass

    # CPU 기본값
    logger.info("GPU 감지 안됨, CPU 사용")
    return "cpu"


class EmbeddingModelManager:
    """
    임베딩 모델 싱글톤 관리자

    전역적으로 하나의 SentenceTransformer 모델 인스턴스만 유지하여
    메모리 중복 사용을 방지하고 로딩 시간을 최적화합니다.
    GPU 가속을 자동으로 감지하고 적용합니다.

    Attributes:
        _instance: 싱글톤 인스턴스
        _model: 로드된 임베딩 모델
        _device: 사용 중인 디바이스
        _lock: 스레드 안전한 초기화를 위한 락

    Example:
        >>> manager = await EmbeddingModelManager.get_instance()
        >>> model = manager.get_model()
        >>> embeddings = model.encode(["Hello, world!"])
    """

    _instance: Optional["EmbeddingModelManager"] = None
    _lock = asyncio.Lock()
    _model: Optional[SentenceTransformer] = None
    _device: Optional[str] = None
    _model_lock = asyncio.Lock()

    def __init__(self):
        """초기화 (내부용)"""
        if EmbeddingModelManager._instance is not None:
            raise RuntimeError("Use get_instance() to get the singleton instance")
        self._model = None
        self._device = None

    @classmethod
    async def get_instance(cls) -> "EmbeddingModelManager":
        """
        싱글톤 인스턴스 반환 (스레드 안전)

        Double-check locking pattern을 사용하여 멀티스레딩 환경에서도
        안전하게 인스턴스를 생성합니다.

        Returns:
            EmbeddingModelManager: 싱글톤 인스턴스
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    logger.info("EmbeddingModelManager 싱글톤 인스턴스 생성")
                    cls._instance = cls()
        return cls._instance

    async def get_model(self) -> SentenceTransformer:
        """
        임베딩 모델 반환 (지연 로딩)

        첫 호출 시 모델을 로드하고 이후에는 캐시된 모델을 반환합니다.
        GPU가 사용 가능한 경우 GPU를 우선 사용합니다.

        Returns:
            SentenceTransformer: all-mpnet-base-v2 모델
        """
        if self._model is None:
            async with self._model_lock:
                if self._model is None:
                    # 디바이스 감지
                    if self._device is None:
                        self._device = _detect_device()

                    logger.info(
                        f"SentenceTransformer 모델 로드 시작: "
                        f"sentence-transformers/all-mpnet-base-v2 (device={self._device})"
                    )

                    self._model = SentenceTransformer(
                        "sentence-transformers/all-mpnet-base-v2",
                        device=self._device,
                    )

                    logger.info(
                        f"SentenceTransformer 모델 로드 완료: "
                        f"차원={self._model.get_sentence_embedding_dimension()}, "
                        f"디바이스={self._model.device}"
                    )
        return self._model

    def get_model_sync(self) -> SentenceTransformer:
        """
        임베딩 모델 반환 (동기 버전)

        비동기 컨텍스트에서 사용하기 어려울 때 사용합니다.
        모델이 로드되지 않은 경우 동기적으로 로드합니다.

        Returns:
            SentenceTransformer: all-mpnet-base-v2 모델
        """
        if self._model is None:
            # 디바이스 감지
            if self._device is None:
                self._device = _detect_device()

            logger.info(
                f"SentenceTransformer 모델 로드 시작 (동기): "
                f"sentence-transformers/all-mpnet-base-v2 (device={self._device})"
            )

            self._model = SentenceTransformer(
                "sentence-transformers/all-mpnet-base-v2",
                device=self._device,
            )

            logger.info(
                f"SentenceTransformer 모델 로드 완료: "
                f"차원={self._model.get_sentence_embedding_dimension()}, "
                f"디바이스={self._model.device}"
            )
        return self._model

    @property
    def device(self) -> str:
        """
        사용 중인 디바이스 반환

        Returns:
            str: 디바이스 ('cuda', 'mps', 'cpu')
        """
        return self._device or "cpu"

    @property
    def embedding_dimension(self) -> int:
        """
        임베딩 차원 반환

        Returns:
            int: 임베딩 차원 (all-mpnet-base-v2는 768)
        """
        if self._model is None:
            return 768  # all-mpnet-base-v2 기본 차원
        return self._model.get_sentence_embedding_dimension()


# 편의 함수
async def get_embedding_model() -> SentenceTransformer:
    """
    임베딩 모델 반환 (편의 함수)

    Returns:
        SentenceTransformer: all-mpnet-base-v2 모델
    """
    manager = await EmbeddingModelManager.get_instance()
    return await manager.get_model()


def get_embedding_model_sync() -> SentenceTransformer:
    """
    임베딩 모델 반환 (동기 편의 함수)

    Returns:
        SentenceTransformer: all-mpnet-base-v2 모델
    """
    return EmbeddingModelManager._instance.get_model_sync()
