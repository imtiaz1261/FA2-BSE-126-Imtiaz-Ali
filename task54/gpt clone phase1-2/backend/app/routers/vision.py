"""
FastAPI routes for Image Understanding (Vision) module.

Endpoints:
- POST /chat/vision/upload - Upload images
- POST /chat/vision - Answer questions about images
- POST /chat/vision/extract - Extract structured data from images
- GET /chat/vision/{request_id} - Get vision request status
- DELETE /chat/vision/images/{image_id} - Delete image
"""

import io
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Message, User, VisionImage, VisionRequest
from app.schemas_vision import (
    ExtractionResult,
    ImageErrorDetail,
    ImageMetadata,
    ImageUploadResponse,
    ImageValidationError,
    VisionExtractionRequest,
    VisionQARequest,
    VisionQAResponse,
    VisionRequestStatus,
)
from app.services.s3_storage import get_s3_service
from app.services.vision_llm import get_vision_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/vision", tags=["vision"])


# ============================================================================
# Image Upload Endpoint
# ============================================================================


@router.post("/upload", response_model=list[ImageUploadResponse])
async def upload_images(
    files: list[UploadFile] = File(...),
    conversation_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload one or more images for vision processing.

    Validates file type and size, stores in S3, returns signed URLs.

    Args:
        files: Image files to upload
        conversation_id: Optional conversation to associate
        db: Database session
        current_user: Authenticated user

    Returns:
        List of uploaded image metadata with signed URLs
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum 10 images per request",
        )

    s3_service = get_s3_service()
    uploaded_images = []
    errors = []

    for idx, file in enumerate(files):
        try:
            # Read file
            file_data = await file.read()

            if not file_data:
                errors.append(
                    ImageErrorDetail(
                        image_index=idx,
                        filename=file.filename or "unknown",
                        error_code="empty_file",
                        error_message="File is empty",
                    )
                )
                continue

            # Validate image
            is_valid, error_msg, metadata = s3_service.validate_image(
                file_data, file.filename or "image.jpg"
            )

            if not is_valid:
                errors.append(
                    ImageErrorDetail(
                        image_index=idx,
                        filename=file.filename or "unknown",
                        error_code=(
                            "unsupported_format"
                            if "format" in error_msg.lower()
                            else "file_too_large"
                            if "size" in error_msg.lower()
                            else "invalid_image"
                        ),
                        error_message=error_msg,
                    )
                )
                continue

            # Upload to S3
            upload_result = s3_service.upload_image(
                file_data,
                file.filename or "image.jpg",
                str(current_user.id),
                content_type=file.content_type or "image/jpeg",
            )

            if not upload_result:
                errors.append(
                    ImageErrorDetail(
                        image_index=idx,
                        filename=file.filename or "unknown",
                        error_code="upload_failed",
                        error_message="Failed to upload to storage",
                    )
                )
                continue

            s3_key, expiry_dt = upload_result

            # Generate signed URL
            url_result = s3_service.generate_signed_url(s3_key)

            if not url_result:
                errors.append(
                    ImageErrorDetail(
                        image_index=idx,
                        filename=file.filename or "unknown",
                        error_code="url_generation_failed",
                        error_message="Failed to generate access URL",
                    )
                )
                continue

            signed_url, url_expiry = url_result

            # Create database record
            image_id = uuid.uuid4()
            conversation_uuid = None
            if conversation_id:
                try:
                    conversation_uuid = uuid.UUID(conversation_id)
                except ValueError:
                    pass

            vision_image = VisionImage(
                id=image_id,
                user_id=current_user.id,
                conversation_id=conversation_uuid,
                filename=file.filename or "image.jpg",
                file_type=metadata.get("format", "JPEG").lower(),
                file_size_bytes=len(file_data),
                s3_key=s3_key,
                signed_url=signed_url,
                signed_url_expires_at=url_expiry,
                metadata=metadata,
            )

            db.add(vision_image)
            await db.flush()

            uploaded_images.append(
                ImageUploadResponse(
                    image_id=image_id,
                    filename=file.filename or "image.jpg",
                    file_type=metadata.get("format", "JPEG").lower(),
                    file_size_bytes=len(file_data),
                    signed_url=signed_url,
                    signed_url_expires_at=url_expiry,
                    metadata=metadata,
                )
            )

            logger.info(
                f"Uploaded image: {file.filename}, user={current_user.id}, "
                f"size={len(file_data)}"
            )

        except Exception as e:
            logger.error(f"Image upload error: {e}")
            errors.append(
                ImageErrorDetail(
                    image_index=idx,
                    filename=file.filename or "unknown",
                    error_code="processing_error",
                    error_message=str(e),
                )
            )

    # Commit successful uploads
    await db.commit()

    # Return uploaded images or error if all failed
    if not uploaded_images and errors:
        raise HTTPException(
            status_code=400,
            detail=ImageValidationError(errors=errors).model_dump(),
        )

    return uploaded_images


# ============================================================================
# Vision Q&A Endpoint
# ============================================================================


@router.post("/qa", response_model=VisionQAResponse)
async def vision_qa(
    request: VisionQARequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Answer a question about one or more images.

    Args:
        request: Image IDs and question
        db: Database session
        current_user: Authenticated user

    Returns:
        Answer generated by vision LLM
    """
    try:
        # Fetch images
        result = await db.execute(
            select(VisionImage).where(VisionImage.id.in_(request.image_ids))
        )
        images = result.scalars().all()

        if len(images) != len(request.image_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more images not found",
            )

        # Verify user owns images
        for img in images:
            if img.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized access to image",
                )

        # Get signed URLs
        image_urls = [img.signed_url for img in images]

        # Call vision LLM
        vision_service = get_vision_service()
        answer = vision_service.understand_image(
            image_urls, request.question
        )

        if not answer:
            raise HTTPException(
                status_code=500,
                detail="Vision LLM processing failed",
            )

        # Store request in database
        request_id = uuid.uuid4()
        vision_request = VisionRequest(
            id=request_id,
            user_id=current_user.id,
            conversation_id=request.conversation_id or uuid.uuid4(),
            request_type="qa",
            prompt=request.question,
            response=answer,
            status="completed",
            image_ids=[str(img_id) for img_id in request.image_ids],
        )

        db.add(vision_request)
        await db.commit()

        logger.info(
            f"Vision Q&A: user={current_user.id}, "
            f"images={len(images)}, status=completed"
        )

        return VisionQAResponse(
            request_id=request_id,
            answer=answer,
            images_processed=request.image_ids,
            created_at=vision_request.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision Q&A error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process images",
        )


# ============================================================================
# Vision Extraction Endpoint
# ============================================================================


@router.post("/extract", response_model=ExtractionResult)
async def vision_extract(
    request: VisionExtractionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Extract structured data from image(s).

    Args:
        request: Images and extraction parameters
        db: Database session
        current_user: Authenticated user

    Returns:
        Extracted data as structured JSON
    """
    try:
        # Fetch images
        result = await db.execute(
            select(VisionImage).where(VisionImage.id.in_(request.image_ids))
        )
        images = result.scalars().all()

        if len(images) != len(request.image_ids):
            raise HTTPException(
                status_code=404,
                detail="One or more images not found",
            )

        # Verify user owns images
        for img in images:
            if img.user_id != current_user.id:
                raise HTTPException(
                    status_code=403,
                    detail="Unauthorized access to image",
                )

        # Get signed URLs
        image_urls = [img.signed_url for img in images]

        # Call vision LLM for extraction
        vision_service = get_vision_service()
        extracted_data = vision_service.extract_structured_data(
            image_urls,
            request.extraction_type,
            request.custom_schema,
            max_retries=1,
        )

        if extracted_data is None:
            raise HTTPException(
                status_code=500,
                detail="Extraction failed - could not parse structured response",
            )

        # Store request in database
        request_id = uuid.uuid4()
        vision_request = VisionRequest(
            id=request_id,
            user_id=current_user.id,
            conversation_id=request.conversation_id or uuid.uuid4(),
            request_type="extract",
            prompt=f"Extract {request.extraction_type}",
            extraction_schema=request.custom_schema,
            extraction_result=extracted_data,
            status="completed",
            image_ids=[str(img_id) for img_id in request.image_ids],
        )

        db.add(vision_request)
        await db.commit()

        logger.info(
            f"Vision extraction: user={current_user.id}, "
            f"type={request.extraction_type}, status=completed"
        )

        return ExtractionResult(
            request_id=request_id,
            extraction_type=request.extraction_type,
            data=extracted_data,
            images_processed=request.image_ids,
            created_at=vision_request.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to extract data from images",
        )


# ============================================================================
# Get Request Status
# ============================================================================


@router.get("/{request_id}", response_model=VisionRequestStatus)
async def get_vision_status(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get status of a vision request.

    Args:
        request_id: Vision request ID
        db: Database session
        current_user: Authenticated user

    Returns:
        Request status and results
    """
    try:
        request_uuid = uuid.UUID(request_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request ID")

    try:
        result = await db.execute(
            select(VisionRequest).where(VisionRequest.id == request_uuid)
        )
        vision_request = result.scalar_one_or_none()

        if not vision_request:
            raise HTTPException(status_code=404, detail="Request not found")

        if vision_request.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized",
            )

        # Convert image_ids from JSON strings to UUIDs
        image_ids = [uuid.UUID(id_str) for id_str in vision_request.image_ids]

        return VisionRequestStatus(
            request_id=vision_request.id,
            status=vision_request.status,
            request_type=vision_request.request_type,
            response=vision_request.response,
            extraction_result=vision_request.extraction_result,
            error_message=vision_request.error_message,
            images_used=image_ids,
            created_at=vision_request.created_at,
            updated_at=vision_request.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get status")


# ============================================================================
# Delete Image
# ============================================================================


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete an uploaded image.

    Args:
        image_id: Image to delete
        db: Database session
        current_user: Authenticated user

    Returns:
        Success response
    """
    try:
        image_uuid = uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid image ID")

    try:
        result = await db.execute(
            select(VisionImage).where(VisionImage.id == image_uuid)
        )
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        if image.user_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorized",
            )

        # Delete from S3
        s3_service = get_s3_service()
        s3_service.delete_image(image.s3_key)

        # Delete from database
        await db.delete(image)
        await db.commit()

        logger.info(f"Deleted image: {image_id}, user={current_user.id}")

        return {"message": "Image deleted", "image_id": str(image_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete image error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete image",
        )
