from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.middleware.request_id import RequestIDMiddleware
from app.observability.logging import configure_logging, get_logger
from app.observability.otel import setup_otel

# from app.api.routes.users import router as users_router

configure_logging()
app = FastAPI()
app.include_router(health_router)
setup_otel(app)
app.add_middleware(RequestIDMiddleware)

app.include_router(health_router)
# app.include_router(users_router)

log = get_logger()
log.info("backend_started")
