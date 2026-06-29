"""
CDN Service for Audio Files
Provides CloudFront CDN integration for optimized audio delivery
"""

import boto3
import logging
import os
from typing import Optional, Dict
from botocore.exceptions import ClientError
import time

logger = logging.getLogger(__name__)


class CDNService:
    """
    CloudFront CDN service for audio file delivery
    """

    def __init__(
        self,
        distribution_id: Optional[str] = None,
        distribution_domain: Optional[str] = None,
        enabled: bool = True,
        region: str = "us-east-1",
    ):
        """
        Initialize CDN service

        Args:
            distribution_id: CloudFront distribution ID
            distribution_domain: CloudFront distribution domain
            enabled: Whether CDN is enabled
            region: AWS region
        """
        self.distribution_id = distribution_id or os.getenv(
            "CLOUDFRONT_DISTRIBUTION_ID"
        )
        self.distribution_domain = distribution_domain or os.getenv("CLOUDFRONT_DOMAIN")
        self.enabled = (
            enabled and os.getenv("CLOUDFRONT_ENABLED", "false").lower() == "true"
        )
        self.region = region

        if self.enabled and (not self.distribution_id or not self.distribution_domain):
            logger.warning(
                "CloudFront enabled but distribution ID or domain not configured. Falling back to S3 URLs."
            )
            self.enabled = False

        if self.enabled:
            try:
                self.cloudfront_client = boto3.client("cloudfront", region_name=region)
                logger.info(
                    f"CDN service initialized with distribution {self.distribution_id}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize CloudFront client: {e}")
                self.enabled = False
                self.cloudfront_client = None
        else:
            self.cloudfront_client = None
            logger.info("CDN service disabled, using direct S3 URLs")

    def get_cdn_url(self, s3_url: str) -> str:
        """
        Convert S3 URL to CloudFront CDN URL

        Args:
            s3_url: Direct S3 URL

        Returns:
            CloudFront URL if CDN enabled, otherwise original S3 URL
        """
        if not self.enabled:
            return s3_url

        try:
            # Extract object key from S3 URL
            # Format: https://bucket-name.s3.region.amazonaws.com/path/to/file
            # or: https://s3.region.amazonaws.com/bucket-name/path/to/file

            if ".s3." in s3_url or "s3." in s3_url:
                # Extract key from S3 URL
                parts = s3_url.split("/", 3)
                if len(parts) >= 4:
                    object_key = parts[3]
                else:
                    logger.warning(f"Could not parse S3 URL: {s3_url}")
                    return s3_url
            else:
                # Already a CDN URL or invalid format
                return s3_url

            # Generate CloudFront URL
            cdn_url = f"https://{self.distribution_domain}/{object_key}"
            logger.debug(f"Converted S3 URL to CDN URL: {s3_url} -> {cdn_url}")
            return cdn_url

        except Exception as e:
            logger.error(f"Error converting S3 URL to CDN URL: {e}")
            return s3_url

    def invalidate_cache(self, paths: list[str]) -> Dict:
        """
        Create CloudFront cache invalidation

        Args:
            paths: List of paths to invalidate (e.g., ['/audio/file1.mp3', '/audio/*'])

        Returns:
            Dict with invalidation status
        """
        if not self.enabled:
            return {"success": False, "error": "CDN not enabled"}

        if not paths:
            return {"success": False, "error": "No paths provided"}

        try:
            # Ensure paths start with /
            normalized_paths = [f"/{p.lstrip('/')}" for p in paths]

            # Create invalidation
            response = self.cloudfront_client.create_invalidation(
                DistributionId=self.distribution_id,
                InvalidationBatch={
                    "Paths": {
                        "Quantity": len(normalized_paths),
                        "Items": normalized_paths,
                    },
                    "CallerReference": f"vidhi-invalidation-{int(time.time())}",
                },
            )

            invalidation_id = response["Invalidation"]["Id"]
            status = response["Invalidation"]["Status"]

            logger.info(
                f"CloudFront invalidation created: {invalidation_id} (status: {status})"
            )

            return {
                "success": True,
                "invalidation_id": invalidation_id,
                "status": status,
                "paths": normalized_paths,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(
                f"CloudFront invalidation failed: {error_code} - {error_message}"
            )

            return {"success": False, "error": f"{error_code}: {error_message}"}
        except Exception as e:
            logger.error(f"Unexpected error during cache invalidation: {e}")
            return {"success": False, "error": str(e)}

    def get_invalidation_status(self, invalidation_id: str) -> Dict:
        """
        Get status of a CloudFront invalidation

        Args:
            invalidation_id: Invalidation ID

        Returns:
            Dict with invalidation status
        """
        if not self.enabled:
            return {"success": False, "error": "CDN not enabled"}

        try:
            response = self.cloudfront_client.get_invalidation(
                DistributionId=self.distribution_id, Id=invalidation_id
            )

            status = response["Invalidation"]["Status"]
            create_time = response["Invalidation"]["CreateTime"]

            return {
                "success": True,
                "invalidation_id": invalidation_id,
                "status": status,
                "create_time": create_time.isoformat(),
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(
                f"Failed to get invalidation status: {error_code} - {error_message}"
            )

            return {"success": False, "error": f"{error_code}: {error_message}"}
        except Exception as e:
            logger.error(f"Unexpected error getting invalidation status: {e}")
            return {"success": False, "error": str(e)}

    def is_enabled(self) -> bool:
        """Check if CDN is enabled"""
        return self.enabled

    def get_distribution_info(self) -> Dict:
        """Get CloudFront distribution information"""
        if not self.enabled:
            return {"enabled": False, "message": "CDN not configured"}

        return {
            "enabled": True,
            "distribution_id": self.distribution_id,
            "distribution_domain": self.distribution_domain,
            "region": self.region,
        }
