# VIDHI Backend - Command Reference

## Quick Commands (Copy-Paste)

### Installation

```bash
# Navigate to backend
cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-backend

# Activate virtual environment
venv\Scripts\activate

# Install minimal dependencies
pip install -r requirements-windows-minimal.txt

# Test installation
python test-installation.py

# Start backend
python app.py
```

### AWS Configuration

```bash
# Configure AWS CLI
aws configure
# Enter: ap-south-1, your access key, your secret key

# Create S3 buckets
aws s3 mb s3://vidhi-audio-prod --region ap-south-1
aws s3 mb s3://vidhi-documents-prod --region ap-south-1

# Verify buckets
aws s3 ls
```

### DynamoDB Tables

```bash
# Users table
aws dynamodb create-table --table-name vidhi-users --attribute-definitions AttributeName=user_id,AttributeType=S --key-schema AttributeName=user_id,KeyType=HASH --billing-mode PAY_PER_REQUEST --region ap-south-1

# Chat history table
aws dynamodb create-table --table-name vidhi-chat-history --attribute-definitions AttributeName=chat_id,AttributeType=S AttributeName=message_id,AttributeType=S --key-schema AttributeName=chat_id,KeyType=HASH AttributeName=message_id,KeyType=RANGE --billing-mode PAY_PER_REQUEST --region ap-south-1

# Cache table
aws dynamodb create-table --table-name vidhi-response-cache --attribute-definitions AttributeName=query_hash,AttributeType=S --key-schema AttributeName=query_hash,KeyType=HASH --billing-mode PAY_PER_REQUEST --region ap-south-1

# Verify tables
aws dynamodb list-tables --region ap-south-1
```

### Testing

```bash
# Test backend health
curl http://localhost:8000/

# Test health check
curl http://localhost:8000/health

# Test chat (after AWS configured)
curl -X POST http://localhost:8000/chat -F "text=What are my rights?" -F "language=english"
```

### Development

```bash
# Start backend (development)
python app.py

# Start backend (production)
uvicorn app:app --host 0.0.0.0 --port 8000

# Run scraper (optional)
python scraper.py

# Run tests (if you add them)
pytest tests/
```

### Troubleshooting

```bash
# Check Python version
python --version

# Check installed packages
pip list

# Check AWS credentials
aws sts get-caller-identity

# Check AWS region
aws configure get region

# Reinstall dependencies
pip install --force-reinstall -r requirements-windows-minimal.txt

# Clear pip cache
pip cache purge

# Check port 8000
netstat -ano | findstr :8000
```

### Environment Setup

```bash
# Copy environment template
copy .env.example .env

# Edit environment file
notepad .env

# Verify environment variables
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('AWS_REGION'))"
```

### Optional Features

```bash
# Install LangChain
pip install langchain==0.0.200 langchain-community==0.0.200

# Install ChromaDB (may fail on Windows)
pip install chromadb==0.4.22

# Install sentence-transformers
pip install sentence-transformers==2.3.1

# Install all requirements (may fail)
pip install -r requirements.txt
```

## Common Workflows

### First Time Setup

```bash
# 1. Create virtual environment (if not exists)
python -m venv venv

# 2. Activate it
venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements-windows-minimal.txt

# 4. Copy environment file
copy .env.example .env

# 5. Edit .env with your AWS credentials
notepad .env

# 6. Configure AWS CLI
aws configure

# 7. Create AWS resources (S3, DynamoDB)
# See AWS Configuration section above

# 8. Start backend
python app.py
```

### Daily Development

```bash
# 1. Navigate to backend
cd vidhi-backend

# 2. Activate venv
venv\Scripts\activate

# 3. Start backend
python app.py

# 4. In another terminal, start frontend
cd vidhi-assistant
npm run dev
```

### Deployment

```bash
# 1. Install production dependencies
pip install -r requirements.txt

# 2. Run tests
pytest tests/

# 3. Build for Lambda
pip install -t package/ -r requirements.txt
cd package
zip -r ../deployment.zip .
cd ..
zip -g deployment.zip app.py configs/ services/ llm_setup/ speech/ stores/ processing/

# 4. Deploy to Lambda
aws lambda update-function-code --function-name vidhi-backend --zip-file fileb://deployment.zip --region ap-south-1
```

### Debugging

```bash
# Check logs
python app.py 2>&1 | tee backend.log

# Verbose logging
LOG_LEVEL=DEBUG python app.py

# Test specific endpoint
curl -v http://localhost:8000/health

# Check AWS connectivity
python -c "import boto3; print(boto3.client('s3').list_buckets())"

# Check Bedrock access
python -c "import boto3; print(boto3.client('bedrock', region_name='ap-south-1').list_foundation_models())"
```

## Environment Variables

Required in `.env`:

```bash
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

# S3 Buckets
S3_BUCKET_DOCUMENTS=vidhi-documents-prod
S3_BUCKET_AUDIO=vidhi-audio-prod

# DynamoDB Tables
DYNAMODB_TABLE_USERS=vidhi-users
DYNAMODB_TABLE_CHAT=vidhi-chat-history
DYNAMODB_TABLE_CACHE=vidhi-response-cache

# Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Optional
BHASHINI_API_KEY=
BHASHINI_USER_ID=
START_WEB_SCRAPING=False
LOG_LEVEL=INFO
```

## Port Configuration

Default: `8000`

To change:

```python
# In app.py, change:
uvicorn.run(app, host="0.0.0.0", port=8001)
```

Or:

```bash
# Command line
uvicorn app:app --port 8001
```

## Useful Aliases (Optional)

Add to your shell profile:

```bash
# Backend shortcuts
alias vb='cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-backend && venv\Scripts\activate'
alias startb='cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-backend && venv\Scripts\activate && python app.py'

# Frontend shortcuts
alias vf='cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-assistant'
alias startf='cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-assistant && npm run dev'

# AWS shortcuts
alias awsls='aws s3 ls'
alias awstables='aws dynamodb list-tables --region ap-south-1'
```

## Quick Reference

| Task | Command |
|------|---------|
| Install deps | `pip install -r requirements-windows-minimal.txt` |
| Test install | `python test-installation.py` |
| Start backend | `python app.py` |
| Test health | `curl http://localhost:8000/` |
| Configure AWS | `aws configure` |
| Create S3 | `aws s3 mb s3://bucket-name --region ap-south-1` |
| Create DynamoDB | See DynamoDB Tables section above |
| Check AWS | `aws sts get-caller-identity` |
| View logs | `python app.py 2>&1 \| tee backend.log` |

## Next Steps

1. Run: `pip install -r requirements-windows-minimal.txt`
2. Run: `python test-installation.py`
3. Run: `python app.py`
4. Open: http://localhost:8000
5. Configure AWS (see COMPLETE_AWS_SETUP_GUIDE.md)
