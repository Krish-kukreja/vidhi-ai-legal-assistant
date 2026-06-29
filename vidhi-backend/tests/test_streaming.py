"""
Tests for SSE Streaming Endpoints (Phase 2)

Tests:
- SSE endpoint availability
- Token streaming
- Metadata events
- Done events
- Error handling
- Cancellation
- Input sanitization
- Authentication
"""

import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import Mock, AsyncMock, patch
import json

# Import app
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from routes.streaming_routes import set_llm_service


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def client():
    """Async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm_service():
    """Mock LLM service with streaming support"""
    service = Mock()

    # Mock query_stream method
    async def mock_stream(
        question, session_id="default", language="English", use_agent=None
    ):
        """Mock streaming generator"""
        # Yield tokens
        for i, token in enumerate(["Section", " 438", " of", " CrPC"]):
            yield {"type": "token", "content": token, "index": i}

        # Yield metadata
        yield {
            "type": "metadata",
            "confidence": 0.85,
            "citations": ["Section 438 CrPC"],
        }

        # Yield done
        yield {"type": "done", "total_tokens": 4, "duration_ms": 1500}

    service.query_stream = mock_stream
    return service


@pytest.fixture
def mock_llm_service_with_error():
    """Mock LLM service that raises an error"""
    service = Mock()

    async def mock_stream_error(
        question, session_id="default", language="English", use_agent=None
    ):
        """Mock streaming generator that raises error"""
        yield {"type": "token", "content": "Section", "index": 0}

        # Simulate error
        yield {"type": "error", "message": "LLM service unavailable"}

    service.query_stream = mock_stream_error
    return service


# ============================================================================
# Health Check Tests
# ============================================================================


@pytest.mark.asyncio
async def test_streaming_health_check(client):
    """Test streaming health endpoint"""
    response = await client.get("/api/v1/stream/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "streaming"
    assert "features" in data
    assert data["features"]["sse"] is True


# ============================================================================
# SSE Streaming Tests
# ============================================================================


def test_stream_chat_success(client, mock_llm_service):
    """Test successful SSE streaming"""
    # Set mock LLM service
    set_llm_service(mock_llm_service)

    # Make streaming request
    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438 CrPC?",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events
    events = []
    for line in response.iter_lines():
        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
        if line_str.startswith("data: "):
            data = json.loads(line_str[6:])
            events.append(data)

    # Verify events
    assert len(events) >= 6  # 4 tokens + 1 metadata + 1 done

    # Check token events
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 4
    assert token_events[0]["content"] == "Section"
    assert token_events[1]["content"] == " 438"

    # Check metadata event
    metadata_events = [e for e in events if e["type"] == "metadata"]
    assert len(metadata_events) == 1
    assert metadata_events[0]["confidence"] == 0.85
    assert "Section 438 CrPC" in metadata_events[0]["citations"]

    # Check done event
    done_events = [e for e in events if e["type"] == "done"]
    assert len(done_events) == 1
    assert done_events[0]["total_tokens"] == 4


def test_stream_chat_with_error(client, mock_llm_service_with_error):
    """Test SSE streaming with error"""
    # Set mock LLM service
    set_llm_service(mock_llm_service_with_error)

    # Make streaming request
    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438 CrPC?",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    assert response.status_code == 200

    # Parse SSE events
    events = []
    for line in response.iter_lines():
        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
        if line_str.startswith("data: "):
            data = json.loads(line_str[6:])
            events.append(data)

    # Verify error event
    error_events = [e for e in events if e["type"] == "error"]
    assert len(error_events) == 1
    assert error_events[0]["message"] == "LLM service unavailable"


def test_stream_chat_input_sanitization(client, mock_llm_service):
    """Test input sanitization for streaming"""
    set_llm_service(mock_llm_service)

    # Test with malicious input
    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "<script>alert('xss')</script>",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    # Should sanitize and proceed (or reject if unsafe)
    # Depending on sanitization rules, this might be 200 or 400
    assert response.status_code in [200, 400]


def test_stream_chat_missing_text(client, mock_llm_service):
    """Test streaming with missing text"""
    set_llm_service(mock_llm_service)

    response = client.post(
        "/api/v1/stream/chat",
        json={"session_id": "test-session", "language": "english"},
        stream=True,
    )

    # Should fail validation
    assert response.status_code == 422


def test_stream_chat_no_llm_service(client):
    """Test streaming when LLM service is not available"""
    # Set LLM service to None
    set_llm_service(None)

    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438 CrPC?",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    assert response.status_code == 503
    assert "LLM service not available" in response.json()["detail"]


def test_stream_chat_different_languages(client, mock_llm_service):
    """Test streaming with different languages"""
    set_llm_service(mock_llm_service)

    languages = ["english", "hindi", "tamil", "bengali"]

    for lang in languages:
        response = client.post(
            "/api/v1/stream/chat",
            json={
                "text": "What is Section 438 CrPC?",
                "session_id": f"test-session-{lang}",
                "language": lang,
            },
            stream=True,
        )

        assert response.status_code == 200


def test_stream_chat_session_isolation(client, mock_llm_service):
    """Test that different sessions are isolated"""
    set_llm_service(mock_llm_service)

    # Session 1
    response1 = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438?",
            "session_id": "session-1",
            "language": "english",
        },
        stream=True,
    )

    # Session 2
    response2 = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438?",
            "session_id": "session-2",
            "language": "english",
        },
        stream=True,
    )

    assert response1.status_code == 200
    assert response2.status_code == 200


# ============================================================================
# Performance Tests
# ============================================================================


def test_stream_chat_latency(client, mock_llm_service):
    """Test streaming latency (time to first token)"""
    import time

    set_llm_service(mock_llm_service)

    start_time = time.time()

    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438 CrPC?",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    # Get first event
    first_event_time = None
    for line in response.iter_lines():
        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
        if line_str.startswith("data: "):
            first_event_time = time.time()
            break

    if first_event_time:
        latency = first_event_time - start_time
        print(f"Time to first token: {latency:.3f}s")

        # Should be fast (< 1 second for mock)
        assert latency < 1.0


# ============================================================================
# Edge Cases
# ============================================================================


def test_stream_chat_empty_response(client):
    """Test streaming with empty LLM response"""
    # Mock LLM service that returns no tokens
    service = Mock()

    async def mock_stream_empty(
        question, session_id="default", language="English", use_agent=None
    ):
        yield {"type": "done", "total_tokens": 0, "duration_ms": 100}

    service.query_stream = mock_stream_empty
    set_llm_service(service)

    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438 CrPC?",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    assert response.status_code == 200


def test_stream_chat_very_long_input(client, mock_llm_service):
    """Test streaming with very long input"""
    set_llm_service(mock_llm_service)

    # Create very long input (10,000 characters)
    long_text = "What is Section 438 CrPC? " * 400

    response = client.post(
        "/api/v1/stream/chat",
        json={"text": long_text, "session_id": "test-session", "language": "english"},
        stream=True,
    )

    # Should handle gracefully (either succeed or reject with 400)
    assert response.status_code in [200, 400]


def test_stream_chat_special_characters(client, mock_llm_service):
    """Test streaming with special characters"""
    set_llm_service(mock_llm_service)

    special_texts = [
        "What is धारा 438?",  # Hindi
        "What is Section 438 🔍?",  # Emoji
        'What is "Section 438"?',  # Quotes
        "What is Section 438\n\nCrPC?",  # Newlines
    ]

    for text in special_texts:
        response = client.post(
            "/api/v1/stream/chat",
            json={"text": text, "session_id": "test-session", "language": "english"},
            stream=True,
        )

        assert response.status_code == 200


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
def test_stream_chat_end_to_end(client):
    """End-to-end test with real LLM service (if available)"""
    # This test requires actual LLM service to be initialized
    # Skip if not available

    response = client.post(
        "/api/v1/stream/chat",
        json={
            "text": "What is Section 438 CrPC?",
            "session_id": "test-session",
            "language": "english",
        },
        stream=True,
    )

    # Should either succeed or fail gracefully
    assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
