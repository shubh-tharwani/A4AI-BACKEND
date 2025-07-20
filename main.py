import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn

from routes import education, assessment_routes, auth, personalization, activities, visual_aids, voice_consolidated
import config
from config import Config

# Set up logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Planning routes enabled
PLANNING_AVAILABLE = True
logger.info("Planning routes enabled")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"Debug mode: {Config.DEBUG}")
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")

# Create FastAPI application with enhanced configuration
app = FastAPI(
    title=Config.APP_NAME,
    version=Config.APP_VERSION,
    description="Advanced AI-powered educational backend with voice assistance, content generation, and personalized learning",
    docs_url="/docs" if Config.DEBUG else None,
    redoc_url="/redoc" if Config.DEBUG else None,
    openapi_url="/openapi.json" if Config.DEBUG else None,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=Config.CORS_METHODS,
    allow_headers=Config.CORS_HEADERS,
)

# Add trusted host middleware for security
if not Config.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["localhost", "127.0.0.1", "*.vercel.app", "*.herokuapp.com"]
    )

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()
    
    # Skip logging for health checks and static files
    skip_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"]
    should_log = not any(request.url.path.startswith(path) for path in skip_paths)
    
    if should_log:
        logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        if should_log:
            logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {str(e)} in {process_time:.4f}s")
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if Config.DEBUG else "Internal server error",
            "path": request.url.path,
            "method": request.method
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} on {request.method} {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )

# Include routers with error handling
try:
    app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])
    app.include_router(education.router, prefix="/api/v1", tags=["Education"])
    app.include_router(assessment_routes.router, prefix="/api/v1", tags=["Assessment"])
    app.include_router(activities.router, prefix="/api/v1", tags=["Activities"])
    app.include_router(visual_aids.router, prefix="/api/v1", tags=["Visual Aids"])
    
    # Planning routes disabled
    if PLANNING_AVAILABLE:
        try:
            from routes import planning
            app.include_router(planning.router, prefix="/api/v1", tags=["Planning"])
            logger.info("Planning routes included successfully")
        except Exception as e:
            logger.error(f"Failed to include planning routes: {e}")
    else:
        logger.warning("Planning routes skipped - disabled for troubleshooting")
    
    app.include_router(personalization.router, prefix="/api/v1", tags=["Personalization"])
    app.include_router(voice_consolidated.router, prefix="/api/v1/voice", tags=["Voice Assistant"])
    
    routes_loaded = 7 if PLANNING_AVAILABLE else 6
    logger.info(f"{routes_loaded} routers loaded successfully")
except Exception as e:
    logger.error(f"Failed to load routers: {str(e)}")
    raise

# Health check endpoint
@app.get("/health", tags=["Health"], summary="Health Check")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers
    """
    return {
        "status": "healthy",
        "app_name": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "timestamp": time.time(),
        "debug": Config.DEBUG
    }

# Root endpoint
@app.get("/", tags=["Root"], summary="Root Endpoint")
async def root():
    """
    Root endpoint with application information
    """
    return {
        "message": f"{Config.APP_NAME} is running!",
        "version": Config.APP_VERSION,
        "status": "operational",
        "docs_url": "/docs" if Config.DEBUG else "Documentation disabled in production",
        "health_check": "/health",
        "api_prefix": "/api/v1"
    }

# Custom OpenAPI schema
def custom_openapi():
    """Custom OpenAPI schema with additional metadata"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=Config.APP_NAME,
        version=Config.APP_VERSION,
        description="Advanced AI-powered educational backend with comprehensive API documentation",
        routes=app.routes,
    )
    
    # Add custom info
    openapi_schema["info"]["contact"] = {
        "name": "A4AI Development Team",
        "email": "support@a4ai.com"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Development server runner
if __name__ == "__main__":
    logger.info(f"Starting development server on {config.HOST}:{config.PORT}")
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL.lower(),
        access_log=True
    )
