"""
Monitoring and Error Tracking for VIDHI
Sentry integration with performance monitoring.

Features:
- Error tracking with context
- Performance monitoring
- User context tracking
- Custom tags and breadcrumbs
- Environment-based configuration
"""

import os
import logging
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Sentry SDK (optional dependency)
try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logger.warning("Sentry SDK not installed. Install with: pip install sentry-sdk")


class MonitoringService:
    """Monitoring and error tracking service"""
    
    def __init__(self):
        self.enabled = False
        self.sentry_dsn = os.getenv("SENTRY_DSN")
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.release = os.getenv("RELEASE_VERSION", "unknown")
    
    def initialize(self):
        """Initialize Sentry SDK"""
        if not SENTRY_AVAILABLE:
            logger.warning("Sentry not available, monitoring disabled")
            return
        
        if not self.sentry_dsn:
            logger.info("SENTRY_DSN not set, monitoring disabled")
            return
        
        try:
            sentry_sdk.init(
                dsn=self.sentry_dsn,
                environment=self.environment,
                release=self.release,
                traces_sample_rate=1.0 if self.environment == "development" else 0.1,
                profiles_sample_rate=1.0 if self.environment == "development" else 0.1,
                integrations=[
                    FastApiIntegration(),
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR
                    )
                ],
                # Don't send PII
                send_default_pii=False,
                # Attach stack traces
                attach_stacktrace=True,
                # Max breadcrumbs
                max_breadcrumbs=50,
            )
            
            self.enabled = True
            logger.info(f"Sentry initialized (env: {self.environment}, release: {self.release})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Sentry: {e}")
    
    def capture_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        user: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Capture an exception with context"""
        if not self.enabled:
            return
        
        try:
            # Set user context
            if user:
                sentry_sdk.set_user({
                    "id": user.get("user_id"),
                    "user_type": user.get("user_type"),
                })
            
            # Set tags
            if tags:
                for key, value in tags.items():
                    sentry_sdk.set_tag(key, value)
            
            # Set context
            if context:
                sentry_sdk.set_context("additional_info", context)
            
            # Capture exception
            sentry_sdk.capture_exception(exception)
            
        except Exception as e:
            logger.error(f"Failed to capture exception in Sentry: {e}")
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        context: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Capture a message"""
        if not self.enabled:
            return
        
        try:
            # Set tags
            if tags:
                for key, value in tags.items():
                    sentry_sdk.set_tag(key, value)
            
            # Set context
            if context:
                sentry_sdk.set_context("additional_info", context)
            
            # Capture message
            sentry_sdk.capture_message(message, level=level)
            
        except Exception as e:
            logger.error(f"Failed to capture message in Sentry: {e}")
    
    def add_breadcrumb(
        self,
        message: str,
        category: str = "default",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """Add a breadcrumb for debugging"""
        if not self.enabled:
            return
        
        try:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
        except Exception as e:
            logger.error(f"Failed to add breadcrumb: {e}")
    
    def start_transaction(self, name: str, op: str = "http.server"):
        """Start a performance transaction"""
        if not self.enabled:
            return None
        
        try:
            return sentry_sdk.start_transaction(name=name, op=op)
        except Exception as e:
            logger.error(f"Failed to start transaction: {e}")
            return None
    
    def set_user(self, user: Dict[str, Any]):
        """Set user context"""
        if not self.enabled:
            return
        
        try:
            sentry_sdk.set_user({
                "id": user.get("user_id"),
                "user_type": user.get("user_type"),
            })
        except Exception as e:
            logger.error(f"Failed to set user context: {e}")
    
    def set_tag(self, key: str, value: str):
        """Set a tag"""
        if not self.enabled:
            return
        
        try:
            sentry_sdk.set_tag(key, value)
        except Exception as e:
            logger.error(f"Failed to set tag: {e}")


# Global monitoring service
monitoring = MonitoringService()


def monitor_function(operation_name: str = None):
    """Decorator to monitor function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            if monitoring.enabled:
                with sentry_sdk.start_span(op=op_name):
                    return await func(*args, **kwargs)
            else:
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            if monitoring.enabled:
                with sentry_sdk.start_span(op=op_name):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Convenience functions
def capture_exception(exception: Exception, **kwargs):
    """Capture an exception"""
    monitoring.capture_exception(exception, **kwargs)


def capture_message(message: str, level: str = "info", **kwargs):
    """Capture a message"""
    monitoring.capture_message(message, level, **kwargs)


def add_breadcrumb(message: str, **kwargs):
    """Add a breadcrumb"""
    monitoring.add_breadcrumb(message, **kwargs)


def set_user(user: Dict[str, Any]):
    """Set user context"""
    monitoring.set_user(user)


def set_tag(key: str, value: str):
    """Set a tag"""
    monitoring.set_tag(key, value)
