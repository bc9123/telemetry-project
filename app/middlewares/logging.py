import uuid
import time
import structlog
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


request_id_var: ContextVar[str] = ContextVar("request_id", default="")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        
        # Bind request ID to all logs in this request
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        start_time = time.time()
        
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None
        )
        
        try:
            response = await call_next(request)
            
            duration = time.time() - start_time
            
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_seconds=round(duration, 3)
            )
            
            # Add request ID to response headers for debugging
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_seconds=round(duration, 3),
                error_type=type(e).__name__
            )
            raise
        finally:
            # Clear context vars
            structlog.contextvars.clear_contextvars()