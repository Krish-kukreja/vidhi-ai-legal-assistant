# VIDHI Backend

Voice-Integrated Defense for Holistic Inclusion - AI Legal Assistant Backend

## Overview

VIDHI backend is built with FastAPI and AWS services, providing:
- AI-powered legal guidance using AWS Bedrock (Claude)
- Multilingual support (22 Indian languages + dialects)
- Government scheme information (2,980+ schemes)
- Voice input/output with AWS Transcribe/Polly
- Document analysis capabilities
- Emergency legal rights information

## Architecture

- **LLM**: AWS Bedrock (Claude 3 Haiku/Sonnet)
- **Embeddings**: AWS Bedrock Titan Embeddings
- **Speech-to-Text**: AWS Transcribe + Bhashini (dialects)
- **Text-to-Speech**: AWS Polly + Bhashini (dialects)
- **Vector DB**: ChromaDB
- **Storage**: AWS S3
- **Database**: AWS DynamoDB
- **Framework**: FastAPI + LangChain

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure AWS

```bash
# Install AWS CLI
# Windows: Download from https://aws.amazon.com/cli/
# Linux/Mac: pip install awscli

# Configure credentials
aws configure
# Enter: Access Key ID, Secret Access Key, Region (ap-south-1)
```

### 3. Set Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# Required: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Optional: BHASHINI_API_KEY (for dialects)
```

### 4. Create AWS Resources

```bash
# Create S3 buckets
aws s3 mb s3://vidhi-documents-prod --region ap-south-1
aws s3 mb s3://vidhi-audio-prod --region ap-south-1

# Create DynamoDB tables
aws dynamodb create-table \
  --table-name vidhi-users \
  --attribute-definitions AttributeName=user_id,AttributeType=S \
  --key-schema AttributeName=user_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1

aws dynamodb create-table \
  --table-name vidhi-chat-history \
  --attribute-definitions \
    AttributeName=chat_id,AttributeType=S \
    AttributeName=message_id,AttributeType=S \
  --key-schema \
    AttributeName=chat_id,KeyType=HASH \
    AttributeName=message_id,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1

aws dynamodb create-table \
  --table-name vidhi-response-cache \
  --attribute-definitions AttributeName=query_hash,AttributeType=S \
  --key-schema AttributeName=query_hash,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1

aws dynamodb create-table \
  --table-name vidhi-embedding-cache \
  --attribute-definitions AttributeName=text_hash,AttributeType=S \
  --key-schema AttributeName=text_hash,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-south-1
```

### 5. Enable AWS Bedrock

```bash
# Go to AWS Console > Bedrock > Model access
# Request access to:
# - Claude 3 Haiku
# - Claude 3 Sonnet (optional)
# - Titan Embeddings
```

### 6. Scrape Government Schemes (Optional)

```bash
# Install Firefox and geckodriver for Selenium
# Windows: Download from https://github.com/mozilla/geckodriver/releases

# Run scraper (takes ~30 minutes)
python scraper.py

# This creates myschemes_scraped.json with 2,980+ schemes
```

### 7. Run the Server

```bash
# Development
python app.py

# Production with Uvicorn
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Health Check
```bash
GET /
GET /health
```

### Chat
```bash
POST /chat
Content-Type: multipart/form-data

Parameters:
- text (optional): Text query
- file (optional): Audio file
- language: Language name (hindi, bengali, etc.)
- language_code: BCP 47 code (hi-IN, bn-IN, etc.)
- use_aws_stt: Force AWS Transcribe usage

Response:
{
  "response": "AI response text",
  "audio_url": "https://...",
  "language": "hindi",
  "from_cache": false
}
```

### Emergency
```bash
POST /emergency
Content-Type: application/json

Body:
{
  "situation": "Description of emergency",
  "language": "hindi",
  "language_code": "hi-IN"
}

Response:
{
  "response": "Emergency rights information",
  "audio_url": "https://...",
  "emergency_contacts": {...},
  "language": "hindi"
}
```

### Supported Languages
```bash
GET /languages

Response:
{
  "aws_transcribe": ["hi-IN", "bn-IN", ...],
  "aws_polly": ["hi", "bn", "en"],
  "bhashini": {"bho": "Bhojpuri", ...}
}
```

## Testing

```bash
# Test with curl
curl -X POST http://localhost:8000/chat \
  -F "text=What are my rights during arrest?" \
  -F "language=hindi" \
  -F "language_code=hi-IN"

# Test emergency endpoint
curl -X POST http://localhost:8000/emergency \
  -H "Content-Type: application/json" \
  -d '{"situation": "Police detention", "language": "hindi"}'
```

## Deployment

### AWS Lambda

```bash
# Install deployment dependencies
pip install mangum

# Package for Lambda
zip -r vidhi-backend.zip . -x "*.git*" "*.pyc" "__pycache__/*" "venv/*"

# Upload to Lambda
aws lambda create-function \
  --function-name vidhi-backend \
  --runtime python3.11 \
  --handler app.handler \
  --zip-file fileb://vidhi-backend.zip \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-execution-role \
  --timeout 30 \
  --memory-size 1024 \
  --region ap-south-1
```

### Docker

```bash
# Build image
docker build -t vidhi-backend .

# Run container
docker run -p 8000:8000 --env-file .env vidhi-backend
```

## Cost Optimization

### Embedding Caching (90% savings)
- Pre-compute embeddings for all schemes
- Cache in DynamoDB with 1-year TTL
- Only compute embeddings for new queries

### Speech-to-Text (80% savings)
- Use browser Web Speech API as primary
- AWS Transcribe only as fallback
- Batch process audio files

### Response Caching (40% savings)
- Cache common queries in DynamoDB
- 24-hour TTL for scheme information
- Pre-generate responses for FAQs

### Estimated Monthly Cost
- Optimized: $155/month (10,000 users)
- Unoptimized: $465/month

## Troubleshooting

### AWS Credentials Error
```bash
# Check credentials
aws sts get-caller-identity

# Reconfigure if needed
aws configure
```

### Bedrock Access Denied
```bash
# Request model access in AWS Console
# Bedrock > Model access > Request access
```

### ChromaDB Error
```bash
# Delete and recreate vector store
rm -rf ./chroma_db
python app.py  # Will recreate on startup
```

### Scraper Not Working
```bash
# Install Firefox
# Download geckodriver: https://github.com/mozilla/geckodriver/releases
# Add geckodriver to PATH
```

## Project Structure

```
vidhi-backend/
├ app.py                      # Main FastAPI application
├ requirements.txt            # Python dependencies
├ .env.example               # Environment variables template
├ scraper.py                 # Government scheme scraper
├ myschemes_scraped.json     # Scraped schemes data
├ configs/
    config.py              # AWS configuration
├ llm_setup/
    bedrock_setup.py       # AWS Bedrock LLM
├ speech/
   ├ aws_transcribe.py      # AWS Transcribe (STT)
   ├ aws_polly.py           # AWS Polly (TTS)
    bhashini.py            # Bhashini API (dialects)
├ processing/
    documents.py           # Document processing
├ stores/
    chroma.py              # ChromaDB vector store
 utils/
     aws_helpers.py         # AWS utility functions
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

MIT License

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: support@vidhi.ai
- Documentation: [link]

## Acknowledgments

- Adapted from UdhaviBot architecture
- Uses AWS Bedrock (Claude) for AI
- Government scheme data from MyScheme.gov.in
- Bhashini API for regional dialects
