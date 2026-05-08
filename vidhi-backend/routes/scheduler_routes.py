"""
Data Refresh Scheduler Routes
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from typing import Dict, Any
from utils.scheduler import trigger_refresh, get_scheduler_status
from middleware.auth_middleware import verify_token

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])


@router.get("/status")
async def get_status(user: Dict = Depends(verify_token)) -> Dict[str, Any]:
    """
    Get scheduler status and refresh history.
    Requires authentication.
    """
    return {
        "success": True,
        "data": get_scheduler_status()
    }


@router.post("/refresh")
async def manual_refresh(
    background_tasks: BackgroundTasks,
    refresh_type: str = "incremental",
    user: Dict = Depends(verify_token)
) -> Dict[str, Any]:
    """
    Manually trigger a data refresh.
    
    Args:
        refresh_type: "incremental" or "full"
    
    Requires authentication.
    """
    if refresh_type not in ["incremental", "full"]:
        return {
            "success": False,
            "error": "Invalid refresh_type. Must be 'incremental' or 'full'"
        }
    
    # Run refresh in background
    background_tasks.add_task(trigger_refresh, refresh_type)
    
    return {
        "success": True,
        "message": f"{refresh_type.capitalize()} refresh triggered in background"
    }
