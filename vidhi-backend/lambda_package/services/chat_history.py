"""
Chat History Service with Language-Preserved Voice Playback
Stores messages with language metadata and audio references for accurate playback
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from speech.aws_polly import synthesize_speech
from speech.bhashini import synthesize_speech_bhashini


class ChatHistoryService:
    """Service for managing chat history with language preservation"""
    
    def __init__(self):
        self.storage = {}  # In-memory storage (replace with DynamoDB in production)
        self.audio_cache = {}  # Audio URL cache (replace with S3 in production)
    
    def save_message(
        self,
        user_id: str,
        chat_id: str,
        message_text: str,
        message_type: str,  # 'user_query' or 'system_response'
        language_code: str,  # e.g., 'hi-IN', 'bn-IN'
        language_name: str,  # e.g., 'hindi', 'bengali'
        dialect: Optional[str] = None,  # e.g., 'Bhojpuri', 'Maithili'
        input_mode: str = 'text',  # 'voice', 'text', 'document'
        audio_data: Optional[bytes] = None  # Original audio if voice input
    ) -> Dict[str, Any]:
        """
        Save a message with complete language metadata
        
        Args:
            user_id: User identifier
            chat_id: Chat session identifier
            message_text: The message content
            message_type: 'user_query' or 'system_response'
            language_code: BCP 47 language code
            language_name: Human-readable language name
            dialect: Optional dialect name
            input_mode: How the message was input
            audio_data: Optional original audio bytes
            
        Returns:
            Saved message object with metadata
        """
        
        message_id = self._generate_message_id(chat_id, message_text)
        timestamp = datetime.utcnow()
        
        # Build language tag (e.g., "hi-IN-Bhojpuri")
        language_tag = language_code
        if dialect:
            language_tag = f"{language_code}-{dialect}"
        
        # Determine TTS engine based on language
        tts_engine = self._select_tts_engine(language_code, dialect)
        
        # Generate audio for system responses
        audio_url = None
        audio_duration = 0
        if message_type == 'system_response':
            audio_url, audio_duration = self._generate_and_cache_audio(
                message_text,
                language_code,
                language_name,
                dialect,
                message_id
            )
        
        # Store original audio for user queries if provided
        original_audio_url = None
        if audio_data and message_type == 'user_query':
            original_audio_url = self._store_audio(audio_data, message_id, 'original')
        
        message = {
            "message_id": message_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "timestamp": timestamp.isoformat(),
            
            "message_content": {
                "text": message_text,
                "message_type": message_type,
                "input_mode": input_mode
            },
            
            "language_metadata": {
                "language_tag": language_tag,
                "language_code": language_code,
                "language_name": language_name,
                "dialect": dialect,
                "script": self._get_script(language_code)
            },
            
            "audio_reference": {
                "original_audio_url": original_audio_url,
                "synthesized_audio_url": audio_url,
                "audio_duration_seconds": audio_duration,
                "tts_engine_used": tts_engine,
                "generation_timestamp": timestamp.isoformat()
            }
        }
        
        # Store in memory (replace with DynamoDB in production)
        if chat_id not in self.storage:
            self.storage[chat_id] = []
        self.storage[chat_id].append(message)
        
        return message
    
    def get_chat_history(
        self,
        chat_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chat history for a session
        
        Args:
            chat_id: Chat session identifier
            limit: Optional limit on number of messages
            
        Returns:
            List of messages with metadata
        """
        messages = self.storage.get(chat_id, [])
        
        if limit:
            messages = messages[-limit:]
        
        return messages
    
    def get_message_playback(
        self,
        chat_id: str,
        message_id: str,
        regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Get audio playback for a specific message in original language
        
        Args:
            chat_id: Chat session identifier
            message_id: Message identifier
            regenerate: Force regeneration of audio
            
        Returns:
            Playback information with audio URL
        """
        # Find message
        messages = self.storage.get(chat_id, [])
        message = next((m for m in messages if m["message_id"] == message_id), None)
        
        if not message:
            raise ValueError(f"Message {message_id} not found in chat {chat_id}")
        
        # Check if we have cached audio
        audio_ref = message["audio_reference"]
        cached_url = audio_ref.get("synthesized_audio_url")
        
        if cached_url and not regenerate:
            # Return cached audio
            return {
                "message_id": message_id,
                "chat_id": chat_id,
                "timestamp": message["timestamp"],
                "message_content": message["message_content"],
                "language_metadata": message["language_metadata"],
                "audio_playback": {
                    "audio_url": cached_url,
                    "audio_format": "mp3",
                    "duration_seconds": audio_ref["audio_duration_seconds"],
                    "tts_engine": audio_ref["tts_engine_used"],
                    "cached": True
                }
            }
        
        # Regenerate audio using stored language metadata
        lang_meta = message["language_metadata"]
        text = message["message_content"]["text"]
        
        audio_url, duration = self._generate_and_cache_audio(
            text,
            lang_meta["language_code"],
            lang_meta["language_name"],
            lang_meta.get("dialect"),
            message_id
        )
        
        # Update message with new audio reference
        message["audio_reference"]["synthesized_audio_url"] = audio_url
        message["audio_reference"]["audio_duration_seconds"] = duration
        message["audio_reference"]["generation_timestamp"] = datetime.utcnow().isoformat()
        
        return {
            "message_id": message_id,
            "chat_id": chat_id,
            "timestamp": message["timestamp"],
            "message_content": message["message_content"],
            "language_metadata": message["language_metadata"],
            "audio_playback": {
                "audio_url": audio_url,
                "audio_format": "mp3",
                "duration_seconds": duration,
                "tts_engine": message["audio_reference"]["tts_engine_used"],
                "cached": False
            }
        }
    
    def _generate_message_id(self, chat_id: str, text: str) -> str:
        """Generate unique message ID"""
        content = f"{chat_id}_{text}_{datetime.utcnow().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _select_tts_engine(self, language_code: str, dialect: Optional[str]) -> str:
        """
        Select appropriate TTS engine based on language and dialect
        
        Args:
            language_code: BCP 47 language code
            dialect: Optional dialect name
            
        Returns:
            TTS engine identifier
        """
        # Dialect-specific engines (use Bhashini)
        if dialect:
            dialect_lower = dialect.lower()
            if dialect_lower in ['bhojpuri', 'maithili', 'awadhi']:
                return f"bhashini-{dialect_lower}"
        
        # AWS Polly supported languages
        polly_languages = {
            'hi-IN': 'aws-polly-hi-IN',
            'bn-IN': 'aws-polly-bn-IN',
            'en-IN': 'aws-polly-en-IN',
            'ta-IN': 'aws-polly-ta-IN',
            'te-IN': 'aws-polly-te-IN',
            'ml-IN': 'aws-polly-ml-IN',
            'kn-IN': 'aws-polly-kn-IN'
        }
        
        return polly_languages.get(language_code, 'aws-polly-hi-IN')
    
    def _generate_and_cache_audio(
        self,
        text: str,
        language_code: str,
        language_name: str,
        dialect: Optional[str],
        message_id: str
    ) -> tuple[str, float]:
        """
        Generate TTS audio and cache it
        
        Args:
            text: Text to synthesize
            language_code: BCP 47 language code
            language_name: Language name
            dialect: Optional dialect
            message_id: Message identifier for caching
            
        Returns:
            Tuple of (audio_url, duration_seconds)
        """
        # Check cache first
        cache_key = f"{message_id}_{language_code}_{dialect}"
        if cache_key in self.audio_cache:
            cached = self.audio_cache[cache_key]
            return cached["url"], cached["duration"]
        
        # Generate audio based on language/dialect
        try:
            if dialect and dialect.lower() in ['bhojpuri', 'maithili', 'awadhi']:
                # Use Bhashini for dialects
                audio_url = synthesize_speech_bhashini(text, dialect.lower())
                duration = len(text.split()) * 0.5  # Rough estimate
            else:
                # Use AWS Polly for standard languages
                audio_url = synthesize_speech(text, language_code)
                duration = len(text.split()) * 0.5  # Rough estimate
            
            # Cache the result
            self.audio_cache[cache_key] = {
                "url": audio_url,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return audio_url, duration
            
        except Exception as e:
            print(f"Error generating audio: {e}")
            # Return empty URL on error
            return "", 0.0
    
    def _store_audio(self, audio_data: bytes, message_id: str, audio_type: str) -> str:
        """
        Store audio file (mock implementation)
        In production, upload to S3 and return pre-signed URL
        
        Args:
            audio_data: Audio bytes
            message_id: Message identifier
            audio_type: 'original' or 'synthesized'
            
        Returns:
            Audio URL
        """
        # Mock implementation - in production, upload to S3
        filename = f"{message_id}_{audio_type}.mp3"
        # In production: upload to S3 and return pre-signed URL
        return f"https://vidhi-audio.s3.ap-south-1.amazonaws.com/{filename}"
    
    def _get_script(self, language_code: str) -> str:
        """Get script name for language"""
        script_map = {
            'hi': 'Devanagari',
            'bn': 'Bengali',
            'ta': 'Tamil',
            'te': 'Telugu',
            'ml': 'Malayalam',
            'kn': 'Kannada',
            'gu': 'Gujarati',
            'mr': 'Devanagari',
            'pa': 'Gurmukhi',
            'or': 'Odia',
            'as': 'Bengali',
            'ur': 'Perso-Arabic',
            'en': 'Latin'
        }
        lang = language_code.split('-')[0]
        return script_map.get(lang, 'Unknown')


# Singleton instance
chat_history_service = ChatHistoryService()
