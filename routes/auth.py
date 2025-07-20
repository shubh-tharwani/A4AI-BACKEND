from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import logging
import re
import sys
import os

# Add parent directory to path to import config.py from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from firebase_config import verify_token, get_user, create_custom_token, set_custom_claims

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")

class SignupRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    display_name: Optional[str] = Field(None, max_length=100, description="User's display name")
    role: Optional[str] = Field(default="student", pattern="^(student|teacher|admin)$", description="User role")
    
    @validator('email')
    def validate_email(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        return v

class TokenRefreshRequest(BaseModel):
    refresh_token: str = Field(..., description="Firebase refresh token")

class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="Email address for password reset")
    
    @validator('email')
    def validate_email(cls, v):
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v

class AuthResponse(BaseModel):
    status: str
    message: str
    user_data: Optional[Dict[str, Any]] = None
    tokens: Optional[Dict[str, Any]] = None

@router.post("/login", 
            summary="User Login",
            description="Authenticate user with email and password",
            response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Authenticate user with email and password
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns authentication tokens and user information
    """
    try:
        if not config.FIREBASE_API_KEY:
            logger.error("Firebase API key not configured")
            raise HTTPException(status_code=500, detail="Authentication service not configured")
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={config.FIREBASE_API_KEY}"
        payload = {
            "email": request.email,
            "password": request.password,
            "returnSecureToken": True
        }
        
        logger.info(f"Login attempt for email: {request.email}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            # Get additional user information
            user_info = get_user(data.get("localId"))
            
            logger.info(f"Successful login for user: {request.email}")
            
            return AuthResponse(
                status="success",
                message="Login successful",
                user_data={
                    "uid": data.get("localId"),
                    "email": data.get("email"),
                    "display_name": data.get("displayName"),
                    "email_verified": data.get("emailVerified", False),
                    "custom_claims": user_info.get("custom_claims", {}) if user_info else {},
                    "last_login": datetime.utcnow().isoformat()
                },
                tokens={
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "expires_in": data.get("expiresIn")
                }
            )
        else:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Invalid credentials")
            logger.warning(f"Failed login attempt for {request.email}: {error_message}")
            raise HTTPException(status_code=401, detail=f"Authentication failed: {error_message}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@router.post("/signup",
            summary="User Registration", 
            description="Create a new user account",
            response_model=AuthResponse)
async def signup(request: SignupRequest):
    """
    Create a new user account
    
    - **email**: User's email address
    - **password**: Password (min 8 chars, must contain upper/lower/number)
    - **display_name**: User's display name (optional)
    - **role**: User role (student/teacher/admin, default: student)
    """
    try:
        if not config.FIREBASE_API_KEY:
            raise HTTPException(status_code=500, detail="Authentication service not configured")
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={config.FIREBASE_API_KEY}"
        payload = {
            "email": request.email,
            "password": request.password,
            "returnSecureToken": True
        }
        
        if request.display_name:
            payload["displayName"] = request.display_name
        
        logger.info(f"Signup attempt for email: {request.email}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            user_id = data.get("localId")
            
            # Set custom claims for the user
            if request.role and request.role != "student":
                success = set_custom_claims(user_id, {
                    "role": request.role,
                    "created_at": datetime.utcnow().isoformat()
                })
                if not success:
                    logger.warning(f"Failed to set custom claims for user {user_id}")
            
            logger.info(f"Successful signup for user: {request.email}")
            
            return AuthResponse(
                status="success",
                message="Account created successfully",
                user_data={
                    "uid": user_id,
                    "email": data.get("email"),
                    "display_name": request.display_name,
                    "role": request.role,
                    "email_verified": False,
                    "created_at": datetime.utcnow().isoformat()
                },
                tokens={
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "expires_in": data.get("expiresIn")
                }
            )
        else:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Registration failed")
            logger.warning(f"Failed signup attempt for {request.email}: {error_message}")
            raise HTTPException(status_code=400, detail=f"Registration failed: {error_message}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Signup error for {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration service error: {str(e)}")

@router.post("/refresh-token",
            summary="Refresh Authentication Token",
            description="Refresh expired authentication token")
async def refresh_token(request: TokenRefreshRequest):
    """
    Refresh expired authentication token
    
    - **refresh_token**: Valid Firebase refresh token
    """
    try:
        if not config.FIREBASE_API_KEY:
            raise HTTPException(status_code=500, detail="Authentication service not configured")
        
        url = f"https://securetoken.googleapis.com/v1/token?key={config.FIREBASE_API_KEY}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": request.refresh_token
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, data=payload)
        
        if response.status_code == 200:
            data = response.json()
            logger.info("Token refreshed successfully")
            
            return {
                "status": "success",
                "message": "Token refreshed successfully",
                "tokens": {
                    "id_token": data.get("id_token"),
                    "refresh_token": data.get("refresh_token"),
                    "expires_in": data.get("expires_in")
                }
            }
        else:
            logger.warning("Token refresh failed")
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token refresh service error")

@router.post("/reset-password",
            summary="Reset Password",
            description="Send password reset email")
async def reset_password(request: PasswordResetRequest):
    """
    Send password reset email
    
    - **email**: Email address to send reset link to
    """
    try:
        if not config.FIREBASE_API_KEY:
            raise HTTPException(status_code=500, detail="Authentication service not configured")
        
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={config.FIREBASE_API_KEY}"
        payload = {
            "requestType": "PASSWORD_RESET",
            "email": request.email
        }
        
        logger.info(f"Password reset requested for: {request.email}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload)
        
        if response.status_code == 200:
            logger.info(f"Password reset email sent to: {request.email}")
            return {
                "status": "success",
                "message": "Password reset email sent successfully"
            }
        else:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", "Failed to send reset email")
            logger.warning(f"Password reset failed for {request.email}: {error_message}")
            raise HTTPException(status_code=400, detail=error_message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error for {request.email}: {str(e)}")
        raise HTTPException(status_code=500, detail="Password reset service error")

@router.get("/verify-token",
           summary="Verify Authentication Token",
           description="Verify the validity of an authentication token",
           dependencies=[Depends(security)])
async def verify_auth_token(request: Request):
    """
    Verify the validity of an authentication token
    
    Returns user information if token is valid
    """
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split(" ")[1]
        user = verify_token(token)
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Get additional user information
        user_info = get_user(user.get("uid"))
        
        return {
            "status": "success",
            "message": "Token is valid",
            "user": {
                "uid": user.get("uid"),
                "email": user.get("email"),
                "email_verified": user.get("email_verified", False),
                "display_name": user_info.get("display_name") if user_info else None,
                "custom_claims": user.get("custom_claims", {}),
                "auth_time": user.get("auth_time"),
                "token_verified_at": datetime.utcnow().isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification error: {str(e)}")
        raise HTTPException(status_code=500, detail="Token verification service error")

@router.get("/health",
           summary="Authentication Service Health Check",
           tags=["Health"])
async def health_check():
    """Health check endpoint for the authentication service"""
    firebase_configured = bool(config.FIREBASE_API_KEY)
    
    return {
        "status": "healthy" if firebase_configured else "degraded",
        "service": "authentication",
        "message": "Authentication service is running properly" if firebase_configured else "Firebase API key not configured",
        "features": ["login", "signup", "token_refresh", "password_reset", "token_verification"],
        "firebase_configured": firebase_configured
    }
