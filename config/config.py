import os
import logging
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class ConfigurationError(Exception):
    """Custom configuration error"""
    pass

class Config:
    """Application configuration management"""
    
    # Google Cloud Configuration
    PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "a4ai-10bf3")
    LOCATION: str = os.getenv("GCP_LOCATION", "us-central1")
    VERTEX_MODEL: str = os.getenv("VERTEX_MODEL", "gemini-2.0-flash-001")
    GOOGLE_GEMINI_MODEL: str = os.getenv("GOOGLE_GEMINI_MODEL", "gemini-2.0-flash-001")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./vertex_ai_key.json")
    
    # Firebase Configuration
    FIREBASE_CREDENTIALS: str = os.getenv("FIREBASE_CREDENTIALS", "./firebase_key.json")
    FIREBASE_API_KEY: Optional[str] = os.getenv("FIREBASE_API_KEY")
    FIREBASE_AUTH_DOMAIN: Optional[str] = os.getenv("FIREBASE_AUTH_DOMAIN")
    FIREBASE_DATABASE_URL: Optional[str] = os.getenv("FIREBASE_DATABASE_URL")
    FIREBASE_STORAGE_BUCKET: Optional[str] = os.getenv("FIREBASE_STORAGE_BUCKET")
    
    # Application Configuration
    APP_NAME: str = os.getenv("APP_NAME", "A4AI Backend")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"
    
    # Security Configuration
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Database Configuration
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB
    ALLOWED_EXTENSIONS: list = os.getenv("ALLOWED_EXTENSIONS", "wav,mp3,flac,webm").split(",")
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./temp_audio")
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    # CORS Configuration
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    CORS_METHODS: list = os.getenv("CORS_METHODS", "GET,POST,PUT,DELETE,OPTIONS").split(",")
    CORS_HEADERS: list = os.getenv("CORS_HEADERS", "*").split(",")
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """
        Validate configuration and return validation results
        
        Returns:
            Dict containing validation results
        """
        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check required files
        required_files = [
            (cls.GOOGLE_APPLICATION_CREDENTIALS, "Google Cloud credentials"),
            (cls.FIREBASE_CREDENTIALS, "Firebase credentials")
        ]
        
        for file_path, description in required_files:
            if not Path(file_path).exists():
                validation_results["errors"].append(f"{description} file not found: {file_path}")
                validation_results["valid"] = False
        
        # Check required environment variables
        if not cls.GOOGLE_API_KEY:
            validation_results["warnings"].append("GOOGLE_API_KEY not set")
        
        if not cls.FIREBASE_API_KEY:
            validation_results["warnings"].append("FIREBASE_API_KEY not set")
        
        if cls.SECRET_KEY == "your-secret-key-here":
            if not cls.DEBUG:
                validation_results["errors"].append("SECRET_KEY must be changed from default value in production")
                validation_results["valid"] = False
            else:
                validation_results["warnings"].append("SECRET_KEY is using default value (development mode)")
        
        # Validate numeric values
        if cls.PORT < 1 or cls.PORT > 65535:
            validation_results["errors"].append(f"Invalid port number: {cls.PORT}")
            validation_results["valid"] = False
        
        if cls.MAX_FILE_SIZE < 1024:  # Less than 1KB
            validation_results["warnings"].append(f"MAX_FILE_SIZE is very small: {cls.MAX_FILE_SIZE} bytes")
        
        return validation_results
    
    @classmethod
    def log_config(cls):
        """Log current configuration (excluding sensitive data)"""
        logger.info("=== Application Configuration ===")
        logger.info(f"App Name: {cls.APP_NAME}")
        logger.info(f"App Version: {cls.APP_VERSION}")
        logger.info(f"Debug Mode: {cls.DEBUG}")
        logger.info(f"Log Level: {cls.LOG_LEVEL}")
        logger.info(f"Host: {cls.HOST}")
        logger.info(f"Port: {cls.PORT}")
        logger.info(f"Project ID: {cls.PROJECT_ID}")
        logger.info(f"Location: {cls.LOCATION}")
        logger.info(f"Vertex Model: {cls.VERTEX_MODEL}")
        logger.info(f"Max File Size: {cls.MAX_FILE_SIZE} bytes")
        logger.info(f"Upload Directory: {cls.UPLOAD_DIR}")
        logger.info(f"CORS Origins: {cls.CORS_ORIGINS}")
        logger.info("================================")

# Create global config instance
config = Config()

# Legacy compatibility - keep original variable names for backward compatibility
PROJECT_ID = config.PROJECT_ID
LOCATION = config.LOCATION
VERTEX_MODEL = config.VERTEX_MODEL
GOOGLE_GEMINI_MODEL = config.GOOGLE_GEMINI_MODEL
GOOGLE_API_KEY = config.GOOGLE_API_KEY
FIREBASE_CREDENTIALS = config.FIREBASE_CREDENTIALS
FIREBASE_API_KEY = config.FIREBASE_API_KEY
GOOGLE_APPLICATION_CREDENTIALS = config.GOOGLE_APPLICATION_CREDENTIALS

# Validate configuration on startup
validation_results = config.validate_config()
if not validation_results["valid"]:
    logger.error("Configuration validation failed:")
    for error in validation_results["errors"]:
        logger.error(f"  ERROR: {error}")
    raise ConfigurationError("Invalid configuration. Please check your environment variables and files.")

if validation_results["warnings"]:
    logger.warning("Configuration warnings:")
    for warning in validation_results["warnings"]:
        logger.warning(f"  WARNING: {warning}")

# Log configuration if not in production
if config.DEBUG:
    config.log_config()
