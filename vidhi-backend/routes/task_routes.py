"""
Task Management API Routes
Provides endpoints for managing background tasks
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from celery.result import AsyncResult
from celery_app import celery_app
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


class TaskSubmitRequest(BaseModel):
    task_type: str
    args: Optional[List] = []
    kwargs: Optional[dict] = {}


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None
    progress: Optional[dict] = None


@router.post("/submit")
async def submit_task(request: TaskSubmitRequest):
    """
    Submit a background task

    Supported task types:
    - refresh_data_pipeline
    - scrape_india_code_acts
    - analyze_document
    - generate_document_summary
    - generate_audio_batch
    """
    try:
        # Map task type to task function
        task_map = {
            "refresh_data_pipeline": "tasks.data_pipeline_tasks.refresh_data_pipeline",
            "scrape_india_code_acts": "tasks.data_pipeline_tasks.scrape_india_code_acts",
            "analyze_document": "tasks.document_tasks.analyze_document",
            "generate_document_summary": "tasks.document_tasks.generate_document_summary",
            "generate_audio_batch": "tasks.audio_tasks.generate_audio_batch",
        }

        if request.task_type not in task_map:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task type. Supported: {list(task_map.keys())}",
            )

        task_name = task_map[request.task_type]

        # Submit task
        result = celery_app.send_task(
            task_name, args=request.args, kwargs=request.kwargs
        )

        logger.info(f"Task submitted: {result.id} ({request.task_type})")

        return {
            "status": "submitted",
            "task_id": result.id,
            "task_type": request.task_type,
        }

    except Exception as e:
        logger.error(f"Task submission error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get status of a background task

    Status values:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has been started
    - PROGRESS: Task is in progress (with progress info)
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed
    - RETRY: Task is being retried
    - REVOKED: Task was cancelled
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": result.state,
            "result": None,
            "error": None,
            "progress": None,
        }

        if result.state == "PENDING":
            response["result"] = {"message": "Task is waiting to be executed"}

        elif result.state == "STARTED":
            response["result"] = {"message": "Task has started"}

        elif result.state == "PROGRESS":
            response["progress"] = result.info

        elif result.state == "SUCCESS":
            response["result"] = result.result

        elif result.state == "FAILURE":
            response["error"] = str(result.info)

        elif result.state == "RETRY":
            response["result"] = {"message": "Task is being retried"}

        elif result.state == "REVOKED":
            response["result"] = {"message": "Task was cancelled"}

        return response

    except Exception as e:
        logger.error(f"Task status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str):
    """
    Cancel a running task

    Note: Task cancellation is best-effort. Tasks that are already
    executing may not stop immediately.
    """
    try:
        result = AsyncResult(task_id, app=celery_app)

        if result.state in ["SUCCESS", "FAILURE", "REVOKED"]:
            return {
                "status": "already_finished",
                "task_id": task_id,
                "current_state": result.state,
            }

        # Revoke task
        result.revoke(terminate=True, signal="SIGTERM")

        logger.info(f"Task cancelled: {task_id}")

        return {"status": "cancelled", "task_id": task_id}

    except Exception as e:
        logger.error(f"Task cancellation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active/list")
async def list_active_tasks():
    """
    List all active tasks

    Returns tasks that are currently running or pending
    """
    try:
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()

        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}

        all_tasks = []

        # Collect active tasks
        for worker, tasks in active.items():
            for task in tasks:
                all_tasks.append(
                    {
                        "task_id": task["id"],
                        "name": task["name"],
                        "status": "active",
                        "worker": worker,
                        "args": task.get("args", []),
                        "kwargs": task.get("kwargs", {}),
                    }
                )

        # Collect scheduled tasks
        for worker, tasks in scheduled.items():
            for task in tasks:
                all_tasks.append(
                    {
                        "task_id": task["request"]["id"],
                        "name": task["request"]["name"],
                        "status": "scheduled",
                        "worker": worker,
                    }
                )

        # Collect reserved tasks
        for worker, tasks in reserved.items():
            for task in tasks:
                all_tasks.append(
                    {
                        "task_id": task["id"],
                        "name": task["name"],
                        "status": "reserved",
                        "worker": worker,
                    }
                )

        return {"status": "success", "total": len(all_tasks), "tasks": all_tasks}

    except Exception as e:
        logger.error(f"List active tasks error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/workers")
async def get_worker_stats():
    """
    Get statistics about Celery workers
    """
    try:
        inspect = celery_app.control.inspect()

        stats = inspect.stats() or {}
        active = inspect.active() or {}

        workers = []
        for worker_name, worker_stats in stats.items():
            workers.append(
                {
                    "name": worker_name,
                    "status": "online",
                    "active_tasks": len(active.get(worker_name, [])),
                    "total_tasks": worker_stats.get("total", {}),
                }
            )

        return {"status": "success", "total_workers": len(workers), "workers": workers}

    except Exception as e:
        logger.error(f"Worker stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check if Celery workers are running
    """
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()

        if not stats:
            return {"status": "unhealthy", "message": "No workers available"}

        return {
            "status": "healthy",
            "workers": len(stats),
            "message": f"{len(stats)} worker(s) available",
        }

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}
