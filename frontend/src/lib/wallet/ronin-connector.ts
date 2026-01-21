/**
 * Ronin Wallet connector utilities.
 *
 * Uses @sky-mavis/tanto-connect for wallet connection.
 * Dynamic imports are used to avoid SSR issues.
 */

export type WalletErrorCode =
  | 'NOT_INSTALLED'
  | 'CONNECTION_REJECTED'
  | 'SIGNATURE_REJECTED'
  | 'DISCONNECTED'
  | 'UNKNOWN';

export class WalletError extends Error {
  constructor(
    public code: WalletErrorCode,
    message: string
  ) {
    super(message);
    this.name = 'WalletError';
  }
}

// Type for the connector - use unknown to avoid type conflicts with library
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type RoninConnector = any;

// Global connector instance
let connectorInstance: RoninConnector | null = null;

/**
 * Check if Ronin Wallet is installed.
 */
export function isRoninWalletInstalled(): boolean {
  if (typeof window === 'undefined') return false;
  // Check for Ronin wallet provider
  return !!(window as unknown as { ronin?: { provider?: unknown } }).ronin?.provider;
}

/**
 * Get or create the Ronin wallet connector.
 * Uses dynamic import to avoid SSR issues.
 */
async function getConnector() {
  if (typeof window === 'undefined') {
    throw new WalletError('UNKNOWN', 'Cannot connect wallet on server side');
  }

  if (!connectorInstance) {
    // Dynamic import to avoid SSR issues
    const { requestRoninWalletConnector } = await import('@sky-mavis/tanto-connect');
    connectorInstance = await requestRoninWalletConnector();
  }
  return connectorInstance;
}

/**
 * Connect to Ronin Wallet.
 *
 * @returns Connected wallet address
 * @throws WalletError if connection fails
 */
export async function connectWallet(): Promise<string> {
  if (!isRoninWalletInstalled()) {
    throw new WalletError(
      'NOT_INSTALLED',
      'Ronin Wallet extension not found. Please install it from https://wallet.roninchain.com/'
    );
  }

  try {
    const connector = await getConnector();
    const accounts = await connector.connect();

    if (!accounts || accounts.length === 0) {
      throw new WalletError('CONNECTION_REJECTED', 'No accounts returned from wallet');
    }

    return accounts[0];
  } catch (error) {
    if (error instanceof WalletError) throw error;

    // Handle user rejection
    const errorMessage = error instanceof Error ? error.message : String(error);
    if (
      errorMessage.includes('rejected') ||
      errorMessage.includes('denied') ||
      errorMessage.includes('cancelled')
    ) {
      throw new WalletError('CONNECTION_REJECTED', 'Connection request was rejected');
    }

    throw new WalletError('UNKNOWN', `Failed to connect wallet: ${errorMessage}`);
  }
}

/**
 * Disconnect from Ronin Wallet.
 */
export async function disconnectWallet(): Promise<void> {
  if (connectorInstance) {
    try {
      await connectorInstance.disconnect();
    } catch {
      // Ignore disconnect errors
    }
    connectorInstance = null;
  }
}

/**
 * Sign a message with the connected wallet.
 *
 * @param message - Message to sign
 * @returns Signature hex string
 * @throws WalletError if signing fails
 */
export async function signMessage(message: string): Promise<string> {
  const connector = await getConnector();

  if (!connector.isConnected) {
    throw new WalletError('DISCONNECTED', 'Wallet is not connected');
  }

  try {
    // Get the provider for direct signing
    const provider = connector.getProvider();
    const accounts = (await provider.request({ method: 'eth_accounts' })) as string[];

    if (!accounts || accounts.length === 0) {
      throw new WalletError('DISCONNECTED', 'No accounts available');
    }

    const account = accounts[0];

    // Use personal_sign for EIP-191 message signing
    const signature = await provider.request({
      method: 'personal_sign',
      params: [message, account],
    });

    return signature as string;
  } catch (error) {
    if (error instanceof WalletError) throw error;

    const errorMessage = error instanceof Error ? error.message : String(error);
    if (
      errorMessage.includes('rejected') ||
      errorMessage.includes('denied') ||
      errorMessage.includes('cancelled')
    ) {
      throw new WalletError('SIGNATURE_REJECTED', 'Signature request was rejected');
    }

    throw new WalletError('UNKNOWN', `Failed to sign message: ${errorMessage}`);
  }
}

/**
 * Get the currently connected address, if any.
 */
export async function getConnectedAddress(): Promise<string | null> {
  if (typeof window === 'undefined') return null;

  try {
    const connector = await getConnector();
    if (!connector.isConnected) return null;

    const provider = connector.getProvider();
    const accounts = (await provider.request({ method: 'eth_accounts' })) as string[];

    if (!accounts || accounts.length === 0) return null;
    return accounts[0];
  } catch {
    return null;
  }
}

/**
 * Subscribe to account changes.
 *
 * @param callback - Called when account changes
 * @returns Unsubscribe function
 */
export function onAccountChange(callback: (address: string | null) => void): () => void {
  if (typeof window === 'undefined') return () => {};

  const ronin = (
    window as unknown as {
      ronin?: {
        provider?: {
          on: (event: string, cb: (accounts: string[]) => void) => void;
          removeListener: (event: string, cb: (accounts: string[]) => void) => void;
        };
      };
    }
  ).ronin;
  if (!ronin?.provider) return () => {};

  const handler = (accounts: string[]) => {
    callback(accounts.length > 0 ? accounts[0] : null);
  };

  ronin.provider.on('accountsChanged', handler);

  return () => {
    ronin?.provider?.removeListener('accountsChanged', handler);
  };
}
