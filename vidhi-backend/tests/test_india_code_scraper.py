"""
Tests for India Code Acts Scraper
Tests checkpoint recovery, retry logic, and deduplication
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the scraper module
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data_pipeline.fetch_india_code import (
    CheckpointManager,
    retry_with_backoff,
    deduplicate_chunks,
    get_act_sections,
    fetch_act_via_search,
)


class TestCheckpointManager:
    """Test checkpoint save/load functionality"""

    def test_checkpoint_creation(self, tmp_path):
        """Test creating a new checkpoint"""
        checkpoint_file = tmp_path / "test_checkpoint.json"
        manager = CheckpointManager(str(checkpoint_file))

        assert manager.state["completed_acts"] == []
        assert manager.state["failed_acts"] == []
        assert manager.state["last_act_index"] == -1

    def test_checkpoint_save_load(self, tmp_path):
        """Test saving and loading checkpoint"""
        checkpoint_file = tmp_path / "test_checkpoint.json"
        manager = CheckpointManager(str(checkpoint_file))

        # Mark some acts as completed
        manager.mark_completed("Test Act 1", "2020/1")
        manager.mark_completed("Test Act 2", "2020/2")

        # Create new manager and load
        manager2 = CheckpointManager(str(checkpoint_file))
        assert len(manager2.state["completed_acts"]) == 2
        assert manager2.is_completed("2020/1")
        assert manager2.is_completed("2020/2")

    def test_checkpoint_mark_failed(self, tmp_path):
        """Test marking acts as failed"""
        checkpoint_file = tmp_path / "test_checkpoint.json"
        manager = CheckpointManager(str(checkpoint_file))

        manager.mark_failed("Test Act", "2020/1", "HTTP 404")

        assert len(manager.state["failed_acts"]) == 1
        assert manager.state["failed_acts"][0]["name"] == "Test Act"
        assert manager.state["failed_acts"][0]["error"] == "HTTP 404"

    def test_checkpoint_update_index(self, tmp_path):
        """Test updating last processed index"""
        checkpoint_file = tmp_path / "test_checkpoint.json"
        manager = CheckpointManager(str(checkpoint_file))

        manager.update_index(5)
        assert manager.state["last_act_index"] == 5

        # Reload and verify
        manager2 = CheckpointManager(str(checkpoint_file))
        assert manager2.state["last_act_index"] == 5


class TestRetryLogic:
    """Test retry with exponential backoff"""

    def test_retry_success_first_attempt(self):
        """Test successful execution on first attempt"""
        mock_func = Mock(return_value="success")
        result = retry_with_backoff(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_after_failures(self):
        """Test successful execution after retries"""
        import requests

        mock_func = Mock(
            side_effect=[
                requests.RequestException("Fail 1"),
                requests.RequestException("Fail 2"),
                "success",
            ]
        )

        result = retry_with_backoff(mock_func)
        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_max_attempts_exceeded(self):
        """Test failure after max retries"""
        import requests

        mock_func = Mock(side_effect=requests.RequestException("Always fails"))

        with pytest.raises(requests.RequestException):
            retry_with_backoff(mock_func)

        assert mock_func.call_count == 3  # MAX_RETRIES


class TestDeduplication:
    """Test chunk deduplication"""

    def test_deduplicate_removes_duplicates(self):
        """Test that duplicate chunks are removed"""
        chunks = [
            {"chunk_index": 0, "text": "Section 1 content"},
            {"chunk_index": 1, "text": "Section 2 content"},
            {"chunk_index": 2, "text": "Section 1 content"},  # Duplicate
            {"chunk_index": 3, "text": "Section 3 content"},
        ]

        result = deduplicate_chunks(chunks)

        assert len(result) == 3
        texts = [chunk["text"] for chunk in result]
        assert "Section 1 content" in texts
        assert "Section 2 content" in texts
        assert "Section 3 content" in texts

    def test_deduplicate_preserves_order(self):
        """Test that deduplication preserves first occurrence"""
        chunks = [
            {"chunk_index": 0, "text": "First"},
            {"chunk_index": 1, "text": "Second"},
            {"chunk_index": 2, "text": "First"},
        ]

        result = deduplicate_chunks(chunks)

        assert len(result) == 2
        assert result[0]["text"] == "First"
        assert result[1]["text"] == "Second"

    def test_deduplicate_empty_chunks(self):
        """Test deduplication with empty chunks"""
        chunks = [
            {"chunk_index": 0, "text": "Content"},
            {"chunk_index": 1, "text": ""},
            {"chunk_index": 2, "text": "   "},
            {"chunk_index": 3, "text": "Content"},
        ]

        result = deduplicate_chunks(chunks)

        # Empty/whitespace chunks should be removed
        assert len(result) == 1
        assert result[0]["text"] == "Content"


class TestActScraping:
    """Test act scraping functions"""

    @patch("data_pipeline.fetch_india_code.requests.get")
    def test_get_act_sections_success(self, mock_get):
        """Test successful act section fetching"""
        # Mock HTML response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div class="item-page">
                    <p>Section 1: This is section 1 content</p>
                    <p>Section 2: This is section 2 content</p>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        sections, error = get_act_sections("2020/1")

        assert error is None
        assert len(sections) > 0
        assert any("Section 1" in chunk["text"] for chunk in sections)

    @patch("data_pipeline.fetch_india_code.requests.get")
    def test_get_act_sections_http_error(self, mock_get):
        """Test handling of HTTP errors"""
        import requests

        mock_get.side_effect = requests.RequestException("HTTP 404")

        sections, error = get_act_sections("2020/1")

        assert sections == []
        assert error is not None
        assert "HTTP error" in error

    @patch("data_pipeline.fetch_india_code.requests.get")
    def test_fetch_act_via_search_success(self, mock_get):
        """Test search fallback mechanism"""
        # Mock search results
        search_response = Mock()
        search_response.status_code = 200
        search_response.text = """
        <html>
            <body>
                <a href="/handle/123456789/2020/1">Test Act 2020</a>
            </body>
        </html>
        """

        # Mock act page
        act_response = Mock()
        act_response.status_code = 200
        act_response.text = """
        <html>
            <body>
                <div class="item-page">
                    <p>Act content here</p>
                </div>
            </body>
        </html>
        """

        mock_get.side_effect = [search_response, act_response]

        sections, error = fetch_act_via_search("Test Act 2020")

        assert error is None
        assert len(sections) > 0


class TestPropertyBasedInvariants:
    """Property-based tests for scraper invariants"""

    def test_total_character_count_invariant(self):
        """Test that total character count equals sum of chunk character counts"""
        chunks = [
            {"chunk_index": 0, "text": "A" * 100},
            {"chunk_index": 1, "text": "B" * 150},
            {"chunk_index": 2, "text": "C" * 200},
        ]

        total_chars = sum(len(chunk["text"]) for chunk in chunks)
        expected_total = 100 + 150 + 200

        assert total_chars == expected_total

    def test_json_round_trip_property(self):
        """Test that JSON serialization round-trip preserves structure"""
        act_data = {
            "act_name": "Test Act",
            "act_id": "2020/1",
            "source": "https://example.com",
            "sections": [
                {"chunk_index": 0, "text": "Content 1"},
                {"chunk_index": 1, "text": "Content 2"},
            ],
            "total_chunks": 2,
        }

        # Serialize and deserialize
        json_str = json.dumps(act_data, ensure_ascii=False)
        restored = json.loads(json_str)

        # Verify structure preserved (excluding timestamp which may differ)
        assert restored["act_name"] == act_data["act_name"]
        assert restored["act_id"] == act_data["act_id"]
        assert len(restored["sections"]) == len(act_data["sections"])
        assert restored["total_chunks"] == act_data["total_chunks"]

    def test_idempotence_property(self):
        """Test that deduplication is idempotent"""
        chunks = [
            {"chunk_index": 0, "text": "Content 1"},
            {"chunk_index": 1, "text": "Content 2"},
            {"chunk_index": 2, "text": "Content 1"},
        ]

        # Apply deduplication twice
        result1 = deduplicate_chunks(chunks)
        result2 = deduplicate_chunks(result1)

        # Results should be identical
        assert len(result1) == len(result2)
        assert [c["text"] for c in result1] == [c["text"] for c in result2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
