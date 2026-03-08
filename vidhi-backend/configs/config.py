"""
AWS Configuration for VIDHI Backend
Replaces Google services with AWS equivalents
"""
import os
from dotenv import load_dotenv

load_dotenv()

# AWS Configuration
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# S3 Buckets
S3_BUCKET_DOCUMENTS = os.getenv("S3_BUCKET_DOCUMENTS", "vidhi-documents-prod")
S3_BUCKET_AUDIO = os.getenv("S3_BUCKET_AUDIO", "vidhi-audio-prod")

# DynamoDB Tables
DYNAMODB_TABLE_USERS = os.getenv("DYNAMODB_TABLE_USERS", "vidhi-users")
DYNAMODB_TABLE_CHAT = os.getenv("DYNAMODB_TABLE_CHAT", "vidhi-chat-history")
DYNAMODB_TABLE_CACHE = os.getenv("DYNAMODB_TABLE_CACHE", "vidhi-response-cache")
DYNAMODB_TABLE_EMBEDDING_CACHE = os.getenv("DYNAMODB_TABLE_EMBEDDING_CACHE", "vidhi-embedding-cache")

# AWS Bedrock Configuration
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
BEDROCK_MODEL_ID_ADVANCED = os.getenv("BEDROCK_MODEL_ID_ADVANCED", "anthropic.claude-3-sonnet-20240229-v1:0")
BEDROCK_EMBEDDINGS_MODEL = os.getenv("BEDROCK_EMBEDDINGS_MODEL", "amazon.titan-embed-text-v1")

# AWS Polly Configuration (Text-to-Speech)
POLLY_VOICE_MAP = {
    'hi': {'VoiceId': 'Kajal', 'Engine': 'neural'},  # Hindi
    'bn': {'VoiceId': 'Tanishaa', 'Engine': 'neural'},  # Bengali
    'en': {'VoiceId': 'Kajal', 'Engine': 'neural'},  # Indian English
    # Add more as AWS adds support
}

# AWS Transcribe Configuration (Speech-to-Text)
TRANSCRIBE_SUPPORTED_LANGUAGES = [
    'hi-IN',  # Hindi
    'bn-IN',  # Bengali
    'ta-IN',  # Tamil
    'te-IN',  # Telugu
    'mr-IN',  # Marathi
    'gu-IN',  # Gujarati
    'kn-IN',  # Kannada
    'ml-IN',  # Malayalam
    'pa-IN',  # Punjabi
    'en-IN',  # English
]

# Bhashini API Configuration (for dialects not supported by AWS)
BHASHINI_API_KEY = os.getenv("BHASHINI_API_KEY")
BHASHINI_BASE_URL = "https://dhruva-api.bhashini.gov.in/services"
BHASHINI_USER_ID = os.getenv("BHASHINI_USER_ID")
BHASHINI_API_KEY_ULCA = os.getenv("BHASHINI_API_KEY_ULCA")

# Document Processing Configuration
CHUNK_SIZE = 2400
CHUNK_OVERLAP = 200

# Scraper Configuration
START_WEB_SCRAPING = os.getenv("START_WEB_SCRAPING", "False").lower() == "true"
SCHEMES_JSON_PATH = "myschemes_scraped.json"
SCHEMES_S3_KEY = "schemes/myschemes_scraped.json"

# Cache Configuration
RESPONSE_CACHE_TTL_HOURS = 24
EMBEDDING_CACHE_TTL_DAYS = 365

# API Configuration
API_RATE_LIMIT_PER_MINUTE = 100
API_RATE_LIMIT_ANONYMOUS = 20

# Legal Knowledge Base
LEGAL_DOCUMENTS_S3_PREFIX = "legal-docs/"
CONSTITUTION_S3_KEY = "legal-docs/constitution-of-india.json"

# Emergency Mode Configuration
EMERGENCY_CONTACTS = {
    "national_legal_aid": "15100",
    "women_helpline": "1091",
    "child_helpline": "1098",
    "police": "100",
}

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Feature Flags
ENABLE_VOICE_INPUT = os.getenv("ENABLE_VOICE_INPUT", "True").lower() == "true"
ENABLE_DOCUMENT_ANALYSIS = os.getenv("ENABLE_DOCUMENT_ANALYSIS", "True").lower() == "true"
ENABLE_SCHEME_MATCHING = os.getenv("ENABLE_SCHEME_MATCHING", "True").lower() == "true"
ENABLE_CACHING = os.getenv("ENABLE_CACHING", "True").lower() == "true"

# Cost Optimization
USE_BROWSER_STT_FIRST = True  # Use browser Web Speech API before AWS Transcribe
PRECOMPUTE_EMBEDDINGS = True  # Pre-compute embeddings for schemes
CACHE_COMMON_QUERIES = True  # Cache frequently asked questions


def get_embeddings():
    """
    Get AWS Bedrock embeddings instance.
    Lazy import to avoid issues when boto3 is not configured.
    """
    try:
        from langchain_aws import BedrockEmbeddings
        
        return BedrockEmbeddings(
            model_id=BEDROCK_EMBEDDINGS_MODEL,
            region_name=AWS_REGION
        )
    except ImportError as e:
        print(f"Warning: LangChain not installed: {e}")
        print("Trying HuggingFace embeddings fallback...")
        
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-mpnet-base-v2"
            )
        except ImportError:
            print("Warning: HuggingFace embeddings not available")
            print("Install with: pip install sentence-transformers")
            return None
    except Exception as e:
        print(f"Warning: Could not initialize Bedrock embeddings: {e}")
        print("This is normal if AWS is not configured yet")
        print("Run 'aws configure' to set up AWS credentials")
        return None


def validate_aws_config():
    """Validate that required AWS configuration is present"""
    required_vars = []
    
    if not AWS_ACCESS_KEY_ID:
        required_vars.append("AWS_ACCESS_KEY_ID")
    if not AWS_SECRET_ACCESS_KEY:
        required_vars.append("AWS_SECRET_ACCESS_KEY")
    
    if required_vars:
        print(f"Warning: Missing AWS configuration: {', '.join(required_vars)}")
        print("Set these in your .env file or environment variables")
        return False
    
    return True


# Validate on import
if __name__ != "__main__":
    validate_aws_config()
