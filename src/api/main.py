"""
Main FastAPI application.
Entry point for the REST API backend.

Run with: poetry run python -m api.main
Or:       poetry run uvicorn api.main:app --reload
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from loguru import logger
import os

from pipeline.config import get_settings
from api.schemas import HealthResponse
from api.routes import github, spotify, dashboard, admin

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    # Startup
    logger.info("=" * 60)
    logger.info("Personal Data Analytics Dashboard API Starting")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug: {settings.debug}")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"API: {settings.api_host}:{settings.effective_port}")
    logger.info("")
    logger.info("Available endpoints:")
    logger.info("  Health: GET /health")
    logger.info("  GitHub: /api/github/*")
    logger.info("  Spotify: /api/spotify/*")
    logger.info("  Dashboard: /api/dashboard/*")
    logger.info("")
    logger.info("API Documentation:")
    logger.info(f"  Swagger UI: http://localhost:{settings.effective_port}/docs")
    logger.info(f"  ReDoc: http://localhost:{settings.effective_port}/redoc")
    logger.info("=" * 60)

    # Start background scheduler (runs alongside API in same process)
    _scheduler = None
    if settings.scheduler_enabled:
        try:
            from pipeline_jobs.scheduler import PipelineScheduler
            _scheduler = PipelineScheduler()
            _scheduler.start()
            logger.info("Background data pipeline scheduler started")
        except Exception as exc:
            logger.warning(f"Scheduler could not start (non-fatal): {exc}")

    yield

    # Shutdown
    logger.info("API shutting down...")
    if _scheduler is not None:
        try:
            _scheduler.stop()
        except Exception:
            pass


app = FastAPI(
    title="Personal Data Analytics Dashboard API",
    description="REST API for GitHub and Spotify data analytics",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Setup logging
logger.add(
    settings.log_file,
    rotation="00:00",
    retention="30 days",
    level=settings.log_level,
)

# ============================================================================
# Middleware
# ============================================================================

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        ["*"] if settings.is_development
        else [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom exception handler
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.exception("Unhandled exception: {}", exc)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc) if settings.debug else "An error occurred",
            "status_code": 500,
        },
    )


# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status and API information
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.environment,
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Alias for health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="0.1.0",
        environment=settings.environment,
    )


# ============================================================================
# Route Registration
# ============================================================================

# Include routers
app.include_router(github.router)
app.include_router(spotify.router)
app.include_router(dashboard.router)
app.include_router(admin.router)

# Add version prefix route for future versioning
app.include_router(github.router, prefix="/v1", tags=["v1"])
app.include_router(spotify.router, prefix="/v1", tags=["v1"])
app.include_router(dashboard.router, prefix="/v1", tags=["v1"])
app.include_router(admin.router, prefix="/v1", tags=["v1"])


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
            port=settings.effective_port,
        workers=settings.api_workers,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
