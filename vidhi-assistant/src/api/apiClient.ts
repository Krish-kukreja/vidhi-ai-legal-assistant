/**
 * Enhanced API Client with error handling and retry logic.
 * 
 * Wraps the base API client with:
 * - Automatic error handling
 * - Retry logic for failed requests
 * - Request/response interceptors
 * - Authentication token management
 */

import { handleApiError, retryWithBackoff, isNetworkError, isServerError } from '@/utils/errorHandler';
import * as baseClient from './client';

// Re-export types
export * from './client';

/**
 * Get authentication token from localStorage.
 *
 * The login flow (pages/Login.tsx) stores the backend JWT under `vidhi_token`.
 * (`vidhi_auth` holds only a plain identifier string like "professional_5" /
 * "guest_...", not JSON, so it must NOT be parsed as the token source.)
 */
function getAuthToken(): string | null {
  return localStorage.getItem('vidhi_token');
}

/**
 * Enhanced fetch with authentication and error handling
 */
async function enhancedFetch(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  // Add authentication token if available
  const token = getAuthToken();
  if (token) {
    options.headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    };
  }

  // Add request ID for tracking
  const requestId = crypto.randomUUID();
  options.headers = {
    ...options.headers,
    'X-Client-Request-ID': requestId,
  };

  try {
    const response = await fetch(url, options);

    // Log response time if available
    const responseTime = response.headers.get('X-Response-Time');
    if (responseTime) {
      console.log(`Request completed in ${responseTime}`);
    }

    return response;
  } catch (error) {
    // Network error - wrap with more context
    throw {
      message: 'Network error',
      originalError: error,
      requestId,
    };
  }
}

/**
 * Wrapper for API calls with error handling and retry
 */
async function apiCall<T>(
  fn: () => Promise<T>,
  options: {
    retry?: boolean;
    maxRetries?: number;
    showError?: boolean;
  } = {}
): Promise<T> {
  const {
    retry = false,
    maxRetries = 3,
    showError = true,
  } = options;

  try {
    if (retry) {
      return await retryWithBackoff(fn, maxRetries);
    } else {
      return await fn();
    }
  } catch (error) {
    if (showError) {
      handleApiError(error);
    }
    throw error;
  }
}

// ============================================================================
// Enhanced API Methods
// ============================================================================

/**
 * Send a chat query with error handling
 */
export async function sendQuery(
  request: baseClient.QueryRequest,
  signal?: AbortSignal
): Promise<baseClient.QueryResponse> {
  return apiCall(() => baseClient.sendQuery(request, signal), {
    retry: false, // Don't retry chat requests
    showError: true,
  });
}

/**
 * Send audio query with retry on network errors
 */
export async function sendAudioQuery(
  audioBlob: Blob,
  language: string,
  language_code: string,
  use_aws_stt: boolean = false
): Promise<baseClient.QueryResponse> {
  return apiCall(
    () => baseClient.sendAudioQuery(audioBlob, language, language_code, use_aws_stt),
    {
      retry: true, // Retry audio uploads
      maxRetries: 2,
      showError: true,
    }
  );
}

/**
 * Get emergency rights with retry
 */
export async function getEmergencyRights(
  request: baseClient.EmergencyRequest
): Promise<baseClient.EmergencyResponse> {
  return apiCall(() => baseClient.getEmergencyRights(request), {
    retry: true,
    maxRetries: 3,
    showError: true,
  });
}

/**
 * Get supported languages (cached)
 */
let languagesCache: baseClient.LanguagesResponse | null = null;
export async function getSupportedLanguages(): Promise<baseClient.LanguagesResponse> {
  if (languagesCache) {
    return languagesCache;
  }

  const result = await apiCall(() => baseClient.getSupportedLanguages(), {
    retry: true,
    showError: false, // Don't show error for background requests
  });

  languagesCache = result;
  return result;
}

/**
 * Health check with timeout
 */
export async function healthCheck(): Promise<{ status: string; services: Record<string, boolean> }> {
  return apiCall(() => baseClient.healthCheck(), {
    retry: false,
    showError: false,
  });
}

/**
 * Check backend availability
 */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    return await baseClient.isBackendAvailable();
  } catch {
    return false;
  }
}

// ============================================================================
// Document Education API (Enhanced)
// ============================================================================

export async function simplifyDocument(
  request: baseClient.DocumentSimplifyRequest
): Promise<baseClient.DocumentSimplifyResponse> {
  return apiCall(() => baseClient.simplifyDocument(request), {
    retry: false, // Don't retry expensive operations
    showError: true,
  });
}

export async function explainClause(
  request: baseClient.ClauseExplanationRequest
): Promise<{ clause: string; explanation: string; language: string }> {
  return apiCall(() => baseClient.explainClause(request), {
    retry: false,
    showError: true,
  });
}

export async function defineTerm(
  request: baseClient.TermDefinitionRequest
): Promise<any> {
  return apiCall(() => baseClient.defineTerm(request), {
    retry: true,
    maxRetries: 2,
    showError: true,
  });
}

export async function askDocumentQuestion(
  request: baseClient.InteractiveQARequest
): Promise<{ question: string; answer: string; language: string }> {
  return apiCall(() => baseClient.askDocumentQuestion(request), {
    retry: false,
    showError: true,
  });
}

export async function createTeachingSession(
  request: baseClient.TeachingSessionRequest
): Promise<any> {
  return apiCall(() => baseClient.createTeachingSession(request), {
    retry: false,
    showError: true,
  });
}

// ============================================================================
// Chat History API (Enhanced)
// ============================================================================

export async function saveMessage(
  request: baseClient.SaveMessageRequest
): Promise<any> {
  return apiCall(() => baseClient.saveMessage(request), {
    retry: true,
    maxRetries: 3,
    showError: false, // Silent failure for history saves
  });
}

export async function getChatHistory(
  chatId: string,
  limit?: number
): Promise<{ chat_id: string; message_count: number; messages: any[] }> {
  return apiCall(() => baseClient.getChatHistory(chatId, limit), {
    retry: true,
    showError: true,
  });
}

export async function getMessagePlayback(
  chatId: string,
  messageId: string,
  regenerate: boolean = false
): Promise<baseClient.MessagePlaybackResponse> {
  return apiCall(() => baseClient.getMessagePlayback(chatId, messageId, regenerate), {
    retry: true,
    maxRetries: 2,
    showError: true,
  });
}

// ============================================================================
// Document Drafting API (Enhanced)
// ============================================================================

export async function draftDocument(
  request: baseClient.DocumentDraftingRequest
): Promise<baseClient.DocumentDraftingResponse> {
  return apiCall(() => baseClient.draftDocument(request), {
    retry: false, // Don't retry expensive operations
    showError: true,
  });
}

// ============================================================================
// Streaming API (Phase 2)
// ============================================================================

export interface StreamEvent {
  type: 'token' | 'metadata' | 'done' | 'error';
  content?: string;
  index?: number;
  confidence?: number;
  citations?: string[];
  total_tokens?: number;
  duration_ms?: number;
  message?: string;
}

/**
 * Stream chat response token-by-token using Server-Sent Events (SSE)
 * 
 * @param text - User query text
 * @param sessionId - Session identifier for conversation context
 * @param language - Response language preference
 * @param signal - AbortSignal for cancellation
 * @returns AsyncGenerator yielding StreamEvent objects
 * 
 * @example
 * ```typescript
 * for await (const event of streamChat("What is Section 438?", "session-123", "english")) {
 *   if (event.type === 'token') {
 *     console.log(event.content); // Display token
 *   } else if (event.type === 'done') {
 *     console.log('Streaming complete');
 *   }
 * }
 * ```
 */
export async function* streamChat(
  text: string,
  sessionId: string,
  language: string = 'english',
  signal?: AbortSignal
): AsyncGenerator<StreamEvent, void, unknown> {
  const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
  const url = `${API_BASE_URL}/api/v1/stream/chat`;
  
  // Get authentication token
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        text,
        session_id: sessionId,
        language
      }),
      signal
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP ${response.status}: ${errorText}`);
    }
    
    if (!response.body) {
      throw new Error('Response body is null');
    }
    
    // Read SSE stream
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }
      
      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });
      
      // Process complete SSE events (separated by \n\n)
      const events = buffer.split('\n\n');
      
      // Keep the last incomplete event in buffer
      buffer = events.pop() || '';
      
      for (const eventText of events) {
        if (!eventText.trim()) continue;
        
        // Parse SSE format: "event: type\ndata: {...}"
        const lines = eventText.split('\n');
        let eventType = 'message';
        let data = '';
        
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            data = line.slice(6).trim();
          }
        }
        
        if (data) {
          try {
            const parsed: StreamEvent = JSON.parse(data);
            yield parsed;
          } catch (e) {
            console.error('Failed to parse SSE data:', data, e);
          }
        }
      }
    }
    
  } catch (error: any) {
    if (error.name === 'AbortError') {
      // User cancelled - yield cancellation event
      yield {
        type: 'error',
        message: 'Request cancelled'
      };
    } else {
      // Network or other error
      console.error('Streaming error:', error);
      yield {
        type: 'error',
        message: error.message || 'Streaming failed'
      };
    }
  }
}
