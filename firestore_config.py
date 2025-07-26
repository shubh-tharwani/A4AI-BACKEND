import os
import logging
from google.cloud import firestore
from dotenv import load_dotenv
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Firestore Configuration
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "a4ai-10bf3")
DATABASE_NAME = os.getenv("FIRESTORE_DATABASE", "a4ai-db")
FIRESTORE_COLLECTION = os.getenv("FIRESTORE_COLLECTION", "users_assessments")

# Google Cloud credentials - Use dedicated Firestore credentials
GOOGLE_APPLICATION_CREDENTIALS_FIRESTORE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_FIRESTORE", "./firestore_key.json")

# Set the Firestore credentials in environment for this service
# We use a temporary environment variable to avoid conflicts with other services
original_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS_FIRESTORE

try:
    # Initialize Firestore client with specific database
    logger.info(f"Initializing Firestore client with database: {DATABASE_NAME}")
    logger.info(f"Using Firestore credentials: {GOOGLE_APPLICATION_CREDENTIALS_FIRESTORE}")
    db = firestore.Client(project=PROJECT_ID, database=DATABASE_NAME)
    logger.info(f"Firestore client initialized successfully for project: {PROJECT_ID}, database: {DATABASE_NAME}")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {str(e)}")
    # Fallback to default database
    logger.info("Attempting to initialize with default database")
    db = firestore.Client(project=PROJECT_ID)
    logger.warning("Using default Firestore database due to initialization error")
finally:
    # Restore original credentials environment variable to avoid affecting other services
    if original_credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = original_credentials
    else:
        # If there were no original credentials, remove the environment variable
        os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
    logger.info("Restored original GOOGLE_APPLICATION_CREDENTIALS environment variable")

def get_firestore_db() -> firestore.Client:
    """
    Returns Firestore client instance
    
    Returns:
        firestore.Client: Configured Firestore client
    """
    return db

def get_firestore_collection(collection_name: Optional[str] = None) -> firestore.CollectionReference:
    """
    Returns Firestore collection reference
    
    Args:
        collection_name: Optional collection name, defaults to FIRESTORE_COLLECTION
        
    Returns:
        firestore.CollectionReference: Collection reference
    """
    collection = collection_name or FIRESTORE_COLLECTION
    return db.collection(collection)

def get_document_reference(collection_name: str, document_id: str) -> firestore.DocumentReference:
    """
    Returns a document reference for a specific collection and document ID
    
    Args:
        collection_name: Name of the collection
        document_id: ID of the document
        
    Returns:
        firestore.DocumentReference: Document reference
    """
    return db.collection(collection_name).document(document_id)

def test_connection() -> bool:
    """
    Test Firestore connection
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        # Try to get a non-existent document to test connection
        test_ref = db.collection("_connection_test").document("test")
        test_ref.get()  # This will succeed even if document doesn't exist
        logger.info("Firestore connection test successful")
        return True
    except Exception as e:
        logger.error(f"Firestore connection test failed: {str(e)}")
        return False

# Configuration summary
def log_firestore_config():
    """Log current Firestore configuration"""
    logger.info("=== Firestore Configuration ===")
    logger.info(f"Project ID: {PROJECT_ID}")
    logger.info(f"Database Name: {DATABASE_NAME}")
    logger.info(f"Default Collection: {FIRESTORE_COLLECTION}")
    logger.info(f"Firestore Credentials File: {GOOGLE_APPLICATION_CREDENTIALS_FIRESTORE}")
    logger.info("===============================")

# Initialize and test connection on import
if __name__ != "__main__":
    log_firestore_config()
    if not test_connection():
        logger.warning("Firestore connection test failed - some features may not work properly")

# Test script - run this file directly to test Firestore configuration
if __name__ == "__main__":
    print("Testing Firestore Configuration...")
    print("=" * 40)
    
    log_firestore_config()
    
    print("\n🔄 Testing Firestore connection...")
    if test_connection():
        print("✅ Firestore connection successful!")
    else:
        print("❌ Firestore connection failed!")
        
    print("\n" + "=" * 40)
    print("Firestore configuration test completed!")
