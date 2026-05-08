# VIDHI Voice Streaming - Technical Guide

**Version**: 1.0.0  
**Last Updated**: May 7, 2026

---

## Architecture

### Voice Pipeline

```
┌─────────────────┐
│  User Speech    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Browser        │ ← MediaRecorder API
│  Recording      │   (WebM/Opus codec)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Base64 Encode  │ ← FileReader API
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WebSocket      │ ← Send audio chunks
│  Client         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  WebSocket      │ ← /api/v1/ws/voice
│  Server         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Upload to S3   │ ← s3://bucket/ws-transcribe/...
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Transcribe │ ← Start transcription job
│  Job            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Poll Status    │ ← Wait for COMPLETED (1-3s)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Get Transcript │ ← Download from S3/HTTPS
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  LLM Query      │ ← query_stream() method
│  (Streaming)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AWS Polly TTS  │ ← get_or_create_audio()
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audio Playback │ ← HTML5 Audio element
└─────────────────┘
```

---

## WebSocket Protocol

### Message Types

#### Client → Server

**1. start_session**
```json
{
  "type": "start_session",
  "session_id": "user-session-123",
  "language": "english",
  "language_code": "en-IN"
}
```

**2. audio_chunk**
```json
{
  "type": "audio_chunk",
  "data": "base64_encoded_audio_data",
  "format": "webm"
}
```

**3. audio_complete**
```json
{
  "type": "audio_complete",
  "format": "webm"
}
```

**4. end_session**
```json
{
  "type": "end_session"
}
```

#### Server → Client

**1. session_started**
```json
{
  "type": "session_started",
  "session_id": "user-session-123",
  "language": "english"
}
```

**2. chunk_received**
```json
{
  "type": "chunk_received",
  "size": 1024
}
```

**3. transcription**
```json
{
  "type": "transcription",
  "text": "What is Section 438 CrPC?",
  "is_final": true,
  "language_code": "en-IN"
}
```

**4. llm_token**
```json
{
  "type": "llm_token",
  "content": "Section",
  "index": 0
}
```

**5. metadata**
```json
{
  "type": "metadata",
  "confidence": 0.85,
  "citations": ["Section 438 CrPC"]
}
```

**6. audio_url**
```json
{
  "type": "audio_url",
  "url": "https://bucket.s3.amazonaws.com/audio.mp3",
  "format": "mp3"
}
```

**7. status**
```json
{
  "type": "status",
  "message": "Transcribing audio..."
}
```

**8. done**
```json
{
  "type": "done",
  "duration_ms": 3500,
  "transcript": "What is Section 438 CrPC?",
  "response": "Section 438 CrPC allows..."
}
```

**9. error**
```json
{
  "type": "error",
  "message": "Transcription service unavailable"
}
```

---

## Audio Formats

### Supported Formats
- **WebM** (preferred): Opus codec, 16kHz sample rate
- **OGG**: Opus codec, 16kHz sample rate
- **MP3**: MPEG Audio Layer 3
- **MP4/M4A**: AAC codec
- **WAV**: PCM, 16kHz sample rate
- **FLAC**: Lossless compression

### Recommended Settings
```javascript
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm;codecs=opus',
  audioBitsPerSecond: 16000
});
```

### Browser Compatibility
| Browser | WebM | OGG | MP3 | MP4 |
|---------|------|-----|-----|-----|
| Chrome  | ✅   | ✅  | ✅  | ✅  |
| Firefox | ✅   | ✅  | ❌  | ❌  |
| Safari  | ❌   | ❌  | ✅  | ✅  |
| Edge    | ✅   | ✅  | ✅  | ✅  |

---

## AWS Services Configuration

### AWS Transcribe

**Supported Languages**:
- Hindi (hi-IN)
- Bengali (bn-IN)
- Tamil (ta-IN)
- Telugu (te-IN)
- Marathi (mr-IN)
- Gujarati (gu-IN)
- Kannada (kn-IN)
- Malayalam (ml-IN)
- Punjabi (pa-IN)
- English (en-IN)

**Configuration**:
```python
transcribe_service = AWSTranscribeService(region='ap-south-1')

result = transcribe_service.transcribe_audio(
    audio_s3_uri='s3://bucket/audio.webm',
    language_code='hi-IN',
    identify_language=False,
    media_format='webm'
)
```

**Pricing** (as of 2026):
- $0.024 per minute (batch transcription)
- $0.040 per minute (streaming transcription)

### AWS Polly

**Supported Voices**:
- Hindi: Kajal (neural)
- Bengali: Tanishaa (neural)
- English (India): Kajal (neural)

**Configuration**:
```python
polly_service = AWSPollyService(region='ap-south-1')

result = polly_service.synthesize_speech(
    text='Section 438 CrPC allows...',
    language_code='hi-IN',
    output_format='mp3'
)
```

**Pricing** (as of 2026):
- $16.00 per 1 million characters (neural voices)
- $4.00 per 1 million characters (standard voices)

---

## Performance Optimization

### Current Performance
| Stage | Time | Optimization Potential |
|-------|------|----------------------|
| WebSocket connection | < 100ms | ✅ Optimal |
| Audio upload | < 500ms | ⚠️ Depends on network |
| Transcription | 1-3s | 🔴 High (use streaming) |
| LLM first token | < 500ms | ✅ Optimal |
| LLM complete | 1-2s | ✅ Optimal |
| TTS generation | 500ms-1s | ⚠️ Medium (use streaming) |
| **Total** | **3-7s** | **Target: < 3s** |

### Optimization Strategies

#### 1. Use AWS Transcribe Streaming API
**Current**: Batch transcription (1-3s latency)  
**Optimized**: Streaming transcription (< 500ms latency)

```python
# Instead of batch job
transcribe_result = transcribe_service.transcribe_audio(s3_uri, ...)

# Use streaming API
async for event in transcribe_service.transcribe_stream(audio_stream):
    if event['type'] == 'transcript':
        yield event['text']
```

**Benefit**: Reduce transcription latency by 1-2.5 seconds

#### 2. Use AWS Polly Streaming
**Current**: Generate complete audio file (500ms-1s)  
**Optimized**: Stream audio chunks (< 200ms to first chunk)

```python
# Instead of complete synthesis
audio_url = polly_service.synthesize_and_upload_to_s3(text, ...)

# Use streaming synthesis
async for audio_chunk in polly_service.synthesize_stream(text):
    yield audio_chunk
```

**Benefit**: Reduce TTS latency by 300-800ms

#### 3. Parallel Processing
**Current**: Sequential (Transcribe → LLM → TTS)  
**Optimized**: Start TTS while LLM is streaming

```python
# Start TTS generation as soon as we have enough tokens
if token_count >= 10:
    asyncio.create_task(generate_tts(partial_response))
```

**Benefit**: Reduce total latency by 500ms-1s

#### 4. Audio Compression
**Current**: WebM with default settings  
**Optimized**: Opus codec at 16kbps

```javascript
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm;codecs=opus',
  audioBitsPerSecond: 16000  // Lower bitrate for speech
});
```

**Benefit**: Reduce upload time by 30-50%

#### 5. Connection Pooling
**Current**: New S3 connection per request  
**Optimized**: Reuse S3 connections

```python
# Use connection pooling
import boto3
from botocore.config import Config

config = Config(
    max_pool_connections=50,
    retries={'max_attempts': 3}
)

s3 = boto3.client('s3', config=config)
```

**Benefit**: Reduce S3 upload latency by 50-100ms

---

## Error Handling

### Common Errors

#### 1. Microphone Access Denied
**Error**: `NotAllowedError: Permission denied`  
**Solution**: 
- Show clear permission instructions
- Provide fallback to text input
- Check HTTPS requirement

#### 2. WebSocket Connection Failed
**Error**: `WebSocket connection failed`  
**Solution**:
- Retry with exponential backoff (3 attempts)
- Check firewall/proxy settings
- Verify WebSocket endpoint URL

#### 3. Transcription Failed
**Error**: `Transcription service unavailable`  
**Solution**:
- Check AWS Transcribe service status
- Verify S3 bucket permissions
- Check audio format compatibility

#### 4. Audio Too Short
**Error**: `No audio data received`  
**Solution**:
- Require minimum recording duration (1 second)
- Show recording indicator
- Provide feedback on audio quality

#### 5. Network Timeout
**Error**: `Request timeout`  
**Solution**:
- Increase timeout settings
- Show progress indicator
- Allow cancellation and retry

---

## Security Considerations

### 1. Microphone Permission
- Always request permission explicitly
- Show clear explanation of why permission is needed
- Respect user's choice to deny

### 2. Audio Data Privacy
- Audio files stored in private S3 bucket
- No public access to audio files
- Implement S3 lifecycle policy (delete after 7 days)
- No audio recording without user consent

### 3. Session Isolation
- Each session has unique ID
- No cross-session data leakage
- Session-specific S3 keys
- Proper cleanup on disconnect

### 4. Input Validation
- Validate audio format
- Validate audio size (max 10MB)
- Validate session ID
- Sanitize all text inputs

### 5. Rate Limiting
- Limit WebSocket connections per IP
- Limit audio uploads per user
- Implement DoS protection

---

## Testing

### Unit Tests
```bash
# Backend
pytest tests/test_websocket.py -v

# Frontend
npm test websocket.test.ts
```

### Integration Tests
```bash
# Start backend
uvicorn app:app --reload

# Start frontend
npm run dev

# Manual testing:
# 1. Open browser
# 2. Navigate to voice chat
# 3. Click mic button
# 4. Speak a question
# 5. Verify transcription
# 6. Verify response
# 7. Verify audio playback
```

### Load Testing
```bash
# Use locust or k6 for load testing
# Test concurrent WebSocket connections
# Test audio upload throughput
# Test end-to-end latency under load
```

---

## Monitoring

### Metrics to Track
1. **WebSocket Connections**
   - Active connections
   - Connection success rate
   - Reconnection rate
   - Average connection duration

2. **Audio Processing**
   - Upload success rate
   - Average upload time
   - Transcription success rate
   - Average transcription time

3. **LLM Performance**
   - First token latency
   - Token throughput
   - Error rate

4. **TTS Performance**
   - Generation success rate
   - Average generation time
   - Audio quality

5. **End-to-End**
   - Total pipeline latency
   - User satisfaction
   - Error rate

### Logging
```python
# Log all voice interactions
logger.info(f"Voice session started: {session_id}")
logger.info(f"Transcribed: {transcript[:50]}...")
logger.info(f"Voice processing complete: {duration_ms}ms")
logger.error(f"Transcription error: {error}")
```

---

## Troubleshooting Guide

### Problem: High Latency

**Symptoms**: End-to-end latency > 7 seconds

**Diagnosis**:
1. Check network latency: `ping api.vidhi.com`
2. Check AWS region: Should be `ap-south-1`
3. Check audio size: Should be < 1MB
4. Check transcription time: Should be < 3s

**Solutions**:
1. Use streaming transcription
2. Optimize audio encoding
3. Use CDN for audio playback
4. Implement caching

### Problem: Poor Audio Quality

**Symptoms**: Transcription accuracy < 80%

**Diagnosis**:
1. Check microphone quality
2. Check background noise
3. Check audio format
4. Check sample rate

**Solutions**:
1. Use noise cancellation
2. Use echo cancellation
3. Increase sample rate to 48kHz
4. Use better codec (Opus)

### Problem: Frequent Disconnections

**Symptoms**: WebSocket disconnects frequently

**Diagnosis**:
1. Check network stability
2. Check firewall settings
3. Check proxy configuration
4. Check server logs

**Solutions**:
1. Implement heartbeat/ping-pong
2. Increase timeout settings
3. Add reconnection logic
4. Use WebSocket over HTTPS

---

## Best Practices

### 1. User Experience
- Show clear recording indicator
- Provide visual feedback (waveform)
- Show status at each stage
- Allow cancellation at any time
- Handle errors gracefully

### 2. Performance
- Use audio compression
- Implement caching
- Use connection pooling
- Optimize buffer sizes
- Monitor memory usage

### 3. Security
- Request permissions explicitly
- Validate all inputs
- Implement rate limiting
- Use HTTPS/WSS
- Clean up resources

### 4. Reliability
- Implement reconnection logic
- Handle network errors
- Provide fallback options
- Log all errors
- Monitor metrics

---

## Future Enhancements

### Phase 1 (Short Term)
1. Implement AWS Transcribe Streaming API
2. Implement AWS Polly Streaming
3. Add voice activity detection (VAD)
4. Add noise cancellation
5. Optimize audio encoding

### Phase 2 (Medium Term)
1. Multi-language voice support
2. Voice settings (speed, pitch, volume)
3. Voice history playback
4. Real-time translation
5. Voice biometrics

### Phase 3 (Long Term)
1. Custom voice models
2. Emotion detection
3. Speaker diarization
4. Voice cloning
5. Real-time collaboration

---

**Last Updated**: May 7, 2026  
**Version**: 1.0.0  
**Maintainer**: VIDHI Development Team
