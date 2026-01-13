"""
RAG 검색 API 라우터

업로드된 파일에서 관련 내용을 검색하는 API 엔드포인트를 제공합니다.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from api.schemas.rag_search import RAGSearchRequest, RAGSearchResponse
from services.rag_search_service import get_rag_search_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/rag/search",
    response_model=RAGSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="RAG 검색",
    description="업로드된 파일에서 질문과 관련된 내용을 검색합니다",
)
async def search_rag(request: RAGSearchRequest):
    """
    RAG 검색 엔드포인트

    지정된 채팅방에 업로드된 파일들에서 사용자 질문과 관련된 텍스트 청크를 검색합니다.

    Args:
        request: 검색 요청
            - query: 검색 질문
            - chat_room_id: 채팅방 ID
            - limit: 반환할 최대 결과 수 (기본값: 5)
            - threshold: 유사도 임계값 (기본값: 0.5)

    Returns:
        RAGSearchResponse: 검색 결과
            - chunks: 검색된 청크 리스트
            - total_chunks: 검색된 총 청크 수

    Raises:
        HTTPException 400: 요청 데이터 유효성 검증 실패
        HTTPException 500: 서버 내부 에러
    """
    try:
        # 검색 서비스 가져오기
        search_service = await get_rag_search_service()

        # 검색 수행
        chunks = await search_service.search(
            query=request.query,
            chat_room_id=request.chat_room_id,
            limit=request.limit,
            threshold=request.threshold,
        )

        logger.info(
            f"RAG 검색 완료: chat_room_id={request.chat_room_id}, "
            f"query='{request.query[:50]}...', results={len(chunks)}"
        )

        return RAGSearchResponse(chunks=chunks, total_chunks=len(chunks))

    except ValueError as e:
        # 비즈니스 로직 에러 (채팅방 없음 등)
        logger.warning(
            f"RAG 검색 요청 실패: chat_room_id={request.chat_room_id}, "
            f"query='{request.query}', error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except RuntimeError as e:
        # 실행 시간 에러 (임베딩 실패, 검색 실패 등)
        logger.error(
            f"RAG 검색 실행 실패: chat_room_id={request.chat_room_id}, "
            f"query='{request.query}', error={str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    except Exception as e:
        # 예상치 못한 에러
        logger.error(
            f"RAG 검색 예상치 못한 에러: chat_room_id={request.chat_room_id}, "
            f"query='{request.query}', error={str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"검색 중 오류가 발생했습니다",
        )
