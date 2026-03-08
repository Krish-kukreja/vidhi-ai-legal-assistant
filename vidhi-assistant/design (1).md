# Technical Design Document

## System Overview

VIDHI is built as a cloud-native, serverless application leveraging AWS infrastructure for scalability and cost efficiency. The architecture follows a microservices pattern where specialized components handle distinct responsibilities like voice processing, document analysis, and scheme matching. The system is designed to handle traffic spikes during scheme announcement periods while maintaining sub-2-second response times and keeping operational costs under ₹0.50 per query.

The platform operates across web and mobile interfaces, with React Native or Flutter providing cross-platform mobile support and a responsive web interface for desktop users. All components communicate through a central API Gateway that routes requests to appropriate Lambda functions, ensuring loose coupling and independent scalability of each service.

## High-Level Architecture

The VIDHI system is organized into five primary layers that work together to deliver the complete user experience.

### User Interface Layer

This layer encompasses both mobile applications and web interfaces that users interact with directly. The mobile app is built using React Native or Flutter to ensure consistent experiences across iOS and Android devices while minimizing development overhead. The web interface uses responsive design principles to work seamlessly on desktop browsers and mobile web.

The UI layer handles local state management, offline caching of frequently accessed content, and optimistic updates to provide immediate feedback even before server responses arrive. Voice recording and playback happen at this layer, with audio streams sent to backend services for processing.

### API Gateway and Orchestration Layer

AWS API Gateway serves as the single entry point for all client requests, providing authentication, rate limiting, and request routing. Behind the gateway, an orchestration service built on Node.js or Python coordinates complex workflows that span multiple backend services.

For example, when a user asks about government schemes, the orchestrator retrieves the user profile, calls the scheme matching service, fetches current scheme data from government APIs, and formats the response with personalized recommendations. This layer also manages conversation context across multiple exchanges, storing session state in DynamoDB for quick retrieval.

### AI and Processing Core

The AI core leverages AWS Bedrock for generative AI capabilities, providing natural language understanding and response generation. AWS Transcribe handles speech-to-text conversion for voice inputs, supporting all 22 official Indian languages plus regional dialects. AWS Polly provides text-to-speech output, with language selection based on the detected or user-specified language preference.

For document analysis, AWS Textract performs OCR on uploaded images, extracting text from contracts, agreements, and forms. The extracted text is then analyzed by the AI model to identify potential risks, unfair clauses, and legal compliance issues. The AI is prompted with Indian legal context including relevant sections of the Contract Act, Consumer Protection Act, and other applicable laws.

### Data and Integration Layer

This layer manages all persistent data storage and external integrations. DynamoDB serves as the primary database for user profiles, chat history, and session data, chosen for its serverless nature and ability to scale automatically. S3 stores uploaded documents, cached content for offline access, and audio files for voice history playback.

External integrations connect to government APIs including MyGov for scheme information, UIDAI for Aadhaar authentication, Digilocker for document access, and e-Courts for legal case data. The system implements circuit breakers and fallback mechanisms to handle API unavailability gracefully.

### Security and Compliance Overlay

Security permeates every layer but is conceptually treated as an overlay that enforces policies across the system. All data in transit uses TLS 1.3 encryption, while data at rest in DynamoDB and S3 is encrypted using AWS KMS. User authentication leverages AWS Cognito with support for Aadhaar and Digilocker integration.

The system implements DPDP Act compliance through data minimization, purpose limitation, and user consent management. Sensitive queries are processed ephemerally without permanent storage, and federated learning approaches are used where possible to train models without centralizing user data.

## Data Model and Schema Design

The data model is designed to support personalization, conversation history, and the critical voice history playback feature with language preservation.

### User Profile Schema

```
User_Profile {
  user_id: String (Primary Key)
  aadhaar_hash: String (Optional, hashed for privacy)
  digilocker_linked: Boolean
  preferred_language: String (ISO 639-1 code + dialect tag)
  location: {
    state: String
    district: String
    coordinates: GeoPoint (Optional)
  }
  demographics: {
    age_range: String
    occupation: String
    income_bracket: String
  }
  preferences: {
    voice_enabled: Boolean
    offline_mode: Boolean
    notification_settings: Object
  }
  created_at: Timestamp
  last_active: Timestamp
}
```

The user profile stores minimal information necessary for personalization while respecting privacy. The Aadhaar number is never stored directly; instead, a cryptographic hash is used for linking purposes. Location and demographic data enable accurate scheme matching without requiring excessive personal details.

### Chat History Schema

This is the critical schema that enables voice history playback with language preservation. Each message in a conversation is stored with complete metadata about the language used and references to audio artifacts.

```
Chat_History {
  chat_id: String (Primary Key)
  user_id: String (Foreign Key to User_Profile)
  message_id: String (Sort Key)
  timestamp: Timestamp
  
  message_content: {
    text: String
    message_type: Enum ['user_query', 'system_response']
    input_mode: Enum ['voice', 'text', 'document']
  }
  
  language_metadata: {
    language_tag: String (e.g., 'hi-IN-Bhojpuri', 'bn-IN', 'ta-IN')
    language_code: String (ISO 639-1, e.g., 'hi', 'bn', 'ta')
    dialect: String (Optional, e.g., 'Bhojpuri', 'Maithili', 'Awadhi')
    script: String (e.g., 'Devanagari', 'Bengali', 'Tamil')
    confidence_score: Float (Language detection confidence)
  }
  
  audio_reference: {
    original_audio_s3_key: String (Optional, user's voice input)
    synthesized_audio_s3_key: String (Optional, system's voice response)
    audio_duration_seconds: Float
    tts_engine_used: String (e.g., 'aws-polly-hi-IN', 'bhashini-bhojpuri')
    voice_id: String (Specific voice model identifier)
  }
  
  context: {
    conversation_topic: String
    related_message_ids: Array<String>
    intent_classification: String
  }
  
  ttl: Timestamp (Optional, for automatic expiry per retention policy)
}
```

The language_metadata object is the key to preserving the original language for playback. When a user asks a question in Bhojpuri on Monday and wants to replay that conversation on Thursday, the system reads the language_tag field to determine that it must use Bhojpuri for text-to-speech synthesis, not standard Hindi or any other language.

The audio_reference object stores pointers to S3 where actual audio files are kept. For user queries, we may store the original audio recording. For system responses, we store the synthesized speech output. This allows for instant playback without regenerating audio, improving performance and reducing costs.

### Government Scheme Cache Schema

```
Scheme_Cache {
  scheme_id: String (Primary Key)
  scheme_name: String
  scheme_name_translations: Map<String, String> (Language code to translated name)
  
  eligibility_criteria: {
    age_range: Object
    income_limits: Object
    location_restrictions: Array<String>
    occupation_requirements: Array<String>
    gender_specific: Boolean
  }
  
  benefits: {
    description: String
    monetary_value: Float (Optional)
    duration: String
  }
  
  application_process: {
    steps: Array<String>
    required_documents: Array<String>
    application_url: String
    office_locations: Array<Object>
  }
  
  deadlines: {
    application_start: Timestamp
    application_end: Timestamp
    benefit_disbursement: Timestamp
  }
  
  source_api: String
  last_updated: Timestamp
  cache_expiry: Timestamp
}
```

This schema caches government scheme data to reduce dependency on external APIs and improve response times. The cache is refreshed periodically and includes translations for multilingual support.

### Document Analysis Record Schema

```
Document_Analysis {
  analysis_id: String (Primary Key)
  user_id: String (Foreign Key)
  document_s3_key: String
  
  extracted_text: String
  document_type: String (e.g., 'rental_agreement', 'loan_contract', 'employment_contract')
  
  risk_assessment: {
    overall_risk_level: Enum ['low', 'medium', 'high', 'critical']
    identified_risks: Array<{
      risk_type: String
      description: String
      severity: String
      applicable_law: String
      recommendation: String
    }>
  }
  
  clauses_flagged: Array<{
    clause_text: String
    issue_description: String
    legal_reference: String
  }>
  
  educational_content: {
    simplified_summary: String
    clause_explanations: Array<{
      clause_id: String
      original_text: String
      simplified_explanation: String
      key_terms: Array<{
        term: String
        definition: String
        example: String
      }>
      implications: String
      user_rights: String
    }>
    interactive_qa_enabled: Boolean
    teaching_session_id: String (Optional, links to ongoing educational session)
  }
  
  recommendation: String
  disclaimer: String
  
  created_at: Timestamp
  ttl: Timestamp (Ephemeral processing - auto-delete after 30 days)
}
```

Document analysis records are stored temporarily to allow users to review their analysis history but are automatically deleted after 30 days to minimize data retention and comply with privacy principles. The educational_content section stores simplified explanations and teaching materials generated for users who need help understanding the document.

## API Design and Endpoints

The VIDHI API follows RESTful principles with some extensions for real-time features. All endpoints are versioned (e.g., /api/v1/) to support backward compatibility as the system evolves.

### Voice History Playback API

This is the critical API endpoint that enables users to replay historical conversations in their original language.

**Endpoint:** `GET /api/v1/history/{chat_id}/playback`

**Purpose:** Retrieve audio playback for a specific message in a chat history, preserving the original language and dialect used during that interaction.

**Path Parameters:**
- chat_id: String (Required) - The unique identifier for the chat session

**Query Parameters:**
- message_id: String (Required) - The specific message to play back
- regenerate: Boolean (Optional, default: false) - Force regeneration of audio instead of using cached version

**Request Headers:**
- Authorization: Bearer {token}
- Accept: application/json

**Response Structure:**

```json
{
  "status": "success",
  "data": {
    "message_id": "msg_abc123xyz",
    "chat_id": "chat_789def456",
    "timestamp": "2026-02-03T14:30:00Z",
    
    "message_content": {
      "text": "मोरा अधिकार का बा जब पुलिस रोके?",
      "message_type": "user_query"
    },
    
    "language_metadata": {
      "language_tag": "hi-IN-Bhojpuri",
      "language_code": "hi",
      "dialect": "Bhojpuri",
      "script": "Devanagari"
    },
    
    "audio_playback": {
      "audio_url": "https://vidhi-audio.s3.ap-south-1.amazonaws.com/playback/msg_abc123xyz.mp3",
      "audio_format": "mp3",
      "duration_seconds": 4.2,
      "expires_at": "2026-02-06T14:30:00Z",
      "tts_engine": "bhashini-bhojpuri-v2"
    },
    
    "playback_metadata": {
      "cached": true,
      "generation_timestamp": "2026-02-03T14:30:05Z"
    }
  }
}
```

**Error Responses:**

```json
{
  "status": "error",
  "error": {
    "code": "MESSAGE_NOT_FOUND",
    "message": "The requested message does not exist or you don't have permission to access it",
    "details": {}
  }
}
```

**Implementation Flow:**

1. The API Gateway receives the request and validates the authentication token
2. The orchestration service queries DynamoDB Chat_History table using chat_id and message_id
3. The system retrieves the language_metadata object to determine the original language
4. If audio_reference.synthesized_audio_s3_key exists and cached audio is acceptable, generate a pre-signed S3 URL
5. If regeneration is requested or no cached audio exists, call the Voice_Interface service
6. The Voice_Interface selects the appropriate TTS engine based on language_tag
7. For standard languages, use AWS Polly with the correct language code and voice
8. For dialects like Bhojpuri, Maithili, or Awadhi, use Bhashini API with dialect-specific models
9. Generate the audio, store it in S3, update the Chat_History record with the new audio reference
10. Return the pre-signed S3 URL with a 72-hour expiration for client playback

### Additional Core API Endpoints

**Query Processing Endpoint**

`POST /api/v1/query`

Handles all user queries whether voice, text, or multimodal. The request includes the query content, input mode, and language preference. The response provides the AI-generated answer along with sources and related information.

**Scheme Matching Endpoint**

`POST /api/v1/schemes/match`

Takes user profile information and returns a ranked list of government schemes the user is eligible for. The response includes eligibility details, application steps, and deadlines.

**Document Analysis Endpoint**

`POST /api/v1/documents/analyze`

Accepts document uploads (as multipart form data or base64-encoded images), performs OCR, analyzes the content for legal risks, and returns a detailed risk assessment with recommendations.

**Document Education Endpoint**

`POST /api/v1/documents/{analysis_id}/explain`

Provides interactive educational content for users who don't understand a document. Takes the analysis_id and optional clause_id or term parameters, and returns simplified explanations in the user's preferred language. Supports voice output for reading and explaining each section interactively.

Request body:
```json
{
  "clause_id": "clause_3" (Optional - specific clause to explain),
  "term": "indemnity" (Optional - specific legal term to define),
  "language": "hi-IN-Bhojpuri",
  "voice_enabled": true
}
```

Response includes simplified explanations, real-world examples, implications, and audio URLs for voice playback of the teaching content.

**Emergency Mode Endpoint**

`POST /api/v1/emergency/activate`

Immediately returns critical rights information relevant to the emergency situation (e.g., arrest procedures, D.K. Basu guidelines). This endpoint is optimized for ultra-low latency.

## Voice Interface Architecture

The Voice_Interface component is responsible for all speech-related processing, including the critical language preservation for history playback.

### Language Detection and Tagging

When a user submits a voice query, the system must accurately detect not just the language but also the specific dialect. This is accomplished through a multi-stage process:

1. AWS Transcribe performs initial speech-to-text conversion with language identification
2. For standard languages (Hindi, Bengali, Tamil, etc.), Transcribe provides high-confidence language codes
3. For dialects, a secondary classification model analyzes phonetic patterns and vocabulary to identify specific dialects like Bhojpuri, Maithili, or Awadhi
4. The detected language and dialect are combined into a language_tag (e.g., "hi-IN-Bhojpuri") and stored in the Chat_History record

This language_tag becomes the permanent record of what language was used for that specific message, ensuring accurate playback later.

### Text-to-Speech Engine Selection

When generating voice output (either for immediate responses or historical playback), the Voice_Interface must select the appropriate TTS engine based on the language_tag:

**For Standard Languages:**
- Use AWS Polly with language-specific voices
- Hindi: Polly voice "Aditi" or "Kajal" (hi-IN)
- Bengali: Polly voice "Tanishaa" (bn-IN)
- Tamil: Polly voice "Shruti" (ta-IN)
- And similarly for other official languages

**For Regional Dialects:**
- Use Bhashini API which provides dialect-specific TTS models
- Bhojpuri: Bhashini Bhojpuri model
- Maithili: Bhashini Maithili model
- Awadhi: Bhashini Awadhi model

The selection logic is implemented as a configuration-driven mapping:

```
language_tag_to_tts_engine = {
  "hi-IN": {"provider": "aws-polly", "voice_id": "Aditi", "language_code": "hi-IN"},
  "hi-IN-Bhojpuri": {"provider": "bhashini", "model": "bhojpuri-tts-v2", "language_code": "bho"},
  "bn-IN": {"provider": "aws-polly", "voice_id": "Tanishaa", "language_code": "bn-IN"},
  "ta-IN": {"provider": "aws-polly", "voice_id": "Shruti", "language_code": "ta-IN"},
  // ... additional mappings
}
```

When the playback API is called, the system looks up the stored language_tag in this mapping and invokes the correct TTS provider with the appropriate parameters. This ensures that a Bhojpuri query from three days ago is played back in Bhojpuri, not standard Hindi.

### Audio Caching Strategy

To optimize performance and reduce costs, synthesized audio is cached in S3:

1. When a system response is first generated, the TTS output is stored in S3
2. The S3 key is recorded in the Chat_History audio_reference field
3. On subsequent playback requests, the cached audio is served via pre-signed URL
4. Audio files have a 90-day lifecycle policy, after which they're moved to S3 Glacier or deleted
5. If cached audio is unavailable, the system regenerates it using the stored text and language_tag

## Document Education and Teaching System

A critical feature of VIDHI is its ability to not just analyze documents but actively teach users what they mean. Many citizens encounter legal documents they don't understand, and VIDHI bridges this gap through interactive educational sessions.

### Simplified Explanation Generation

When a user indicates they don't understand a document (either explicitly by asking "What does this mean?" or implicitly through follow-up questions), the Document_Analyzer activates its teaching mode. The AI model is prompted to:

1. Break down the document into logical sections (preamble, key obligations, payment terms, termination clauses, etc.)
2. For each section, generate a simplified explanation that avoids legal jargon
3. Identify complex legal terms and provide definitions with everyday examples
4. Explain the practical implications of each clause in terms the user can relate to
5. Highlight what rights the user has and what obligations they're accepting

For example, if a rental agreement says "The lessee shall indemnify the lessor against any claims arising from the use of the premises," VIDHI would explain: "This means if someone gets hurt in the house you're renting and they sue the landlord, you have to pay for the landlord's legal costs. This is a big responsibility, so make sure you have insurance."

### Interactive Voice Teaching

The teaching system leverages VIDHI's voice capabilities to create an interactive learning experience:

1. The user can ask VIDHI to "read and explain" the document
2. VIDHI reads each clause aloud in the user's language, then pauses to provide the simplified explanation
3. After each section, VIDHI asks "Do you understand this part, or would you like me to explain more?"
4. Users can interrupt at any time to ask questions like "What does 'force majeure' mean?" or "What happens if I break this rule?"
5. The system maintains context throughout the teaching session, remembering what's been explained and what the user is struggling with

This conversational approach makes legal education accessible even to users with limited literacy, as they can learn through natural dialogue rather than reading dense text.

### Contextual Examples and Scenarios

To make abstract legal concepts concrete, the teaching system provides relatable examples based on the user's context:

- For a farmer in rural West Bengal reviewing a loan agreement, examples might reference crop cycles and harvest seasons
- For an urban worker reviewing an employment contract, examples might reference typical workplace situations
- For a small business owner reviewing a vendor agreement, examples might reference common business scenarios

The system uses the user's profile information (location, occupation, demographics) to tailor examples that resonate with their lived experience.

### Progressive Complexity and Adaptive Learning

The teaching system adapts to the user's comprehension level:

1. Initial explanations are very simple, assuming no legal knowledge
2. If the user asks sophisticated follow-up questions, the system provides more detailed explanations
3. If the user seems confused, the system backs up and tries a different explanation approach
4. The system tracks which concepts the user has understood and which need more work

This adaptive approach ensures that both highly educated users and those with limited formal education can learn at their own pace.

### Legal Term Glossary and Knowledge Base

VIDHI maintains a comprehensive glossary of legal terms commonly found in Indian documents, with definitions in all supported languages. When explaining a document, the system:

1. Identifies legal terms that appear in the document
2. Provides definitions from the glossary in the user's language
3. Explains how each term applies specifically to this document
4. Offers to explain related terms that might help understanding

For example, when explaining "arbitration," VIDHI might also offer to explain "mediation" and "litigation" so the user understands their options for dispute resolution.

### Teaching Session Persistence

Educational sessions are saved so users can return to them later:

1. When a user starts learning about a document, a teaching_session_id is created
2. The system tracks which sections have been explained and which questions have been asked
3. If the user leaves and comes back later, they can resume where they left off
4. The session history is stored in the Document_Analysis record and linked to Chat_History

This allows users to learn in multiple sessions, which is important for complex documents that might take time to fully understand.

## Scaling and Performance Considerations

The serverless architecture on AWS Lambda provides automatic scaling, but several design decisions optimize performance and cost:

### Lambda Function Optimization

Each Lambda function is sized appropriately for its workload. The voice processing Lambda has higher memory allocation (2GB) to handle audio encoding/decoding efficiently, while the scheme matching Lambda uses less memory (512MB) since it primarily performs database queries and simple filtering.

Functions are kept warm during peak hours using CloudWatch Events that ping them every 5 minutes, reducing cold start latency. For the emergency mode endpoint, provisioned concurrency ensures zero cold starts.

### DynamoDB Capacity Planning

DynamoDB tables use on-demand capacity mode to automatically scale with traffic. The Chat_History table is partitioned by user_id with message_id as the sort key, allowing efficient retrieval of a user's conversation history. A Global Secondary Index on timestamp enables queries for recent conversations across all users (used for analytics and monitoring).

### S3 and CloudFront for Audio Delivery

Audio files are stored in S3 with CloudFront as a CDN layer. When a playback URL is generated, it points to CloudFront, which caches frequently accessed audio files at edge locations. This reduces latency for users replaying recent conversations and lowers S3 data transfer costs.

### Caching Strategy

Redis (via AWS ElastiCache) caches frequently accessed data:
- Government scheme information (refreshed every 6 hours)
- Common legal rights queries and responses (refreshed daily)
- User profile data (invalidated on updates)

This reduces database load and improves response times for common queries.

## Offline Mode and Progressive Web App

For users with intermittent connectivity, the mobile app and web interface implement offline-first principles:

### Service Worker and Local Storage

The web app uses a service worker to cache essential resources including:
- Core UI assets (HTML, CSS, JavaScript)
- Frequently accessed legal guides and rights information
- The user's recent conversation history
- Audio files for recent voice interactions

When offline, the app serves cached content and queues new queries for submission when connectivity returns.

### Mobile App Offline Database

The React Native or Flutter mobile app uses SQLite for local storage, maintaining a synchronized copy of:
- User profile and preferences
- Recent chat history with audio references
- Cached government scheme information
- Offline-accessible legal guides

Background sync ensures the local database stays current when the device has connectivity.

## Security Architecture

Security is implemented through multiple layers of defense:

### Authentication and Authorization

AWS Cognito manages user authentication with support for:
- Aadhaar-based authentication via UIDAI integration
- Digilocker OAuth integration
- Anonymous access for unauthenticated users (with limited features)

JWT tokens are issued upon authentication and validated at the API Gateway level. Each token includes user_id and permission scopes that determine which endpoints and features the user can access.

### Data Encryption

All data is encrypted both in transit and at rest:
- TLS 1.3 for all API communications
- AWS KMS for encrypting DynamoDB tables and S3 buckets
- Client-side encryption for sensitive documents before upload

### Privacy-Preserving Features

To comply with DPDP Act and protect user privacy:
- Sensitive queries (e.g., emergency mode, certain legal questions) are processed ephemerally without storage
- User analytics are aggregated and anonymized before storage
- Federated learning approaches train AI models without centralizing raw user data
- Users can request data deletion, triggering automated cleanup across all storage systems

### Rate Limiting and Abuse Prevention

API Gateway implements rate limiting to prevent abuse:
- Authenticated users: 100 requests per minute
- Anonymous users: 20 requests per minute
- Emergency mode endpoint: No rate limiting (to ensure access during crises)

## Integration with Government Systems

VIDHI integrates with multiple government APIs and services:

### MyGov API Integration

The MyGov API provides current information on government schemes, announcements, and initiatives. VIDHI polls this API every 6 hours to refresh its scheme cache. When new schemes are announced, the system identifies potentially eligible users and sends proactive notifications.

### UIDAI Aadhaar Integration

For users who choose to authenticate with Aadhaar, VIDHI uses UIDAI's eKYC API to verify identity and retrieve basic demographic information. This enables personalized scheme recommendations based on age, location, and other factors. The Aadhaar number itself is never stored; only a cryptographic hash is retained for linking purposes.

### Digilocker Integration

Digilocker integration allows users to grant VIDHI access to their government-issued documents (e.g., income certificates, caste certificates, domicile certificates). This enables automatic eligibility verification for schemes without requiring users to manually upload documents. Access is granted through OAuth, and VIDHI only retrieves documents with explicit user consent.

### e-Courts API Integration

Where available, VIDHI integrates with e-Courts APIs to provide information on legal case status, court procedures, and judgments. This is particularly useful for the Rights_Advisor component when explaining legal precedents and procedures.

## Monitoring and Observability

The system implements comprehensive monitoring to ensure reliability and performance:

### CloudWatch Metrics and Alarms

Key metrics tracked include:
- API response times (with alarms for p99 latency > 2 seconds)
- Lambda function errors and throttles
- DynamoDB consumed capacity and throttled requests
- S3 request rates and error rates
- TTS API call volumes and costs

Alarms trigger notifications to the operations team when thresholds are exceeded.

### Distributed Tracing

AWS X-Ray provides distributed tracing across the entire request flow, from API Gateway through Lambda functions to external API calls. This enables rapid diagnosis of performance bottlenecks and errors.

### Logging and Audit Trails

All API requests are logged to CloudWatch Logs with:
- Request/response payloads (with PII redacted)
- User authentication details
- Execution duration and resource consumption
- Error messages and stack traces

For compliance, an audit trail tracks all access to user data, including who accessed what data and when.

## Cost Optimization

To maintain per-query costs under ₹0.50, several optimizations are implemented:

### AI Model Selection

The system uses different AI models based on query complexity:
- Simple queries (e.g., "What is Article 21?") use smaller, faster models
- Complex queries (e.g., document analysis) use more capable models
- The orchestration layer classifies query complexity and routes accordingly

### Caching and Reuse

Responses to common queries are cached and reused:
- "What are my rights during arrest?" is asked frequently and can be served from cache
- Government scheme information is cached and refreshed periodically rather than fetched per query
- TTS audio for common responses is pre-generated and cached

### Batch Processing

Non-urgent operations are batched:
- Scheme eligibility notifications are processed in daily batches
- Analytics and reporting run as scheduled batch jobs
- Model training and updates happen during off-peak hours

### Resource Right-Sizing

Lambda functions, DynamoDB tables, and other resources are continuously monitored and right-sized based on actual usage patterns. Over-provisioned resources are scaled down, while under-provisioned resources are scaled up to prevent throttling.

## Future Extensibility

The architecture is designed to accommodate future enhancements:

### Additional Language Support

The language_tag system can easily accommodate new languages and dialects by adding entries to the TTS engine mapping. As new TTS models become available (e.g., for tribal languages), they can be integrated without changing the core architecture.

### Advanced AI Capabilities

The modular AI core can be enhanced with:
- Multi-turn dialogue management for complex legal consultations
- Sentiment analysis to detect user distress and escalate to human support
- Personalized learning to adapt explanations based on user comprehension

### Expanded Document Types

The Document_Analyzer can be extended to handle additional document types:
- Property sale deeds
- Employment contracts
- Insurance policies
- Medical consent forms

Each document type would have specialized analysis rules and legal references.

### Integration with Legal Aid Networks

Future versions could integrate with legal aid organizations and pro bono lawyer networks, enabling seamless referrals when users need professional legal assistance beyond VIDHI's capabilities.

## Conclusion

The VIDHI technical architecture balances multiple competing concerns: performance, cost, scalability, privacy, and accessibility. The serverless AWS infrastructure provides automatic scaling and cost efficiency, while the carefully designed data model enables critical features like language-preserved voice history playback. The modular architecture allows independent evolution of components, and the comprehensive monitoring ensures reliability and rapid issue resolution. This design positions VIDHI to serve millions of Indian citizens with accessible, affordable legal guidance while maintaining the highest standards of privacy and security.
