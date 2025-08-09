import uuid

from app.observability.logging import bind_ctx, clear_ctx
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        rid = request.headers.get("x-request-id", str(uuid.uuid4()))
        bind_ctx(request_id=rid, path=request.url.path, method=request.method)
        try:
            response = await call_next(request)
        finally:
            clear_ctx()
        response.headers["x-request-id"] = rid
        return response
