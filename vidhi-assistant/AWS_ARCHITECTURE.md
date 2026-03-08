# AWS Architecture for VIDHI - Budget Optimized ($300)

## Cost-Effective AWS Services Selection

### 1. Compute & API Layer
**AWS Lambda** (Serverless)
- Cost: ~$20-30/month for 1M requests
- Why: Pay per execution, auto-scaling, no idle costs
- Free Tier: 1M requests/month free forever
- Use for: API endpoints, orchestration, business logic

**AWS API Gateway** (REST API)
- Cost: ~$10-15/month for 1M requests
- Why: Managed API routing, authentication, rate limiting
- Free Tier: 1M API calls/month for 12 months
- Use for: Single entry point for all client requests

### 2. AI & ML Services
**AWS Bedrock** (Claude 3 Haiku recommended)
- Cost: ~$80-100/month (largest expense)
- Claude 3 Haiku: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- Why: Most cost-effective for conversational AI
- Alternative: Claude 3.5 Sonnet for complex queries only
- Use for: Legal advice, document analysis, conversational responses

**AWS Transcribe** (Speech-to-Text)
- Cost: ~$20-30/month for 10,000 minutes
- Supports: Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam, Punjabi
- Price: $0.024 per minute (standard), $0.048 per minute (medical/custom)
- Free Tier: 60 minutes/month for 12 months
- Use for: Voice input processing

**AWS Polly** (Text-to-Speech)
- Cost: ~$15-20/month for 5M characters
- Supports: Hindi, Bengali, Tamil, Telugu, Marathi, Gujarati, Kannada, Malayalam
- Price: $4.00 per 1M characters (standard), $16.00 per 1M characters (neural)
- Free Tier: 5M characters/month for 12 months
- Use for: Voice output for standard languages

**AWS Textract** (Document OCR)
- Cost: ~$10-15/month for 1,000 pages
- Price: $1.50 per 1,000 pages (DetectDocumentText)
- Free Tier: 1,000 pages/month for 3 months
- Use for: Document scanning and analysis

### 3. Data Storage
**Amazon DynamoDB** (NoSQL Database)
- Cost: ~$5-10/month with on-demand pricing
- Why: Serverless, auto-scaling, pay per request
- Free Tier: 25GB storage, 25 read/write capacity units forever
- Use for: User profiles, chat history, session data

**Amazon S3** (Object Storage)
- Cost: ~$5-10/month for 50GB + requests
- Price: $0.023 per GB/month (Standard), $0.0125 per GB (Intelligent-Tiering)
- Free Tier: 5GB storage, 20,000 GET requests for 12 months
- Use for: Documents, audio files, cached content

### 4. Authentication & Security
**AWS Cognito** (User Authentication)
- Cost: ~$5/month for 10,000 MAU (Monthly Active Users)
- Free Tier: 50,000 MAU forever
- Why: Managed authentication, supports custom identity providers
- Use for: User authentication, Aadhaar integration

**AWS KMS** (Key Management)
- Cost: ~$1-2/month
- Price: $1/key/month + $0.03 per 10,000 requests
- Free Tier: 20,000 requests/month
- Use for: Encryption keys for data at rest

### 5. Content Delivery
**Amazon CloudFront** (CDN)
- Cost: ~$5-10/month for 50GB data transfer
- Free Tier: 1TB data transfer out for 12 months
- Why: Reduces latency for audio playback, caches static content
- Use for: Audio file delivery, static assets

### 6. Monitoring & Logging
**AWS CloudWatch** (Monitoring)
- Cost: ~$5/month for basic monitoring
- Free Tier: 10 custom metrics, 5GB logs ingestion
- Use for: Application monitoring, error tracking

**AWS X-Ray** (Distributed Tracing)
- Cost: ~$2-3/month
- Free Tier: 100,000 traces/month
- Use for: Performance debugging

## Total Estimated Monthly Cost Breakdown

| Service | Monthly Cost | Priority |
|---------|-------------|----------|
| AWS Bedrock (Claude Haiku) | $80-100 | Critical |
| AWS Lambda | $20-30 | Critical |
| AWS Transcribe | $20-30 | Critical |
| AWS Polly | $15-20 | Critical |
| API Gateway | $10-15 | Critical |
| AWS Textract | $10-15 | High |
| DynamoDB | $5-10 | Critical |
| S3 | $5-10 | Critical |
| CloudFront | $5-10 | Medium |
| Cognito | $5 | High |
| CloudWatch | $5 | Medium |
| X-Ray | $2-3 | Low |
| KMS | $1-2 | Medium |
| **TOTAL** | **$183-260/month** | |

## Budget Optimization Strategies

### Phase 1: MVP with $300 Budget (First Month)
**Focus on Core Features Only:**
1. ✅ AWS Lambda + API Gateway (Free Tier)
2. ✅ AWS Bedrock (Claude Haiku) - $80
3. ✅ AWS Transcribe (Hindi only initially) - $20
4. ✅ AWS Polly (Hindi only initially) - $15
5. ✅ DynamoDB (Free Tier)
6. ✅ S3 (Free Tier)
7. ✅ Cognito (Free Tier)

**First Month Cost: ~$115-130**

### Cost Reduction Tactics

1. **Aggressive Caching**
   - Cache common legal queries in DynamoDB (TTL: 24 hours)
   - Pre-generate TTS for frequently asked questions
   - Use CloudFront for audio caching
   - Estimated savings: 40-50% on AI costs

2. **Smart AI Model Selection**
   - Use Claude Haiku for simple queries (rights, schemes)
   - Use Claude Sonnet only for document analysis
   - Implement query classification to route appropriately
   - Estimated savings: 30-40% on Bedrock costs

3. **Batch Processing**
   - Process scheme notifications in daily batches
   - Batch TTS generation for common responses
   - Use SQS for async processing (free tier: 1M requests)
   - Estimated savings: 20-30% on Lambda costs

4. **Language Prioritization**
   - Start with top 5 languages: Hindi, Bengali, Tamil, Telugu, Marathi
   - Add others based on user demand
   - Estimated savings: 50% on Transcribe/Polly costs initially

5. **Free Tier Maximization**
   - Use Lambda free tier (1M requests/month)
   - Use DynamoDB free tier (25GB + 25 RCU/WCU)
   - Use S3 free tier (5GB storage)
   - Use Cognito free tier (50K MAU)
   - Estimated savings: $40-50/month

6. **Ephemeral Processing**
   - Don't store sensitive queries (privacy + cost savings)
   - Auto-delete old chat history (30-day TTL)
   - Use S3 Lifecycle policies (move to Glacier after 30 days)
   - Estimated savings: 30% on storage costs

## Regional Dialect Handling (Bhojpuri, Maithili, etc.)

**Problem:** AWS Transcribe/Polly don't support regional dialects

**Solution Options:**

### Option 1: Bhashini API (Government of India) - RECOMMENDED
- **Cost:** FREE (government initiative)
- **Coverage:** Bhojpuri, Maithili, Awadhi, and 11 Indian languages
- **Integration:** REST API, can be called from Lambda
- **Limitation:** May have rate limits, less reliable than AWS
- **Use for:** Dialects not supported by AWS

### Option 2: Fallback to Standard Language
- Detect dialect (Bhojpuri) → Use standard Hindi with AWS Polly
- Add disclaimer: "Responding in standard Hindi"
- **Cost:** $0 additional
- **User Experience:** Acceptable for MVP

### Option 3: Hybrid Approach (BEST)
- Use AWS Transcribe/Polly for standard languages (faster, more reliable)
- Use Bhashini API for dialects (free, government-backed)
- Implement fallback chain: Bhashini → AWS → Browser TTS
- **Cost:** Minimal additional Lambda execution time

## Recommended Architecture for $300 Budget

```
┌─────────────────────────────────────────────────────────────┐
│                     Client (React App)                       │
│  - Web Speech API (fallback for voice input)                │
│  - Browser TTS (fallback for voice output)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              AWS CloudFront (CDN) - Optional                 │
│  - Cache static assets and audio files                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS API Gateway                            │
│  - Authentication (Cognito)                                  │
│  - Rate limiting                                             │
│  - Request routing                                           │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┐
        ▼            ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
   │ Query   │ │ Voice   │ │Document │ │ Scheme  │
   │ Lambda  │ │ Lambda  │ │ Lambda  │ │ Lambda  │
   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
        │           │           │           │
        ▼           ▼           ▼           ▼
   ┌──────────────────────────────────────────────┐
   │         AWS Bedrock (Claude Haiku)           │
   │  - Legal advice generation                   │
   │  - Document analysis                         │
   │  - Conversational responses                  │
   └──────────────────────────────────────────────┘
        │           │           │
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │   AWS   │ │   AWS   │ │   AWS   │
   │Transcribe│ │  Polly  │ │Textract │
   └─────────┘ └─────────┘ └─────────┘
        │           │           │
        ▼           ▼           ▼
   ┌──────────────────────────────────────────────┐
   │            Bhashini API (Dialects)           │
   │  - Bhojpuri, Maithili, Awadhi TTS/STT       │
   └──────────────────────────────────────────────┘
        │           │           │
        ▼           ▼           ▼
   ┌─────────┐ ┌─────────┐ ┌─────────┐
   │DynamoDB │ │    S3   │ │ Cognito │
   │- Users  │ │- Docs   │ │- Auth   │
   │- Chats  │ │- Audio  │ │         │
   │- Cache  │ │         │ │         │
   └─────────┘ └─────────┘ └─────────┘
```

## Implementation Priority (One Problem at a Time)

### Week 1-2: Foundation
1. Set up AWS account and configure services
2. Create Lambda functions with API Gateway
3. Implement basic authentication with Cognito
4. Set up DynamoDB tables

### Week 3-4: Voice & Language (CURRENT FOCUS)
1. ✅ Implement 22 language support in frontend
2. Integrate AWS Transcribe for speech-to-text
3. Integrate AWS Polly for text-to-speech
4. Add Bhashini API for dialects
5. Implement language detection and tagging

### Week 5-6: AI Integration
1. Connect AWS Bedrock (Claude Haiku)
2. Build conversational AI for legal queries
3. Implement response caching
4. Add legal knowledge base

### Week 7-8: Document Analysis
1. Integrate AWS Textract
2. Build document risk analysis
3. Implement educational explanations

### Week 9-10: Government Schemes
1. Integrate MyGov API
2. Build scheme matching algorithm
3. Implement eligibility checking

## Monitoring Budget Usage

**Set up AWS Budgets (Free):**
1. Create budget alert at $200 (66% of $300)
2. Create budget alert at $250 (83% of $300)
3. Create budget alert at $280 (93% of $300)

**Cost Optimization Dashboard:**
- Monitor Bedrock token usage daily
- Track Transcribe/Polly minutes weekly
- Review Lambda execution times
- Identify and cache expensive queries

## Scaling Beyond $300

**If usage grows:**
1. Implement user tiers (free vs. premium)
2. Add rate limiting per user
3. Consider AWS Reserved Instances for predictable workloads
4. Explore AWS Activate credits for startups (up to $100K)
5. Apply for AWS grants for social impact projects

## Conclusion

With $300/month budget, you can build a functional MVP focusing on:
- Core conversational AI (Hindi + 4 major languages)
- Basic document analysis
- Government scheme information
- Emergency rights advisory

The architecture is designed to scale efficiently as budget increases, with clear paths to add more languages, features, and capacity.
