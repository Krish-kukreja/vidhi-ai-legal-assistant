"""
Streaming Routes for VIDHI
Server-Sent Events (SSE) for real-time LLM response streaming.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import json
import logging
import asyncio

from middleware.auth_middleware import get_current_user_optional
from utils.input_sanitization import sanitize_api_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stream", tags=["streaming"])

# Global LLM service (will be set by app.py)
_llm_service = None


def set_llm_service(llm_service):
    """Set the LLM service instance for streaming routes."""
    global _llm_service
    _llm_service = llm_service


# Request Models

class StreamChatRequest(BaseModel):
    """Request model for streaming chat."""
    text: str
    session_id: str = "default"
    language: str = "english"
    use_agent: Optional[bool] = None


# SSE Event Formatting

def format_sse_event(data: dict, event: str = "message") -> str:
    """
    Format data as Server-Sent Event.
    
    Args:
        data: Data to send
        event: Event type
    
    Returns:
        Formatted SSE string
    """
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# Streaming Endpoints

@router.post("/chat")
async def stream_chat(
    request: StreamChatRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Stream LLM response token-by-token using Server-Sent Events.
    
    Args:
        request: Chat request with text, session_id, language
        current_user: Authenticated user (optional)
    
    Returns:
        StreamingResponse with SSE events
    
    Events:
        - token: Individual token from LLM
        - metadata: Confidence, citations, etc.
        - done: Streaming complete
        - error: Error occurred
    """
    try:
        # Sanitize input
        sanitized = sanitize_api_input(
            text=request.text,
            session_id=request.session_id,
            language=request.language
        )
        
        if not sanitized['is_safe']:
            raise HTTPException(
                status_code=400,
                detail=sanitized['safety_reason']
            )
        
        text = sanitized['text']
        session_id = sanitized['session_id']
        language = sanitized['language']
        
        # Check if LLM service is available
        if _llm_service is None:
            raise HTTPException(
                status_code=503,
                detail="LLM service not available"
            )
        
        # Check if streaming is supported
        if not hasattr(_llm_service, 'query_stream'):
            raise HTTPException(
                status_code=501,
                detail="Streaming not supported by LLM service"
            )
        
        # Get user ID for logging
        user_id = current_user.get('user_id', 'guest') if current_user else 'guest'
        
        logger.info(f"Streaming chat request from user={user_id}, session={session_id}")
        
        # Create streaming generator
        async def event_generator() -> AsyncGenerator[str, None]:
            """Generate SSE events from LLM stream."""
            try:
                # Stream from LLM
                async for event in _llm_service.query_stream(
                    question=text,
                    session_id=session_id,
                    language=language,
                    use_agent=request.use_agent
                ):
                    # Format as SSE event
                    event_type = event.get('type', 'message')
                    yield format_sse_event(event, event=event_type)
                    
                    # Small delay to prevent overwhelming client
                    await asyncio.sleep(0.01)
                
                logger.info(f"Streaming complete for user={user_id}, session={session_id}")
                
            except Exception as e:
                logger.error(f"Streaming error for user={user_id}: {e}")
                error_event = {
                    "type": "error",
                    "message": str(e)
                }
                yield format_sse_event(error_event, event="error")
        
        # Return streaming response
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stream_chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health")
async def streaming_health():
    """
    Health check for streaming service.
    
    Returns:
        Status of streaming service
    """
    return {
        "status": "healthy",
        "service": "streaming",
        "features": {
            "sse": True,
            "websocket": False  # Will be enabled in Week 2
        }
    }

