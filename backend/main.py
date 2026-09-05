from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import time
import structlog

from core.config import settings
from core.logging import configure_logging, get_logger, log_api_request
from core.celery_app import celery_app
from database.session import init_db, close_db
from api.v1.router import api_router

configure_logging()
logger = get_logger("main")


REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Secure Code Reviewer", version="1.0.0", environment=settings.ENVIRONMENT)
    
    await init_db()
    logger.info("Database initialized")
    
    yield
    
    logger.info("Shutting down AI Secure Code Reviewer")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title="AI Secure Code Reviewer",
    description="Production-quality AI-powered security code review platform",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)


@app.middleware("http")
async def add_metrics_and_logging(request: Request, call_next):
    start_time = time.time()
    
    request_id = request.headers.get("X-Request-ID", "")
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    duration_ms = duration * 1000
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    log_api_request(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    
    response.headers["X-Process-Time"] = str(duration_ms)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_code": "INTERNAL_ERROR",
        }
    )


app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": time.time(),
        "services": {
            "database": "connected",
            "redis": "connected",
            "chromadb": "connected",
        }
    }


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "AI Secure Code Reviewer",
        "version": "1.0.0",
        "description": "Production-quality AI-powered security code review platform",
        "docs": "/docs",
        "health": "/health",
        "metrics": "/metrics",
    }