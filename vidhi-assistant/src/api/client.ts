/**
 * VIDHI API Client
 * Connects frontend to backend API
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

export interface QueryRequest {
  text: string;
  language: string;
  language_code: string;
  use_aws_stt?: boolean;
  files?: File[];
}

export interface QueryResponse {
  response: string;
  audio_url?: string;
  language: string;
  from_cache: boolean;
}

export interface EmergencyRequest {
  situation: string;
  language: string;
  language_code: string;
}

export interface EmergencyResponse {
  response: string;
  audio_url?: string;
  emergency_contacts: Record<string, string>;
  language: string;
}

export interface LanguagesResponse {
  aws_transcribe: string[];
  aws_polly: string[];
  bhashini: Record<string, string>;
}

/**
 * Send a chat query to the backend
 */
export async function sendQuery(request: QueryRequest, signal?: AbortSignal): Promise<QueryResponse> {
  const formData = new FormData();
  formData.append('text', request.text);
  formData.append('language', request.language);
  formData.append('language_code', request.language_code);
  if (request.use_aws_stt !== undefined) {
    formData.append('use_aws_stt', request.use_aws_stt.toString());
  }
  if (request.files && request.files.length > 0) {
    request.files.forEach(file => {
      formData.append('files', file, file.name);
    });
  }

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Send audio file for transcription and chat
 */
export async function sendAudioQuery(
  audioBlob: Blob,
  language: string,
  language_code: string,
  use_aws_stt: boolean = false
): Promise<QueryResponse> {
  const formData = new FormData();
  formData.append('files', audioBlob, 'audio.wav');
  formData.append('language', language);
  formData.append('language_code', language_code);
  formData.append('use_aws_stt', use_aws_stt.toString());

  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get emergency legal rights information
 */
export async function getEmergencyRights(
  request: EmergencyRequest
): Promise<EmergencyResponse> {
  const response = await fetch(`${API_BASE_URL}/emergency`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get list of supported languages
 */
export async function getSupportedLanguages(): Promise<LanguagesResponse> {
  const response = await fetch(`${API_BASE_URL}/languages`);

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Health check
 */
export async function healthCheck(): Promise<{ status: string; services: Record<string, boolean> }> {
  const response = await fetch(`${API_BASE_URL}/health`);

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Check if backend is available
 */
export async function isBackendAvailable(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });
    return response.ok;
  } catch {
    return false;
  }
}

// ============================================================================
// DOCUMENT EDUCATION API
// ============================================================================

export interface DocumentSimplifyRequest {
  document_text: string;
  document_type: string;
  language?: string;
}

export interface DocumentSection {
  title: string;
  original_text: string;
  simplified: string;
  key_points: string[];
  warnings: string[];
}

export interface LegalTerm {
  term: string;
  definition: string;
  example: string;
  glossary_definition?: any;
}

export interface DocumentSimplifyResponse {
  summary: string;
  sections: DocumentSection[];
  legal_terms: LegalTerm[];
  overall_assessment: {
    fairness: string;
    concerns: string[];
    recommendations: string[];
  };
}

export interface ClauseExplanationRequest {
  clause_text: string;
  document_context: string;
  language?: string;
  user_profile?: any;
}

export interface TermDefinitionRequest {
  term: string;
  language?: string;
  context?: string;
}

export interface InteractiveQARequest {
  question: string;
  document_text: string;
  conversation_history?: Array<{ question: string; answer: string }>;
  language?: string;
}

export interface TeachingSessionRequest {
  document_text: string;
  document_type: string;
  language?: string;
}

/**
 * Simplify a legal document with section-by-section explanations
 */
export async function simplifyDocument(
  request: DocumentSimplifyRequest
): Promise<DocumentSimplifyResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/simplify`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Explain a specific clause in detail
 */
export async function explainClause(
  request: ClauseExplanationRequest
): Promise<{ clause: string; explanation: string; language: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/explain-clause`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Define a legal term with examples
 */
export async function defineTerm(
  request: TermDefinitionRequest
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/define-term`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Ask questions about a document interactively
 */
export async function askDocumentQuestion(
  request: InteractiveQARequest
): Promise<{ question: string; answer: string; language: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/interactive-qa`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Create a structured teaching session for a document
 */
export async function createTeachingSession(
  request: TeachingSessionRequest
): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/teaching-session`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

// ============================================================================
// LANGUAGE-PRESERVED VOICE HISTORY API
// ============================================================================

export interface SaveMessageRequest {
  user_id: string;
  chat_id: string;
  message_text: string;
  message_type: 'user_query' | 'system_response';
  language_code: string;
  language_name: string;
  dialect?: string;
  input_mode?: 'voice' | 'text' | 'document';
  audio_file?: File;
}

export interface MessagePlaybackResponse {
  message_id: string;
  chat_id: string;
  timestamp: string;
  message_content: {
    text: string;
    message_type: string;
  };
  language_metadata: {
    language_tag: string;
    language_code: string;
    language_name: string;
    dialect?: string;
    script: string;
  };
  audio_playback: {
    audio_url: string;
    audio_format: string;
    duration_seconds: number;
    tts_engine: string;
    cached: boolean;
  };
}

/**
 * Save a message with language metadata for future playback
 */
export async function saveMessage(request: SaveMessageRequest): Promise<any> {
  const formData = new FormData();
  formData.append('user_id', request.user_id);
  formData.append('chat_id', request.chat_id);
  formData.append('message_text', request.message_text);
  formData.append('message_type', request.message_type);
  formData.append('language_code', request.language_code);
  formData.append('language_name', request.language_name);

  if (request.dialect) {
    formData.append('dialect', request.dialect);
  }
  if (request.input_mode) {
    formData.append('input_mode', request.input_mode);
  }
  if (request.audio_file) {
    formData.append('audio_file', request.audio_file);
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/history/save-message`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Get chat history for a session
 */
export async function getChatHistory(
  chatId: string,
  limit?: number
): Promise<{ chat_id: string; message_count: number; messages: any[] }> {
  const url = new URL(`${API_BASE_URL}/api/v1/history/${chatId}`);
  if (limit) {
    url.searchParams.append('limit', limit.toString());
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Get audio playback for a specific message in its original language
 * 
 * This is the critical function that enables language-preserved voice playback.
 * When you replay a Bhojpuri message from 3 days ago, it plays in Bhojpuri.
 */
export async function getMessagePlayback(
  chatId: string,
  messageId: string,
  regenerate: boolean = false
): Promise<MessagePlaybackResponse> {
  const url = new URL(`${API_BASE_URL}/api/v1/history/${chatId}/playback`);
  url.searchParams.append('message_id', messageId);
  if (regenerate) {
    url.searchParams.append('regenerate', 'true');
  }

  const response = await fetch(url.toString());

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

/**
 * Get list of supported languages with TTS engine information
 */
export async function getSupportedLanguagesDetailed(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/api/v1/languages/supported`);

  if (!response.ok) {
    throw new Error(`API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

// ============================================================================
// DOCUMENT DRAFTING API
// ============================================================================

export interface DocumentDraftingRequest {
  document_type: string;
  parties: string;
  key_terms: string;
}

export interface DocumentDraftingResponse {
  success: boolean;
  markdown_draft: string;
  download_url: string;
  template_used: string;
}

/**
 * Draft a legal document based on templates and user input
 */
export async function draftDocument(
  request: DocumentDraftingRequest
): Promise<DocumentDraftingResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/documents/draft`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.statusText}`);
  }

  const result = await response.json();
  return result.data;
}

