/**
 * Ronin Network configuration for mainnet and testnet (Saigon).
 */

export type NetworkId = 'mainnet' | 'testnet';

export interface NetworkConfig {
  id: NetworkId;
  name: string;
  chainId: number;
  chainIdHex: string;
  rpcUrl: string;
  explorerUrl: string;
  nativeCurrency: {
    name: string;
    symbol: string;
    decimals: number;
  };
}

/**
 * Ronin Mainnet configuration.
 */
export const RONIN_MAINNET: NetworkConfig = {
  id: 'mainnet',
  name: 'Ronin',
  chainId: 2020,
  chainIdHex: '0x7e4',
  rpcUrl: 'https://api.roninchain.com/rpc',
  explorerUrl: 'https://app.roninchain.com',
  nativeCurrency: {
    name: 'RON',
    symbol: 'RON',
    decimals: 18,
  },
};

/**
 * Ronin Testnet (Saigon) configuration.
 */
export const RONIN_TESTNET: NetworkConfig = {
  id: 'testnet',
  name: 'Saigon Testnet',
  chainId: 2021,
  chainIdHex: '0x7e5',
  rpcUrl: 'https://saigon-testnet.roninchain.com/rpc',
  explorerUrl: 'https://saigon-app.roninchain.com',
  nativeCurrency: {
    name: 'RON',
    symbol: 'RON',
    decimals: 18,
  },
};

/**
 * Network configurations by ID.
 */
export const NETWORKS: Record<NetworkId, NetworkConfig> = {
  mainnet: RONIN_MAINNET,
  testnet: RONIN_TESTNET,
};

/**
 * Get the current network configuration based on environment.
 *
 * Set NEXT_PUBLIC_RONIN_NETWORK to 'testnet' to use Saigon testnet.
 * Defaults to mainnet in production.
 */
export function getCurrentNetwork(): NetworkConfig {
  const networkEnv = process.env.NEXT_PUBLIC_RONIN_NETWORK as NetworkId | undefined;

  if (networkEnv && NETWORKS[networkEnv]) {
    return NETWORKS[networkEnv];
  }

  // Default to mainnet
  return RONIN_MAINNET;
}

/**
 * Get the explorer URL for an address on the current network.
 */
export function getExplorerAddressUrl(address: string): string {
  const network = getCurrentNetwork();
  return `${network.explorerUrl}/address/${address}`;
}

/**
 * Get the explorer URL for a transaction on the current network.
 */
export function getExplorerTxUrl(txHash: string): string {
  const network = getCurrentNetwork();
  return `${network.explorerUrl}/tx/${txHash}`;
}

/**
 * Check if the current network is testnet.
 */
export function isTestnet(): boolean {
  return getCurrentNetwork().id === 'testnet';
}
