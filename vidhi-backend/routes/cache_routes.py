"""
Cache Management Routes
"""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from utils.cache import get_cache_stats, clear_all_caches, cleanup_all_caches
from middleware.auth_middleware import verify_token

router = APIRouter(prefix="/api/v1/cache", tags=["cache"])


@router.get("/stats")
async def get_stats(user: Dict = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get cache statistics.
    Requires authentication.
    """
    return {"success": True, "data": get_cache_stats()}


@router.post("/clear")
async def clear_cache(user: Dict = Depends(verify_token)) -> Dict[str, Any]:
    """
    Clear all caches.
    Requires authentication.
    """
    clear_all_caches()
    return {"success": True, "message": "All caches cleared"}


@router.post("/cleanup")
async def cleanup_cache(user: Dict = Depends(verify_token)) -> Dict[str, Any]:
    """
    Cleanup expired cache entries.
    Requires authentication.
    """
    cleanup_all_caches()
    return {"success": True, "message": "Expired cache entries cleaned up"}
