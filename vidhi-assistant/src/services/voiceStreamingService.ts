/**
 * Voice Streaming Service
 * WebSocket-based bidirectional voice streaming with real-time transcription and TTS.
 */

export interface VoiceStreamingConfig {
  apiBaseUrl?: string;
  sessionId?: string;
  language?: string;
  languageCode?: string;
  onTranscription?: (text: string, isFinal: boolean) => void;
  onLLMToken?: (content: string, index: number) => void;
  onAudioUrl?: (url: string) => void;
  onStatus?: (message: string) => void;
  onError?: (error: string) => void;
  onDone?: (data: { transcript: string; response: string; duration_ms: number }) => void;
}

export interface VoiceStreamingMessage {
  type: string;
  [key: string]: any;
}

export class VoiceStreamingService {
  private ws: WebSocket | null = null;
  private config: VoiceStreamingConfig;
  private isConnected: boolean = false;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 3;
  private reconnectDelay: number = 1000; // ms
  
  constructor(config: VoiceStreamingConfig) {
    this.config = {
      apiBaseUrl: config.apiBaseUrl || import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
      sessionId: config.sessionId || `session_${Date.now()}`,
      language: config.language || 'english',
      languageCode: config.languageCode || 'en-IN',
      ...config
    };
  }
  
  /**
   * Connect to WebSocket server
   */
  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Convert HTTP URL to WebSocket URL
        const wsUrl = this.config.apiBaseUrl!
          .replace('http://', 'ws://')
          .replace('https://', 'wss://');
        
        const url = `${wsUrl}/api/v1/ws/voice`;
        
        console.log('Connecting to WebSocket:', url);
        
        this.ws = new WebSocket(url);
        
        this.ws.onopen = () => {
          console.log('WebSocket connected');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          
          // Send session initialization
          this.send({
            type: 'start_session',
            session_id: this.config.sessionId,
            language: this.config.language,
            language_code: this.config.languageCode
          });
          
          resolve();
        };
        
        this.ws.onmessage = (event) => {
          try {
            const message: VoiceStreamingMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          this.config.onError?.('WebSocket connection error');
        };
        
        this.ws.onclose = () => {
          console.log('WebSocket closed');
          this.isConnected = false;
          
          // Attempt reconnection
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
              this.connect().catch(console.error);
            }, this.reconnectDelay * this.reconnectAttempts);
          }
        };
        
        // Timeout if connection takes too long
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('WebSocket connection timeout'));
            this.disconnect();
          }
        }, 10000);
        
      } catch (error) {
        reject(error);
      }
    });
  }
  
  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.ws) {
      // Send end session message
      if (this.isConnected) {
        this.send({ type: 'end_session' });
      }
      
      this.ws.close();
      this.ws = null;
      this.isConnected = false;
    }
  }
  
  /**
   * Send audio chunk to server
   */
  async sendAudioChunk(audioData: Blob, format: string = 'webm'): Promise<void> {
    if (!this.isConnected || !this.ws) {
      throw new Error('WebSocket not connected');
    }
    
    // Convert Blob to base64
    const base64Data = await this.blobToBase64(audioData);
    
    this.send({
      type: 'audio_chunk',
      data: base64Data,
      format: format
    });
  }
  
  /**
   * Signal that audio recording is complete
   */
  sendAudioComplete(format: string = 'webm'): void {
    if (!this.isConnected || !this.ws) {
      throw new Error('WebSocket not connected');
    }
    
    this.send({
      type: 'audio_complete',
      format: format
    });
  }
  
  /**
   * Send message to server
   */
  private send(message: VoiceStreamingMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('Cannot send message: WebSocket not open');
    }
  }
  
  /**
   * Handle incoming message from server
   */
  private handleMessage(message: VoiceStreamingMessage): void {
    switch (message.type) {
      case 'session_started':
        console.log('Session started:', message.session_id);
        break;
      
      case 'chunk_received':
        // Audio chunk acknowledged
        console.log('Chunk received:', message.size, 'bytes');
        break;
      
      case 'transcription':
        console.log('Transcription:', message.text);
        this.config.onTranscription?.(message.text, message.is_final);
        break;
      
      case 'llm_token':
        this.config.onLLMToken?.(message.content, message.index);
        break;
      
      case 'metadata':
        console.log('Metadata:', message);
        break;
      
      case 'audio_url':
        console.log('Audio URL:', message.url);
        this.config.onAudioUrl?.(message.url);
        break;
      
      case 'status':
        console.log('Status:', message.message);
        this.config.onStatus?.(message.message);
        break;
      
      case 'done':
        console.log('Processing complete:', message);
        this.config.onDone?.({
          transcript: message.transcript,
          response: message.response,
          duration_ms: message.duration_ms
        });
        break;
      
      case 'error':
        console.error('Server error:', message.message);
        this.config.onError?.(message.message);
        break;
      
      case 'session_ended':
        console.log('Session ended');
        this.disconnect();
        break;
      
      default:
        console.warn('Unknown message type:', message.type);
    }
  }
  
  /**
   * Convert Blob to base64 string
   */
  private blobToBase64(blob: Blob): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        // Remove data URL prefix (e.g., "data:audio/webm;base64,")
        const base64Data = base64.split(',')[1];
        resolve(base64Data);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  }
  
  /**
   * Check if connected
   */
  isWebSocketConnected(): boolean {
    return this.isConnected && this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}

/**
 * Audio Recorder Helper
 */
export class AudioRecorder {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  
  /**
   * Start recording audio
   */
  async startRecording(): Promise<void> {
    try {
      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000
        }
      });
      
      // Create MediaRecorder
      const options: MediaRecorderOptions = {
        mimeType: 'audio/webm;codecs=opus'
      };
      
      // Fallback to other formats if webm not supported
      if (!MediaRecorder.isTypeSupported(options.mimeType!)) {
        options.mimeType = 'audio/ogg;codecs=opus';
        if (!MediaRecorder.isTypeSupported(options.mimeType!)) {
          options.mimeType = 'audio/mp4';
        }
      }
      
      this.mediaRecorder = new MediaRecorder(this.stream, options);
      this.audioChunks = [];
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };
      
      // Start recording (collect data every 100ms)
      this.mediaRecorder.start(100);
      
      console.log('Recording started');
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  }
  
  /**
   * Stop recording and return audio blob
   */
  async stopRecording(): Promise<Blob> {
    return new Promise((resolve, reject) => {
      if (!this.mediaRecorder) {
        reject(new Error('MediaRecorder not initialized'));
        return;
      }
      
      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, {
          type: this.mediaRecorder!.mimeType
        });
        
        // Stop all tracks
        if (this.stream) {
          this.stream.getTracks().forEach(track => track.stop());
        }
        
        console.log('Recording stopped, blob size:', audioBlob.size);
        resolve(audioBlob);
      };
      
      this.mediaRecorder.stop();
    });
  }
  
  /**
   * Get audio chunks collected so far
   */
  getAudioChunks(): Blob[] {
    return this.audioChunks;
  }
  
  /**
   * Check if recording
   */
  isRecording(): boolean {
    return this.mediaRecorder !== null && this.mediaRecorder.state === 'recording';
  }
}
