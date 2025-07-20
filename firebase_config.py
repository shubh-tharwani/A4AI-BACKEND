import firebase_admin
from firebase_admin import credentials, auth, exceptions
import os
import logging
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with proper error handling"""
    try:
        # Check if Firebase is already initialized
        if firebase_admin._apps:
            logger.info("Firebase Admin SDK already initialized")
            return True
            
        cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase_key.json")
        
        if not os.path.exists(cred_path):
            logger.error(f"Firebase credentials file not found: {cred_path}")
            raise FileNotFoundError(f"Firebase credentials file not found: {cred_path}")
        
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        logger.info(f"Firebase Admin SDK initialized successfully with credentials: {cred_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {str(e)}")
        raise

# Initialize Firebase on module import
initialize_firebase()

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify Firebase ID token and return decoded user information
    
    Args:
        token (str): Firebase ID token
        
    Returns:
        dict: Decoded token with user information or None if invalid
    """
    if not token or not token.strip():
        logger.warning("Empty or invalid token provided")
        return None
        
    try:
        decoded_token = auth.verify_id_token(token)
        logger.info(f"Token verified successfully for user: {decoded_token.get('uid', 'unknown')}")
        return decoded_token
        
    except exceptions.InvalidArgumentError as e:
        logger.warning(f"Invalid token format: {str(e)}")
        return None
        
    except exceptions.FirebaseError as e:
        logger.warning(f"Firebase token verification failed: {str(e)}")
        return None
        
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        return None

def get_user(uid: str) -> Optional[Dict[str, Any]]:
    """
    Get user information by UID
    
    Args:
        uid (str): User UID
        
    Returns:
        dict: User information or None if not found
    """
    try:
        user_record = auth.get_user(uid)
        return {
            "uid": user_record.uid,
            "email": user_record.email,
            "email_verified": user_record.email_verified,
            "display_name": user_record.display_name,
            "photo_url": user_record.photo_url,
            "disabled": user_record.disabled,
            "provider_data": [
                {
                    "provider_id": provider.provider_id,
                    "uid": provider.uid,
                    "email": provider.email
                } for provider in user_record.provider_data
            ],
            "custom_claims": user_record.custom_claims or {},
            "metadata": {
                "creation_time": user_record.user_metadata.creation_timestamp,
                "last_sign_in_time": user_record.user_metadata.last_sign_in_timestamp,
                "last_refresh_time": user_record.user_metadata.last_refresh_timestamp
            }
        }
    except exceptions.UserNotFoundError:
        logger.warning(f"User not found: {uid}")
        return None
    except Exception as e:
        logger.error(f"Error getting user {uid}: {str(e)}")
        return None

def create_custom_token(uid: str, additional_claims: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """
    Create a custom token for a user
    
    Args:
        uid (str): User UID
        additional_claims (dict): Additional claims to include in the token
        
    Returns:
        str: Custom token or None if creation failed
    """
    try:
        custom_token = auth.create_custom_token(uid, additional_claims)
        logger.info(f"Custom token created for user: {uid}")
        return custom_token.decode('utf-8')
    except Exception as e:
        logger.error(f"Error creating custom token for user {uid}: {str(e)}")
        return None

def set_custom_claims(uid: str, custom_claims: Dict[str, Any]) -> bool:
    """
    Set custom claims for a user
    
    Args:
        uid (str): User UID
        custom_claims (dict): Custom claims to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        auth.set_custom_user_claims(uid, custom_claims)
        logger.info(f"Custom claims set for user {uid}: {custom_claims}")
        return True
    except Exception as e:
        logger.error(f"Error setting custom claims for user {uid}: {str(e)}")
        return False

def revoke_refresh_tokens(uid: str) -> bool:
    """
    Revoke all refresh tokens for a user
    
    Args:
        uid (str): User UID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        auth.revoke_refresh_tokens(uid)
        logger.info(f"Refresh tokens revoked for user: {uid}")
        return True
    except Exception as e:
        logger.error(f"Error revoking refresh tokens for user {uid}: {str(e)}")
        return False
