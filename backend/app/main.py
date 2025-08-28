import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.dev import router as dev_router  # Dev only
from app.api.routes.health import router as health_router
from app.db.database import init_db
from app.middleware.request_id import RequestIDMiddleware
from app.observability.logging import configure_logging, get_logger
from app.observability.otel import setup_otel

# from app.api.routes.users import router as users_router

configure_logging()
app = FastAPI()
app.include_router(health_router)
setup_otel(app)
app.add_middleware(RequestIDMiddleware)

# Include auth routes
app.include_router(auth_router)

# Dev only!
app.include_router(dev_router)

log = get_logger()
log.info("backend_started")

# Sets up CORS to frontend domain & port in prod
cors_env = os.getenv("CORS_ORIGINS", "http://localhost:8082")
origins: list[str] = [o.strip() for o in cors_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    try:
        await init_db()
        log.info("Database initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize database: {e}")
        # In production, you might want to exit here
        # For development, we'll continue and let the app handle DB errors


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    from app.db.database import close_db

    await close_db()
    log.info("Database connections closed")
