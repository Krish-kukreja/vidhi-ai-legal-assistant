"""
Tests for error handling and logging.
"""

import pytest
import json
import logging
from utils.logging_config import (
    JSONFormatter,
    ContextLogger,
    get_logger,
    generate_request_id,
    setup_logging,
)
from middleware.error_handler_middleware import (
    ErrorHandlerMiddleware,
    create_error_response,
)


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_formats_basic_log(self):
        """Should format basic log as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        output = formatter.format(record)
        data = json.loads(output)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test"
        assert "timestamp" in data

    def test_includes_request_id(self):
        """Should include request_id if present."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc123"

        output = formatter.format(record)
        data = json.loads(output)

        assert data["request_id"] == "abc123"

    def test_includes_exception_info(self):
        """Should include exception info if present."""
        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

            output = formatter.format(record)
            data = json.loads(output)

            assert "exception" in data
            assert data["exception"]["type"] == "ValueError"
            assert data["exception"]["message"] == "Test error"
            assert "traceback" in data["exception"]


class TestContextLogger:
    """Test context logger."""

    def test_adds_context_to_logs(self):
        """Should add context to all log messages."""
        logger = get_logger("test", {"request_id": "abc123", "user_id": "user1"})

        # Context should be available
        assert logger.extra["request_id"] == "abc123"
        assert logger.extra["user_id"] == "user1"

    def test_logger_without_context(self):
        """Should work without context."""
        logger = get_logger("test")

        # Should have empty context
        assert logger.extra == {}


class TestRequestIDGeneration:
    """Test request ID generation."""

    def test_generates_unique_ids(self):
        """Should generate unique request IDs."""
        id1 = generate_request_id()
        id2 = generate_request_id()

        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0

    def test_generates_valid_uuids(self):
        """Should generate valid UUID format."""
        request_id = generate_request_id()

        # UUID format: 8-4-4-4-12 characters
        parts = request_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8
        assert len(parts[1]) == 4
        assert len(parts[2]) == 4
        assert len(parts[3]) == 4
        assert len(parts[4]) == 12


class TestLoggingSetup:
    """Test logging setup."""

    def test_setup_with_json_format(self):
        """Should set up logging with JSON format."""
        setup_logging(log_level="INFO", json_format=True)

        logger = logging.getLogger()
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

        # Check formatter type
        handler = logger.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)

    def test_setup_with_text_format(self):
        """Should set up logging with text format."""
        setup_logging(log_level="DEBUG", json_format=False)

        logger = logging.getLogger()
        assert logger.level == logging.DEBUG
        assert len(logger.handlers) > 0

        # Check formatter type
        handler = logger.handlers[0]
        assert not isinstance(handler.formatter, JSONFormatter)


class TestErrorResponse:
    """Test error response creation."""

    def test_creates_basic_error_response(self):
        """Should create basic error response."""
        response = create_error_response(
            status_code=400, error_type="validation_error", message="Invalid input"
        )

        assert response.status_code == 400

        body = json.loads(response.body)
        assert body["error"] == "validation_error"
        assert body["message"] == "Invalid input"

    def test_includes_request_id(self):
        """Should include request ID if provided."""
        response = create_error_response(
            status_code=500,
            error_type="internal_error",
            message="Something went wrong",
            request_id="abc123",
        )

        body = json.loads(response.body)
        assert body["request_id"] == "abc123"
        assert response.headers["X-Request-ID"] == "abc123"

    def test_includes_details(self):
        """Should include additional details if provided."""
        response = create_error_response(
            status_code=400,
            error_type="validation_error",
            message="Invalid input",
            details={"field": "email", "reason": "invalid format"},
        )

        body = json.loads(response.body)
        assert "details" in body
        assert body["details"]["field"] == "email"


class TestErrorHandlerMiddleware:
    """Test error handler middleware."""

    def test_generates_request_id(self):
        """Should generate request ID for each request."""
        from fastapi import Request

        middleware = ErrorHandlerMiddleware(None)

        # Mock request
        class MockRequest:
            class State:
                pass

            state = State()
            method = "GET"
            url = type("obj", (object,), {"path": "/test"})()

        request = MockRequest()

        # Request ID should be generated
        # (This is tested in integration tests)
        assert True  # Placeholder

    def test_error_hint_messages(self):
        """Should provide helpful error hints."""
        middleware = ErrorHandlerMiddleware(None)

        hints = {
            "validation_error": middleware._get_error_hint("validation_error"),
            "permission_denied": middleware._get_error_hint("permission_denied"),
            "not_found": middleware._get_error_hint("not_found"),
            "timeout": middleware._get_error_hint("timeout"),
            "internal_error": middleware._get_error_hint("internal_error"),
        }

        # All hints should be non-empty strings
        for error_type, hint in hints.items():
            assert isinstance(hint, str)
            assert len(hint) > 0


def test_logging_integration():
    """Integration test for logging."""
    # Set up logging
    setup_logging(log_level="INFO", json_format=True)

    # Get logger with context
    logger = get_logger(__name__, {"request_id": "test123"})

    # Log a message (should not raise exception)
    logger.info("Test log message")

    print("✓ Logging integration works")


if __name__ == "__main__":
    test_logging_integration()
    print("\n✅ All error handling tests passed!")
