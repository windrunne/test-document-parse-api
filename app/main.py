from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
from app.config import settings
from app.database import engine, Base
from app.api.v1 import auth, orders, documents
from app.core.exception_handlers import register_exception_handlers

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting DME Orders API...")
    
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    yield
    
    logger.info("Shutting down DME Orders API...")


app = FastAPI(
    title="DME Orders API",
    description="A comprehensive API for managing DME orders with AI-powered document processing",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    logger.info(f"Request: {request.method} {request.url}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "Something went wrong"
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )



app.include_router(auth.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DME Orders API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs" if settings.debug else "Documentation disabled in production"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
