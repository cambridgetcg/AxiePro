/**
 * Base API client with error handling.
 */
import { config } from '@/lib/config';
import { createLogger } from '@/lib/logger';

const log = createLogger('ApiClient');

/**
 * Custom error class for API errors.
 */
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public data?: unknown
  ) {
    super(`API Error: ${status} ${statusText}`);
    this.name = 'ApiError';
  }

  /**
   * Check if this is an authentication error.
   */
  get isAuthError(): boolean {
    return this.status === 401 || this.status === 403;
  }
}

export interface ApiClientOptions extends RequestInit {
  /**
   * JWT auth token for authenticated requests.
   */
  authToken?: string;
}

/**
 * Generic API client for making requests to the backend.
 *
 * @param endpoint - API endpoint (e.g., '/valuation/123')
 * @param options - Fetch options with optional authToken
 * @returns Parsed JSON response
 * @throws ApiError on non-2xx responses
 */
export async function apiClient<T>(
  endpoint: string,
  options?: ApiClientOptions
): Promise<T> {
  const url = `${config.apiBaseUrl}/api/${config.apiVersion}${endpoint}`;
  const method = options?.method || 'GET';

  const { authToken, ...fetchOptions } = options || {};

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((fetchOptions?.headers as Record<string, string>) || {}),
  };

  // Add auth header if token provided
  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  log.debug('Request', { method, endpoint, hasAuth: !!authToken });

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    if (!response.ok) {
      let errorData: unknown;
      try {
        errorData = await response.json();
      } catch {
        // Response body is not JSON
      }
      log.error('Response error', {
        method,
        endpoint,
        status: response.status,
        statusText: response.statusText,
      });
      throw new ApiError(response.status, response.statusText, errorData);
    }

    log.debug('Response success', { method, endpoint, status: response.status });
    return response.json();
  } catch (error) {
    // Log network errors (not ApiErrors, those are already logged)
    if (!(error instanceof ApiError)) {
      log.error('Network error', { method, endpoint, error: String(error) });
    }
    throw error;
  }
}
