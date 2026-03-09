"""
Bhashini API Integration for VIDHI
For regional dialects not supported by AWS (Bhojpuri, Maithili, etc.)
"""
import requests
import logging
import base64
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BhashiniService:
    """
    Bhashini API service for Indian language dialects.
    Free government service for languages not supported by AWS.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        user_id: Optional[str] = None,
        base_url: str = "https://dhruva-api.bhashini.gov.in/services"
    ):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = base_url
        
        # Supported languages
        self.supported_languages = {
            'bho': 'Bhojpuri',
            'mai': 'Maithili',
            'awa': 'Awadhi',
            'hi': 'Hindi',
            'bn': 'Bengali',
            'ta': 'Tamil',
            'te': 'Telugu',
            'mr': 'Marathi',
            'gu': 'Gujarati',
            'kn': 'Kannada',
            'ml': 'Malayalam',
            'pa': 'Punjabi',
            'or': 'Odia',
            'as': 'Assamese'
        }
    
    def speech_to_text(
        self,
        audio_base64: str,
        source_language: str = 'hi',
        audio_format: str = 'wav',
        sampling_rate: int = 16000
    ) -> Dict:
        """
        Convert speech to text using Bhashini ASR.
        
        Args:
            audio_base64: Base64 encoded audio
            source_language: Language code (bho, mai, hi, etc.)
            audio_format: Audio format
            sampling_rate: Sampling rate in Hz
        
        Returns:
            Dict with transcription result
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Bhashini API key not configured'
            }
        
        try:
            payload = {
                'pipelineTasks': [{
                    'taskType': 'asr',
                    'config': {
                        'language': {
                            'sourceLanguage': source_language
                        },
                        'audioFormat': audio_format,
                        'samplingRate': sampling_rate
                    }
                }],
                'inputData': {
                    'audio': [{
                        'audioContent': audio_base64
                    }]
                }
            }
            
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.base_url}/inference/pipeline",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            transcript = data['pipelineResponse'][0]['output'][0]['source']
            
            logger.info(f"Bhashini ASR successful for language: {source_language}")
            
            return {
                'success': True,
                'transcript': transcript,
                'language_code': source_language,
                'service': 'bhashini'
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Bhashini ASR request error: {e}")
            return {
                'success': False,
                'error': f"Request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Bhashini ASR error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def text_to_speech(
        self,
        text: str,
        target_language: str = 'hi',
        gender: str = 'female',
        sampling_rate: int = 16000
    ) -> Dict:
        """
        Convert text to speech using Bhashini TTS.
        
        Args:
            text: Text to convert
            target_language: Language code
            gender: Voice gender (male/female)
            sampling_rate: Sampling rate in Hz
        
        Returns:
            Dict with audio content (base64)
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Bhashini API key not configured'
            }
        
        try:
            payload = {
                'pipelineTasks': [{
                    'taskType': 'tts',
                    'config': {
                        'language': {
                            'sourceLanguage': target_language
                        },
                        'gender': gender,
                        'samplingRate': sampling_rate
                    }
                }],
                'inputData': {
                    'input': [{
                        'source': text
                    }]
                }
            }
            
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.base_url}/inference/pipeline",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            audio_content = data['pipelineResponse'][0]['audio'][0]['audioContent']
            
            logger.info(f"Bhashini TTS successful for language: {target_language}")
            
            return {
                'success': True,
                'audio_base64': audio_content,
                'language_code': target_language,
                'service': 'bhashini'
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Bhashini TTS request error: {e}")
            return {
                'success': False,
                'error': f"Request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Bhashini TTS error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> Dict:
        """
        Translate text between languages.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
        
        Returns:
            Dict with translated text
        """
        if not self.api_key:
            return {
                'success': False,
                'error': 'Bhashini API key not configured'
            }
        
        try:
            payload = {
                'pipelineTasks': [{
                    'taskType': 'translation',
                    'config': {
                        'language': {
                            'sourceLanguage': source_language,
                            'targetLanguage': target_language
                        }
                    }
                }],
                'inputData': {
                    'input': [{
                        'source': text
                    }]
                }
            }
            
            headers = {
                'Authorization': self.api_key,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.base_url}/inference/pipeline",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            translated_text = data['pipelineResponse'][0]['output'][0]['target']
            
            logger.info(f"Bhashini translation: {source_language} -> {target_language}")
            
            return {
                'success': True,
                'translated_text': translated_text,
                'source_language': source_language,
                'target_language': target_language,
                'service': 'bhashini'
            }
        
        except Exception as e:
            logger.error(f"Bhashini translation error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_supported(self, language_code: str) -> bool:
        """Check if language is supported by Bhashini"""
        return language_code in self.supported_languages
    
    def get_supported_languages(self) -> Dict:
        """Get list of supported languages"""
        return self.supported_languages
