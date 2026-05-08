/**
 * Error handling utilities for the frontend.
 * 
 * Provides consistent error handling and user-friendly error messages.
 */

import { toast } from '@/components/ui/use-toast';

export interface ApiError {
  error: string;
  message: string;
  request_id?: string;
  details?: Record<string, any>;
  hint?: string;
}

/**
 * Handle API errors and show appropriate toast messages.
 */
export function handleApiError(error: any): void {
  console.error('API Error:', error);

  // Check if it's a network error
  if (!error.response) {
    toast({
      variant: 'destructive',
      title: 'Network Error',
      description: 'Unable to connect to the server. Please check your internet connection.',
    });
    return;
  }

  // Extract error details
  const status = error.response?.status;
  const data: ApiError = error.response?.data || {};

  // Handle specific status codes
  switch (status) {
    case 400:
      toast({
        variant: 'destructive',
        title: 'Invalid Request',
        description: data.message || 'Please check your input and try again.',
      });
      break;

    case 401:
      toast({
        variant: 'destructive',
        title: 'Authentication Required',
        description: 'Please log in to continue.',
      });
      // Redirect to login after a delay
      setTimeout(() => {
        window.location.href = '/login';
      }, 2000);
      break;

    case 403:
      toast({
        variant: 'destructive',
        title: 'Access Denied',
        description: data.message || 'You don\'t have permission to access this resource.',
      });
      break;

    case 404:
      toast({
        variant: 'destructive',
        title: 'Not Found',
        description: data.message || 'The requested resource was not found.',
      });
      break;

    case 429:
      toast({
        variant: 'destructive',
        title: 'Too Many Requests',
        description: data.message || 'Please wait a moment before trying again.',
      });
      break;

    case 500:
    case 502:
    case 503:
    case 504:
      toast({
        variant: 'destructive',
        title: 'Server Error',
        description: data.message || 'An error occurred on the server. Please try again later.',
      });
      break;

    default:
      toast({
        variant: 'destructive',
        title: 'Error',
        description: data.message || 'An unexpected error occurred.',
      });
  }

  // Log request ID if available (for debugging)
  if (data.request_id) {
    console.log('Request ID:', data.request_id);
  }
}

/**
 * Handle general JavaScript errors.
 */
export function handleError(error: Error, context?: string): void {
  console.error(`Error${context ? ` in ${context}` : ''}:`, error);

  toast({
    variant: 'destructive',
    title: 'Error',
    description: error.message || 'An unexpected error occurred.',
  });
}

/**
 * Retry a function with exponential backoff.
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  initialDelay: number = 1000
): Promise<T> {
  let lastError: Error;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (i < maxRetries - 1) {
        const delay = initialDelay * Math.pow(2, i);
        console.log(`Retry ${i + 1}/${maxRetries} after ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError!;
}

/**
 * Safe async function wrapper that catches errors.
 */
export function safeAsync<T extends any[], R>(
  fn: (...args: T) => Promise<R>,
  errorHandler?: (error: Error) => void
): (...args: T) => Promise<R | undefined> {
  return async (...args: T) => {
    try {
      return await fn(...args);
    } catch (error) {
      if (errorHandler) {
        errorHandler(error as Error);
      } else {
        handleError(error as Error);
      }
      return undefined;
    }
  };
}

/**
 * Check if error is a specific type.
 */
export function isNetworkError(error: any): boolean {
  return !error.response && error.request;
}

export function isAuthError(error: any): boolean {
  return error.response?.status === 401;
}

export function isRateLimitError(error: any): boolean {
  return error.response?.status === 429;
}

export function isServerError(error: any): boolean {
  const status = error.response?.status;
  return status >= 500 && status < 600;
}

/**
 * Get user-friendly error message.
 */
export function getErrorMessage(error: any): string {
  if (typeof error === 'string') {
    return error;
  }

  if (error.response?.data?.message) {
    return error.response.data.message;
  }

  if (error.message) {
    return error.message;
  }

  return 'An unexpected error occurred';
}

/**
 * Log error to external service (e.g., Sentry).
 */
export function logErrorToService(error: Error, context?: Record<string, any>): void {
  // In production, send to error tracking service
  if (import.meta.env.PROD) {
    // Example: Sentry
    // if (window.Sentry) {
    //   window.Sentry.captureException(error, { extra: context });
    // }
    console.error('Error logged:', error, context);
  } else {
    console.error('Error:', error, context);
  }
}
