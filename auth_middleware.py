from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Dict, Any, List
import logging
from firebase_config import verify_token, get_user

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security scheme for Swagger UI
security = HTTPBearer()

class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class AuthorizationError(HTTPException):
    """Custom authorization error"""
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

async def firebase_auth(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Enhanced Firebase authentication middleware with detailed logging and error handling
    
    Args:
        request: FastAPI request object
        credentials: HTTP Bearer credentials
        
    Raises:
        AuthenticationError: If authentication fails
    """
    try:
        # Extract token from credentials
        token = credentials.credentials
        
        if not token or not token.strip():
            logger.warning(f"Empty token provided from IP: {request.client.host}")
            raise AuthenticationError("Authentication token is required")
        
        # Verify token with Firebase
        user = verify_token(token)
        if not user:
            logger.warning(f"Invalid token provided from IP: {request.client.host}")
            raise AuthenticationError("Invalid authentication token")
        
        # Add user info to request state
        request.state.user = user
        request.state.user_id = user.get("uid")
        request.state.user_email = user.get("email")
        request.state.user_role = user.get("role", "student")  # Default role
        
        logger.info(f"User authenticated successfully: {user.get('uid')} from IP: {request.client.host}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in authentication: {str(e)}")
        raise AuthenticationError("Authentication service error")

async def optional_firebase_auth(request: Request):
    """
    Optional Firebase authentication - doesn't raise errors if no token provided
    
    Args:
        request: FastAPI request object
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            request.state.user = None
            request.state.user_id = None
            request.state.user_email = None
            request.state.user_role = "anonymous"
            return
        
        token = auth_header.split(" ")[1]
        user = verify_token(token)
        
        if user:
            request.state.user = user
            request.state.user_id = user.get("uid")
            request.state.user_email = user.get("email")
            request.state.user_role = user.get("role", "student")
            logger.info(f"Optional auth successful for user: {user.get('uid')}")
        else:
            request.state.user = None
            request.state.user_id = None
            request.state.user_email = None
            request.state.user_role = "anonymous"
            
    except Exception as e:
        logger.warning(f"Optional auth failed: {str(e)}")
        request.state.user = None
        request.state.user_id = None
        request.state.user_email = None
        request.state.user_role = "anonymous"

def require_roles(allowed_roles: List[str]):
    """
    Role-based authorization decorator
    
    Args:
        allowed_roles: List of roles that are allowed to access the endpoint
        
    Returns:
        Dependency function for FastAPI
    """
    async def role_checker(request: Request):
        if not hasattr(request.state, "user") or not request.state.user:
            raise AuthenticationError("Authentication required")
        
        user_role = request.state.user.get("role", "student")
        custom_claims = request.state.user.get("custom_claims", {})
        user_roles = custom_claims.get("roles", [user_role])
        
        # Ensure user_roles is a list
        if isinstance(user_roles, str):
            user_roles = [user_roles]
        
        # Check if user has any of the required roles
        if not any(role in allowed_roles for role in user_roles):
            logger.warning(f"Access denied for user {request.state.user_id} with roles {user_roles}. Required: {allowed_roles}")
            raise AuthorizationError(f"Insufficient permissions. Required roles: {allowed_roles}")
        
        logger.info(f"Role authorization successful for user {request.state.user_id} with roles {user_roles}")
        return True
    
    return role_checker

def require_admin():
    """Require admin role"""
    return require_roles(["admin", "super_admin"])

def require_teacher():
    """Require teacher or admin role"""
    return require_roles(["teacher", "admin", "super_admin"])

def require_student():
    """Require student, teacher, or admin role"""
    return require_roles(["student", "teacher", "admin", "super_admin"])

async def get_current_user(request: Request) -> Dict[str, Any]:
    """
    Get current authenticated user information
    
    Args:
        request: FastAPI request object
        
    Returns:
        User information dictionary
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    if not hasattr(request.state, "user") or not request.state.user:
        raise AuthenticationError("User not authenticated")
    
    return request.state.user

async def get_current_user_id(request: Request) -> str:
    """
    Get current authenticated user ID
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID string
        
    Raises:
        AuthenticationError: If user is not authenticated
    """
    user = await get_current_user(request)
    return user.get("uid", "")
