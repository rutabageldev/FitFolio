import uuid

from starlette.middleware.base import BaseHTTPMiddleware

from app.observability import logging as app_logging


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id", str(uuid.uuid4()))
        app_logging.bind_ctx(
            request_id=rid, path=request.url.path, method=request.method
        )
        try:
            response = await call_next(request)
        finally:
            app_logging.clear_ctx()
        response.headers["x-request-id"] = rid
        return response
