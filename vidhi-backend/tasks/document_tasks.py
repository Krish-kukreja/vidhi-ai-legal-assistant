"""
Document Processing Background Tasks
Handles long-running document analysis operations
"""

import logging
from datetime import datetime
from celery import Task
from celery_app import celery_app

logger = logging.getLogger(__name__)


class CallbackTask(Task):
    """Base task with callbacks"""

    def on_success(self, retval, task_id, args, kwargs):
        logger.info(f"Task {task_id} succeeded")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error(f"Task {task_id} failed: {exc}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="tasks.document_tasks.analyze_document",
    time_limit=300,  # 5 minutes
    soft_time_limit=240,  # 4 minutes
    max_retries=3,
)
def analyze_document(self, document_text, document_type, language="english"):
    """
    Analyze a document (long-running operation)

    Args:
        document_text: Document content
        document_type: Type of document
        language: Language for analysis

    Returns:
        dict: Analysis results
    """
    try:
        logger.info(f"Starting document analysis (type={document_type})")

        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Analyzing..."},
        )

        # Import here to avoid circular dependencies
        from services.document_education import document_education_service

        self.update_state(
            state="PROGRESS",
            meta={"current": 30, "total": 100, "status": "Processing..."},
        )

        # Perform analysis
        result = document_education_service.simplify_document(
            document_text=document_text, document_type=document_type, language=language
        )

        self.update_state(
            state="PROGRESS",
            meta={"current": 90, "total": 100, "status": "Finalizing..."},
        )

        return {
            "status": "success",
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Document analysis error: {e}")
        raise self.retry(countdown=30, exc=e)


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name="tasks.document_tasks.generate_document_summary",
    time_limit=180,  # 3 minutes
    max_retries=3,
)
def generate_document_summary(self, document_text, max_length=500):
    """
    Generate document summary

    Args:
        document_text: Document content
        max_length: Maximum summary length

    Returns:
        dict: Summary result
    """
    try:
        logger.info("Starting document summary generation")

        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": 100, "status": "Generating summary..."},
        )

        # Simple summary generation (you can enhance this)
        words = document_text.split()
        summary = " ".join(words[:max_length])

        if len(words) > max_length:
            summary += "..."

        return {
            "status": "success",
            "summary": summary,
            "original_length": len(words),
            "summary_length": min(len(words), max_length),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        raise self.retry(countdown=30, exc=e)
