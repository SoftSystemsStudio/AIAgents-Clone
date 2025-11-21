"""
Gmail Cleanup API - FastAPI Application.

Multi-tenant SaaS API for automated Gmail inbox cleanup.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.domain.customer import QuotaExceededError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    
    Runs on startup and shutdown to initialize/cleanup resources.
    """
    # Startup
    logger.info("🚀 Starting Gmail Cleanup API...")
    logger.info("📊 Initializing database connection...")
    # TODO: Initialize database pool
    # TODO: Initialize Redis connection for rate limiting
    # TODO: Start background tasks (usage tracking, cleanup jobs)
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down Gmail Cleanup API...")
    # TODO: Close database pool
    # TODO: Close Redis connection
    # TODO: Stop background tasks


# Create FastAPI application
app = FastAPI(
    title="Gmail Cleanup API",
    description="Automated Gmail inbox cleanup with AI-powered categorization",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# CORS middleware - allows frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "http://localhost:5173",  # Vite dev
        "https://yourdomain.com",  # Production frontend
        # TODO: Replace with actual frontend domain
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# Global exception handlers
@app.exception_handler(QuotaExceededError)
async def quota_exceeded_handler(request: Request, exc: QuotaExceededError):
    """Handle quota exceeded errors with helpful message"""
    logger.warning(f"Quota exceeded for customer: {exc}")
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "quota_exceeded",
            "message": str(exc),
            "upgrade_url": "/api/v1/billing/upgrade",  # TODO: Actual upgrade URL
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": str(exc),
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unexpected errors"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred. Please try again later.",
        }
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns 200 if service is healthy.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available.
    
    Returns:
    - 200 if service is ready to accept traffic
    - 503 if service is starting up or has dependency issues
    """
    # TODO: Check database connection
    # TODO: Check Redis connection
    # TODO: Check external API availability
    
    is_ready = True  # Replace with actual checks
    
    if not is_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected",  # TODO: Actual status
        "redis": "connected",  # TODO: Actual status
    }


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root - provides basic info and links"""
    return {
        "name": "Gmail Cleanup API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health",
        "endpoints": {
            "auth": "/api/v1/auth",
            "gmail": "/api/v1/gmail",
            "customer": "/api/v1/customer",
            "billing": "/api/v1/billing",
        }
    }


# Import and register route modules
from src.api.gmail_cleanup import router as gmail_router

app.include_router(gmail_router, prefix="/api/v1/gmail", tags=["Gmail"])

# TODO: Add more routers as they're created
# from src.api.auth_routes import router as auth_router
# from src.api.customer_routes import router as customer_router
# from src.api.billing_routes import router as billing_router
# app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
# app.include_router(customer_router, prefix="/api/v1/customer", tags=["Customer"])
# app.include_router(billing_router, prefix="/api/v1/billing", tags=["Billing"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (dev only)
        log_level="info",
    )
