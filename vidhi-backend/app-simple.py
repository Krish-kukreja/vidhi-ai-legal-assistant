"""
VIDHI Backend - Simple Version (No Pydantic Models)
For Python 3.13 compatibility
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
import logging
import os
import time
from typing import Optional

# Initialize FastAPI app
app = FastAPI(
    title="VIDHI API",
    description="Voice-Integrated Defense for Holistic Inclusion - AI Legal Assistant",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Try to import configurations
try:
    from configs import config
    CONFIG_AVAILABLE = True
    logger.info("Configuration loaded successfully")
except ImportError as e:
    logger.warning(f"Configuration not available: {e}")
    CONFIG_AVAILABLE = False

# Initialize service availability flags
BEDROCK_AVAILABLE = False
TRANSCRIBE_AVAILABLE = False
POLLY_AVAILABLE = False
BHASHINI_AVAILABLE = False
CHROMA_AVAILABLE = False

# Try to import services
try:
    from llm_setup.bedrock_setup import BedrockLLMService, EmergencyLLMService
    BEDROCK_AVAILABLE = True
    logger.info("Bedrock services available")
except ImportError as e:
    logger.warning(f"Bedrock services not available: {e}")

try:
    from speech.aws_transcribe import AWSTranscribeService
    TRANSCRIBE_AVAILABLE = True
    logger.info("Transcribe service available")
except ImportError as e:
    logger.warning(f"Transcribe service not available: {e}")

try:
    from speech.aws_polly import AWSPollyService, CachedPollyService
    POLLY_AVAILABLE = True
    logger.info("Polly service available")
except ImportError as e:
    logger.warning(f"Polly service not available: {e}")

try:
    from speech.bhashini import BhashiniService
    BHASHINI_AVAILABLE = False # Disabled by user request
    logger.info("Bhashini service imported but set to False")
except ImportError as e:
    logger.warning(f"Bhashini service not available: {e}")

try:
    from stores.chroma import store_embeddings, load_vectorstore, create_retriever
    CHROMA_AVAILABLE = True
    logger.info("ChromaDB available")
except ImportError as e:
    logger.warning(f"ChromaDB not available: {e}")

# Global service instances
llm_service = None
emergency_llm = None
transcribe_service = None
polly_service = None
bhashini_service = None
vectorstore = None
retriever = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global llm_service, emergency_llm, transcribe_service, polly_service, bhashini_service
    
    logger.info("Starting VIDHI backend...")
    logger.info(f"Available services: Bedrock={BEDROCK_AVAILABLE}, Chroma={CHROMA_AVAILABLE}")
    logger.info(f"Transcribe={TRANSCRIBE_AVAILABLE}, Polly={POLLY_AVAILABLE}, Bhashini={BHASHINI_AVAILABLE}")
    
    # Initialize services if available and configured
    if BEDROCK_AVAILABLE and CONFIG_AVAILABLE:
        try:
            # Initialize LLM services
            logger.info("Initializing Bedrock services...")
            llm_service = BedrockLLMService(logger, retriever=vectorstore)
            if llm_service.error:
                logger.error(f"Error initializing primary BedrockLLMService: {llm_service.error}")
            else:
                logger.info("Primary Bedrock LLM initialized")
                
            emergency_llm = EmergencyLLMService(logger)
            if emergency_llm.error:
                logger.error(f"Error from within EmergencyLLMService: {emergency_llm.error}")
            else:
                logger.info("Emergency LLM initialized")
        except Exception as e:
            logger.error(f"Error initializing Bedrock services: {e}", exc_info=True)
    
    if TRANSCRIBE_AVAILABLE and CONFIG_AVAILABLE:
        try:
            transcribe_service = AWSTranscribeService(region=config.AWS_REGION)
            logger.info("Transcribe service initialized")
        except Exception as e:
            logger.error(f"Error initializing Transcribe: {e}")
    
    if POLLY_AVAILABLE and CONFIG_AVAILABLE:
        try:
            polly_service = AWSPollyService(region=config.AWS_REGION)
            logger.info("Polly service initialized")
        except Exception as e:
            logger.error(f"Error initializing Polly: {e}")
    
    logger.info("VIDHI backend started successfully!")
    logger.info("Note: Some features may be limited due to missing optional dependencies")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "VIDHI API",
        "status": "running",
        "version": "1.0.0",
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "features": {
            "config_available": CONFIG_AVAILABLE,
            "bedrock_available": BEDROCK_AVAILABLE,
            "transcribe_available": TRANSCRIBE_AVAILABLE,
            "polly_available": POLLY_AVAILABLE,
            "chroma_available": CHROMA_AVAILABLE
        }
    }


@app.get("/favicon.ico")
async def favicon():
    """Return 204 for favicon requests to avoid 404 errors"""
    return Response(status_code=204)


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "config": CONFIG_AVAILABLE,
            "llm": llm_service is not None,
            "emergency_llm": emergency_llm is not None,
            "vectorstore": vectorstore is not None,
            "transcribe": transcribe_service is not None,
            "polly": polly_service is not None,
            "bhashini": bhashini_service is not None
        },
        "dependencies": {
            "bedrock": BEDROCK_AVAILABLE,
            "transcribe": TRANSCRIBE_AVAILABLE,
            "polly": POLLY_AVAILABLE,
            "chroma": CHROMA_AVAILABLE,
            "bhashini": BHASHINI_AVAILABLE
        }
    }


@app.post("/chat")
async def chat(
    text: Optional[str] = Form(None),
    language: str = Form("english"),
    language_code: str = Form("en-IN")
):
    """
    Simple chat endpoint for VIDHI.
    Returns basic response until full services are configured.
    """
    try:
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        logger.info(f"Chat request: {text[:50]}... in {language}")
        
        # If primary LLM is available, use it
        if llm_service:
            try:
                response = llm_service.get_response(text, language)
                return {
                    "response": response,
                    "language": language,
                    "source": "bedrock_llm",
                    "audio_url": None
                }
            except Exception as e:
                logger.error(f"Error with Bedrock LLM: {e}")
        
        # Fallback response
        fallback_responses = {
            "english": "I'm VIDHI, your legal assistant. I'm currently starting up and configuring AWS services. Please ensure AWS Bedrock is configured for full functionality. Your question has been received.",
            "hindi": "मैं विधि हूं, आपका कानूनी सहायक। मैं वर्तमान में AWS सेवाओं को कॉन्फ़िगर कर रहा हूं। पूर्ण कार्यक्षमता के लिए कृपया AWS Bedrock को कॉन्फ़िगर करें।",
            "bengali": "আমি বিধি, আপনার আইনি সহায়ক। আমি বর্তমানে AWS সেবা কনফিগার করছি। সম্পূর্ণ কার্যকারিতার জন্য AWS Bedrock কনফিগার করুন।"
        }
        
        response_text = fallback_responses.get(language.lower(), fallback_responses["english"])
        
        return {
            "response": response_text,
            "language": language,
            "source": "fallback",
            "audio_url": None,
            "note": "Configure AWS Bedrock for full AI functionality"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emergency")
async def emergency(
    situation: str = Form(...),
    language: str = Form("english"),
    language_code: str = Form("en-IN")
):
    """
    Emergency endpoint for urgent legal situations.
    """
    try:
        logger.info(f"Emergency request: {situation[:50]}...")
        
        if emergency_llm:
            try:
                rights_info = emergency_llm.get_emergency_rights(situation, language)
                return {
                    "response": rights_info,
                    "language": language,
                    "source": "bedrock_emergency",
                    "emergency_contacts": {
                        "national_legal_aid": "15100",
                        "women_helpline": "1091",
                        "child_helpline": "1098",
                        "police": "100"
                    }
                }
            except Exception as e:
                logger.error(f"Error with emergency LLM: {e}")
        
        # Fallback emergency response
        emergency_response = """EMERGENCY LEGAL RIGHTS (India):

1. Right to remain silent (Article 20)
2. Right to legal counsel (Article 22)
3. Right to inform family/friend of arrest
4. No torture or coercion allowed
5. Medical examination within 48 hours if arrested

EMERGENCY CONTACTS:
- National Legal Aid: 15100
- Police: 100
- Women Helpline: 1091
- Child Helpline: 1098

This is a basic response. Configure AWS Bedrock for detailed legal guidance."""

        return {
            "response": emergency_response,
            "language": language,
            "source": "fallback_emergency",
            "emergency_contacts": {
                "national_legal_aid": "15100",
                "women_helpline": "1091", 
                "child_helpline": "1098",
                "police": "100"
            }
        }
    
    except Exception as e:
        logger.error(f"Error in emergency endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "status": "success",
        "data": {
            "core_languages": [
                {"code": "en-IN", "name": "English", "supported": True},
                {"code": "hi-IN", "name": "Hindi", "supported": True},
                {"code": "bn-IN", "name": "Bengali", "supported": True}
            ],
            "aws_polly": [
                {"code": "hi-IN", "name": "Hindi", "available": POLLY_AVAILABLE},
                {"code": "bn-IN", "name": "Bengali", "available": POLLY_AVAILABLE},
                {"code": "en-IN", "name": "English", "available": POLLY_AVAILABLE}
            ],
            "aws_transcribe": [
                {"code": "hi-IN", "name": "Hindi", "available": TRANSCRIBE_AVAILABLE},
                {"code": "bn-IN", "name": "Bengali", "available": TRANSCRIBE_AVAILABLE},
                {"code": "en-IN", "name": "English", "available": TRANSCRIBE_AVAILABLE}
            ],
            "note": "Full language support available after AWS configuration"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)