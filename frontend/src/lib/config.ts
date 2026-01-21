/**
 * Application configuration with environment variable support.
 */
export const config = {
  // API base URL - empty string means use relative URLs (works with Next.js proxy in dev)
  // In production, set NEXT_PUBLIC_API_URL to your backend domain (e.g., https://api.axiepro.io)
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL || '',
  apiVersion: 'v1',

  // Network configuration
  // Set NEXT_PUBLIC_RONIN_NETWORK to 'testnet' to use Saigon testnet
  roninNetwork: (process.env.NEXT_PUBLIC_RONIN_NETWORK || 'mainnet') as 'mainnet' | 'testnet',

  // Debug logging
  // Enabled by default in development, can override with NEXT_PUBLIC_DEBUG=true in production
  debug: process.env.NODE_ENV !== 'production' || process.env.NEXT_PUBLIC_DEBUG === 'true',
  logLevel: (process.env.NEXT_PUBLIC_LOG_LEVEL || 'debug') as 'debug' | 'info' | 'warn' | 'error',

  // Cache and polling configuration
  defaultStaleTime: 60_000, // 1 minute
  dealsPollingInterval: 30_000, // 30 seconds
  valuationStaleTime: 5 * 60_000, // 5 minutes
} as const;
