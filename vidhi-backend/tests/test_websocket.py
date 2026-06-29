"""
Tests for WebSocket Voice Streaming
"""

import pytest
import json
import base64
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio

from app import app
from routes.websocket_routes import set_services


# Mock services
class MockLLMService:
    """Mock LLM service for testing"""

    async def query_stream(self, question, session_id="default", language="English"):
        """Mock streaming query"""
        # Simulate token streaming
        tokens = ["Section", " 438", " CrPC", " allows", " anticipatory", " bail"]
        for i, token in enumerate(tokens):
            yield {"type": "token", "content": token, "index": i}

        # Send metadata
        yield {
            "type": "metadata",
            "confidence": 0.85,
            "citations": ["Section 438 CrPC"],
        }

        # Send done
        yield {"type": "done", "total_tokens": len(tokens)}


class MockTranscribeService:
    """Mock AWS Transcribe service"""

    def __init__(self):
        self.s3_bucket = "test-bucket"

    def upload_audio_to_s3(self, audio_data, bucket, key):
        """Mock S3 upload"""
        return f"s3://{bucket}/{key}"

    def transcribe_audio(
        self, s3_uri, language_code, identify_language=False, media_format="webm"
    ):
        """Mock transcription"""
        return {
            "success": True,
            "transcript": "What is Section 438 CrPC?",
            "language_code": language_code,
            "confidence": 0.95,
        }


class MockPollyService:
    """Mock AWS Polly service"""

    def get_or_create_audio(self, text, language_code):
        """Mock TTS"""
        return {
            "success": True,
            "audio_url": "https://test-bucket.s3.amazonaws.com/test-audio.mp3",
            "cached": False,
        }


# Initialize mock services at module level
llm_service = MockLLMService()
transcribe_service = MockTranscribeService()
polly_service = MockPollyService()

# Set services for WebSocket routes
set_services(llm_service, transcribe_service, polly_service)

# Create test client at module level
client = TestClient(app)


@pytest.fixture
def mock_services():
    """Setup mock services"""
    # Services already set at module level
    yield {"llm": llm_service, "transcribe": transcribe_service, "polly": polly_service}


# ============================================================================
# WebSocket Connection Tests
# ============================================================================


def test_websocket_health():
    """Test WebSocket health endpoint"""
    response = client.get("/api/v1/ws/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "websocket"
    assert "active_connections" in data
    assert "features" in data


def test_websocket_connection_without_init(mock_services):
    """Test WebSocket connection without session initialization"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Send invalid first message
        websocket.send_json({"type": "audio_chunk", "data": "invalid"})

        # Should receive error
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "First message must be start_session" in response["message"]


def test_websocket_session_start(mock_services):
    """Test WebSocket session initialization"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Send session start
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
                "language_code": "en-IN",
            }
        )

        # Should receive confirmation
        response = websocket.receive_json()
        assert response["type"] == "session_started"
        assert response["session_id"] == "test-session"
        assert response["language"] == "english"


def test_websocket_input_sanitization(mock_services):
    """Test input sanitization in WebSocket"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Send malicious session ID
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "<script>alert('xss')</script>",
                "language": "english",
            }
        )

        # Should receive error or sanitized session
        response = websocket.receive_json()
        # Either error or sanitized session_id
        if response["type"] == "error":
            assert "Invalid input" in response["message"]
        else:
            assert "<script>" not in response["session_id"]


# ============================================================================
# Audio Streaming Tests
# ============================================================================


def test_websocket_audio_chunk_received(mock_services):
    """Test audio chunk acknowledgment"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
            }
        )
        websocket.receive_json()  # session_started

        # Send audio chunk
        audio_data = b"fake audio data"
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        websocket.send_json(
            {"type": "audio_chunk", "data": audio_b64, "format": "webm"}
        )

        # Should receive acknowledgment
        response = websocket.receive_json()
        assert response["type"] == "chunk_received"
        assert response["size"] == len(audio_data)


def test_websocket_audio_complete_no_data(mock_services):
    """Test audio complete without data"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
            }
        )
        websocket.receive_json()

        # Send audio complete without sending chunks
        websocket.send_json({"type": "audio_complete", "format": "webm"})

        # Should receive error
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "No audio data" in response["message"]


@pytest.mark.asyncio
async def test_websocket_full_voice_pipeline(mock_services):
    """Test complete voice processing pipeline"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
                "language_code": "en-IN",
            }
        )

        response = websocket.receive_json()
        assert response["type"] == "session_started"

        # Send audio chunk
        audio_data = b"fake audio data for transcription"
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        websocket.send_json(
            {"type": "audio_chunk", "data": audio_b64, "format": "webm"}
        )

        # Receive acknowledgment
        response = websocket.receive_json()
        assert response["type"] == "chunk_received"

        # Send audio complete
        websocket.send_json({"type": "audio_complete", "format": "webm"})

        # Collect all responses
        responses = []
        while True:
            try:
                response = websocket.receive_json(timeout=5)
                responses.append(response)

                if response["type"] == "done":
                    break
            except:
                break

        # Verify pipeline stages
        response_types = [r["type"] for r in responses]

        # Should have: status, transcription, llm_tokens, audio_url, done
        assert "status" in response_types  # "Transcribing audio..."
        assert "transcription" in response_types
        assert "llm_token" in response_types
        assert "done" in response_types

        # Verify transcription
        transcription = next(r for r in responses if r["type"] == "transcription")
        assert transcription["text"] == "What is Section 438 CrPC?"
        assert transcription["is_final"] == True

        # Verify done message
        done = next(r for r in responses if r["type"] == "done")
        assert "duration_ms" in done
        assert "transcript" in done
        assert "response" in done


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_websocket_unknown_message_type(mock_services):
    """Test handling of unknown message types"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
            }
        )
        websocket.receive_json()

        # Send unknown message type
        websocket.send_json({"type": "unknown_type", "data": "test"})

        # Should receive error
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Unknown message type" in response["message"]


def test_websocket_invalid_json(mock_services):
    """Test handling of invalid JSON"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
            }
        )
        websocket.receive_json()

        # Send invalid JSON (send text instead of JSON)
        websocket.send_text("invalid json {")

        # Should receive error
        response = websocket.receive_json()
        assert response["type"] == "error"
        assert "Invalid JSON" in response["message"]


def test_websocket_session_end(mock_services):
    """Test session termination"""
    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
            }
        )
        websocket.receive_json()

        # End session
        websocket.send_json({"type": "end_session"})

        # Should receive confirmation
        response = websocket.receive_json()
        assert response["type"] == "session_ended"
        assert response["session_id"] == "test-session"


# ============================================================================
# Service Availability Tests
# ============================================================================


def test_websocket_without_transcribe_service():
    """Test WebSocket when transcribe service is unavailable"""
    # Set services with None transcribe
    set_services(MockLLMService(), None, MockPollyService())

    try:
        with client.websocket_connect("/api/v1/ws/voice") as websocket:
            # Initialize session
            websocket.send_json(
                {
                    "type": "start_session",
                    "session_id": "test-session",
                    "language": "english",
                }
            )
            websocket.receive_json()

            # Send audio
            audio_b64 = base64.b64encode(b"test audio").decode("utf-8")
            websocket.send_json({"type": "audio_chunk", "data": audio_b64})
            websocket.receive_json()

            websocket.send_json({"type": "audio_complete"})

            # Should receive error about transcription service
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Transcription service not available" in response["message"]
    finally:
        set_services(None, None, None)


def test_websocket_without_llm_service():
    """Test WebSocket when LLM service is unavailable"""
    # Set services with None LLM
    set_services(None, MockTranscribeService(), MockPollyService())

    try:
        with client.websocket_connect("/api/v1/ws/voice") as websocket:
            # Initialize session
            websocket.send_json(
                {
                    "type": "start_session",
                    "session_id": "test-session",
                    "language": "english",
                }
            )
            websocket.receive_json()

            # Send audio
            audio_b64 = base64.b64encode(b"test audio").decode("utf-8")
            websocket.send_json({"type": "audio_chunk", "data": audio_b64})
            websocket.receive_json()

            websocket.send_json({"type": "audio_complete"})

            # Collect responses until error
            responses = []
            while True:
                try:
                    response = websocket.receive_json(timeout=5)
                    responses.append(response)
                    if response["type"] == "error":
                        break
                except:
                    break

            # Should have transcription but error on LLM
            response_types = [r["type"] for r in responses]
            assert "transcription" in response_types
            assert "error" in response_types

            error = next(r for r in responses if r["type"] == "error")
            assert "LLM service not available" in error["message"]
    finally:
        set_services(None, None, None)


# ============================================================================
# Performance Tests
# ============================================================================


@pytest.mark.asyncio
async def test_websocket_latency(mock_services):
    """Test WebSocket response latency"""
    import time

    with client.websocket_connect("/api/v1/ws/voice") as websocket:
        # Initialize session
        start_time = time.time()

        websocket.send_json(
            {
                "type": "start_session",
                "session_id": "test-session",
                "language": "english",
            }
        )

        response = websocket.receive_json()
        init_latency = time.time() - start_time

        assert response["type"] == "session_started"
        assert init_latency < 1.0  # Should be < 1 second

        # Send audio and measure end-to-end latency
        audio_b64 = base64.b64encode(b"test audio data").decode("utf-8")

        start_time = time.time()
        websocket.send_json({"type": "audio_chunk", "data": audio_b64})
        websocket.receive_json()  # chunk_received

        websocket.send_json({"type": "audio_complete"})

        # Wait for first meaningful response (transcription or llm_token)
        while True:
            response = websocket.receive_json(timeout=10)
            if response["type"] in ["transcription", "llm_token"]:
                first_response_latency = time.time() - start_time
                break

        # First response should be < 5 seconds (including mock delays)
        assert first_response_latency < 5.0


# ============================================================================
# Concurrent Connection Tests
# ============================================================================


def test_websocket_multiple_sessions(mock_services):
    """Test multiple concurrent WebSocket sessions"""
    sessions = []

    try:
        # Create 3 concurrent sessions
        for i in range(3):
            ws = client.websocket_connect("/api/v1/ws/voice")
            websocket = ws.__enter__()

            websocket.send_json(
                {
                    "type": "start_session",
                    "session_id": f"test-session-{i}",
                    "language": "english",
                }
            )

            response = websocket.receive_json()
            assert response["type"] == "session_started"
            assert response["session_id"] == f"test-session-{i}"

            sessions.append((ws, websocket))

        # Verify all sessions are active
        assert len(sessions) == 3

    finally:
        # Cleanup
        for ws, websocket in sessions:
            try:
                websocket.send_json({"type": "end_session"})
                ws.__exit__(None, None, None)
            except:
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
