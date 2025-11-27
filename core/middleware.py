import time
import logging
from fastapi import FastAPI, Request

logger = logging.getLogger("middleware")

def add_middlewares(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        
        response = await call_next(request)
        
        process_time_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Process-Time-ms"] = f"{process_time_ms:.2f}"
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time_ms:.2f}ms"
        )
        
        return response



