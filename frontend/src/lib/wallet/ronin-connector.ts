/**
 * Ronin Wallet connector utilities.
 *
 * Uses @sky-mavis/tanto-connect for wallet connection.
 * Dynamic imports are used to avoid SSR issues.
 * Supports both Ronin Mainnet and Saigon Testnet.
 */

import { getCurrentNetwork, type NetworkConfig } from './network';
import { createLogger } from '@/lib/logger';

const log = createLogger('RoninConnector');

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
  log.debug('Checking wallet installation');
  if (!isRoninWalletInstalled()) {
    log.warn('Wallet not installed');
    throw new WalletError(
      'NOT_INSTALLED',
      'Ronin Wallet extension not found. Please install it from https://wallet.roninchain.com/'
    );
  }

  try {
    log.debug('Getting connector');
    const connector = await getConnector();
    log.debug('Requesting connection');
    const accounts = await connector.connect();

    if (!accounts || accounts.length === 0) {
      log.warn('No accounts returned');
      throw new WalletError('CONNECTION_REJECTED', 'No accounts returned from wallet');
    }

    log.info('Connected', { address: `${accounts[0].slice(0, 10)}...` });
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
      log.debug('Connection rejected by user');
      throw new WalletError('CONNECTION_REJECTED', 'Connection request was rejected');
    }

    log.error('Connection failed', { error: errorMessage });
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
  log.debug('Signing message', { length: message.length });
  const connector = await getConnector();

  if (!connector.isConnected) {
    log.warn('Wallet not connected');
    throw new WalletError('DISCONNECTED', 'Wallet is not connected');
  }

  try {
    // Get the provider for direct signing
    const provider = connector.getProvider();
    const accounts = (await provider.request({ method: 'eth_accounts' })) as string[];

    if (!accounts || accounts.length === 0) {
      log.warn('No accounts available');
      throw new WalletError('DISCONNECTED', 'No accounts available');
    }

    const account = accounts[0];
    log.debug('Requesting signature', { account: `${account.slice(0, 10)}...` });

    // Use personal_sign for EIP-191 message signing
    const signature = await provider.request({
      method: 'personal_sign',
      params: [message, account],
    });

    log.debug('Message signed successfully');
    return signature as string;
  } catch (error) {
    if (error instanceof WalletError) throw error;

    const errorMessage = error instanceof Error ? error.message : String(error);
    if (
      errorMessage.includes('rejected') ||
      errorMessage.includes('denied') ||
      errorMessage.includes('cancelled')
    ) {
      log.debug('Signature rejected by user');
      throw new WalletError('SIGNATURE_REJECTED', 'Signature request was rejected');
    }

    log.error('Signing failed', { error: errorMessage });
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

/**
 * Get the current chain ID from the connected wallet.
 *
 * @returns Chain ID in decimal or null if not connected
 */
export async function getChainId(): Promise<number | null> {
  if (typeof window === 'undefined') return null;

  try {
    const connector = await getConnector();
    if (!connector.isConnected) return null;

    const provider = connector.getProvider();
    const chainIdHex = (await provider.request({ method: 'eth_chainId' })) as string;
    return parseInt(chainIdHex, 16);
  } catch {
    return null;
  }
}

/**
 * Switch to the expected network based on environment configuration.
 *
 * @returns True if already on correct network or switch successful
 * @throws WalletError if switch fails
 */
export async function ensureCorrectNetwork(): Promise<boolean> {
  const expectedNetwork = getCurrentNetwork();
  const currentChainId = await getChainId();

  log.debug('Checking network', {
    expected: expectedNetwork.chainId,
    current: currentChainId,
  });

  if (currentChainId === expectedNetwork.chainId) {
    log.debug('Already on correct network');
    return true;
  }

  try {
    log.info('Switching network', { to: expectedNetwork.name });
    const connector = await getConnector();
    const provider = connector.getProvider();

    // Try to switch to the expected network
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: expectedNetwork.chainIdHex }],
    });

    log.info('Network switched', { network: expectedNetwork.name });
    return true;
  } catch (error) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const err = error as any;

    // If network not added, try to add it
    if (err?.code === 4902) {
      log.debug('Network not found, adding it');
      return addNetwork(expectedNetwork);
    }

    log.error('Network switch failed', { error: err?.message });
    throw new WalletError(
      'UNKNOWN',
      `Failed to switch to ${expectedNetwork.name}: ${err?.message || 'Unknown error'}`
    );
  }
}

/**
 * Add a network to the wallet.
 *
 * @param network - Network configuration to add
 * @returns True if successful
 */
async function addNetwork(network: NetworkConfig): Promise<boolean> {
  try {
    const connector = await getConnector();
    const provider = connector.getProvider();

    await provider.request({
      method: 'wallet_addEthereumChain',
      params: [
        {
          chainId: network.chainIdHex,
          chainName: network.name,
          rpcUrls: [network.rpcUrl],
          blockExplorerUrls: [network.explorerUrl],
          nativeCurrency: network.nativeCurrency,
        },
      ],
    });

    return true;
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    throw new WalletError('UNKNOWN', `Failed to add network: ${errorMessage}`);
  }
}

/**
 * Subscribe to chain changes.
 *
 * @param callback - Called when chain changes with new chain ID
 * @returns Unsubscribe function
 */
export function onChainChange(callback: (chainId: number) => void): () => void {
  if (typeof window === 'undefined') return () => {};

  const ronin = (
    window as unknown as {
      ronin?: {
        provider?: {
          on: (event: string, cb: (chainIdHex: string) => void) => void;
          removeListener: (event: string, cb: (chainIdHex: string) => void) => void;
        };
      };
    }
  ).ronin;
  if (!ronin?.provider) return () => {};

  const handler = (chainIdHex: string) => {
    callback(parseInt(chainIdHex, 16));
  };

  ronin.provider.on('chainChanged', handler);

  return () => {
    ronin?.provider?.removeListener('chainChanged', handler);
  };
}
