/**
 * Zustand store for wallet connection and authentication state.
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { createLogger } from '@/lib/logger';

const log = createLogger('WalletStore');
import {
  connectWallet as connectRonin,
  disconnectWallet as disconnectRonin,
  signMessage,
  getConnectedAddress,
  onAccountChange,
  isRoninWalletInstalled,
  WalletError,
  WalletErrorCode,
} from '@/lib/wallet/ronin-connector';
import { requestChallenge, verifySignature } from '@/lib/wallet/auth';

export interface WalletState {
  // Connection state
  address: string | null;
  isConnected: boolean;
  isConnecting: boolean;

  // Authentication state
  authToken: string | null;
  authExpiry: number | null;
  isAuthenticating: boolean;

  // Error state
  error: {
    code: WalletErrorCode;
    message: string;
  } | null;

  // Computed helpers
  isAuthenticated: () => boolean;
  isOwnWallet: (address: string) => boolean;
}

export interface WalletActions {
  connect: () => Promise<void>;
  disconnect: () => void;
  authenticate: () => Promise<void>;
  clearError: () => void;
  checkConnection: () => Promise<void>;
  setError: (code: WalletErrorCode, message: string) => void;
}

export type WalletStore = WalletState & WalletActions;

/**
 * Wallet store with persistence for auth token.
 */
export const useWalletStore = create<WalletStore>()(
  persist(
    (set, get) => ({
      // Initial state
      address: null,
      isConnected: false,
      isConnecting: false,
      authToken: null,
      authExpiry: null,
      isAuthenticating: false,
      error: null,

      // Computed helpers
      isAuthenticated: () => {
        const { authToken, authExpiry } = get();
        if (!authToken || !authExpiry) return false;
        return Date.now() < authExpiry;
      },

      isOwnWallet: (walletAddress: string) => {
        const { address, isAuthenticated } = get();
        if (!address || !isAuthenticated()) return false;
        return address.toLowerCase() === walletAddress.toLowerCase();
      },

      // Actions
      connect: async () => {
        if (get().isConnecting) return;

        log.info('Connecting wallet...');
        set({ isConnecting: true, error: null });

        try {
          const address = await connectRonin();
          log.info('Wallet connected', { address: `${address.slice(0, 10)}...` });
          set({
            address: address.toLowerCase(),
            isConnected: true,
            isConnecting: false,
          });

          // Set up account change listener
          onAccountChange((newAddress) => {
            if (newAddress) {
              // If account changed, clear auth and update address
              set({
                address: newAddress.toLowerCase(),
                authToken: null,
                authExpiry: null,
              });
            } else {
              // Account disconnected
              get().disconnect();
            }
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Failed to connect wallet';
          log.error('Connection failed', {
            code: error instanceof WalletError ? error.code : 'UNKNOWN',
            message: errorMessage,
          });
          if (error instanceof WalletError) {
            set({
              error: { code: error.code, message: error.message },
              isConnecting: false,
            });
          } else {
            set({
              error: {
                code: 'UNKNOWN',
                message: errorMessage,
              },
              isConnecting: false,
            });
          }
        }
      },

      disconnect: () => {
        log.info('Disconnecting wallet');
        disconnectRonin();
        set({
          address: null,
          isConnected: false,
          authToken: null,
          authExpiry: null,
          error: null,
        });
      },

      authenticate: async () => {
        const { address, isConnected, isAuthenticating } = get();

        if (!isConnected || !address || isAuthenticating) return;

        log.info('Starting authentication...', { address: `${address.slice(0, 10)}...` });
        set({ isAuthenticating: true, error: null });

        try {
          // Step 1: Request challenge from server
          log.debug('Requesting challenge');
          const challenge = await requestChallenge(address);
          log.debug('Challenge received', { challengeId: challenge.challenge_id.slice(0, 8) });

          // Step 2: Sign the challenge message
          log.debug('Signing challenge message');
          const signature = await signMessage(challenge.message);
          log.debug('Message signed');

          // Step 3: Verify signature and get JWT token
          log.debug('Verifying signature');
          const result = await verifySignature(challenge.challenge_id, signature);

          log.info('Authentication successful');
          // Store the token and expiry
          set({
            authToken: result.token,
            authExpiry: new Date(result.expires_at).getTime(),
            isAuthenticating: false,
          });
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
          log.error('Authentication failed', {
            code: error instanceof WalletError ? error.code : 'UNKNOWN',
            message: errorMessage,
          });
          if (error instanceof WalletError) {
            set({
              error: { code: error.code, message: error.message },
              isAuthenticating: false,
            });
          } else {
            set({
              error: {
                code: 'UNKNOWN',
                message: errorMessage,
              },
              isAuthenticating: false,
            });
          }
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setError: (code: WalletErrorCode, message: string) => {
        set({ error: { code, message } });
      },

      checkConnection: async () => {
        // Only run on client
        if (typeof window === 'undefined') return;

        // Check if Ronin is installed and connected
        if (!isRoninWalletInstalled()) {
          return;
        }

        try {
          const address = await getConnectedAddress();
          if (address) {
            set({
              address: address.toLowerCase(),
              isConnected: true,
            });
          }
        } catch {
          // Ignore errors during initial check
        }
      },
    }),
    {
      name: 'axiepro-wallet',
      partialize: (state) => ({
        // Only persist auth token (connection must be re-established)
        authToken: state.authToken,
        authExpiry: state.authExpiry,
      }),
    }
  )
);

/**
 * Get auth header for API requests.
 *
 * @returns Authorization header object or empty object if not authenticated
 */
export function getAuthHeader(): Record<string, string> {
  const { authToken, isAuthenticated } = useWalletStore.getState();
  if (!authToken || !isAuthenticated()) return {};
  return { Authorization: `Bearer ${authToken}` };
}

/**
 * Require authentication and return the token.
 *
 * @returns Auth token
 * @throws Error if not authenticated
 */
export function requireAuth(): string {
  const { authToken, isAuthenticated } = useWalletStore.getState();
  if (!authToken || !isAuthenticated()) {
    throw new Error('Authentication required');
  }
  return authToken;
}
