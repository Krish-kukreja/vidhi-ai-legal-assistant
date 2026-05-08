"""
WebSocket Routes for VIDHI
Bidirectional voice streaming with real-time transcription and TTS.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, Optional
import json
import logging
import asyncio
import base64
from datetime import datetime

from utils.input_sanitization import sanitize_api_input

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])

# Global services (will be set by app.py)
_llm_service = None
_transcribe_service = None
_polly_service = None

# Active WebSocket connections
_active_connections: Dict[str, WebSocket] = {}


def set_services(llm_service, transcribe_service, polly_service):
    """Set service instances for WebSocket routes."""
    global _llm_service, _transcribe_service, _polly_service
    _llm_service = llm_service
    _transcribe_service = transcribe_service
    _polly_service = polly_service


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept and store WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: session={session_id}")
    
    def disconnect(self, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")
    
    async def send_message(self, session_id: str, message: dict):
        """Send message to specific session."""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections."""
        for websocket in self.active_connections.values():
            await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/voice")
async def voice_streaming(websocket: WebSocket):
    """
    WebSocket endpoint for bidirectional voice streaming.
    
    Flow:
    1. Client sends audio chunks
    2. Server transcribes audio (AWS Transcribe)
    3. Server queries LLM with transcription
    4. Server generates speech (AWS Polly)
    5. Server sends audio chunks back to client
    
    Message Types:
    - Client → Server: audio_chunk, start_session, end_session
    - Server → Client: transcription, llm_token, audio_chunk, done, error
    """
    session_id = None
    
    try:
        # Accept connection
        await websocket.accept()
        logger.info("WebSocket connection accepted")
        
        # Wait for session initialization
        init_message = await websocket.receive_json()
        
        if init_message.get("type") != "start_session":
            await websocket.send_json({
                "type": "error",
                "message": "First message must be start_session"
            })
            await websocket.close()
            return
        
        # Extract session info
        session_id = init_message.get("session_id", f"ws_{datetime.now().timestamp()}")
        language = init_message.get("language", "english")
        language_code = init_message.get("language_code", "en-IN")
        
        # Sanitize inputs
        sanitized = sanitize_api_input(
            session_id=session_id,
            language=language
        )
        
        if not sanitized.get('is_safe', True):
            await websocket.send_json({
                "type": "error",
                "message": sanitized.get('safety_reason', 'Invalid input')
            })
            await websocket.close()
            return
        
        session_id = sanitized.get('session_id', session_id)
        language = sanitized.get('language', language)
        
        # Register connection
        manager.active_connections[session_id] = websocket
        
        # Send confirmation
        await websocket.send_json({
            "type": "session_started",
            "session_id": session_id,
            "language": language
        })
        
        logger.info(f"Voice session started: {session_id}")
        
        # Audio buffer for accumulating chunks
        audio_buffer = bytearray()
        
        # Main message loop
        while True:
            try:
                message = await websocket.receive_json()
                message_type = message.get("type")
                
                if message_type == "audio_chunk":
                    # Receive audio chunk from client
                    audio_data_b64 = message.get("data")
                    audio_format = message.get("format", "webm")
                    
                    if not audio_data_b64:
                        continue
                    
                    # Decode base64 audio
                    audio_data = base64.b64decode(audio_data_b64)
                    audio_buffer.extend(audio_data)
                    
                    # Send acknowledgment
                    await websocket.send_json({
                        "type": "chunk_received",
                        "size": len(audio_data)
                    })
                
                elif message_type == "audio_complete":
                    # Client finished sending audio
                    if len(audio_buffer) == 0:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No audio data received"
                        })
                        continue
                    
                    # Process the complete audio
                    await process_voice_input(
                        websocket,
                        session_id,
                        bytes(audio_buffer),
                        language,
                        language_code,
                        message.get("format", "webm")
                    )
                    
                    # Clear buffer
                    audio_buffer.clear()
                
                elif message_type == "end_session":
                    # Client wants to end session
                    await websocket.send_json({
                        "type": "session_ended",
                        "session_id": session_id
                    })
                    break
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}"
                    })
            
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {session_id}")
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected during initialization")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
    finally:
        # Cleanup
        if session_id:
            manager.disconnect(session_id)


async def process_voice_input(
    websocket: WebSocket,
    session_id: str,
    audio_data: bytes,
    language: str,
    language_code: str,
    audio_format: str
):
    """
    Process voice input through the full pipeline:
    1. Transcribe audio
    2. Query LLM
    3. Generate speech
    4. Send audio back
    """
    try:
        import time
        start_time = time.time()
        
        # Step 1: Transcribe audio
        if not _transcribe_service:
            await websocket.send_json({
                "type": "error",
                "message": "Transcription service not available"
            })
            return
        
        await websocket.send_json({
            "type": "status",
            "message": "Transcribing audio..."
        })
        
        # Upload to S3 and transcribe
        timestamp = int(time.time())
        s3_key = f"ws-transcribe/{session_id}/{timestamp}.{audio_format}"
        
        try:
            # Get S3 bucket from transcribe service config
            s3_bucket = getattr(_transcribe_service, 's3_bucket', None)
            if not s3_bucket:
                # Fallback to environment variable or default
                import os
                s3_bucket = os.getenv('S3_BUCKET_AUDIO', 'vidhi-audio-prod')
            
            s3_uri = _transcribe_service.upload_audio_to_s3(
                audio_data,
                s3_bucket,
                s3_key
            )
            
            transcribe_result = _transcribe_service.transcribe_audio(
                s3_uri,
                language_code,
                identify_language=False,
                media_format=audio_format
            )
            
            if not transcribe_result['success']:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Transcription failed: {transcribe_result['error']}"
                })
                return
            
            transcript = transcribe_result['transcript']
            
            # Send transcription to client
            await websocket.send_json({
                "type": "transcription",
                "text": transcript,
                "is_final": True,
                "language_code": transcribe_result['language_code']
            })
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"Transcription error: {str(e)}"
            })
            return
        
        # Step 2: Query LLM (streaming)
        if not _llm_service:
            await websocket.send_json({
                "type": "error",
                "message": "LLM service not available"
            })
            return
        
        await websocket.send_json({
            "type": "status",
            "message": "Generating response..."
        })
        
        full_response = ""
        
        try:
            async for event in _llm_service.query_stream(
                question=transcript,
                session_id=session_id,
                language=language
            ):
                if event.get('type') == 'token':
                    # Send LLM token to client
                    await websocket.send_json({
                        "type": "llm_token",
                        "content": event.get('content'),
                        "index": event.get('index')
                    })
                    full_response += event.get('content', '')
                
                elif event.get('type') == 'metadata':
                    # Send metadata
                    await websocket.send_json({
                        "type": "metadata",
                        "confidence": event.get('confidence'),
                        "citations": event.get('citations')
                    })
                
                elif event.get('type') == 'error':
                    await websocket.send_json({
                        "type": "error",
                        "message": event.get('message')
                    })
                    return
        
        except Exception as e:
            logger.error(f"LLM error: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"LLM error: {str(e)}"
            })
            return
        
        # Step 3: Generate speech (TTS)
        if not _polly_service:
            # No TTS available - just send done
            await websocket.send_json({
                "type": "done",
                "duration_ms": int((time.time() - start_time) * 1000),
                "transcript": transcript,
                "response": full_response
            })
            return
        
        await websocket.send_json({
            "type": "status",
            "message": "Generating speech..."
        })
        
        try:
            tts_result = _polly_service.get_or_create_audio(
                full_response,
                language_code
            )
            
            if tts_result['success']:
                # Send audio URL to client
                await websocket.send_json({
                    "type": "audio_url",
                    "url": tts_result['audio_url'],
                    "format": "mp3"
                })
            else:
                logger.warning(f"TTS failed: {tts_result.get('error')}")
        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            # Non-fatal - continue without audio
        
        # Step 4: Send completion
        await websocket.send_json({
            "type": "done",
            "duration_ms": int((time.time() - start_time) * 1000),
            "transcript": transcript,
            "response": full_response
        })
        
        logger.info(f"Voice processing complete for session {session_id}")
    
    except Exception as e:
        logger.error(f"Error in voice processing pipeline: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Pipeline error: {str(e)}"
        })


@router.get("/health")
async def websocket_health():
    """
    Health check for WebSocket service.
    
    Returns:
        Status of WebSocket service and active connections
    """
    return {
        "status": "healthy",
        "service": "websocket",
        "active_connections": len(manager.active_connections),
        "features": {
            "voice_streaming": True,
            "transcription": _transcribe_service is not None,
            "tts": _polly_service is not None,
            "llm": _llm_service is not None
        }
    }
