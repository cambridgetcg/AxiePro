/**
 * Base API client with error handling.
 */
import { config } from '@/lib/config';

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
}

/**
 * Generic API client for making requests to the backend.
 *
 * @param endpoint - API endpoint (e.g., '/valuation/123')
 * @param options - Fetch options
 * @returns Parsed JSON response
 * @throws ApiError on non-2xx responses
 */
export async function apiClient<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${config.apiBaseUrl}/api/${config.apiVersion}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorData: unknown;
    try {
      errorData = await response.json();
    } catch {
      // Response body is not JSON
    }
    throw new ApiError(response.status, response.statusText, errorData);
  }

  return response.json();
}
