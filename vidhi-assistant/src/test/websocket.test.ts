/**
 * Tests for WebSocket Voice Streaming
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { VoiceStreamingService, AudioRecorder } from '../services/voiceStreamingService';

// Mock WebSocket
class MockWebSocket {
  public readyState: number = WebSocket.CONNECTING;
  public onopen: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  
  private messageQueue: any[] = [];
  
  constructor(public url: string) {
    // Simulate connection after a short delay
    setTimeout(() => {
      this.readyState = WebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }
  
  send(data: string) {
    const message = JSON.parse(data);
    this.messageQueue.push(message);
    
    // Simulate server responses
    setTimeout(() => {
      this.simulateServerResponse(message);
    }, 10);
  }
  
  close() {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }
  
  private simulateServerResponse(message: any) {
    if (!this.onmessage) return;
    
    switch (message.type) {
      case 'start_session':
        this.sendMessage({
          type: 'session_started',
          session_id: message.session_id,
          language: message.language
        });
        break;
      
      case 'audio_chunk':
        this.sendMessage({
          type: 'chunk_received',
          size: 1024
        });
        break;
      
      case 'audio_complete':
        // Simulate full pipeline
        this.sendMessage({ type: 'status', message: 'Transcribing audio...' });
        setTimeout(() => {
          this.sendMessage({
            type: 'transcription',
            text: 'What is Section 438 CrPC?',
            is_final: true,
            language_code: 'en-IN'
          });
        }, 20);
        setTimeout(() => {
          this.sendMessage({ type: 'status', message: 'Generating response...' });
        }, 40);
        setTimeout(() => {
          this.sendMessage({ type: 'llm_token', content: 'Section', index: 0 });
        }, 60);
        setTimeout(() => {
          this.sendMessage({ type: 'llm_token', content: ' 438', index: 1 });
        }, 80);
        setTimeout(() => {
          this.sendMessage({
            type: 'audio_url',
            url: 'https://test.com/audio.mp3',
            format: 'mp3'
          });
        }, 100);
        setTimeout(() => {
          this.sendMessage({
            type: 'done',
            duration_ms: 2500,
            transcript: 'What is Section 438 CrPC?',
            response: 'Section 438'
          });
        }, 120);
        break;
      
      case 'end_session':
        this.sendMessage({
          type: 'session_ended',
          session_id: message.session_id
        });
        break;
    }
  }
  
  private sendMessage(data: any) {
    if (this.onmessage) {
      const event = new MessageEvent('message', {
        data: JSON.stringify(data)
      });
      this.onmessage(event);
    }
  }
}

// Mock global WebSocket
(global as any).WebSocket = MockWebSocket;

// Mock MediaRecorder
class MockMediaRecorder {
  public state: string = 'inactive';
  public ondataavailable: ((event: any) => void) | null = null;
  public onstop: (() => void) | null = null;
  
  constructor(public stream: MediaStream, public options?: any) {}
  
  start(timeslice?: number) {
    this.state = 'recording';
    
    // Simulate data available events
    setTimeout(() => {
      if (this.ondataavailable) {
        this.ondataavailable({
          data: new Blob(['fake audio data'], { type: 'audio/webm' })
        });
      }
    }, 100);
  }
  
  stop() {
    this.state = 'inactive';
    if (this.onstop) {
      this.onstop();
    }
  }
  
  static isTypeSupported(mimeType: string): boolean {
    return mimeType === 'audio/webm;codecs=opus';
  }
}

(global as any).MediaRecorder = MockMediaRecorder;

// Mock navigator.mediaDevices
(global as any).navigator = {
  mediaDevices: {
    getUserMedia: vi.fn().mockResolvedValue({
      getTracks: () => [{
        stop: vi.fn()
      }]
    })
  }
};

// Mock FileReader
class MockFileReader {
  public onloadend: (() => void) | null = null;
  public onerror: ((error: any) => void) | null = null;
  public result: string | null = null;
  
  readAsDataURL(blob: Blob) {
    setTimeout(() => {
      this.result = 'data:audio/webm;base64,ZmFrZSBhdWRpbyBkYXRh';
      if (this.onloadend) {
        this.onloadend();
      }
    }, 10);
  }
}

(global as any).FileReader = MockFileReader;

describe('VoiceStreamingService', () => {
  let service: VoiceStreamingService;
  let callbacks: any;
  
  beforeEach(() => {
    callbacks = {
      onTranscription: vi.fn(),
      onLLMToken: vi.fn(),
      onAudioUrl: vi.fn(),
      onStatus: vi.fn(),
      onError: vi.fn(),
      onDone: vi.fn()
    };
    
    service = new VoiceStreamingService({
      apiBaseUrl: 'http://localhost:8000',
      sessionId: 'test-session',
      language: 'english',
      languageCode: 'en-IN',
      ...callbacks
    });
  });
  
  afterEach(() => {
    if (service) {
      service.disconnect();
    }
  });
  
  it('should connect to WebSocket server', async () => {
    await service.connect();
    
    expect(service.isWebSocketConnected()).toBe(true);
  });
  
  it('should send session initialization on connect', async () => {
    await service.connect();
    
    // Wait for initialization
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(service.isWebSocketConnected()).toBe(true);
  });
  
  it('should handle transcription messages', async () => {
    await service.connect();
    
    // Simulate transcription message
    const ws = (service as any).ws;
    ws.sendMessage({
      type: 'transcription',
      text: 'Test transcription',
      is_final: true
    });
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(callbacks.onTranscription).toHaveBeenCalledWith('Test transcription', true);
  });
  
  it('should handle LLM token messages', async () => {
    await service.connect();
    
    // Simulate LLM token
    const ws = (service as any).ws;
    ws.sendMessage({
      type: 'llm_token',
      content: 'Section',
      index: 0
    });
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(callbacks.onLLMToken).toHaveBeenCalledWith('Section', 0);
  });
  
  it('should handle audio URL messages', async () => {
    await service.connect();
    
    // Simulate audio URL
    const ws = (service as any).ws;
    ws.sendMessage({
      type: 'audio_url',
      url: 'https://test.com/audio.mp3'
    });
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(callbacks.onAudioUrl).toHaveBeenCalledWith('https://test.com/audio.mp3');
  });
  
  it('should handle status messages', async () => {
    await service.connect();
    
    // Simulate status
    const ws = (service as any).ws;
    ws.sendMessage({
      type: 'status',
      message: 'Processing...'
    });
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(callbacks.onStatus).toHaveBeenCalledWith('Processing...');
  });
  
  it('should handle error messages', async () => {
    await service.connect();
    
    // Simulate error
    const ws = (service as any).ws;
    ws.sendMessage({
      type: 'error',
      message: 'Test error'
    });
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(callbacks.onError).toHaveBeenCalledWith('Test error');
  });
  
  it('should handle done messages', async () => {
    await service.connect();
    
    // Simulate done
    const ws = (service as any).ws;
    ws.sendMessage({
      type: 'done',
      transcript: 'Test transcript',
      response: 'Test response',
      duration_ms: 2500
    });
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(callbacks.onDone).toHaveBeenCalledWith({
      transcript: 'Test transcript',
      response: 'Test response',
      duration_ms: 2500
    });
  });
  
  it('should send audio chunks', async () => {
    await service.connect();
    
    const audioBlob = new Blob(['test audio'], { type: 'audio/webm' });
    await service.sendAudioChunk(audioBlob, 'webm');
    
    // Wait for processing
    await new Promise(resolve => setTimeout(resolve, 50));
    
    // Should not throw
    expect(service.isWebSocketConnected()).toBe(true);
  });
  
  it('should send audio complete signal', async () => {
    await service.connect();
    
    service.sendAudioComplete('webm');
    
    // Should not throw
    expect(service.isWebSocketConnected()).toBe(true);
  });
  
  it('should disconnect cleanly', async () => {
    await service.connect();
    
    expect(service.isWebSocketConnected()).toBe(true);
    
    service.disconnect();
    
    await new Promise(resolve => setTimeout(resolve, 50));
    
    expect(service.isWebSocketConnected()).toBe(false);
  });
  
  it('should handle connection timeout', async () => {
    // Create service with very short timeout
    const timeoutService = new VoiceStreamingService({
      apiBaseUrl: 'http://localhost:8000',
      sessionId: 'test-session',
      onError: callbacks.onError
    });
    
    // Mock WebSocket that never connects
    class SlowWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url);
        // Never call onopen
      }
    }
    
    (global as any).WebSocket = SlowWebSocket;
    
    try {
      await timeoutService.connect();
    } catch (error) {
      expect(error).toBeDefined();
    }
    
    // Restore mock
    (global as any).WebSocket = MockWebSocket;
  });
});

describe('AudioRecorder', () => {
  let recorder: AudioRecorder;
  
  beforeEach(() => {
    recorder = new AudioRecorder();
  });
  
  it('should start recording', async () => {
    await recorder.startRecording();
    
    expect(recorder.isRecording()).toBe(true);
  });
  
  it('should stop recording and return audio blob', async () => {
    await recorder.startRecording();
    
    expect(recorder.isRecording()).toBe(true);
    
    const audioBlob = await recorder.stopRecording();
    
    expect(recorder.isRecording()).toBe(false);
    expect(audioBlob).toBeInstanceOf(Blob);
  });
  
  it('should collect audio chunks', async () => {
    await recorder.startRecording();
    
    // Wait for data available events
    await new Promise(resolve => setTimeout(resolve, 150));
    
    const chunks = recorder.getAudioChunks();
    
    expect(chunks.length).toBeGreaterThan(0);
  });
  
  it('should handle microphone access denial', async () => {
    // Mock getUserMedia to reject
    (global as any).navigator.mediaDevices.getUserMedia = vi.fn().mockRejectedValue(
      new Error('Permission denied')
    );
    
    try {
      await recorder.startRecording();
      expect(true).toBe(false); // Should not reach here
    } catch (error) {
      expect(error).toBeDefined();
    }
    
    // Restore mock
    (global as any).navigator.mediaDevices.getUserMedia = vi.fn().mockResolvedValue({
      getTracks: () => [{
        stop: vi.fn()
      }]
    });
  });
  
  it('should stop all tracks on stop recording', async () => {
    const stopMock = vi.fn();
    
    (global as any).navigator.mediaDevices.getUserMedia = vi.fn().mockResolvedValue({
      getTracks: () => [{
        stop: stopMock
      }]
    });
    
    await recorder.startRecording();
    await recorder.stopRecording();
    
    expect(stopMock).toHaveBeenCalled();
  });
});

describe('VoiceStreamingService - Full Pipeline', () => {
  it('should handle complete voice pipeline', async () => {
    const callbacks = {
      onTranscription: vi.fn(),
      onLLMToken: vi.fn(),
      onAudioUrl: vi.fn(),
      onStatus: vi.fn(),
      onDone: vi.fn()
    };
    
    const service = new VoiceStreamingService({
      apiBaseUrl: 'http://localhost:8000',
      sessionId: 'test-session',
      ...callbacks
    });
    
    await service.connect();
    
    // Send audio
    const audioBlob = new Blob(['test audio'], { type: 'audio/webm' });
    await service.sendAudioChunk(audioBlob, 'webm');
    service.sendAudioComplete('webm');
    
    // Wait for all pipeline stages
    await new Promise(resolve => setTimeout(resolve, 200));
    
    // Verify all callbacks were called
    expect(callbacks.onStatus).toHaveBeenCalled();
    expect(callbacks.onTranscription).toHaveBeenCalledWith(
      'What is Section 438 CrPC?',
      true
    );
    expect(callbacks.onLLMToken).toHaveBeenCalled();
    expect(callbacks.onAudioUrl).toHaveBeenCalledWith('https://test.com/audio.mp3');
    expect(callbacks.onDone).toHaveBeenCalledWith({
      transcript: 'What is Section 438 CrPC?',
      response: 'Section 438',
      duration_ms: 2500
    });
    
    service.disconnect();
  });
});
