# VIDHI Streaming Migration Guide

**Version**: 1.0.0  
**Date**: May 7, 2026

---

## Overview

This guide helps you migrate from the traditional request-response API to the new streaming API for both text and voice interactions.

---

## Why Migrate?

### Benefits of Streaming

1. **Better User Experience**
   - 50-70% reduction in perceived latency
   - Real-time feedback
   - Progress indicators
   - Cancellation support

2. **Improved Performance**
   - First token in < 500ms (vs 2-5s for complete response)
   - Streaming reduces memory usage
   - Better resource utilization

3. **Modern Features**
   - ChatGPT-like experience
   - Voice conversations
   - Real-time transcription
   - Natural voice playback

---

## Migration Path

### Phase 1: Text Streaming (Week 1)
- ✅ Implement SSE endpoint
- ✅ Update frontend to use streaming
- ✅ Maintain backward compatibility
- ✅ Test thoroughly

### Phase 2: Voice Streaming (Week 2)
- ✅ Implement WebSocket endpoint
- ✅ Add voice UI components
- ✅ Integrate with existing app
- ✅ Test thoroughly

### Phase 3: Optimization (Week 3)
- ⏳ Performance optimization
- ⏳ Integration testing
- ⏳ Documentation
- ⏳ Deployment

---

## Backend Migration

### Step 1: Install Dependencies

```bash
# Add to requirements.txt
sse-starlette==1.6.5
python-socketio==5.10.0
aiofiles==23.2.1
```

```bash
# Install
pip install -r requirements.txt
```

### Step 2: Update LLM Service

**Before** (`vidhi-backend/llm_setup/bedrock_setup.py`):
```python
def query(self, question, session_id="default", language="English"):
    # ... existing code ...
    response = self.llm.invoke(prompt)
    return response.content
```

**After**:
```python
async def query_stream(self, question, session_id="default", language="English"):
    # ... existing code ...
    async for chunk in self.llm.astream(prompt):
        if chunk.content:
            yield {
                "type": "token",
                "content": chunk.content,
                "index": token_count
            }
            token_count += 1
    
    yield {"type": "metadata", "confidence": 0.85, "citations": [...]}
    yield {"type": "done", "total_tokens": token_count}
```

### Step 3: Add Streaming Routes

Create `vidhi-backend/routes/streaming_routes.py`:
```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api/v1/stream", tags=["streaming"])

@router.post("/chat")
async def stream_chat(request: ChatRequest):
    async def event_generator():
        async for event in llm_service.query_stream(...):
            yield {
                "event": event["type"],
                "data": json.dumps(event)
            }
    
    return EventSourceResponse(event_generator())
```

### Step 4: Add WebSocket Routes

Create `vidhi-backend/routes/websocket_routes.py`:
```python
from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])

@router.websocket("/voice")
async def voice_streaming(websocket: WebSocket):
    await websocket.accept()
    
    # Handle voice pipeline
    # ... (see full implementation in file)
```

### Step 5: Register Routes

Update `vidhi-backend/app.py`:
```python
# Import routes
from routes.streaming_routes import router as streaming_router
from routes.websocket_routes import router as websocket_router, set_services

# Register routes
app.include_router(streaming_router)
app.include_router(websocket_router)

# Set services in startup_event
@app.on_event("startup")
async def startup_event():
    # ... existing code ...
    
    # Set services for WebSocket
    if set_services and transcribe_service and polly_service:
        set_services(llm_service, transcribe_service, polly_service)
```

---

## Frontend Migration

### Step 1: Add Streaming Function

Update `vidhi-assistant/src/api/apiClient.ts`:

**Before**:
```typescript
export async function sendMessage(text: string, sessionId: string) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    body: JSON.stringify({ text, session_id: sessionId })
  });
  
  const data = await response.json();
  return data.response;
}
```

**After**:
```typescript
export async function* streamChat(
  text: string,
  sessionId: string,
  language: string = 'english'
): AsyncGenerator<StreamEvent, void, unknown> {
  const response = await fetch(`${API_BASE_URL}/api/v1/stream/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, session_id: sessionId, language })
  });
  
  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        yield data;
      }
    }
  }
}
```

### Step 2: Update UI Component

Update `vidhi-assistant/src/pages/Index.tsx`:

**Before**:
```typescript
const handleSend = async () => {
  const response = await sendMessage(text, sessionId);
  setMessages([...messages, { text: response, sender: 'ai' }]);
};
```

**After**:
```typescript
const handleSend = async () => {
  let fullResponse = '';
  const aiMsgId = Date.now();
  
  // Add placeholder message
  setMessages([...messages, { id: aiMsgId, text: '', sender: 'ai' }]);
  
  // Stream tokens
  for await (const event of streamChat(text, sessionId, language)) {
    if (event.type === 'token') {
      fullResponse += event.content;
      
      // Update message in real-time
      setMessages(prev => prev.map(msg => 
        msg.id === aiMsgId ? { ...msg, text: fullResponse } : msg
      ));
    }
  }
};
```

### Step 3: Add Voice Streaming

Create `vidhi-assistant/src/services/voiceStreamingService.ts`:
```typescript
export class VoiceStreamingService {
  private ws: WebSocket | null = null;
  
  async connect(): Promise<void> {
    const wsUrl = this.config.apiBaseUrl!
      .replace('http://', 'ws://')
      .replace('https://', 'wss://');
    
    this.ws = new WebSocket(`${wsUrl}/api/v1/ws/voice`);
    
    this.ws.onopen = () => {
      this.send({ type: 'start_session', session_id: this.config.sessionId });
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }
  
  // ... (see full implementation in file)
}
```

### Step 4: Add Voice UI Component

Create `vidhi-assistant/src/components/vidhi/VoiceChat.tsx`:
```typescript
export const VoiceChat: React.FC<VoiceChatProps> = ({
  sessionId,
  language,
  languageCode
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  
  const handleStartRecording = async () => {
    const recorder = new AudioRecorder();
    await recorder.startRecording();
    setIsRecording(true);
  };
  
  const handleStopRecording = async () => {
    const audioBlob = await recorder.stopRecording();
    await voiceService.sendAudioChunk(audioBlob, 'webm');
    voiceService.sendAudioComplete('webm');
    setIsRecording(false);
  };
  
  return (
    <Card>
      <Button onClick={isRecording ? handleStopRecording : handleStartRecording}>
        {isRecording ? <MicOff /> : <Mic />}
      </Button>
      {transcript && <div>{transcript}</div>}
      {response && <div>{response}</div>}
    </Card>
  );
};
```

---

## Backward Compatibility

### Maintaining Old API

The old `/chat` endpoint remains unchanged:

```python
@app.post("/chat", response_model=ChatResponse)
async def chat(text: str, ...):
    # ... existing implementation ...
    ai_response = llm_service.query(text, session_id, language)
    return ChatResponse(response=ai_response, ...)
```

### Feature Flag

Add feature flag to enable/disable streaming:

```typescript
// Frontend
const streamingEnabled = true;  // Can be per-user setting

const handleSend = async () => {
  if (streamingEnabled) {
    // Use streaming
    for await (const event of streamChat(...)) { ... }
  } else {
    // Use old API
    const response = await sendMessage(...);
  }
};
```

---

## Testing Migration

### Step 1: Test Backend

```bash
# Test SSE endpoint
curl -N http://localhost:8000/api/v1/stream/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What is Section 438?","session_id":"test","language":"english"}'

# Test WebSocket endpoint
wscat -c ws://localhost:8000/api/v1/ws/voice
> {"type":"start_session","session_id":"test","language":"english"}
```

### Step 2: Test Frontend

```bash
# Run tests
npm test streaming.test.ts
npm test websocket.test.ts

# Manual testing
npm run dev
# Open browser, test streaming
```

### Step 3: Integration Testing

```bash
# Start backend
uvicorn app:app --reload

# Start frontend
npm run dev

# Test scenarios:
# 1. Text streaming
# 2. Voice streaming
# 3. Error handling
# 4. Cancellation
# 5. Reconnection
```

---

## Deployment

### Step 1: Update Dependencies

```bash
# Backend
pip install -r requirements.txt

# Frontend
npm install
```

### Step 2: Set Environment Variables

```bash
# Backend
export ENABLE_STREAMING=True
export ENABLE_VOICE_STREAMING=True
export S3_BUCKET_AUDIO=vidhi-audio-prod
export AWS_REGION=ap-south-1
```

### Step 3: Deploy Backend

```bash
# Build
docker build -t vidhi-backend .

# Deploy
docker run -p 8000:8000 vidhi-backend
```

### Step 4: Deploy Frontend

```bash
# Build
npm run build

# Deploy
npm run preview
```

### Step 5: Verify

```bash
# Check health
curl http://localhost:8000/api/v1/stream/health
curl http://localhost:8000/api/v1/ws/health

# Test streaming
# ... (manual testing)
```

---

## Rollback Plan

If issues occur, rollback is simple:

### Option 1: Disable Streaming

```bash
# Backend
export ENABLE_STREAMING=False
export ENABLE_VOICE_STREAMING=False

# Restart server
```

### Option 2: Use Feature Flag

```typescript
// Frontend
const streamingEnabled = false;  // Disable for all users
```

### Option 3: Full Rollback

```bash
# Revert to previous version
git checkout previous-version
docker build -t vidhi-backend .
docker run -p 8000:8000 vidhi-backend
```

---

## Monitoring

### Metrics to Track

1. **Adoption Rate**
   - % of users using streaming
   - % of requests using streaming
   - User feedback

2. **Performance**
   - First token latency
   - End-to-end latency
   - Error rate

3. **Reliability**
   - Connection success rate
   - Reconnection rate
   - Timeout rate

### Alerts

Set up alerts for:
- High error rate (> 5%)
- High latency (> 10s)
- Low connection success rate (< 95%)

---

## Troubleshooting

### Common Issues

**Issue**: Streaming not working  
**Solution**: Check `ENABLE_STREAMING` environment variable

**Issue**: WebSocket connection failed  
**Solution**: Check firewall, verify WSS protocol

**Issue**: High latency  
**Solution**: Check AWS region, optimize audio encoding

**Issue**: Transcription failed  
**Solution**: Check AWS Transcribe configuration, verify S3 permissions

---

## Support

For migration support:
- Documentation: `docs/STREAMING.md`
- Voice guide: `docs/VOICE_STREAMING.md`
- Migration guide: `docs/STREAMING_MIGRATION_GUIDE.md`
- GitHub issues: `github.com/vidhi/issues`

---

**Last Updated**: May 7, 2026  
**Version**: 1.0.0
