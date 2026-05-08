"""
Middleware to automatically sanitize inputs for all API endpoints.
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
from utils.input_sanitization import check_content_safety, sanitize_chat_input, sanitize_document_text

logger = logging.getLogger(__name__)


class InputSanitizationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that sanitizes all text inputs before they reach endpoint handlers.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Only process POST/PUT/PATCH requests with JSON or form data
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                # Check content type
                content_type = request.headers.get("content-type", "")
                
                if "application/json" in content_type:
                    # Parse JSON body
                    body = await request.body()
                    if body:
                        import json
                        try:
                            data = json.loads(body)
                            
                            # Sanitize text fields
                            sanitized_data = self._sanitize_dict(data, request.url.path)
                            
                            # Check for unsafe content
                            is_safe, reason = self._check_dict_safety(sanitized_data)
                            if not is_safe:
                                return JSONResponse(
                                    status_code=400,
                                    content={"detail": f"Invalid input: {reason}"}
                                )
                            
                            # Replace request body with sanitized data
                            sanitized_body = json.dumps(sanitized_data).encode()
                            
                            # Create new request with sanitized body
                            async def receive():
                                return {"type": "http.request", "body": sanitized_body}
                            
                            request._receive = receive
                            
                        except json.JSONDecodeError:
                            pass  # Let the endpoint handle invalid JSON
                
                # Note: Form data sanitization is handled in the chat endpoint directly
                # because FastAPI's Form() parsing happens after middleware
                
            except Exception as e:
                logger.error(f"Error in sanitization middleware: {e}")
                # Don't block request on middleware errors
        
        response = await call_next(request)
        return response
    
    def _sanitize_dict(self, data: dict, path: str) -> dict:
        """Recursively sanitize all string values in a dictionary."""
        if not isinstance(data, dict):
            return data
        
        # Determine if this is a document endpoint (less aggressive sanitization)
        is_document = "/documents/" in path
        
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                # Sanitize based on field name and endpoint type
                if key in ['document_text', 'clause_text', 'document_context', 'content']:
                    sanitized[key] = sanitize_document_text(value)
                elif key in ['text', 'message', 'query', 'question', 'term', 'clause']:
                    sanitized[key] = sanitize_chat_input(value)
                else:
                    # Default: light sanitization
                    sanitized[key] = value.strip() if value else value
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value, path)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item, path) if isinstance(item, dict)
                    else sanitize_chat_input(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _check_dict_safety(self, data: dict) -> tuple[bool, str]:
        """Check all string values in a dictionary for safety."""
        if not isinstance(data, dict):
            return True, None
        
        for key, value in data.items():
            if isinstance(value, str):
                is_safe, reason = check_content_safety(value)
                if not is_safe:
                    return False, f"{key}: {reason}"
            elif isinstance(value, dict):
                is_safe, reason = self._check_dict_safety(value)
                if not is_safe:
                    return False, reason
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        is_safe, reason = check_content_safety(item)
                        if not is_safe:
                            return False, f"{key}: {reason}"
                    elif isinstance(item, dict):
                        is_safe, reason = self._check_dict_safety(item)
                        if not is_safe:
                            return False, reason
        
        return True, None
