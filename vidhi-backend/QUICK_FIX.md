# VIDHI Backend - Quick Fix for Rust Errors

## The Problem

You're getting Rust compilation errors because Python 3.13 + Windows + some packages = compilation hell.

## The Solution (5 Minutes)

### Copy-Paste These Commands:

```bash
# 1. Go to backend directory
cd C:\Users\iamkr\projects\CodeForces\Vidhi\vidhi-backend

# 2. Activate virtual environment
venv\Scripts\activate

# 3. Install ONLY pre-built packages (no Rust needed)
pip install -r requirements-windows-minimal.txt

# 4. Test installation
python test-installation.py

# 5. Start backend
python app.py
```

### Expected Result:

```
INFO:     Started server process
INFO:     Waiting for application startup.
WARNING:  Bedrock LLM not available: No module named 'langchain'
WARNING:  ChromaDB not available: No module named 'chromadb'
INFO:     VIDHI backend started successfully!
INFO:     Note: Some features may be limited due to missing optional dependencies
INFO:     Uvicorn running on http://0.0.0.0:8000
```

The warnings are NORMAL! Backend works, just needs AWS configuration.

### Test It Works:

Open browser: http://localhost:8000

Should see:
```json
{"service":"VIDHI API","status":"running","version":"1.0.0"}
```

## What Changed?

1. ✅ Backend now handles missing optional dependencies gracefully
2. ✅ Minimal requirements file with only pre-built Windows wheels
3. ✅ No Rust/Cargo compilation needed
4. ✅ Backend starts and runs (with limited features until AWS configured)

## What Works Now?

✅ Backend server runs
✅ API endpoints accessible
✅ Ready for AWS configuration
✅ Will work with frontend once AWS is set up

## What Doesn't Work Yet?

❌ RAG/Vector search (needs LangChain + ChromaDB or AWS OpenSearch)
❌ Government scheme matching (needs vector store)
❌ AWS services (needs configuration)

## Next Steps:

1. **Configure AWS** (see COMPLETE_AWS_SETUP_GUIDE.md)
   - Run: `aws configure`
   - Create S3 buckets
   - Create DynamoDB tables
   - Enable Bedrock models

2. **Test with Frontend**
   - Start backend: `python app.py`
   - Start frontend: `cd ../vidhi-assistant && npm run dev`
   - Open: http://localhost:5173

3. **Add Optional Features Later** (if needed)
   - Install LangChain: `pip install langchain==0.0.200`
   - Install ChromaDB: `pip install chromadb==0.4.22` (may fail - use AWS OpenSearch instead)
   - Run scraper: `python scraper.py`

## If It Still Doesn't Work:

### Option 1: Install packages one by one

```bash
pip install fastapi==0.100.0
pip install uvicorn==0.23.0
pip install boto3==1.34.34
pip install python-dotenv==1.0.0
pip install requests==2.31.0
```

### Option 2: Use Python 3.11 instead of 3.13

1. Download Python 3.11 from python.org
2. Install it
3. Create new venv: `python3.11 -m venv venv`
4. Try again

### Option 3: Skip backend for now

1. Use mock backend for frontend development
2. Configure AWS later
3. Deploy to AWS Lambda (no local dependencies needed)

## Questions?

Read these files:
- `INSTALLATION_STEPS.md` - Detailed step-by-step guide
- `WINDOWS_SETUP.md` - Windows-specific instructions
- `COMPLETE_AWS_SETUP_GUIDE.md` - AWS configuration

Or just run: `python test-installation.py` to diagnose issues
