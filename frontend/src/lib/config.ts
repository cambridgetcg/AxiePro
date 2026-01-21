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

  // Cache and polling configuration
  defaultStaleTime: 60_000, // 1 minute
  dealsPollingInterval: 30_000, // 30 seconds
  valuationStaleTime: 5 * 60_000, // 5 minutes
} as const;
