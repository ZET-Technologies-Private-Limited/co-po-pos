"""
FastAPI application entry point with advanced setup
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config.settings import get_settings
from app.core.logging.system_logger import SystemLogger, setup_logging
from app.core.database.connection_manager import db_manager
from app.core.infrastructure.redis_client import ping_redis, close_redis_client
from app.core.infrastructure.neo4j_client import verify_neo4j, close_driver


# Setup logging
logger = SystemLogger("main")
setup_logging()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info(
        "Application starting",
        environment=settings.environment,
        debug=settings.debug
    )
    
    # Initialize database
    await db_manager.initialize()
    await db_manager.create_tables()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    await db_manager.close()
    await close_redis_client()
    await close_driver()
    logger.info("Application shutdown")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="AI-Based CO-PO-PSO Mapping and Attainment Chatbot",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc)
    )
    
    response_body: dict = {"detail": "Internal server error"}
    if settings.debug:
        response_body["error"] = str(exc)
    return JSONResponse(status_code=500, content=response_body)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    db_ok = await db_manager.health_check()
    redis_ok = await ping_redis()
    neo4j_ok = await verify_neo4j()

    return {
        "status": "healthy" if db_ok else "degraded",
        "environment": settings.environment,
        "app_name": settings.app_name,
        "dependencies": {
            "postgres": db_ok,
            "redis": redis_ok,
            "neo4j": neo4j_ok,
        }
    }


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint"""
    return {
        "message": "CO-PO-PSO Mapping and Attainment Chatbot API",
        "version": "1.0.0",
        "api_prefix": settings.api_prefix,
        "documentation": "/docs"
    }


# Import and register API routes
from app.api.v1.routes import router as api_router

app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers if settings.is_production else 1,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
