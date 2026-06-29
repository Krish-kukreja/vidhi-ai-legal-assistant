"""
CDN Management API Routes
Provides endpoints for CDN cache management
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from services.cdn_service import CDNService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/cdn", tags=["cdn"])

# Initialize CDN service
cdn_service = CDNService()


class InvalidateRequest(BaseModel):
    paths: List[str]


class InvalidateResponse(BaseModel):
    success: bool
    invalidation_id: str = None
    status: str = None
    paths: List[str] = None
    error: str = None


class InvalidationStatusResponse(BaseModel):
    success: bool
    invalidation_id: str = None
    status: str = None
    create_time: str = None
    error: str = None


class DistributionInfoResponse(BaseModel):
    enabled: bool
    distribution_id: str = None
    distribution_domain: str = None
    region: str = None
    message: str = None


@router.post("/invalidate", response_model=InvalidateResponse)
async def invalidate_cache(request: InvalidateRequest):
    """
    Create CloudFront cache invalidation

    Requires admin authentication (handled by auth middleware)

    Example:
    ```json
    {
        "paths": ["/audio/file1.mp3", "/audio/*"]
    }
    ```
    """
    try:
        if not cdn_service.is_enabled():
            raise HTTPException(status_code=503, detail="CDN service not enabled")

        if not request.paths:
            raise HTTPException(status_code=400, detail="No paths provided")

        # Limit to 100 paths per request (CloudFront limit is 3000 per batch)
        if len(request.paths) > 100:
            raise HTTPException(
                status_code=400, detail="Maximum 100 paths per invalidation request"
            )

        result = cdn_service.invalidate_cache(request.paths)

        if not result["success"]:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Invalidation failed")
            )

        return InvalidateResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in invalidate_cache endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/invalidation/{invalidation_id}", response_model=InvalidationStatusResponse
)
async def get_invalidation_status(invalidation_id: str):
    """
    Get status of a CloudFront invalidation

    Status values:
    - InProgress: Invalidation is in progress
    - Completed: Invalidation completed successfully
    """
    try:
        if not cdn_service.is_enabled():
            raise HTTPException(status_code=503, detail="CDN service not enabled")

        result = cdn_service.get_invalidation_status(invalidation_id)

        if not result["success"]:
            raise HTTPException(
                status_code=404, detail=result.get("error", "Invalidation not found")
            )

        return InvalidationStatusResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_invalidation_status endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info", response_model=DistributionInfoResponse)
async def get_distribution_info():
    """
    Get CloudFront distribution information
    """
    try:
        info = cdn_service.get_distribution_info()
        return DistributionInfoResponse(**info)

    except Exception as e:
        logger.error(f"Error in get_distribution_info endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def cdn_health_check():
    """
    Check CDN service health
    """
    try:
        is_enabled = cdn_service.is_enabled()

        if is_enabled:
            return {
                "status": "healthy",
                "cdn_enabled": True,
                "distribution_id": cdn_service.distribution_id,
            }
        else:
            return {
                "status": "disabled",
                "cdn_enabled": False,
                "message": "CDN not configured, using direct S3 URLs",
            }

    except Exception as e:
        logger.error(f"Error in cdn_health_check endpoint: {e}")
        return {"status": "unhealthy", "error": str(e)}
