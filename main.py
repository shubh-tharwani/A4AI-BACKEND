import logging
import time
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
import uvicorn

from routes import education, assessment_routes, auth, personalization, activities, visual_aids, voice_consolidated
from app.routes import voice  # Add this import
import config
from config import Config

# Set up enhanced logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('app.log', mode='a')  # File output
    ]
)
logger = logging.getLogger(__name__)

# Also set up uvicorn logger to be more visible
uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.setLevel(logging.INFO)

# Planning routes enabled
PLANNING_AVAILABLE = True
logger.info("Planning routes enabled")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info(f"Debug mode: {Config.DEBUG}")
    
    # Create uploads and temp_image directories
    uploads_dir = os.path.join(os.getcwd(), "uploads")
    temp_image_dir = os.path.join(os.getcwd(), "temp_image")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(temp_image_dir, exist_ok=True)
    logger.info(f"Created directories: {uploads_dir}, {temp_image_dir}")
    
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

# Mount static files for serving uploaded images
uploads_dir = os.path.join(os.getcwd(), "uploads")
if not os.path.exists(uploads_dir):
    os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Mount static files for serving visual aid images
temp_image_dir = os.path.join(os.getcwd(), "temp_image")
if not os.path.exists(temp_image_dir):
    os.makedirs(temp_image_dir, exist_ok=True)
app.mount("/temp_image", StaticFiles(directory="temp_image"), name="temp_image")

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
        error_msg = f"Request failed: {str(e)} in {process_time:.4f}s on {request.method} {request.url.path}"
        logger.error(error_msg, exc_info=True)
        print(f"ERROR: {error_msg}")  # Also print to console for immediate visibility
        raise

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    error_msg = f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}"
    logger.error(error_msg, exc_info=True)
    print(f"ERROR: {error_msg}")  # Also print to console for immediate visibility
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if Config.DEBUG else "Internal server error",
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time()
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Enhanced HTTP exception handler"""
    error_msg = f"HTTP {exc.status_code}: {exc.detail} on {request.method} {request.url.path}"
    logger.warning(error_msg)
    print(f"WARNING: {error_msg}")  # Also print to console for immediate visibility
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            "timestamp": time.time()
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
    
    # Add the new voice assistant router
    try:
        app.include_router(voice.router, prefix="/api/v1/voice", tags=["Voice Assistant API"])
        logger.info("Voice Assistant API routes included successfully")
        voice_api_loaded = True
    except Exception as e:
        logger.error(f"Failed to include Voice Assistant API routes: {e}")
        voice_api_loaded = False
    
    # Include teacher dashboard routes
    try:
        from routes.teacher_dashboard import router as teacher_dashboard_router
        app.include_router(teacher_dashboard_router, prefix="/api/v1", tags=["Teacher Dashboard"])
        logger.info("Teacher dashboard routes included successfully")
        teacher_routes_loaded = True
    except Exception as e:
        logger.error(f"Failed to include teacher dashboard routes: {e}")
        teacher_routes_loaded = False
    
    # Include orchestrator routes
    try:
        from routes.orchestrator_routes import router as orchestrator_router
        app.include_router(orchestrator_router, prefix="/api/v1", tags=["Orchestration"])
        logger.info("Orchestrator routes included successfully")
        orchestrator_loaded = True
    except Exception as e:
        logger.error(f"Failed to include orchestrator routes: {e}")
        orchestrator_loaded = False
    
    # Count loaded routes
    base_routes = 6  # auth, education, assessment, activities, visual_aids, personalization, voice
    routes_loaded = base_routes
    if PLANNING_AVAILABLE:
        routes_loaded += 1
    if teacher_routes_loaded:
        routes_loaded += 1
    if orchestrator_loaded:
        routes_loaded += 1
    
    logger.info(f"{routes_loaded} routers loaded successfully")
except Exception as e:
    logger.error(f"Failed to load routers: {str(e)}")
    raise
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
    logger.info(f"Starting development server on {Config.HOST}:{Config.PORT}")
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.RELOAD,
        log_level=Config.LOG_LEVEL.lower(),
        access_log=True
    )
