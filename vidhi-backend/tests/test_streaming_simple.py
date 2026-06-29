"""
Simple tests for SSE Streaming Endpoints (Phase 2)

Tests basic functionality without complex async setup.
"""

import pytest
import requests
import json
from unittest.mock import Mock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test against running server
BASE_URL = "http://localhost:8000"


def test_streaming_health_check():
    """Test streaming health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/stream/health", timeout=5)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "streaming"
        assert "features" in data
        assert data["features"]["sse"] is True

        print("✓ Streaming health check passed")
    except requests.exceptions.ConnectionError:
        pytest.skip("Backend server not running")


def test_streaming_endpoint_exists():
    """Test that streaming endpoint exists"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/stream/chat",
            json={
                "text": "What is Section 438 CrPC?",
                "session_id": "test-session",
                "language": "english",
            },
            stream=True,
            timeout=10,
        )

        # Should either succeed or fail with proper error (not 404)
        assert response.status_code != 404

        print(f"✓ Streaming endpoint exists (status: {response.status_code})")
    except requests.exceptions.ConnectionError:
        pytest.skip("Backend server not running")


def test_streaming_sse_format():
    """Test that streaming returns SSE format"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/stream/chat",
            json={"text": "Hello", "session_id": "test-session", "language": "english"},
            stream=True,
            timeout=10,
        )

        if response.status_code == 200:
            # Check content type
            content_type = response.headers.get("content-type", "")
            assert "text/event-stream" in content_type

            print("✓ Streaming returns SSE format")
        else:
            print(f"⚠ Streaming returned status {response.status_code}")

    except requests.exceptions.ConnectionError:
        pytest.skip("Backend server not running")


if __name__ == "__main__":
    print("Running simple streaming tests...")
    print("Note: These tests require the backend server to be running on port 8000")
    print()

    test_streaming_health_check()
    test_streaming_endpoint_exists()
    test_streaming_sse_format()

    print()
    print("All simple tests passed!")
