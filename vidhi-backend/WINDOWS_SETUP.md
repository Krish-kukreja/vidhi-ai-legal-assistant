# VIDHI Backend - Windows Setup Guide

## Current Issue: Rust Compilation Errors

You're encountering errors because some Python packages (pydantic-core, lxml, chromadb) need to be compiled from source, which requires Rust toolchain on Windows.

## Solution: Minimal Installation (Recommended)

We'll install only the essential packages that have pre-built Windows wheels, then add optional features later.

### Step 1: Clean Installation

```bash
# Make sure you're in the vidhi-backend directory
cd vidhi-backend

# Activate virtual environment
venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install minimal requirements (NO compilation needed)
pip install -r requirements-windows-minimal.txt
```

### Step 2: Test Backend Startup

```bash
# Try to start the backend
python app.py
```

The backend should start with warnings about missing optional features. This is NORMAL and EXPECTED.

You should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
WARNING:  Bedrock LLM not available: ...
WARNING:  ChromaDB not available: ...
INFO:     VIDHI backend started successfully!
INFO:     Note: Some features may be limited due to missing optional dependencies
```

### Step 3: Verify Basic Functionality

Open another terminal and test:

```bash
# Test health endpoint
curl http://localhost:8000/

# Should return:
# {"service":"VIDHI API","status":"running","version":"1.0.0"}
```

### Step 4: Configure AWS (Required for Full Functionality)

Follow the main setup guide to:
1. Create AWS account
2. Configure AWS CLI: `aws configure`
3. Create S3 buckets
4. Create DynamoDB tables
5. Enable Bedrock models

See: `COMPLETE_AWS_SETUP_GUIDE.md`

### Step 5: Install Optional Features (After AWS Setup)

Once AWS is configured and the basic backend works, install optional features one by one:

```bash
# Install LangChain (for RAG functionality)
pip install langchain==0.0.200 langchain-community==0.0.200

# Install ChromaDB (for vector search)
# This may still fail on Windows - we can use AWS OpenSearch instead
pip install chromadb==0.4.22

# Install sentence-transformers (for embeddings)
# Large download - only if you want local embeddings
pip install sentence-transformers==2.3.1
```

## Alternative: Use AWS Services Instead of Local Dependencies

If ChromaDB installation keeps failing, we can replace it with AWS services:

1. **AWS OpenSearch** - Instead of ChromaDB for vector search
2. **AWS Bedrock Embeddings** - Instead of sentence-transformers
3. **AWS Lambda** - Deploy backend without local dependencies

This is actually BETTER for production and costs less!

## What Works with Minimal Installation?

✅ FastAPI server runs
✅ Health check endpoints
✅ AWS Bedrock integration (once configured)
✅ AWS S3 file storage
✅ AWS DynamoDB data storage
✅ Basic chat functionality

❌ Vector search (needs ChromaDB or AWS OpenSearch)
❌ Document embeddings (needs sentence-transformers or AWS Bedrock)
❌ Scheme matching (needs vector store)

## Next Steps

1. Get the minimal backend running (Steps 1-3 above)
2. Configure AWS services (Step 4)
3. Test with frontend
4. Add optional features as needed

## Troubleshooting

### If minimal installation still fails:

```bash
# Install packages one by one
pip install fastapi==0.100.0
pip install uvicorn==0.23.0
pip install boto3==1.34.34
pip install python-dotenv==1.0.0
pip install requests==2.31.0
pip install beautifulsoup4==4.12.3
```

### If you want to install Rust properly:

1. Download Rust installer: https://rustup.rs/
2. Run installer and follow prompts
3. Restart terminal
4. Try: `pip install -r requirements.txt`

But this is NOT required - the minimal installation is sufficient!

## Questions?

- Backend won't start? Check Python version: `python --version` (need 3.9-3.12)
- Port 8000 in use? Change port in app.py: `uvicorn.run(app, port=8001)`
- AWS errors? Make sure you ran `aws configure` first
