import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.dev import router as dev_router  # Dev only
from app.api.routes.health import router as health_router
from app.api.v1 import router as v1_router
from app.db.database import init_db
from app.middleware.csrf import CSRFMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.observability.logging import configure_logging, get_logger
from app.observability.otel import setup_otel

# from app.api.routes.users import router as users_router

configure_logging()


log = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown handling."""
    # Startup
    try:
        await init_db()
        log.info("Database initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize database: {e}")
        # Continue running; endpoints that need DB should handle errors gracefully

    # Initialize Redis connection
    try:
        from app.core.redis_client import get_redis

        await get_redis()
        log.info("Redis connection established", redis_url=os.getenv("REDIS_URL"))
    except Exception as e:
        log.error(f"Failed to connect to Redis: {e}")

    # Start background cleanup job
    if os.getenv("ENABLE_CLEANUP_JOB", "true").lower() == "true":
        import asyncio

        from app.core.cleanup import schedule_cleanup_job

        asyncio.create_task(schedule_cleanup_job(interval_hours=24))
        log.info("Background cleanup job scheduled (runs every 24 hours)")

    # Initialize OpenTelemetry unless explicitly disabled
    if os.getenv("OTEL_SDK_DISABLED", "").lower() not in {"1", "true", "yes"}:
        try:
            setup_otel(app)
        except Exception as e:
            log.error(f"Failed to initialize OpenTelemetry: {e}")

    yield

    # Shutdown
    try:
        from app.core.redis_client import close_redis
        from app.db.database import close_db

        await close_db()
        log.info("Database connections closed")

        await close_redis()
        log.info("Redis connection closed")
    except Exception as e:
        log.error(f"Error during shutdown cleanup: {e}")


app = FastAPI(
    title="FitFolio API",
    version="1.0.0",
    description="Personal fitness tracking API with passwordless authentication",
    lifespan=lifespan,
)

# Health check (no versioning - stays at root)
app.include_router(health_router)

app.add_middleware(RequestIDMiddleware)

# API v1 routes (all v1 endpoints aggregated in v1 router)
app.include_router(v1_router, prefix="/api/v1")


# API root endpoint for version discovery
@app.get("/api")
async def api_root():
    """API root endpoint - returns available API versions."""
    return {
        "message": "FitFolio API",
        "versions": {"v1": "/api/v1"},
        "docs": "/docs",
        "health": "/healthz",
    }


# Dev only! (no versioning - debug endpoints)
app.include_router(dev_router)

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

# CSRF protection (must be after CORS)
app.add_middleware(CSRFMiddleware)

# Rate limiting (must be after CSRF to avoid wasting rate limit budget on CSRF failures)
app.add_middleware(
    RateLimitMiddleware,
    exempt_paths=["/docs", "/redoc", "/openapi.json"],  # Exempt API docs
)
