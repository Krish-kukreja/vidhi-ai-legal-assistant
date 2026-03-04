# VIDHI Backend - Step-by-Step Installation (Windows)

## Current Situation

You're getting Rust compilation errors because some Python packages need to be compiled from source. We'll work around this by installing only pre-built packages first.

## Quick Start (Copy-Paste These Commands)

### Step 1: Navigate to Backend Directory

```bash
cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-backend
```

### Step 2: Activate Virtual Environment

```bash
venv\Scripts\activate
```

You should see `(venv)` at the start of your command prompt.

### Step 3: Install Minimal Dependencies

```bash
pip install -r requirements-windows-minimal.txt
```

This installs only packages with pre-built Windows wheels (no compilation needed).

### Step 4: Test Backend Startup

```bash
python app.py
```

Expected output:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
WARNING:  Bedrock LLM not available: No module named 'langchain'
WARNING:  ChromaDB not available: No module named 'chromadb'
INFO:     VIDHI backend started successfully!
INFO:     Note: Some features may be limited due to missing optional dependencies
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The warnings are NORMAL! The backend will work once AWS is configured.

### Step 5: Test in Browser

Open: http://localhost:8000

You should see:
```json
{
  "service": "VIDHI API",
  "status": "running",
  "version": "1.0.0"
}
```

## What Just Happened?

✅ Backend server is running
✅ FastAPI is working
✅ Basic endpoints are accessible
⚠️ AWS services not configured yet (that's next)
⚠️ Optional features disabled (RAG, vector search)

## Next: Configure AWS Services

Now that the backend runs, follow these steps to enable full functionality:

### 1. Install AWS CLI

Download from: https://aws.amazon.com/cli/

Or use:
```bash
pip install awscli
```

### 2. Configure AWS Credentials

```bash
aws configure
```

Enter:
- AWS Access Key ID: (from AWS Console)
- AWS Secret Access Key: (from AWS Console)
- Default region: `ap-south-1` (Mumbai)
- Default output format: `json`

### 3. Create S3 Buckets

```bash
# For audio files
aws s3 mb s3://vidhi-audio-prod --region ap-south-1

# For documents
aws s3 mb s3://vidhi-documents-prod --region ap-south-1
```

### 4. Create DynamoDB Tables

```bash
# Users table
aws dynamodb create-table \
    --table-name vidhi-users \
    --attribute-definitions AttributeName=user_id,AttributeType=S \
    --key-schema AttributeName=user_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-south-1

# Chat history table
aws dynamodb create-table \
    --table-name vidhi-chat-history \
    --attribute-definitions AttributeName=chat_id,AttributeType=S AttributeName=message_id,AttributeType=S \
    --key-schema AttributeName=chat_id,KeyType=HASH AttributeName=message_id,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region ap-south-1

# Response cache table
aws dynamodb create-table \
    --table-name vidhi-response-cache \
    --attribute-definitions AttributeName=query_hash,AttributeType=S \
    --key-schema AttributeName=query_hash,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region ap-south-1
```

### 5. Enable Bedrock Models

1. Go to AWS Console: https://console.aws.amazon.com/bedrock/
2. Select region: **ap-south-1 (Mumbai)**
3. Click "Model access" in left sidebar
4. Models are now auto-enabled (no manual request needed)
5. Verify Claude 3 Haiku is available

### 6. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

Edit `.env` and fill in:
```
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

S3_BUCKET_DOCUMENTS=vidhi-documents-prod
S3_BUCKET_AUDIO=vidhi-audio-prod

DYNAMODB_TABLE_USERS=vidhi-users
DYNAMODB_TABLE_CHAT=vidhi-chat-history
DYNAMODB_TABLE_CACHE=vidhi-response-cache

BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Optional - skip for now
BHASHINI_API_KEY=
BHASHINI_USER_ID=
START_WEB_SCRAPING=False
```

### 7. Restart Backend

```bash
# Stop the running backend (Ctrl+C)
# Start it again
python app.py
```

Now you should see:
```
INFO:     Bedrock LLM service initialized successfully
INFO:     AWS Polly service initialized
INFO:     AWS Transcribe service initialized
INFO:     VIDHI backend started successfully!
```

## Testing Full Functionality

### Test Chat Endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -F "text=What are my rights during arrest?" \
  -F "language=english"
```

### Test Health Check

```bash
curl http://localhost:8000/health
```

Should show all services as `true`.

## Optional: Install Advanced Features

Once the basic backend works with AWS, you can add optional features:

### Install LangChain (for RAG)

```bash
pip install langchain==0.0.200 langchain-community==0.0.200
```

### Install ChromaDB (for vector search)

```bash
# This may fail on Windows - that's OK, we can use AWS OpenSearch instead
pip install chromadb==0.4.22
```

### Run Scraper (for government schemes)

```bash
python scraper.py
```

This downloads government scheme data (takes 30-60 minutes).

## Troubleshooting

### Backend won't start

```bash
# Check Python version (need 3.9-3.12, not 3.13)
python --version

# If 3.13, install 3.11 from python.org
```

### Port 8000 already in use

```bash
# Find and kill process using port 8000
netstat -ano | findstr :8000
taskkill /PID <process_id> /F
```

### AWS credentials not working

```bash
# Verify credentials
aws sts get-caller-identity

# Should show your AWS account info
```

### Import errors

```bash
# Reinstall minimal requirements
pip install --force-reinstall -r requirements-windows-minimal.txt
```

## Summary

1. ✅ Install minimal dependencies (no Rust needed)
2. ✅ Start backend (with warnings - that's OK)
3. ✅ Configure AWS services
4. ✅ Test with frontend
5. ⏭️ Add optional features later

The backend will work with just the minimal installation + AWS configuration!
