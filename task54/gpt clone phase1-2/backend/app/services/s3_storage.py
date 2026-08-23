"""
S3-compatible object storage integration for image uploads.

Supports AWS S3, MinIO, and other S3-compatible services.
Provides signed URLs for secure, time-limited access to images.
"""

import io
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from PIL import Image

from app.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "webp", "gif"}
MAX_FILE_SIZE_BYTES = settings.max_image_size_mb * 1024 * 1024


# ============================================================================
# S3 Storage Service
# ============================================================================


class S3StorageService:
    """Manage image uploads to S3-compatible storage."""

    def __init__(self):
        """Initialize S3 client."""
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )
        self.bucket = settings.s3_bucket
        self.expiry_hours = settings.image_upload_expiry_hours

    def validate_image(
        self, file_data: bytes, filename: str
    ) -> tuple[bool, Optional[str], Optional[dict]]:
        """
        Validate image file.

        Args:
            file_data: Raw file bytes
            filename: Original filename

        Returns:
            (is_valid, error_message, metadata)
            metadata includes: format, width, height, size_bytes
        """
        # Check file size
        if len(file_data) > MAX_FILE_SIZE_BYTES:
            return (
                False,
                f"File size {len(file_data)} bytes exceeds {MAX_FILE_SIZE_BYTES} bytes limit",
                None,
            )

        # Get file extension
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in SUPPORTED_FORMATS:
            return (
                False,
                f"Unsupported format '{ext}'. Supported: {', '.join(SUPPORTED_FORMATS)}",
                None,
            )

        # Try to open as image and get dimensions
        try:
            img = Image.open(io.BytesIO(file_data))
            img.load()  # Force load to validate

            return (
                True,
                None,
                {
                    "format": img.format or ext.upper(),
                    "width": img.width,
                    "height": img.height,
                    "size_bytes": len(file_data),
                },
            )
        except Exception as e:
            logger.warning(f"Image validation failed: {e}")
            return False, f"Invalid image file: {str(e)}", None

    def upload_image(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        content_type: str = "image/jpeg",
    ) -> Optional[tuple[str, datetime]]:
        """
        Upload image to S3.

        Args:
            file_data: Raw file bytes
            filename: Original filename
            user_id: User ID for scoping
            content_type: MIME type

        Returns:
            (s3_key, signed_url_expiry) or None if failed
        """
        # Generate S3 key: users/{user_id}/{uuid}_{filename}
        image_id = str(uuid.uuid4())
        s3_key = f"users/{user_id}/{image_id}_{filename}"

        try:
            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_data,
                ContentType=content_type,
                Metadata={
                    "user-id": user_id,
                    "original-filename": filename,
                },
            )

            logger.info(f"Uploaded image to S3: {s3_key} ({len(file_data)} bytes)")
            return s3_key, datetime.utcnow() + timedelta(hours=self.expiry_hours)

        except ClientError as e:
            logger.error(f"S3 upload error: {e}")
            return None

    def generate_signed_url(
        self,
        s3_key: str,
        expiry_hours: Optional[int] = None,
    ) -> Optional[tuple[str, datetime]]:
        """
        Generate signed URL for image access.

        Args:
            s3_key: S3 object key
            expiry_hours: How long URL is valid (default: configured)

        Returns:
            (signed_url, expiry_datetime) or None if failed
        """
        expiry = expiry_hours or self.expiry_hours

        try:
            # Generate presigned URL
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": s3_key},
                ExpiresIn=int(expiry * 3600),  # Convert hours to seconds
            )

            expiry_dt = datetime.utcnow() + timedelta(hours=expiry)
            logger.debug(f"Generated signed URL for {s3_key}")

            return url, expiry_dt

        except ClientError as e:
            logger.error(f"Signed URL generation error: {e}")
            return None

    def delete_image(self, s3_key: str) -> bool:
        """
        Delete image from S3.

        Args:
            s3_key: S3 object key

        Returns:
            Success status
        """
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            logger.info(f"Deleted image from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"S3 deletion error: {e}")
            return False

    def get_image_metadata(self, s3_key: str) -> Optional[dict]:
        """
        Get S3 object metadata.

        Args:
            s3_key: S3 object key

        Returns:
            Metadata dict or None if not found
        """
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=s3_key)
            return {
                "size_bytes": response.get("ContentLength", 0),
                "content_type": response.get("ContentType", "image/jpeg"),
                "last_modified": response.get("LastModified"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return None
            logger.error(f"Metadata retrieval error: {e}")
            return None


# ============================================================================
# Global Instance
# ============================================================================

_s3_service: Optional[S3StorageService] = None


def get_s3_service() -> S3StorageService:
    """Get or create global S3 service instance."""
    global _s3_service

    if _s3_service is None:
        _s3_service = S3StorageService()

    return _s3_service
