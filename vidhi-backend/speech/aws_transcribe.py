"""
AWS Transcribe Service for VIDHI
Replaces Google Gemini Audio API
"""
import boto3
import time
import logging
import json
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class AWSTranscribeService:
    """
    AWS Transcribe service for speech-to-text conversion.
    Supports 9 Indian languages.
    """
    
    def __init__(self, region: str = "ap-south-1"):
        self.transcribe = boto3.client('transcribe', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.region = region
    
    def transcribe_audio(
        self,
        audio_s3_uri: str,
        language_code: str = 'hi-IN',
        job_name: Optional[str] = None,
        identify_language: bool = False,
        media_format: str = 'wav'
    ) -> Dict:
        """
        Transcribe audio file from S3.
        
        Args:
            audio_s3_uri: S3 URI of audio file (s3://bucket/key)
            language_code: Language code (hi-IN, bn-IN, etc.)
            job_name: Optional job name
            identify_language: Auto-detect language
            media_format: Audio format (wav, webm, ogg, mp4, flac, mp3)
        
        Returns:
            Dict with transcription results
        """
        if not job_name:
            job_name = f"vidhi-transcribe-{int(time.time())}"
        
        try:
            params = {
                'TranscriptionJobName': job_name,
                'Media': {'MediaFileUri': audio_s3_uri},
                'MediaFormat': media_format,
                # Note: NOT setting OutputBucketName here.
                # When omitted, AWS returns a pre-signed HTTPS URL we can fetch with requests.get().
                # When set, AWS returns an s3:// URI which requires boto3 to read.
            }
            
            if identify_language:
                # Auto-detect language from supported list
                params['IdentifyLanguage'] = True
                params['LanguageOptions'] = [
                    'hi-IN', 'bn-IN', 'ta-IN', 'te-IN', 'mr-IN',
                    'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN', 'en-IN'
                ]
            else:
                params['LanguageCode'] = language_code
            
            # Start transcription job
            self.transcribe.start_transcription_job(**params)
            logger.info(f"Started transcription job: {job_name}")
            
            # Wait for completion
            while True:
                result = self.transcribe.get_transcription_job(
                    TranscriptionJobName=job_name
                )
                status = result['TranscriptionJob']['TranscriptionJobStatus']
                
                if status in ['COMPLETED', 'FAILED']:
                    break
                
                logger.debug(f"Transcription job {job_name} status: {status}")
                time.sleep(2)
            
            if status == 'COMPLETED':
                # Get transcript
                transcript_uri = result['TranscriptionJob']['Transcript']['TranscriptFileUri']
                transcript_data = self._download_transcript(transcript_uri)
                
                detected_language = result['TranscriptionJob'].get('LanguageCode', language_code)
                
                try:
                    transcript_text = transcript_data['results']['transcripts'][0]['transcript']
                except (KeyError, IndexError, TypeError) as e:
                    logger.error(f"Error parsing transcript data: {e}. Data received: {str(transcript_data)[:200]}")
                    return {
                        'success': False,
                        'error': 'Could not parse transcription result from AWS. The audio may be too short or unclear.'
                    }

                return {
                    'success': True,
                    'transcript': transcript_text,
                    'language_code': detected_language,
                    'confidence': self._get_average_confidence(transcript_data),
                    'job_name': job_name
                }

            else:
                failure_reason = result['TranscriptionJob'].get('FailureReason', 'Unknown')
                logger.error(f"Transcription failed: {failure_reason}")
                return {
                    'success': False,
                    'error': failure_reason
                }
        
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _download_transcript(self, transcript_uri: str) -> Dict:
        """Download transcript JSON from S3 — handles both s3:// and https:// URIs."""
        try:
            if transcript_uri.startswith('s3://'):
                # Parse s3://bucket/key
                parts = transcript_uri[5:].split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ''
                logger.info(f"Downloading transcript from S3: bucket={bucket}, key={key}")
                response = self.s3.get_object(Bucket=bucket, Key=key)
                import json
                return json.loads(response['Body'].read().decode('utf-8'))
            else:
                # Pre-signed HTTPS URL — download directly
                response = requests.get(transcript_uri, timeout=30)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error downloading transcript from {transcript_uri}: {e}")
            return {}

    
    def _get_average_confidence(self, transcript_data: Dict) -> float:
        """Calculate average confidence score"""
        try:
            items = transcript_data['results']['items']
            confidences = [
                float(item['alternatives'][0]['confidence'])
                for item in items
                if 'confidence' in item.get('alternatives', [{}])[0]
            ]
            return sum(confidences) / len(confidences) if confidences else 0.0
        except Exception:
            return 0.0
    
    def upload_audio_to_s3(
        self,
        audio_data: bytes,
        bucket: str,
        key: str,
        content_type: str = 'audio/wav'
    ) -> str:
        """
        Upload audio file to S3.
        
        Args:
            audio_data: Audio file bytes
            bucket: S3 bucket name
            key: S3 object key
            content_type: MIME type
        
        Returns:
            S3 URI
        """
        try:
            self.s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=audio_data,
                ContentType=content_type
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            logger.info(f"Uploaded audio to: {s3_uri}")
            return s3_uri
        
        except Exception as e:
            logger.error(f"Error uploading audio to S3: {e}")
            raise
    
    def transcribe_from_file(
        self,
        audio_file_path: str,
        bucket: str,
        language_code: str = 'hi-IN'
    ) -> Dict:
        """
        Transcribe audio from local file.
        
        Args:
            audio_file_path: Path to local audio file
            bucket: S3 bucket to upload to
            language_code: Language code
        
        Returns:
            Transcription results
        """
        try:
            # Read audio file
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()
            
            # Upload to S3
            key = f"transcribe-input/{int(time.time())}.wav"
            s3_uri = self.upload_audio_to_s3(audio_data, bucket, key)
            
            # Transcribe
            return self.transcribe_audio(s3_uri, language_code)
        
        except Exception as e:
            logger.error(f"Error transcribing from file: {e}")
            return {
                'success': False,
                'error': str(e)
            }


class HybridSpeechToText:
    """
    Hybrid speech-to-text service that uses browser API first, AWS as fallback.
    This reduces costs by 80%.
    """
    
    def __init__(self, aws_transcribe: AWSTranscribeService):
        self.aws_transcribe = aws_transcribe
    
    def transcribe(
        self,
        audio_data: bytes = None,
        use_aws: bool = False,
        language_code: str = 'hi-IN'
    ) -> Dict:
        """
        Transcribe audio with hybrid approach.
        
        Args:
            audio_data: Audio bytes (if using AWS)
            use_aws: Force AWS Transcribe usage
            language_code: Language code
        
        Returns:
            Transcription result or instruction to use browser
        """
        if not use_aws:
            # Instruct frontend to use browser Web Speech API
            return {
                'use_browser': True,
                'message': 'Please use browser speech recognition for better performance',
                'supported_languages': [
                    'hi-IN', 'bn-IN', 'ta-IN', 'te-IN', 'mr-IN',
                    'gu-IN', 'kn-IN', 'ml-IN', 'pa-IN', 'en-IN'
                ]
            }
        else:
            # Use AWS Transcribe as fallback
            if not audio_data:
                return {
                    'success': False,
                    'error': 'Audio data required for AWS transcription'
                }
            
            # Upload and transcribe
            bucket = 'vidhi-audio-prod'
            key = f"transcribe-input/{int(time.time())}.wav"
            s3_uri = self.aws_transcribe.upload_audio_to_s3(
                audio_data, bucket, key
            )
            
            return self.aws_transcribe.transcribe_audio(s3_uri, language_code)
