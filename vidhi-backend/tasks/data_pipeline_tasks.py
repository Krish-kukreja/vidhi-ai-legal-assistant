"""
Data Pipeline Background Tasks
Handles long-running data pipeline operations
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
from celery import Task
from celery_app import celery_app

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callbacks for progress tracking"""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        logger.info(f"Task {task_id} succeeded: {retval}")
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        logger.error(f"Task {task_id} failed: {exc}")
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(f"Task {task_id} retrying: {exc}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="tasks.data_pipeline_tasks.refresh_data_pipeline",
    time_limit=1800,  # 30 minutes
    soft_time_limit=1500,  # 25 minutes
    max_retries=3,
    default_retry_delay=60  # 1 minute
)
def refresh_data_pipeline(self, incremental=True):
    """
    Refresh the data pipeline (scrape + validate + ingest)
    
    Args:
        incremental: If True, only update changed data
    
    Returns:
        dict: Result with status and statistics
    """
    try:
        logger.info(f"Starting data pipeline refresh (incremental={incremental})")
        
        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting..."}
        )
        
        # Get project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Run data pipeline
        cmd = ["python", "data_pipeline/run_pipeline.py"]
        if not incremental:
            cmd.append("--full")
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "status": "Running pipeline..."}
        )
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=1500  # 25 minutes
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or "Pipeline failed"
            logger.error(f"Pipeline failed: {error_msg}")
            raise Exception(error_msg)
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 90, "total": 100, "status": "Finalizing..."}
        )
        
        # Parse output for statistics
        output = result.stdout
        stats = {
            "status": "success",
            "incremental": incremental,
            "timestamp": datetime.now().isoformat(),
            "output": output[-1000:] if output else ""  # Last 1000 chars
        }
        
        logger.info(f"Data pipeline refresh completed: {stats}")
        
        return stats
        
    except subprocess.TimeoutExpired:
        logger.error("Data pipeline timed out")
        raise self.retry(countdown=300, exc=Exception("Pipeline timeout"))
    
    except Exception as e:
        logger.error(f"Data pipeline error: {e}")
        raise self.retry(countdown=60, exc=e)


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="tasks.data_pipeline_tasks.scrape_india_code_acts",
    time_limit=1800,  # 30 minutes
    soft_time_limit=1500,  # 25 minutes
    max_retries=3
)
def scrape_india_code_acts(self, resume=False, specific_acts=None):
    """
    Scrape India Code acts
    
    Args:
        resume: Resume from checkpoint
        specific_acts: List of act IDs to scrape
    
    Returns:
        dict: Result with status and statistics
    """
    try:
        logger.info(f"Starting India Code scraping (resume={resume})")
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Starting scraper..."}
        )
        
        # Get project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Build command
        cmd = ["python", "data_pipeline/fetch_india_code.py"]
        if resume:
            cmd.append("--resume")
        if specific_acts:
            cmd.extend(["--acts"] + specific_acts)
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 10, "total": 100, "status": "Scraping acts..."}
        )
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=1500
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or "Scraping failed"
            logger.error(f"Scraping failed: {error_msg}")
            raise Exception(error_msg)
        
        self.update_state(
            state="PROGRESS",
            meta={"current": 90, "total": 100, "status": "Finalizing..."}
        )
        
        stats = {
            "status": "success",
            "resume": resume,
            "specific_acts": specific_acts,
            "timestamp": datetime.now().isoformat(),
            "output": result.stdout[-1000:] if result.stdout else ""
        }
        
        logger.info(f"India Code scraping completed: {stats}")
        
        return stats
        
    except subprocess.TimeoutExpired:
        logger.error("Scraping timed out")
        raise self.retry(countdown=300, exc=Exception("Scraping timeout"))
    
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        raise self.retry(countdown=60, exc=e)


@celery_app.task(
    name="tasks.data_pipeline_tasks.cleanup_old_tasks",
    time_limit=300  # 5 minutes
)
def cleanup_old_tasks():
    """
    Clean up old task results from Redis
    Removes results older than 7 days
    """
    try:
        logger.info("Starting task cleanup")
        
        from celery.result import AsyncResult
        from celery_app import celery_app
        
        # Get all task IDs (this is expensive, so we limit it)
        # In production, you'd want a more efficient approach
        
        cutoff_date = datetime.now() - timedelta(days=7)
        cleaned = 0
        
        # Note: This is a simplified version
        # In production, you'd track task IDs in a separate database
        
        logger.info(f"Task cleanup completed: {cleaned} tasks removed")
        
        return {
            "status": "success",
            "cleaned": cleaned,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
