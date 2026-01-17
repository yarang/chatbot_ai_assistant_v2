"""
API Router Module

모든 API 라우터를 중앙 집중식으로 관리합니다.
/api prefix를 가진 모든 엔드포인트가 여기에 포함됩니다.
"""

from fastapi import APIRouter


def get_api_router() -> APIRouter:
    """
    API 라우터를 생성하고 모든 API 하위 라우터를 포함합니다.

    이 함수를 통해 포함되는 라우터들:
    - qa_router: 질문 응답 API (/api/qa/*)
    - persona_router: 페르소나 관리 API (/api/persona/*)
    - file_upload_router: 파일 업로드 API (/api/files/*)
    - rag_search_router: RAG 검색 API (/api/rag/*)
    - streaming_router: 실시간 스트리밍 API (/api/streaming/*)

    Returns:
        APIRouter: 모든 API 하위 라우터가 포함된 라우터

    Note:
        Lazy import를 사용하여 순환 참조를 방지합니다.
        main.py가 import될 때 바로 모든 모듈이 로드되지 않도록 합니다.
    """
    from api.file_upload_router import router as file_upload_router
    from api.persona_router import router as persona_router
    from api.qa_router import router as qa_router
    from api.rag_search_router import router as rag_search_router
    from api.streaming_router import router as streaming_router

    router = APIRouter(
        tags=["API"],
        responses={
            200: {"description": "Success"},
            401: {"description": "Unauthorized"},
            404: {"description": "Not Found"},
            422: {"description": "Validation Error"},
            500: {"description": "Internal Server Error"},
        },
    )

    # 개별 기능별로 명확한 prefix 분리
    router.include_router(qa_router, prefix="/qa", tags=["Q&A"])
    router.include_router(persona_router, prefix="/persona", tags=["Persona"])
    router.include_router(file_upload_router, prefix="/files", tags=["Files"])
    router.include_router(rag_search_router, prefix="/rag", tags=["RAG"])
    router.include_router(streaming_router, prefix="/streaming", tags=["Streaming"])

    return router


# 빈 라우터 (하위 호환성용 - 더 이상 사용하지 않음)
router = APIRouter()
