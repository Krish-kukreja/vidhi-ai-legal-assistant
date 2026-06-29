"""
Audio Processing Background Tasks
Handles batch audio generation and cleanup
"""

import os
import logging
from datetime import datetime, timedelta
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
    name="tasks.audio_tasks.generate_audio_batch",
    time_limit=600,  # 10 minutes
    max_retries=3,
)
def generate_audio_batch(self, texts, language_code="en-IN"):
    """
    Generate audio for multiple texts in batch

    Args:
        texts: List of text strings
        language_code: Language code for TTS

    Returns:
        dict: Results with audio URLs
    """
    try:
        logger.info(f"Starting batch audio generation ({len(texts)} texts)")

        self.update_state(
            state="PROGRESS",
            meta={"current": 0, "total": len(texts), "status": "Generating audio..."},
        )

        # Import here to avoid circular dependencies
        from speech.aws_polly import CachedPollyService, AWSPollyService
        from configs import config

        # Initialize Polly service
        polly_service = AWSPollyService(region=config.AWS_REGION)
        cached_polly = CachedPollyService(polly_service, config.S3_BUCKET_AUDIO)

        results = []
        for i, text in enumerate(texts):
            try:
                result = cached_polly.get_or_create_audio(text, language_code)
                results.append(
                    {
                        "text": text[:50] + "..." if len(text) > 50 else text,
                        "success": result["success"],
                        "audio_url": result.get("audio_url"),
                        "error": result.get("error"),
                    }
                )

                self.update_state(
                    state="PROGRESS",
                    meta={
                        "current": i + 1,
                        "total": len(texts),
                        "status": f"Generated {i + 1}/{len(texts)}",
                    },
                )

            except Exception as e:
                logger.error(f"Audio generation failed for text {i}: {e}")
                results.append(
                    {
                        "text": text[:50] + "..." if len(text) > 50 else text,
                        "success": False,
                        "error": str(e),
                    }
                )

        success_count = sum(1 for r in results if r["success"])

        return {
            "status": "success",
            "total": len(texts),
            "successful": success_count,
            "failed": len(texts) - success_count,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Batch audio generation error: {e}")
        raise self.retry(countdown=60, exc=e)


@celery_app.task(
    name="tasks.audio_tasks.cleanup_old_audio", time_limit=600  # 10 minutes
)
def cleanup_old_audio(days=30):
    """
    Clean up old audio files from S3

    Args:
        days: Delete files older than this many days

    Returns:
        dict: Cleanup statistics
    """
    try:
        logger.info(f"Starting audio cleanup (older than {days} days)")

        import boto3
        from configs import config

        s3 = boto3.client(
            "s3",
            region_name=config.AWS_REGION,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )

        bucket = config.S3_BUCKET_AUDIO
        cutoff_date = datetime.now() - timedelta(days=days)

        # List objects
        paginator = s3.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=bucket, Prefix="audio/")

        deleted = 0
        errors = 0

        for page in pages:
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                # Check if file is old enough
                if obj["LastModified"].replace(tzinfo=None) < cutoff_date:
                    try:
                        s3.delete_object(Bucket=bucket, Key=obj["Key"])
                        deleted += 1
                        logger.info(f"Deleted old audio: {obj['Key']}")
                    except Exception as e:
                        logger.error(f"Failed to delete {obj['Key']}: {e}")
                        errors += 1

        logger.info(f"Audio cleanup completed: {deleted} deleted, {errors} errors")

        return {
            "status": "success",
            "deleted": deleted,
            "errors": errors,
            "cutoff_date": cutoff_date.isoformat(),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Audio cleanup error: {e}")
        return {"status": "error", "error": str(e)}
