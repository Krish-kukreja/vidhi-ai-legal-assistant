/**
 * Tests for SSE Streaming Client (Phase 2)
 * 
 * Tests:
 * - streamChat function
 * - SSE event parsing
 * - Token accumulation
 * - Metadata handling
 * - Error handling
 * - Cancellation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { streamChat, StreamEvent } from '@/api/apiClient';

// ============================================================================
// Mock Setup
// ============================================================================

// Mock fetch globally
global.fetch = vi.fn();

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock as any;

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Create a mock SSE response
 */
function createMockSSEResponse(events: StreamEvent[]): Response {
  // Format events as SSE
  const sseText = events
    .map((event) => {
      const eventType = event.type || 'message';
      const data = JSON.stringify(event);
      return `event: ${eventType}\ndata: ${data}\n\n`;
    })
    .join('');

  // Create readable stream
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(sseText));
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      'Content-Type': 'text/event-stream',
    },
  });
}

/**
 * Collect all events from async generator
 */
async function collectEvents(
  generator: AsyncGenerator<StreamEvent, void, unknown>
): Promise<StreamEvent[]> {
  const events: StreamEvent[] = [];
  for await (const event of generator) {
    events.push(event);
  }
  return events;
}

// ============================================================================
// Tests
// ============================================================================

describe('streamChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.getItem.mockReturnValue(null);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should stream tokens successfully', async () => {
    // Mock SSE response
    const mockEvents: StreamEvent[] = [
      { type: 'token', content: 'Section', index: 0 },
      { type: 'token', content: ' 438', index: 1 },
      { type: 'token', content: ' CrPC', index: 2 },
      { type: 'metadata', confidence: 0.85, citations: ['Section 438 CrPC'] },
      { type: 'done', total_tokens: 3, duration_ms: 1500 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Verify events
    expect(events).toHaveLength(5);

    // Check token events
    expect(events[0].type).toBe('token');
    expect(events[0].content).toBe('Section');
    expect(events[1].content).toBe(' 438');
    expect(events[2].content).toBe(' CrPC');

    // Check metadata event
    expect(events[3].type).toBe('metadata');
    expect(events[3].confidence).toBe(0.85);
    expect(events[3].citations).toContain('Section 438 CrPC');

    // Check done event
    expect(events[4].type).toBe('done');
    expect(events[4].total_tokens).toBe(3);
  });

  it('should handle authentication token', async () => {
    // Mock auth token
    localStorageMock.getItem.mockReturnValue(
      JSON.stringify({ access_token: 'test-token-123' })
    );

    const mockEvents: StreamEvent[] = [
      { type: 'token', content: 'Hello', index: 0 },
      { type: 'done', total_tokens: 1, duration_ms: 100 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('Hello', 'test-session', 'english');
    await collectEvents(generator);

    // Verify fetch was called with auth header
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token-123',
        }),
      })
    );
  });

  it('should handle error events', async () => {
    const mockEvents: StreamEvent[] = [
      { type: 'token', content: 'Section', index: 0 },
      { type: 'error', message: 'LLM service unavailable' },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Verify error event
    expect(events).toHaveLength(2);
    expect(events[1].type).toBe('error');
    expect(events[1].message).toBe('LLM service unavailable');
  });

  it('should handle network errors', async () => {
    // Mock network error
    (global.fetch as any).mockRejectedValue(new Error('Network error'));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Should yield error event
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('error');
    expect(events[0].message).toContain('Network error');
  });

  it('should handle HTTP errors', async () => {
    // Mock HTTP error
    (global.fetch as any).mockResolvedValue(
      new Response('Internal Server Error', { status: 500 })
    );

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Should yield error event
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('error');
    expect(events[0].message).toContain('500');
  });

  it('should handle cancellation', async () => {
    const mockEvents: StreamEvent[] = [
      { type: 'token', content: 'Section', index: 0 },
      { type: 'token', content: ' 438', index: 1 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Create abort controller
    const controller = new AbortController();

    // Stream chat
    const generator = streamChat(
      'What is Section 438?',
      'test-session',
      'english',
      controller.signal
    );

    // Collect first event
    const iterator = generator[Symbol.asyncIterator]();
    const first = await iterator.next();
    expect(first.value.type).toBe('token');

    // Cancel
    controller.abort();

    // Try to get next event - should handle abort
    try {
      await iterator.next();
    } catch (error: any) {
      // AbortError is expected
      expect(error.name).toBe('AbortError');
    }
  });

  it('should handle empty response', async () => {
    const mockEvents: StreamEvent[] = [
      { type: 'done', total_tokens: 0, duration_ms: 100 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Should have done event
    expect(events).toHaveLength(1);
    expect(events[0].type).toBe('done');
    expect(events[0].total_tokens).toBe(0);
  });

  it('should handle malformed SSE data', async () => {
    // Create response with malformed JSON
    const sseText = 'event: token\ndata: {invalid json}\n\n';
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(sseText));
        controller.close();
      },
    });

    (global.fetch as any).mockResolvedValue(
      new Response(stream, {
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
      })
    );

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Should handle gracefully (skip malformed events)
    expect(events).toHaveLength(0);
  });

  it('should send correct request body', async () => {
    const mockEvents: StreamEvent[] = [
      { type: 'done', total_tokens: 0, duration_ms: 100 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session-123', 'hindi');
    await collectEvents(generator);

    // Verify request body
    expect(global.fetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          text: 'What is Section 438?',
          session_id: 'test-session-123',
          language: 'hindi',
        }),
      })
    );
  });

  it('should handle multiple metadata events', async () => {
    const mockEvents: StreamEvent[] = [
      { type: 'token', content: 'Section', index: 0 },
      { type: 'metadata', confidence: 0.8, citations: ['Source 1'] },
      { type: 'token', content: ' 438', index: 1 },
      { type: 'metadata', confidence: 0.9, citations: ['Source 2'] },
      { type: 'done', total_tokens: 2, duration_ms: 1000 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Should receive all events
    expect(events).toHaveLength(5);

    // Check metadata events
    const metadataEvents = events.filter((e) => e.type === 'metadata');
    expect(metadataEvents).toHaveLength(2);
    expect(metadataEvents[0].confidence).toBe(0.8);
    expect(metadataEvents[1].confidence).toBe(0.9);
  });

  it('should handle very long responses', async () => {
    // Create 1000 token events
    const mockEvents: StreamEvent[] = [];
    for (let i = 0; i < 1000; i++) {
      mockEvents.push({ type: 'token', content: `word${i} `, index: i });
    }
    mockEvents.push({ type: 'done', total_tokens: 1000, duration_ms: 5000 });

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is Section 438?', 'test-session', 'english');
    const events = await collectEvents(generator);

    // Should receive all events
    expect(events).toHaveLength(1001);
    expect(events[1000].type).toBe('done');
    expect(events[1000].total_tokens).toBe(1000);
  });

  it('should handle special characters in tokens', async () => {
    const mockEvents: StreamEvent[] = [
      { type: 'token', content: 'धारा', index: 0 },
      { type: 'token', content: ' 438', index: 1 },
      { type: 'token', content: ' 🔍', index: 2 },
      { type: 'done', total_tokens: 3, duration_ms: 500 },
    ];

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    // Stream chat
    const generator = streamChat('What is धारा 438?', 'test-session', 'hindi');
    const events = await collectEvents(generator);

    // Should handle special characters
    expect(events[0].content).toBe('धारा');
    expect(events[2].content).toBe(' 🔍');
  });
});

// ============================================================================
// Performance Tests
// ============================================================================

describe('streamChat performance', () => {
  it('should handle rapid token streaming', async () => {
    // Create 100 tokens
    const mockEvents: StreamEvent[] = [];
    for (let i = 0; i < 100; i++) {
      mockEvents.push({ type: 'token', content: `token${i} `, index: i });
    }
    mockEvents.push({ type: 'done', total_tokens: 100, duration_ms: 1000 });

    (global.fetch as any).mockResolvedValue(createMockSSEResponse(mockEvents));

    const startTime = Date.now();

    // Stream chat
    const generator = streamChat('Test query', 'test-session', 'english');
    await collectEvents(generator);

    const duration = Date.now() - startTime;

    // Should complete quickly (< 1 second for mock)
    expect(duration).toBeLessThan(1000);
  });
});
