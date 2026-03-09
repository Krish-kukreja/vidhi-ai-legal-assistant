"""
AWS Polly Service for VIDHI
Replaces Google Cloud Text-to-Speech
"""
import boto3
import time
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class AWSPollyService:
    """
    AWS Polly service for text-to-speech conversion.
    Supports Hindi, Bengali, and English with neural voices.
    """
    
    def __init__(self, region: str = "ap-south-1"):
        self.polly = boto3.client('polly', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.region = region
        
        # Voice mapping for supported languages
        self.voice_map = {
            'hi': {'VoiceId': 'Kajal', 'Engine': 'neural', 'LanguageCode': 'hi-IN'},
            'hi-IN': {'VoiceId': 'Kajal', 'Engine': 'neural', 'LanguageCode': 'hi-IN'},
            'bn': {'VoiceId': 'Tanishaa', 'Engine': 'neural', 'LanguageCode': 'bn-IN'},
            'bn-IN': {'VoiceId': 'Tanishaa', 'Engine': 'neural', 'LanguageCode': 'bn-IN'},
            'en': {'VoiceId': 'Kajal', 'Engine': 'neural', 'LanguageCode': 'en-IN'},
            'en-IN': {'VoiceId': 'Kajal', 'Engine': 'neural', 'LanguageCode': 'en-IN'},
        }
    
    def synthesize_speech(
        self,
        text: str,
        language_code: str = 'hi-IN',
        output_format: str = 'mp3'
    ) -> Dict:
        """
        Convert text to speech using AWS Polly.
        
        Args:
            text: Text to convert
            language_code: Language code (hi-IN, bn-IN, en-IN)
            output_format: Audio format (mp3, ogg_vorbis, pcm)
        
        Returns:
            Dict with audio stream and metadata
        """
        try:
            # Get voice configuration
            voice_config = self.voice_map.get(
                language_code,
                self.voice_map['hi-IN']  # Default to Hindi
            )
            
            # Synthesize speech
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat=output_format,
                VoiceId=voice_config['VoiceId'],
                Engine=voice_config['Engine'],
                LanguageCode=voice_config['LanguageCode']
            )
            
            # Read audio stream
            audio_stream = response['AudioStream'].read()
            
            logger.info(f"Synthesized speech: {len(text)} chars, {len(audio_stream)} bytes")
            
            return {
                'success': True,
                'audio_stream': audio_stream,
                'content_type': response['ContentType'],
                'language_code': language_code,
                'voice_id': voice_config['VoiceId']
            }
        
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def synthesize_and_upload_to_s3(
        self,
        text: str,
        bucket: str,
        language_code: str = 'hi-IN',
        key_prefix: str = 'tts/'
    ) -> Dict:
        """
        Synthesize speech and upload to S3.
        
        Args:
            text: Text to convert
            bucket: S3 bucket name
            language_code: Language code
            key_prefix: S3 key prefix
        
        Returns:
            Dict with S3 URL and metadata
        """
        try:
            # Synthesize speech
            result = self.synthesize_speech(text, language_code)
            
            if not result['success']:
                return result
            
            # Generate S3 key
            timestamp = int(time.time())
            key = f"{key_prefix}{timestamp}-{language_code}.mp3"
            
            # Upload to S3
            self.s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=result['audio_stream'],
                ContentType='audio/mpeg',
                Metadata={
                    'language': language_code,
                    'voice_id': result['voice_id'],
                    'text_length': str(len(text))
                }
            )
            
            # Generate public URL
            audio_url = f"https://{bucket}.s3.{self.region}.amazonaws.com/{key}"
            
            logger.info(f"Uploaded TTS audio to: {audio_url}")
            
            return {
                'success': True,
                'audio_url': audio_url,
                'audio_key': key,
                'language_code': language_code,
                'voice_id': result['voice_id'],
                'duration_estimate': len(text) / 15  # Rough estimate: 15 chars/second
            }
        
        except Exception as e:
            logger.error(f"Error synthesizing and uploading: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_presigned_url(
        self,
        bucket: str,
        key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for audio file.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            expiration: URL expiration in seconds
        
        Returns:
            Presigned URL
        """
        try:
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return ""
    
    def batch_synthesize(
        self,
        texts: list,
        bucket: str,
        language_code: str = 'hi-IN'
    ) -> list:
        """
        Batch synthesize multiple texts.
        
        Args:
            texts: List of texts to synthesize
            bucket: S3 bucket name
            language_code: Language code
        
        Returns:
            List of results
        """
        results = []
        
        for text in texts:
            result = self.synthesize_and_upload_to_s3(
                text, bucket, language_code
            )
            results.append(result)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        logger.info(f"Batch synthesized {len(texts)} texts")
        return results


class CachedPollyService:
    """
    Wrapper around Polly that caches generated audio in S3.
    Reduces costs by reusing audio for common responses.
    """
    
    def __init__(self, polly_service: AWSPollyService, cache_bucket: str):
        self.polly = polly_service
        self.cache_bucket = cache_bucket
        self.s3 = boto3.client('s3', region_name=polly_service.region)
    
    def get_or_create_audio(
        self,
        text: str,
        language_code: str = 'hi-IN'
    ) -> Dict:
        """
        Get cached audio or create new one.
        
        Args:
            text: Text to convert
            language_code: Language code
        
        Returns:
            Dict with audio URL
        """
        import hashlib
        
        # Generate cache key
        text_hash = hashlib.sha256(f"{text}-{language_code}".encode()).hexdigest()
        cache_key = f"tts-cache/{language_code}/{text_hash}.mp3"
        
        try:
            # Check if cached audio exists
            self.s3.head_object(Bucket=self.cache_bucket, Key=cache_key)
            
            # Audio exists, return URL
            audio_url = f"https://{self.cache_bucket}.s3.{self.polly.region}.amazonaws.com/{cache_key}"
            
            logger.info(f"Using cached audio: {cache_key}")
            
            return {
                'success': True,
                'audio_url': audio_url,
                'audio_key': cache_key,
                'cached': True,
                'language_code': language_code
            }
        
        except self.s3.exceptions.ClientError:
            # Audio doesn't exist, create it
            logger.info(f"Cache miss, generating new audio: {text[:50]}...")
            
            result = self.polly.synthesize_speech(text, language_code)
            
            if not result['success']:
                return result
            
            # Upload to cache
            self.s3.put_object(
                Bucket=self.cache_bucket,
                Key=cache_key,
                Body=result['audio_stream'],
                ContentType='audio/mpeg',
                Metadata={
                    'language': language_code,
                    'text_hash': text_hash
                }
            )
            
            audio_url = f"https://{self.cache_bucket}.s3.{self.polly.region}.amazonaws.com/{cache_key}"
            
            return {
                'success': True,
                'audio_url': audio_url,
                'audio_key': cache_key,
                'cached': False,
                'language_code': language_code
            }
