"""
Celery Tasks Package
Contains all background task definitions
"""

from .data_pipeline_tasks import (
    refresh_data_pipeline,
    scrape_india_code_acts,
    cleanup_old_tasks
)

from .document_tasks import (
    analyze_document,
    generate_document_summary
)

from .audio_tasks import (
    generate_audio_batch,
    cleanup_old_audio
)

__all__ = [
    "refresh_data_pipeline",
    "scrape_india_code_acts",
    "cleanup_old_tasks",
    "analyze_document",
    "generate_document_summary",
    "generate_audio_batch",
    "cleanup_old_audio",
]
