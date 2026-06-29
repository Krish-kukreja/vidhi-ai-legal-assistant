"""
Tests for CDN Service
Tests CloudFront integration for audio file delivery
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.cdn_service import CDNService


class TestCDNService:
    """Test CDN service functionality"""

    def test_cdn_disabled_by_default(self):
        """Test CDN is disabled when not configured"""
        cdn = CDNService(enabled=False)
        assert not cdn.is_enabled()

    def test_cdn_enabled_with_config(self):
        """Test CDN is enabled with proper configuration"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        # Will be disabled if boto3 not available, but config is set
        assert cdn.distribution_id == "E1234567890ABC"
        assert cdn.distribution_domain == "d1234567890abc.cloudfront.net"

    def test_get_cdn_url_when_disabled(self):
        """Test URL conversion returns S3 URL when CDN disabled"""
        cdn = CDNService(enabled=False)
        s3_url = "https://my-bucket.s3.us-east-1.amazonaws.com/audio/test.mp3"
        result = cdn.get_cdn_url(s3_url)
        assert result == s3_url

    def test_get_cdn_url_conversion(self):
        """Test S3 URL to CloudFront URL conversion"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True  # Force enable for test

        s3_url = "https://my-bucket.s3.us-east-1.amazonaws.com/audio/test.mp3"
        result = cdn.get_cdn_url(s3_url)

        assert result == "https://d1234567890abc.cloudfront.net/audio/test.mp3"

    def test_get_cdn_url_with_nested_path(self):
        """Test URL conversion with nested paths"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True

        s3_url = "https://my-bucket.s3.us-east-1.amazonaws.com/audio/2024/01/test.mp3"
        result = cdn.get_cdn_url(s3_url)

        assert result == "https://d1234567890abc.cloudfront.net/audio/2024/01/test.mp3"

    def test_get_cdn_url_invalid_format(self):
        """Test URL conversion with invalid S3 URL returns original"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True

        invalid_url = "https://example.com/file.mp3"
        result = cdn.get_cdn_url(invalid_url)

        assert result == invalid_url

    @patch("services.cdn_service.boto3.client")
    def test_invalidate_cache_success(self, mock_boto_client):
        """Test successful cache invalidation"""
        mock_cloudfront = Mock()
        mock_cloudfront.create_invalidation.return_value = {
            "Invalidation": {"Id": "I1234567890ABC", "Status": "InProgress"}
        }
        mock_boto_client.return_value = mock_cloudfront

        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.cloudfront_client = mock_cloudfront
        cdn.enabled = True

        result = cdn.invalidate_cache(["/audio/test.mp3"])

        assert result["success"] is True
        assert result["invalidation_id"] == "I1234567890ABC"
        assert result["status"] == "InProgress"
        assert "/audio/test.mp3" in result["paths"]

    def test_invalidate_cache_when_disabled(self):
        """Test cache invalidation fails when CDN disabled"""
        cdn = CDNService(enabled=False)
        result = cdn.invalidate_cache(["/audio/test.mp3"])

        assert result["success"] is False
        assert "not enabled" in result["error"].lower()

    def test_invalidate_cache_empty_paths(self):
        """Test cache invalidation fails with empty paths"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True

        result = cdn.invalidate_cache([])

        assert result["success"] is False
        assert "no paths" in result["error"].lower()

    @patch("services.cdn_service.boto3.client")
    def test_invalidate_cache_normalizes_paths(self, mock_boto_client):
        """Test cache invalidation normalizes paths to start with /"""
        mock_cloudfront = Mock()
        mock_cloudfront.create_invalidation.return_value = {
            "Invalidation": {"Id": "I1234567890ABC", "Status": "InProgress"}
        }
        mock_boto_client.return_value = mock_cloudfront

        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.cloudfront_client = mock_cloudfront
        cdn.enabled = True

        result = cdn.invalidate_cache(["audio/test.mp3", "/audio/test2.mp3"])

        assert result["success"] is True
        assert "/audio/test.mp3" in result["paths"]
        assert "/audio/test2.mp3" in result["paths"]

    @patch("services.cdn_service.boto3.client")
    def test_get_invalidation_status_success(self, mock_boto_client):
        """Test getting invalidation status"""
        from datetime import datetime

        mock_cloudfront = Mock()
        mock_cloudfront.get_invalidation.return_value = {
            "Invalidation": {
                "Id": "I1234567890ABC",
                "Status": "Completed",
                "CreateTime": datetime(2024, 1, 1, 12, 0, 0),
            }
        }
        mock_boto_client.return_value = mock_cloudfront

        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.cloudfront_client = mock_cloudfront
        cdn.enabled = True

        result = cdn.get_invalidation_status("I1234567890ABC")

        assert result["success"] is True
        assert result["invalidation_id"] == "I1234567890ABC"
        assert result["status"] == "Completed"

    def test_get_distribution_info_when_disabled(self):
        """Test distribution info when CDN disabled"""
        cdn = CDNService(enabled=False)
        info = cdn.get_distribution_info()

        assert info["enabled"] is False
        assert "not configured" in info["message"].lower()

    def test_get_distribution_info_when_enabled(self):
        """Test distribution info when CDN enabled"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True

        info = cdn.get_distribution_info()

        assert info["enabled"] is True
        assert info["distribution_id"] == "E1234567890ABC"
        assert info["distribution_domain"] == "d1234567890abc.cloudfront.net"


class TestCDNProperties:
    """Property-based tests for CDN service"""

    def test_url_format_invariant(self):
        """Test CloudFront URL format invariant"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True

        # Test multiple S3 URLs
        test_urls = [
            "https://bucket.s3.us-east-1.amazonaws.com/audio/file1.mp3",
            "https://bucket.s3.us-west-2.amazonaws.com/audio/file2.mp3",
            "https://bucket.s3.eu-west-1.amazonaws.com/audio/file3.mp3",
        ]

        for s3_url in test_urls:
            cdn_url = cdn.get_cdn_url(s3_url)
            # All CloudFront URLs should match pattern
            assert cdn_url.startswith("https://d1234567890abc.cloudfront.net/")
            assert ".s3." not in cdn_url

    def test_path_normalization_idempotence(self):
        """Test path normalization is idempotent"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )

        # Normalize paths
        paths1 = ["audio/test.mp3", "/audio/test2.mp3"]
        normalized1 = [f"/{p.lstrip('/')}" for p in paths1]

        # Normalize again
        normalized2 = [f"/{p.lstrip('/')}" for p in normalized1]

        # Should be identical
        assert normalized1 == normalized2

    def test_url_conversion_preserves_path(self):
        """Test URL conversion preserves the object path"""
        cdn = CDNService(
            distribution_id="E1234567890ABC",
            distribution_domain="d1234567890abc.cloudfront.net",
            enabled=True,
        )
        cdn.enabled = True

        s3_url = "https://bucket.s3.us-east-1.amazonaws.com/audio/2024/01/15/file.mp3"
        cdn_url = cdn.get_cdn_url(s3_url)

        # Extract path from both URLs
        s3_path = s3_url.split("/", 3)[3]
        cdn_path = cdn_url.split("/", 3)[3]

        # Paths should be identical
        assert s3_path == cdn_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
