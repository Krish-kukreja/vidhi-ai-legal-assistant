# Quick Start Reference - VIDHI Setup

## TL;DR - What You Need

### 1. AWS Account Setup (One Time)
```
✅ Create AWS account at aws.amazon.com
✅ Create IAM user with these permissions:
   - AmazonS3FullAccess
   - AmazonDynamoDBFullAccess
   - AmazonTranscribeFullAccess
   - AmazonPollyFullAccess
   - AmazonBedrockFullAccess
✅ Get Access Key ID + Secret Access Key
```

### 2. Bedrock Models (UPDATED - Auto-Enabled!)
```
✅ Models are now AUTO-ENABLED when first used
✅ No manual activation needed
✅ Just start using them!

Note: Anthropic (Claude) may need use case approval
Alternative: Use Amazon Titan (instant, no approval)
```

### 3. Create .env File
```bash
cd vidhi-backend
copy .env.example .env  # Windows
# or
cp .env.example .env    # Mac/Linux
```

Edit `.env`:
```env
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=AKIA...your-key...
AWS_SECRET_ACCESS_KEY=wJal...your-secret...
```

### 4. Create AWS Resources

**Option A - AWS CLI (Fast)**:
```bash
# Configure AWS CLI
aws configure

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

**Option B - AWS Console (Manual)**:
- S3: Create 2 buckets (vidhi-documents-prod, vidhi-audio-prod)
- DynamoDB: Create 4 tables (see names above)

### 5. Install & Run Backend
```bash
cd vidhi-backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Install packages
pip install -r requirements.txt

# Run backend
python app.py
```

### 6. Run Frontend
```bash
# New terminal
cd vidhi-assistant
npm install
npm run dev
```

### 7. Test
```bash
# Health check
curl http://localhost:8000/health

# Open browser
http://localhost:5173
```

---

## If Claude Requires Approval

**Quick Fix - Use Amazon Titan Instead**:

1. Edit `vidhi-backend/llm_setup/bedrock_setup.py`

2. Find line ~20:
   ```python
   model_id = "anthropic.claude-3-haiku-20240307-v1:0"
   ```

3. Replace with:
   ```python
   model_id = "amazon.titan-text-express-v1"
   ```

4. Save and restart:
   ```bash
   python app.py
   ```

**Titan is available instantly, no approval needed!**

---

## Common Errors & Fixes

### "AWS credentials not found"
```bash
# Check .env file exists
ls .env  # Should show the file

# Check contents
cat .env  # Should show AWS_ACCESS_KEY_ID=...

# Make sure no spaces around =
# Wrong: AWS_ACCESS_KEY_ID = AKIA...
# Right: AWS_ACCESS_KEY_ID=AKIA...
```

### "Bucket does not exist"
```bash
# List your buckets
aws s3 ls

# Create if missing
aws s3 mb s3://vidhi-documents-prod --region ap-south-1
aws s3 mb s3://vidhi-audio-prod --region ap-south-1
```

### "Table does not exist"
```bash
# List your tables
aws dynamodb list-tables --region ap-south-1

# Create if missing (see commands in section 4)
```

### "Module not found"
```bash
# Make sure virtual environment is activated
# You should see (venv) in your terminal prompt

# If not, activate it:
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux

# Reinstall packages
pip install -r requirements.txt
```

### "Access denied to Bedrock"
```bash
# Option 1: Use Titan instead (instant)
# Edit bedrock_setup.py as shown above

# Option 2: Request Claude access
# Go to Bedrock console → Model catalog → Request access
```

---

## Verification Checklist

Before running, verify:

- [ ] AWS account created
- [ ] IAM user created with 5 permissions
- [ ] Access keys copied
- [ ] .env file created with keys
- [ ] 2 S3 buckets created
- [ ] 4 DynamoDB tables created
- [ ] Python packages installed
- [ ] Virtual environment activated

Then run:
```bash
python app.py
```

Should see:
```
INFO: Starting VIDHI backend...
INFO: Application startup complete.
INFO: Uvicorn running on http://127.0.0.1:8000
```

---

## Cost Estimate

### Free Tier (12 months)
- Most services free for first year
- ~$0 for first few months

### After Free Tier
- ~$155/month for 10,000 users
- ~$0.02 per query

### Cost Breakdown
- Bedrock (AI): $25/month
- Transcribe (Voice): $50/month
- Polly (Voice): $20/month
- Embeddings: $10/month
- DynamoDB: $10/month
- S3: $10/month
- Other: $30/month

---

## Next Steps After Setup

1. **Test all features**:
   - Chat with AI
   - Voice input
   - Document upload
   - Government schemes

2. **Run scraper** (optional):
   ```bash
   python scraper.py
   ```
   Gets 2,980+ government schemes

3. **Get Bhashini API** (optional):
   - For regional dialects
   - https://bhashini.gov.in/

4. **Deploy to production**:
   - AWS Lambda for backend
   - Vercel for frontend

---

## Support

If stuck:
1. Check `COMPLETE_AWS_SETUP_GUIDE.md` for detailed steps
2. Check backend terminal for error messages
3. Check AWS Console to verify resources exist
4. Check .env file for typos

---

**Time to setup**: 30-40 minutes
**Code changes needed**: 0 (or 1 line if using Titan)
**Difficulty**: Easy (just follow steps)

Good luck! 🚀
