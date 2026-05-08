/**
 * Voice Chat Component
 * Real-time bidirectional voice streaming with WebSocket
 */

import React, { useState, useEffect, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { VoiceStreamingService, AudioRecorder } from '@/services/voiceStreamingService';
import { AudioWave } from './AudioWave';

interface VoiceChatProps {
  sessionId: string;
  language?: string;
  languageCode?: string;
  onTranscript?: (text: string) => void;
  onResponse?: (text: string) => void;
  onError?: (error: string) => void;
}

export const VoiceChat: React.FC<VoiceChatProps> = ({
  sessionId,
  language = 'english',
  languageCode = 'en-IN',
  onTranscript,
  onResponse,
  onError
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [response, setResponse] = useState('');
  const [status, setStatus] = useState('');
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  
  const voiceServiceRef = useRef<VoiceStreamingService | null>(null);
  const audioRecorderRef = useRef<AudioRecorder | null>(null);
  const audioElementRef = useRef<HTMLAudioElement | null>(null);
  
  // Initialize WebSocket connection
  useEffect(() => {
    const initializeVoiceService = async () => {
      try {
        const service = new VoiceStreamingService({
          sessionId,
          language,
          languageCode,
          onTranscription: (text, isFinal) => {
            setTranscript(text);
            if (isFinal) {
              onTranscript?.(text);
            }
          },
          onLLMToken: (content) => {
            setResponse(prev => prev + content);
          },
          onAudioUrl: (url) => {
            setAudioUrl(url);
            setIsProcessing(false);
          },
          onStatus: (message) => {
            setStatus(message);
          },
          onError: (error) => {
            console.error('Voice streaming error:', error);
            setStatus(`Error: ${error}`);
            setIsProcessing(false);
            setIsRecording(false);
            onError?.(error);
          },
          onDone: (data) => {
            setTranscript(data.transcript);
            setResponse(data.response);
            onResponse?.(data.response);
            setIsProcessing(false);
            setStatus(`Completed in ${(data.duration_ms / 1000).toFixed(1)}s`);
          }
        });
        
        await service.connect();
        voiceServiceRef.current = service;
        setIsConnected(true);
        setStatus('Connected');
      } catch (error) {
        console.error('Failed to connect:', error);
        setStatus('Connection failed');
        onError?.('Failed to connect to voice service');
      }
    };
    
    initializeVoiceService();
    
    // Cleanup on unmount
    return () => {
      if (voiceServiceRef.current) {
        voiceServiceRef.current.disconnect();
      }
      if (audioRecorderRef.current?.isRecording()) {
        audioRecorderRef.current.stopRecording();
      }
    };
  }, [sessionId, language, languageCode]);
  
  // Handle recording start
  const handleStartRecording = async () => {
    if (!isConnected || !voiceServiceRef.current) {
      setStatus('Not connected');
      return;
    }
    
    try {
      // Reset state
      setTranscript('');
      setResponse('');
      setAudioUrl(null);
      setStatus('Recording...');
      
      // Start recording
      const recorder = new AudioRecorder();
      await recorder.startRecording();
      audioRecorderRef.current = recorder;
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      setStatus('Microphone access denied');
      onError?.('Failed to access microphone');
    }
  };
  
  // Handle recording stop
  const handleStopRecording = async () => {
    if (!audioRecorderRef.current || !voiceServiceRef.current) {
      return;
    }
    
    try {
      setIsRecording(false);
      setIsProcessing(true);
      setStatus('Processing...');
      
      // Stop recording and get audio blob
      const audioBlob = await audioRecorderRef.current.stopRecording();
      
      // Send audio to server
      await voiceServiceRef.current.sendAudioChunk(audioBlob, 'webm');
      voiceServiceRef.current.sendAudioComplete('webm');
      
      audioRecorderRef.current = null;
    } catch (error) {
      console.error('Failed to stop recording:', error);
      setStatus('Recording failed');
      setIsProcessing(false);
      onError?.('Failed to process recording');
    }
  };
  
  // Handle audio playback
  const handlePlayAudio = () => {
    if (!audioUrl) return;
    
    if (audioElementRef.current) {
      audioElementRef.current.pause();
      audioElementRef.current = null;
      setIsPlayingAudio(false);
      return;
    }
    
    const audio = new Audio(audioUrl);
    audio.onended = () => {
      setIsPlayingAudio(false);
      audioElementRef.current = null;
    };
    audio.onerror = () => {
      setIsPlayingAudio(false);
      audioElementRef.current = null;
      setStatus('Audio playback failed');
    };
    
    audio.play();
    audioElementRef.current = audio;
    setIsPlayingAudio(true);
  };
  
  return (
    <Card className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Voice Chat</h3>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
          <span className="text-sm text-muted-foreground">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
      
      {/* Status */}
      {status && (
        <div className="text-sm text-muted-foreground text-center">
          {status}
        </div>
      )}
      
      {/* Recording button */}
      <div className="flex justify-center">
        <Button
          size="lg"
          variant={isRecording ? 'destructive' : 'default'}
          className="rounded-full w-20 h-20"
          onClick={isRecording ? handleStopRecording : handleStartRecording}
          disabled={!isConnected || isProcessing}
        >
          {isProcessing ? (
            <Loader2 className="w-8 h-8 animate-spin" />
          ) : isRecording ? (
            <MicOff className="w-8 h-8" />
          ) : (
            <Mic className="w-8 h-8" />
          )}
        </Button>
      </div>
      
      {/* Audio wave visualization */}
      {isRecording && (
        <div className="flex justify-center">
          <AudioWave isActive={isRecording} />
        </div>
      )}
      
      {/* Transcript */}
      {transcript && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">You said:</h4>
          <div className="p-3 bg-muted rounded-lg text-sm">
            {transcript}
          </div>
        </div>
      )}
      
      {/* Response */}
      {response && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Response:</h4>
          <div className="p-3 bg-primary/10 rounded-lg text-sm">
            {response}
          </div>
        </div>
      )}
      
      {/* Audio playback */}
      {audioUrl && (
        <div className="flex justify-center">
          <Button
            variant="outline"
            onClick={handlePlayAudio}
            disabled={isProcessing}
          >
            {isPlayingAudio ? (
              <>
                <VolumeX className="w-4 h-4 mr-2" />
                Stop Audio
              </>
            ) : (
              <>
                <Volume2 className="w-4 h-4 mr-2" />
                Play Response
              </>
            )}
          </Button>
        </div>
      )}
      
      {/* Instructions */}
      <div className="text-xs text-muted-foreground text-center space-y-1">
        <p>Click the microphone to start recording</p>
        <p>Click again to stop and send your message</p>
      </div>
    </Card>
  );
};
