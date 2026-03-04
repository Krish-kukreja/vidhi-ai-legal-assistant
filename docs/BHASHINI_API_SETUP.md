# Bhashini & ULCA API Setup Guide

## Important: Bhashini is OPTIONAL!

**You can run VIDHI without Bhashini!** It's only needed for regional dialects like Bhojpuri, Maithili, Awadhi.

### What Works Without Bhashini:
- ✅ All 22 official Indian languages (Hindi, Bengali, Tamil, etc.)
- ✅ AWS Polly for voice output
- ✅ AWS Transcribe for voice input
- ✅ All AI features
- ✅ Document analysis
- ✅ Everything except dialect-specific voice

### What Needs Bhashini:
- ❌ Bhojpuri voice input/output
- ❌ Maithili voice input/output
- ❌ Awadhi voice input/output
- ❌ Other regional dialects

**Recommendation**: Start without Bhashini, add it later if you need dialects.

---

## If You Want Bhashini (Optional)

Bhashini is a Government of India initiative for Indian language technology.

### Step 1: Register on Bhashini Platform (10 minutes)

1. **Go to Bhashini Website**:
   - URL: https://bhashini.gov.in/
   - Or: https://bhashini.gov.in/ulca/

2. **Click "Sign Up" or "Register"**:
   - Look for registration button (usually top right)
   - Or go directly to: https://bhashini.gov.in/ulca/user/register

3. **Fill Registration Form**:
   ```
   Name: [Your name]
   Email: [Your email]
   Phone: [Your phone number]
   Organization: [Your organization or "Individual"]
   Purpose: Research/Development/Education
   ```

4. **Verify Email**:
   - Check your email for verification link
   - Click the link to verify

5. **Login**:
   - Go back to https://bhashini.gov.in/ulca/
   - Login with your credentials

### Step 2: Get API Keys (5 minutes)

**Option A: Bhashini Dashboard**

1. **After Login**:
   - Look for "API Keys" or "Developer" section
   - Or go to: https://bhashini.gov.in/ulca/user/api-keys

2. **Generate API Key**:
   - Click "Generate API Key" or "Create New Key"
   - Give it a name: "VIDHI Backend"
   - Copy the API key (looks like: `bhashini_abc123xyz...`)

3. **Get User ID**:
   - Should be visible in your profile
   - Or in the API keys section
   - Looks like: `user_12345` or similar

**Option B: ULCA Platform**

ULCA (Universal Language Contribution API) is part of Bhashini.

1. **Go to ULCA**:
   - URL: https://bhashini.gov.in/ulca/
   - Login with same Bhashini credentials

2. **Navigate to API Section**:
   - Look for "API" or "Developer Tools"
   - Or "Model Inference"

3. **Get ULCA API Key**:
   - Generate new API key
   - Copy the key

### Step 3: Add Keys to .env File (1 minute)

Edit `vidhi-backend/.env`:

```env
# Bhashini API (optional - for dialects)
BHASHINI_API_KEY=bhashini_abc123xyz...
BHASHINI_USER_ID=user_12345
BHASHINI_API_KEY_ULCA=ulca_xyz789abc...
```

### Step 4: Test Bhashini Integration (2 minutes)

```bash
cd vidhi-backend
python app.py
```

Try using a dialect in the frontend:
- Select "Bhojpuri" from language dropdown
- Speak or type a message
- Should work with Bhashini API

---

## Current Status of Bhashini (As of 2026)

### What's Available:
- ✅ Translation APIs
- ✅ Transliteration APIs
- ✅ Some TTS (Text-to-Speech) models
- ✅ Some ASR (Speech Recognition) models

### What May Not Be Available:
- ❌ Full dialect coverage (Bhojpuri, Maithili, etc. may be limited)
- ❌ High-quality voice models for all dialects
- ❌ Real-time streaming APIs

### Alternative Approach:

If Bhashini doesn't have good dialect support, you can:

1. **Use Standard Hindi** for dialects:
   - Most Bhojpuri/Maithili speakers understand Hindi
   - AWS Polly has excellent Hindi voice
   - Better than no voice at all

2. **Use Browser Speech API**:
   - Some browsers support regional languages
   - Free, no API needed
   - Already implemented in frontend

3. **Wait for Bhashini Updates**:
   - Government is actively developing it
   - More languages being added
   - Check back periodically

---

## Troubleshooting Bhashini

### Issue 1: "Bhashini website not loading"
**Solution**:
- Try different browser
- Clear cache
- Try later (government sites can be slow)
- Use VPN if outside India

### Issue 2: "Registration not working"
**Solution**:
- Make sure you're using Indian phone number
- Try email verification instead
- Contact Bhashini support: support@bhashini.gov.in

### Issue 3: "API key not working"
**Solution**:
- Check if key is active in dashboard
- Check if you have API quota remaining
- Verify key is copied correctly (no extra spaces)

### Issue 4: "Dialect not supported"
**Solution**:
- Check Bhashini documentation for supported languages
- Use standard Hindi as fallback
- Use browser speech API

---

## Alternative: Run Without Bhashini

**Recommended for MVP**: Skip Bhashini initially!

### How to Disable Bhashini:

1. **Leave .env empty**:
   ```env
   # Bhashini API (optional - for dialects)
   BHASHINI_API_KEY=
   BHASHINI_USER_ID=
   BHASHINI_API_KEY_ULCA=
   ```

2. **Backend will automatically fallback**:
   - Uses AWS Polly for all languages
   - Uses AWS Transcribe for voice input
   - Works perfectly for 22 official languages

3. **Frontend shows correct options**:
   - Dialects marked as "Limited Support"
   - Users can still select them
   - Will use Hindi as fallback

### What Users See:

**With Bhashini**:
- 🟢 Hindi (Premium - AWS Polly)
- 🟢 Bengali (Premium - AWS Polly)
- 🔵 Bhojpuri (Standard - Bhashini)
- 🔵 Maithili (Standard - Bhashini)

**Without Bhashini**:
- 🟢 Hindi (Premium - AWS Polly)
- 🟢 Bengali (Premium - AWS Polly)
- 🟡 Bhojpuri (Fallback - Hindi)
- 🟡 Maithili (Fallback - Hindi)

**Both work fine!** Bhashini just adds native dialect support.

---

## Cost Comparison

### With Bhashini:
- Bhashini API: Usually FREE (government initiative)
- AWS Polly: $20/month (for standard languages)
- Total: ~$20/month

### Without Bhashini:
- AWS Polly: $20/month (for all languages)
- Total: ~$20/month

**No cost difference!** Bhashini is free but optional.

---

## Bhashini API Documentation

### Official Resources:
- Website: https://bhashini.gov.in/
- ULCA: https://bhashini.gov.in/ulca/
- Documentation: https://bhashini.gitbook.io/
- GitHub: https://github.com/ULCA-IN

### API Endpoints (Example):
```python
# Translation
POST https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/compute

# TTS (Text-to-Speech)
POST https://dhruva-api.bhashini.gov.in/services/inference/pipeline

# ASR (Speech Recognition)
POST https://dhruva-api.bhashini.gov.in/services/inference/pipeline
```

### Request Format (Example):
```json
{
  "pipelineTasks": [
    {
      "taskType": "tts",
      "config": {
        "language": {
          "sourceLanguage": "hi"
        },
        "gender": "female"
      }
    }
  ],
  "inputData": {
    "input": [
      {
        "source": "नमस्ते"
      }
    ]
  }
}
```

---

## Summary: Do You Need Bhashini?

### ✅ Start WITHOUT Bhashini if:
- You're just testing VIDHI
- You don't need specific dialects
- You want to launch quickly
- You're okay with Hindi fallback for dialects

### ✅ Add Bhashini LATER if:
- Users request specific dialect support
- You have time to integrate
- Bhashini has good models for your dialects
- You want native dialect experience

---

## Quick Decision Guide

```
Do you need Bhojpuri/Maithili/Awadhi voice?
    ↓
   NO → Skip Bhashini, use AWS Polly for everything
    ↓
   YES → Is Bhashini registration working?
         ↓
        NO → Skip for now, add later
         ↓
        YES → Register and get API keys
              ↓
              Does Bhashini have good models for your dialect?
              ↓
             NO → Use Hindi fallback
              ↓
             YES → Integrate Bhashini!
```

---

## Recommended Approach

### Phase 1: Launch without Bhashini (Week 1)
- Use AWS Polly for all 22 languages
- Test with real users
- See which dialects are actually requested

### Phase 2: Add Bhashini if needed (Week 2+)
- Register on Bhashini
- Get API keys
- Test dialect quality
- Enable for specific dialects only

### Phase 3: Optimize (Month 2+)
- Monitor usage
- Keep best-performing services
- Remove unused integrations

---

## Current .env Configuration

**Minimal (No Bhashini)**:
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJal...
```

**Full (With Bhashini)**:
```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=wJal...

BHASHINI_API_KEY=bhashini_abc123...
BHASHINI_USER_ID=user_12345
BHASHINI_API_KEY_ULCA=ulca_xyz789...
```

**Both work!** Start with minimal, add Bhashini later if needed.

---

## Contact Information

### Bhashini Support:
- Email: support@bhashini.gov.in
- Website: https://bhashini.gov.in/
- Twitter: @BhashiniIndia (if exists)

### ULCA Support:
- Email: ulca@bhashini.gov.in
- Documentation: https://bhashini.gitbook.io/

---

**Recommendation**: Skip Bhashini for now, launch with AWS services only. Add Bhashini later if users request specific dialects.

**Time to setup Bhashini**: 15-20 minutes (if registration works)
**Time to launch without Bhashini**: 0 minutes (already configured!)

Your choice! 🚀
