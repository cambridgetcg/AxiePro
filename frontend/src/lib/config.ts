/**
 * Application configuration with environment variable support.
 */
export const config = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  apiVersion: 'v1',

  // Cache and polling configuration
  defaultStaleTime: 60_000, // 1 minute
  dealsPollingInterval: 30_000, // 30 seconds
  valuationStaleTime: 5 * 60_000, // 5 minutes
} as const;
// Force rebuild Mon Dec 29 17:48:15 GMT 2025
