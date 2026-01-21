"use client";

import { useEffect } from "react";
import { Wallet, Loader2, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWalletStore } from "@/stores/wallet-store";
import { WalletDropdown } from "./wallet-dropdown";
import { WalletErrorDialog } from "./wallet-error-dialog";

interface WalletButtonProps {
  className?: string;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
  showFullAddress?: boolean;
}

/**
 * Wallet connection button with dropdown when connected.
 */
export function WalletButton({
  className,
  variant = "outline",
  size = "sm",
  showFullAddress = false,
}: WalletButtonProps) {
  const {
    address,
    isConnected,
    isConnecting,
    error,
    connect,
    checkConnection,
    clearError,
  } = useWalletStore();

  // Check for existing connection on mount
  useEffect(() => {
    checkConnection();
  }, [checkConnection]);

  // Disconnected state - show connect button
  if (!isConnected || !address) {
    return (
      <>
        <Button
          variant={variant}
          size={size}
          className={className}
          onClick={connect}
          disabled={isConnecting}
        >
          {isConnecting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="hidden sm:inline ml-2">Connecting...</span>
            </>
          ) : (
            <>
              <Wallet className="h-4 w-4" />
              <span className="hidden sm:inline ml-2">Connect Wallet</span>
            </>
          )}
        </Button>

        {/* Error dialog */}
        <WalletErrorDialog error={error} onClose={clearError} />
      </>
    );
  }

  // Connected state - show dropdown
  const displayAddress = showFullAddress
    ? address
    : `${address.slice(0, 6)}...${address.slice(-4)}`;

  return (
    <>
      <WalletDropdown address={address}>
        <Button variant={variant} size={size} className={className}>
          <Wallet className="h-4 w-4" />
          <span className="ml-2">{displayAddress}</span>
          <ChevronDown className="h-3 w-3 ml-1 opacity-50" />
        </Button>
      </WalletDropdown>

      {/* Error dialog */}
      <WalletErrorDialog error={error} onClose={clearError} />
    </>
  );
}
