"""
Cloud Storage Service
Handles Google Cloud Storage operations for visual aids and media files
"""
import logging
import uuid
import os
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from google.cloud import storage
from google.cloud.exceptions import NotFound, GoogleCloudError

from config import PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS

logger = logging.getLogger(__name__)

class CloudStorageService:
    """Service for handling Google Cloud Storage operations"""
    
    def __init__(self):
        # Set up authentication
        if GOOGLE_APPLICATION_CREDENTIALS:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS
        
        self.client = storage.Client(project=PROJECT_ID)
        self.bucket_name = "a4ai-visual-aids-bucket"  # Configure in environment
        self.bucket = self._get_or_create_bucket()
    
    def _get_or_create_bucket(self) -> Optional[storage.Bucket]:
        """Get existing bucket or create if it doesn't exist"""
        try:
            bucket = self.client.bucket(self.bucket_name)
            if not bucket.exists():
                logger.info(f"Creating new bucket: {self.bucket_name}")
                bucket = self.client.create_bucket(self.bucket_name, location="US")
                # Set bucket permissions for public read if needed
                bucket.make_public(recursive=True, future=True)
                logger.info(f"Successfully created bucket: {self.bucket_name}")
            else:
                logger.info(f"Using existing bucket: {self.bucket_name}")
            return bucket
        except Exception as e:
            logger.error(f"Error with bucket {self.bucket_name}: {e}")
            logger.warning("Cloud Storage service will operate in fallback mode")
            return None
    
    def upload_image(self, image_data: bytes, filename: Optional[str] = None, 
                    content_type: str = "image/png", make_public: bool = True) -> Tuple[str, str]:
        """
        Upload image data to Cloud Storage
        
        Args:
            image_data (bytes): Raw image data
            filename (str, optional): Custom filename (will generate if not provided)
            content_type (str): MIME type of the image
            make_public (bool): Whether to make the file publicly accessible
            
        Returns:
            Tuple[str, str]: (filename, public_url)
        """
        try:
            if not self.bucket:
                raise Exception("Cloud Storage bucket not available - service running in fallback mode")
                
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = uuid.uuid4().hex[:8]
                extension = self._get_extension_from_content_type(content_type)
                filename = f"visual_aid_{timestamp}_{unique_id}{extension}"
            
            # Create blob and upload
            blob = self.bucket.blob(f"visual_aids/{filename}")
            blob.upload_from_string(image_data, content_type=content_type)
            
            # Set cache control for better performance
            blob.cache_control = "public, max-age=86400"  # 1 day
            blob.patch()
            
            # Make public if requested
            public_url = None
            if make_public:
                blob.make_public()
                public_url = blob.public_url
            
            logger.info(f"Successfully uploaded image: {filename}")
            return filename, public_url or f"gs://{self.bucket_name}/visual_aids/{filename}"
            
        except Exception as e:
            logger.error(f"Error uploading image {filename}: {e}")
            raise
    
    def upload_video(self, video_data: bytes, filename: Optional[str] = None,
                    content_type: str = "video/mp4", make_public: bool = True) -> Tuple[str, str]:
        """
        Upload video data to Cloud Storage
        
        Args:
            video_data (bytes): Raw video data
            filename (str, optional): Custom filename
            content_type (str): MIME type of the video
            make_public (bool): Whether to make the file publicly accessible
            
        Returns:
            Tuple[str, str]: (filename, public_url)
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_id = uuid.uuid4().hex[:8]
                extension = self._get_extension_from_content_type(content_type)
                filename = f"video_{timestamp}_{unique_id}{extension}"
            
            # Create blob and upload
            blob = self.bucket.blob(f"videos/{filename}")
            blob.upload_from_string(video_data, content_type=content_type)
            
            # Set appropriate cache control for videos
            blob.cache_control = "public, max-age=604800"  # 1 week
            blob.patch()
            
            # Make public if requested
            public_url = None
            if make_public:
                blob.make_public()
                public_url = blob.public_url
            
            logger.info(f"Successfully uploaded video: {filename}")
            return filename, public_url or f"gs://{self.bucket_name}/videos/{filename}"
            
        except Exception as e:
            logger.error(f"Error uploading video {filename}: {e}")
            raise
    
    def get_signed_url(self, filename: str, expiration_hours: int = 1) -> str:
        """
        Generate a signed URL for private file access
        
        Args:
            filename (str): Name of the file
            expiration_hours (int): Hours until URL expires
            
        Returns:
            str: Signed URL
        """
        try:
            blob = self.bucket.blob(filename)
            expiration = datetime.utcnow() + timedelta(hours=expiration_hours)
            
            signed_url = blob.generate_signed_url(
                expiration=expiration,
                method="GET"
            )
            
            logger.info(f"Generated signed URL for: {filename}")
            return signed_url
            
        except Exception as e:
            logger.error(f"Error generating signed URL for {filename}: {e}")
            raise
    
    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from Cloud Storage
        
        Args:
            filename (str): Name of the file to delete
            
        Returns:
            bool: Success status
        """
        try:
            blob = self.bucket.blob(filename)
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted file: {filename}")
                return True
            else:
                logger.warning(f"File not found for deletion: {filename}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            raise
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if a file exists in Cloud Storage
        
        Args:
            filename (str): Name of the file to check
            
        Returns:
            bool: Whether file exists
        """
        try:
            blob = self.bucket.blob(filename)
            exists = blob.exists()
            logger.debug(f"File {filename} exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Error checking file existence {filename}: {e}")
            return False
    
    def get_file_metadata(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file
        
        Args:
            filename (str): Name of the file
            
        Returns:
            Optional[Dict[str, Any]]: File metadata or None if not found
        """
        try:
            blob = self.bucket.blob(filename)
            if not blob.exists():
                return None
            
            # Reload to get latest metadata
            blob.reload()
            
            metadata = {
                "name": blob.name,
                "size": blob.size,
                "content_type": blob.content_type,
                "created": blob.time_created.isoformat() if blob.time_created else None,
                "updated": blob.updated.isoformat() if blob.updated else None,
                "public_url": blob.public_url if blob.public_url else None,
                "md5_hash": blob.md5_hash,
                "etag": blob.etag
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting file metadata {filename}: {e}")
            return None
    
    def list_files(self, prefix: str = "", limit: int = 100) -> List[Dict[str, Any]]:
        """
        List files in the bucket
        
        Args:
            prefix (str): Filter by prefix
            limit (int): Maximum number of files to return
            
        Returns:
            List[Dict[str, Any]]: List of file information
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix, max_results=limit)
            
            files = []
            for blob in blobs:
                file_info = {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "public_url": blob.public_url if blob.public_url else None
                }
                files.append(file_info)
            
            logger.info(f"Listed {len(files)} files with prefix: {prefix}")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files with prefix {prefix}: {e}")
            raise
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type"""
        extensions = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/avi": ".avi"
        }
        return extensions.get(content_type, ".bin")

# Singleton instance
cloud_storage_service = CloudStorageService()
