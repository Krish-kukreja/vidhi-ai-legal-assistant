"""
VIDHI Backend - FastAPI Application
Adapted from UdhaviBot with AWS services
"""
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import logging
import os
import time
from typing import Optional, List

# --- ADD THESE THREE LINES HERE ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.environ["USER_AGENT"] = "Vidhi-Backend-App/1.0"
# ----------------------------------

# Import configurations
from configs import config

# Try to import optional services - gracefully handle missing dependencies
try:
    from llm_setup.bedrock_setup import BedrockLLMService, EmergencyLLMService
    BEDROCK_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Bedrock LLM not available: {e}")
    BEDROCK_AVAILABLE = False
    BedrockLLMService = None
    EmergencyLLMService = None

try:
    from speech.aws_transcribe import AWSTranscribeService, HybridSpeechToText
    TRANSCRIBE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AWS Transcribe not available: {e}")
    TRANSCRIBE_AVAILABLE = False
    AWSTranscribeService = None

try:
    from speech.aws_polly import AWSPollyService, CachedPollyService
    POLLY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AWS Polly not available: {e}")
    POLLY_AVAILABLE = False
    AWSPollyService = None
    CachedPollyService = None

try:
    from speech.bhashini import BhashiniService
    BHASHINI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Bhashini not available: {e}")
    BHASHINI_AVAILABLE = False
    BhashiniService = None

try:
    from processing.documents import load_json_to_langchain_document_schema, create_scheme_documents
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Document processing not available: {e}")
    DOCUMENT_PROCESSING_AVAILABLE = False

try:
    from stores.chroma import store_embeddings, load_vectorstore, create_retriever
    CHROMA_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ChromaDB not available: {e}")
    CHROMA_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="VIDHI API",
    description="Voice-Integrated Defense for Holistic Inclusion - AI Legal Assistant",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
embeddings = None
vectorstore = None
retriever = None
llm_service = None
emergency_llm = None
transcribe_service = None
polly_service = None
bhashini_service = None

# Pydantic models
class ChatRequest(BaseModel):
    text: Optional[str] = None
    language: str = "hindi"
    language_code: str = "hi-IN"
    use_aws_stt: bool = False

class ChatResponse(BaseModel):
    response: str
    audio_url: Optional[str] = None
    language: str
    from_cache: bool = False

class EmergencyRequest(BaseModel):
    situation: str
    language: str = "hindi"
    language_code: str = "hi-IN"


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global embeddings, vectorstore, retriever, llm_service, emergency_llm
    global transcribe_service, polly_service, bhashini_service
    
    logger.info("Starting VIDHI backend...")
    logger.info(f"Available services: Bedrock={BEDROCK_AVAILABLE}, Chroma={CHROMA_AVAILABLE}, Transcribe={TRANSCRIBE_AVAILABLE}, Polly={POLLY_AVAILABLE}")
    
    try:
        # Initialize embeddings (only if Chroma is available)
        if CHROMA_AVAILABLE:
            logger.info("Initializing embeddings...")
            embeddings = config.get_embeddings()
        else:
            logger.warning("Skipping embeddings - ChromaDB not available")
        
        # Load or create vector store (only if Chroma is available)
        if CHROMA_AVAILABLE and embeddings:
            logger.info("Loading vector store...")
            vectorstore = load_vectorstore(embeddings)
            
            if vectorstore is None:
                logger.info("Vector store not found, creating new one...")
                
                # Check if schemes data exists
                if os.path.exists(config.SCHEMES_JSON_PATH) and DOCUMENT_PROCESSING_AVAILABLE:
                    logger.info(f"Loading schemes from {config.SCHEMES_JSON_PATH}")
                    
                    # Load schemes data
                    import json
                    with open(config.SCHEMES_JSON_PATH, 'r', encoding='utf-8') as f:
                        schemes_data = json.load(f)
                    
                    # Create documents
                    documents = create_scheme_documents(schemes_data)
                    logger.info(f"Created {len(documents)} scheme documents")
                    
                    # Store embeddings
                    vectorstore = store_embeddings(documents, embeddings)
                    logger.info("Vector store created successfully")
                else:
                    if not os.path.exists(config.SCHEMES_JSON_PATH):
                        logger.warning(f"Schemes file not found: {config.SCHEMES_JSON_PATH}")
                        logger.warning("Run scraper.py to download government schemes data")
                    if not DOCUMENT_PROCESSING_AVAILABLE:
                        logger.warning("Document processing not available")
        else:
            logger.warning("Skipping vector store - ChromaDB or embeddings not available")
        
        # Create retriever (only if vectorstore exists)
        if vectorstore and CHROMA_AVAILABLE:
            retriever = create_retriever(vectorstore)
            logger.info("Retriever created successfully")
            
        # Initialize LLM service (only if Bedrock is available)
        if BEDROCK_AVAILABLE:
            logger.info("Initializing Bedrock LLM service...")
            llm_service = BedrockLLMService(logger, retriever)
            
            if llm_service.error:
                logger.error(f"LLM service initialization error: {llm_service.error}")
            else:
                logger.info("LLM service initialized successfully")
        else:
            logger.warning("Skipping LLM service - Bedrock not available")
        
        # Initialize emergency LLM (only if Bedrock is available)
        if BEDROCK_AVAILABLE:
            logger.info("Initializing emergency LLM...")
            emergency_llm = EmergencyLLMService(logger)
        else:
            logger.warning("Skipping emergency LLM - Bedrock not available")
        
        # Initialize speech services
        if config.ENABLE_VOICE_INPUT:
            logger.info("Initializing speech services...")
            
            if TRANSCRIBE_AVAILABLE:
                transcribe_service = AWSTranscribeService(region=config.AWS_REGION)
            else:
                logger.warning("AWS Transcribe not available")
            
            if POLLY_AVAILABLE:
                polly_service = AWSPollyService(region=config.AWS_REGION)
                
                # Wrap Polly with caching
                polly_service = CachedPollyService(polly_service, config.S3_BUCKET_AUDIO)
            else:
                logger.warning("AWS Polly not available")
            
            # Initialize Bhashini for dialects
            if BHASHINI_AVAILABLE and config.BHASHINI_API_KEY:
                bhashini_service = BhashiniService(
                    api_key=config.BHASHINI_API_KEY,
                    user_id=config.BHASHINI_USER_ID
                )
                logger.info("Bhashini service initialized")
            else:
                if not BHASHINI_AVAILABLE:
                    logger.warning("Bhashini module not available")
                else:
                    logger.warning("Bhashini API key not configured")
        
        logger.info("VIDHI backend started successfully!")
        logger.info("Note: Some features may be limited due to missing optional dependencies")
        logger.info("To enable all features, install: pip install -r requirements.txt")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "VIDHI API",
        "status": "running",
        "version": "1.0.0",
        "features": {
            "voice_input": config.ENABLE_VOICE_INPUT,
            "document_analysis": config.ENABLE_DOCUMENT_ANALYSIS,
            "scheme_matching": config.ENABLE_SCHEME_MATCHING
        }
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "llm": llm_service is not None and llm_service.error is None,
            "vectorstore": vectorstore is not None,
            "transcribe": transcribe_service is not None,
            "polly": polly_service is not None,
            "bhashini": bhashini_service is not None
        }
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    text: Optional[str] = Form(None),
    files: List[UploadFile] = File(default=[]),
    language: str = Form("hindi"),
    language_code: str = Form("hi-IN"),
    use_aws_stt: bool = Form(False)
):
    """
    Main chat endpoint for VIDHI.
    Supports text and voice input.
    """
    try:
        user_input = None
        
        # Handle file input (voice or document)
        if files and len(files) > 0:
            extracted_texts = []
            audio_processed = False
            
            for file in files:
                logger.info(f"Processing uploaded file: {file.filename}")
                
                # Check if file has an actual filename (some frameworks send empty files for empty arrays)
                if not file.filename:
                    continue
                    
                # Read file data
                file_data = await file.read()
                mime_type = file.content_type
                
                # Check if it's an audio file
                is_audio = (mime_type and mime_type.startswith('audio/')) or file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg', '.webm'))

                
                if is_audio and not audio_processed:
                    # Only process the first audio file as voice input
                    audio_processed = True
                    # Use hybrid STT (browser first, AWS fallback)
                    if not use_aws_stt and config.USE_BROWSER_STT_FIRST:
                        return JSONResponse({
                            "use_browser_stt": True,
                            "message": "Please use browser speech recognition",
                            "supported_languages": config.TRANSCRIBE_SUPPORTED_LANGUAGES
                        })
                    
                    # Use AWS Transcribe
                    if transcribe_service:
                        # Detect media format from filename extension
                        fname = file.filename.lower()
                        if fname.endswith('.webm'):
                            media_format = 'webm'
                        elif fname.endswith('.ogg'):
                            media_format = 'ogg'
                        elif fname.endswith('.mp4') or fname.endswith('.m4a'):
                            media_format = 'mp4'
                        elif fname.endswith('.mp3'):
                            media_format = 'mp3'
                        elif fname.endswith('.flac'):
                            media_format = 'flac'
                        else:
                            media_format = 'wav'

                        # Upload to S3 and transcribe
                        timestamp = int(time.time())
                        s3_key = f"transcribe-input/{timestamp}.{media_format}"
                        s3_uri = transcribe_service.upload_audio_to_s3(
                            file_data,
                            config.S3_BUCKET_AUDIO,
                            s3_key
                        )
                        
                        result = transcribe_service.transcribe_audio(
                            s3_uri,
                            language_code,
                            identify_language=True,
                            media_format=media_format
                        )

                        
                        if result['success']:
                            # Using audio transcript as the main text
                            user_input = result['transcript']
                            language_code = result['language_code']
                            logger.info(f"Transcribed: {user_input[:50]}...")
                        else:
                            raise HTTPException(status_code=500, detail=result['error'])
                    else:
                        # AWS Transcribe is not configured — return graceful AI response
                        logger.warning("Transcribe service not available, returning fallback response")
                        return JSONResponse({
                            "response": "I received your voice message, but voice transcription (AWS Transcribe) is not currently configured on this server. Please type your question instead, or ask the administrator to set up AWS Transcribe.",
                            "audio_url": None,
                            "language": language,
                            "from_cache": False
                        })

                
                # If it's a document (PDF, DOCX, TXT, Image)
                elif not is_audio:
                    try:
                        import io
                        doc_text = ""
                        
                        if file.filename.lower().endswith('.pdf'):
                            import PyPDF2
                            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_data))
                            for page in pdf_reader.pages:
                                doc_text += page.extract_text() + "\n"
                        
                        elif file.filename.lower().endswith('.docx'):
                            import docx
                            doc = docx.Document(io.BytesIO(file_data))
                            doc_text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                        
                        elif file.filename.lower().endswith('.txt'):
                            doc_text = file_data.decode('utf-8')
                            
                        else:
                            doc_text = f"[User attached a file named {file.filename} but text extraction for this format is currently limited.]"
                        
                        extracted_texts.append(f"--- Document: {file.filename} ---\n{doc_text[:4000]}...")
                        logger.info(f"Extracted document text from {file.filename}")
                        
                    except Exception as e:
                        logger.error(f"Error parsing document {file.filename}: {str(e)}")
                        extracted_texts.append(f"--- Document: {file.filename} ---\n[Error extracting text]")
            
            # Combine all document texts
            if extracted_texts:
                combined_docs = "\n\n".join(extracted_texts)
                base_text = user_input if user_input else text
                if not base_text:
                    base_text = "Please analyze the attached document(s)."
                user_input = f"{base_text}\n\n[Attached Documents Content Start]\n{combined_docs}\n[Attached Documents Content End]"
                    
        # Handle text input without file
        elif text:
            user_input = text

        else:
            raise HTTPException(status_code=400, detail="Either text or audio file is required")
        
        # Safety guard — ensure user_input is never None at this point
        if not user_input:
            if text:
                user_input = text
            else:
                raise HTTPException(status_code=400, detail="Either text or audio file is required")

        # Query LLM with RAG
        if not llm_service or llm_service.error:
            raise HTTPException(status_code=503, detail="LLM service not available")
        
        logger.info(f"Querying LLM: {user_input[:50]}...")

        ai_response = llm_service.query(user_input, language)
        
        # Generate voice output
        audio_url = None
        if polly_service and config.ENABLE_VOICE_INPUT:
            logger.info("Generating voice output...")
            
            # Check if language is supported by AWS Polly
            if language_code in ['hi-IN', 'bn-IN', 'en-IN']:
                tts_result = polly_service.get_or_create_audio(
                    ai_response,
                    language_code
                )
                
                if tts_result['success']:
                    audio_url = tts_result['audio_url']
                    logger.info(f"Audio URL: {audio_url}")
            
            # Use Bhashini for dialects
            elif bhashini_service and bhashini_service.is_supported(language_code[:2]):
                logger.info(f"Using Bhashini for {language_code}")
                tts_result = bhashini_service.text_to_speech(
                    ai_response,
                    language_code[:2]
                )
                
                if tts_result['success']:
                    # Upload Bhashini audio to S3
                    import base64
                    audio_bytes = base64.b64decode(tts_result['audio_base64'])
                    
                    timestamp = int(time.time())
                    s3_key = f"tts/{timestamp}-{language_code}.mp3"
                    
                    import boto3
                    s3_client = boto3.client('s3', region_name=config.AWS_REGION)
                    s3_client.put_object(
                        Bucket=config.S3_BUCKET_AUDIO,
                        Key=s3_key,
                        Body=audio_bytes,
                        ContentType='audio/mpeg'
                    )
                    
                    audio_url = f"https://{config.S3_BUCKET_AUDIO}.s3.{config.AWS_REGION}.amazonaws.com/{s3_key}"
        
        return ChatResponse(
            response=ai_response,
            audio_url=audio_url,
            language=language,
            from_cache=False
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/emergency")
async def emergency(request: EmergencyRequest):
    """
    Emergency endpoint for urgent legal situations.
    Provides immediate rights information.
    """
    try:
        if not emergency_llm:
            raise HTTPException(status_code=503, detail="Emergency service not available")
        
        logger.info(f"Emergency request: {request.situation[:50]}...")
        
        # Get emergency rights information
        rights_info = emergency_llm.get_emergency_rights(
            request.situation,
            request.language
        )
        
        # Generate voice output
        audio_url = None
        if polly_service:
            tts_result = polly_service.get_or_create_audio(
                rights_info,
                request.language_code
            )
            
            if tts_result['success']:
                audio_url = tts_result['audio_url']
        
        return {
            "response": rights_info,
            "audio_url": audio_url,
            "emergency_contacts": config.EMERGENCY_CONTACTS,
            "language": request.language
        }
    
    except Exception as e:
        logger.error(f"Error in emergency endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return {
        "aws_transcribe": config.TRANSCRIBE_SUPPORTED_LANGUAGES,
        "aws_polly": list(config.POLLY_VOICE_MAP.keys()),
        "bhashini": bhashini_service.get_supported_languages() if bhashini_service else {}
    }


# For AWS Lambda deployment
try:
    from mangum import Mangum
    handler = Mangum(app)
except ImportError:
    logger.warning("Mangum not installed. Lambda deployment not available.")
    handler = None


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# Try to import new services - gracefully handle missing dependencies
try:
    from services.document_education import document_education_service
    DOCUMENT_EDUCATION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Document education service not available: {e}")
    DOCUMENT_EDUCATION_AVAILABLE = False
    document_education_service = None

try:
    from services.chat_history import chat_history_service
    CHAT_HISTORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Chat history service not available: {e}")
    CHAT_HISTORY_AVAILABLE = False
    chat_history_service = None

# Additional Pydantic models for new endpoints
class DocumentEducationRequest(BaseModel):
    document_text: str
    document_type: str  # rental_agreement, loan_contract, employment_contract, etc.
    language: str = "english"

class ClauseExplanationRequest(BaseModel):
    clause_text: str
    document_context: str
    language: str = "english"
    user_profile: Optional[dict] = None

class TermDefinitionRequest(BaseModel):
    term: str
    language: str = "english"
    context: Optional[str] = None

class InteractiveQARequest(BaseModel):
    question: str
    document_text: str
    conversation_history: list = []
    language: str = "english"

class TeachingSessionRequest(BaseModel):
    document_text: str
    document_type: str
    language: str = "english"

class MessagePlaybackRequest(BaseModel):
    chat_id: str
    message_id: str
    regenerate: bool = False


# ============================================================================
# DOCUMENT EDUCATION ENDPOINTS
# ============================================================================

@app.post("/api/v1/documents/simplify")
async def simplify_document(request: DocumentEducationRequest):
    """
    Simplify a legal document with section-by-section explanations
    
    This endpoint breaks down complex legal documents into understandable sections,
    providing simplified explanations, key points, and warnings.
    """
    try:
        logger.info(f"Simplifying {request.document_type} document in {request.language}")
        
        result = document_education_service.simplify_document(
            document_text=request.document_text,
            document_type=request.document_type,
            language=request.language
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error simplifying document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/explain-clause")
async def explain_clause(request: ClauseExplanationRequest):
    """
    Explain a specific clause in detail with personalized examples
    
    Provides detailed explanation of a clause with real-world examples
    tailored to the user's context.
    """
    try:
        logger.info(f"Explaining clause in {request.language}")
        
        result = document_education_service.explain_clause(
            clause_text=request.clause_text,
            document_context=request.document_context,
            language=request.language,
            user_profile=request.user_profile
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error explaining clause: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/define-term")
async def define_term(request: TermDefinitionRequest):
    """
    Define a legal term with simple explanations and examples
    
    Provides definitions from the legal glossary or generates explanations
    for terms not in the glossary.
    """
    try:
        logger.info(f"Defining term '{request.term}' in {request.language}")
        
        result = document_education_service.define_term(
            term=request.term,
            language=request.language,
            context=request.context
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error defining term: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/interactive-qa")
async def interactive_qa(request: InteractiveQARequest):
    """
    Answer user questions about a document interactively
    
    Maintains conversation context to provide helpful answers about
    specific aspects of the document.
    """
    try:
        logger.info(f"Interactive Q&A in {request.language}")
        
        answer = document_education_service.interactive_qa(
            question=request.question,
            document_text=request.document_text,
            conversation_history=request.conversation_history,
            language=request.language
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": {
                "question": request.question,
                "answer": answer,
                "language": request.language
            }
        })
        
    except Exception as e:
        logger.error(f"Error in interactive Q&A: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/documents/teaching-session")
async def create_teaching_session(request: TeachingSessionRequest):
    """
    Create a structured teaching session for a document
    
    Generates a step-by-step interactive teaching session to help users
    understand the document thoroughly.
    """
    try:
        logger.info(f"Creating teaching session for {request.document_type} in {request.language}")
        
        result = document_education_service.generate_teaching_session(
            document_text=request.document_text,
            document_type=request.document_type,
            language=request.language
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error creating teaching session: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# LANGUAGE-PRESERVED VOICE HISTORY ENDPOINTS
# ============================================================================

@app.post("/api/v1/history/save-message")
async def save_message(
    user_id: str = Form(...),
    chat_id: str = Form(...),
    message_text: str = Form(...),
    message_type: str = Form(...),
    language_code: str = Form(...),
    language_name: str = Form(...),
    dialect: Optional[str] = Form(None),
    input_mode: str = Form("text"),
    audio_file: Optional[UploadFile] = File(None)
):
    """
    Save a message with language metadata for future playback
    
    Stores messages with complete language information to enable
    accurate voice playback in the original language/dialect.
    """
    try:
        logger.info(f"Saving message for user {user_id} in {language_name}")
        
        # Read audio data if provided
        audio_data = None
        if audio_file:
            audio_data = await audio_file.read()
        
        message = chat_history_service.save_message(
            user_id=user_id,
            chat_id=chat_id,
            message_text=message_text,
            message_type=message_type,
            language_code=language_code,
            language_name=language_name,
            dialect=dialect,
            input_mode=input_mode,
            audio_data=audio_data
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": message
        })
        
    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history/{chat_id}")
async def get_chat_history(chat_id: str, limit: Optional[int] = None):
    """
    Retrieve chat history for a session
    
    Returns all messages in a chat session with language metadata.
    """
    try:
        logger.info(f"Retrieving chat history for {chat_id}")
        
        messages = chat_history_service.get_chat_history(chat_id, limit)
        
        return JSONResponse(content={
            "status": "success",
            "data": {
                "chat_id": chat_id,
                "message_count": len(messages),
                "messages": messages
            }
        })
        
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/history/{chat_id}/playback")
async def get_message_playback(
    chat_id: str,
    message_id: str,
    regenerate: bool = False
):
    """
    Get audio playback for a specific message in its original language
    
    This is the critical endpoint that enables language-preserved voice playback.
    When you replay a Bhojpuri message from 3 days ago, it plays in Bhojpuri,
    not standard Hindi.
    
    Args:
        chat_id: Chat session identifier
        message_id: Specific message to play back
        regenerate: Force regeneration of audio instead of using cache
        
    Returns:
        Audio URL with playback metadata
    """
    try:
        logger.info(f"Getting playback for message {message_id} in chat {chat_id}")
        
        playback_data = chat_history_service.get_message_playback(
            chat_id=chat_id,
            message_id=message_id,
            regenerate=regenerate
        )
        
        return JSONResponse(content={
            "status": "success",
            "data": playback_data
        })
        
    except ValueError as e:
        logger.error(f"Message not found: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting playback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/languages/supported")
async def get_supported_languages():
    """
    Get list of supported languages with TTS engine information
    
    Returns information about which languages are supported by AWS Polly,
    Bhashini, or browser fallback.
    """
    return JSONResponse(content={
        "status": "success",
        "data": {
            "aws_polly": [
                {"code": "hi-IN", "name": "Hindi", "quality": "premium"},
                {"code": "bn-IN", "name": "Bengali", "quality": "premium"},
                {"code": "en-IN", "name": "English", "quality": "premium"},
                {"code": "ta-IN", "name": "Tamil", "quality": "premium"},
                {"code": "te-IN", "name": "Telugu", "quality": "premium"},
                {"code": "ml-IN", "name": "Malayalam", "quality": "premium"},
                {"code": "kn-IN", "name": "Kannada", "quality": "premium"}
            ],
            "bhashini": [
                {"code": "bho", "name": "Bhojpuri", "dialect": True, "quality": "standard"},
                {"code": "mai", "name": "Maithili", "dialect": True, "quality": "standard"},
                {"code": "awa", "name": "Awadhi", "dialect": True, "quality": "standard"}
            ],
            "browser_fallback": [
                {"code": "gu-IN", "name": "Gujarati", "quality": "basic"},
                {"code": "mr-IN", "name": "Marathi", "quality": "basic"},
                {"code": "pa-IN", "name": "Punjabi", "quality": "basic"}
            ]
        }
    })
