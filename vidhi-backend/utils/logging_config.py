"""
Structured logging configuration for VIDHI backend.

Provides JSON-formatted logs with request tracking and context.
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Any, Dict
import uuid


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format.

    Makes logs easier to parse and aggregate in production.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        # Add user ID if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        # Add endpoint if available
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Add extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return json.dumps(log_data)


class ContextLogger(logging.LoggerAdapter):
    """
    Logger adapter that adds context to all log messages.

    Automatically includes request_id, user_id, etc. in logs.
    """

    def process(self, msg, kwargs):
        """Add context to log message."""
        # Add context from extra dict
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Merge adapter context with log context
        for key, value in self.extra.items():
            if key not in kwargs["extra"]:
                kwargs["extra"][key] = value

        return msg, kwargs


def setup_logging(log_level: str = "INFO", json_format: bool = True):
    """
    Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON format (True) or plain text (False)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))

    # Set formatter
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)


def get_logger(name: str, context: Dict[str, Any] = None) -> ContextLogger:
    """
    Get a logger with optional context.

    Args:
        name: Logger name (usually __name__)
        context: Optional context dict (request_id, user_id, etc.)

    Returns:
        ContextLogger instance
    """
    logger = logging.getLogger(name)

    if context:
        return ContextLogger(logger, context)

    return ContextLogger(logger, {})


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


# Example usage:
# logger = get_logger(__name__, {"request_id": "abc123", "user_id": "user@example.com"})
# logger.info("Processing request")
# Output: {"timestamp": "2026-05-06T10:30:00Z", "level": "INFO", "message": "Processing request", "request_id": "abc123", "user_id": "user@example.com"}
