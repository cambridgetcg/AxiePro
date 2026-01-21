"use client";

import { Copy, LogOut, ExternalLink, Shield, CheckCircle, Loader2 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useWalletStore } from "@/stores/wallet-store";
import { useState, useCallback } from "react";
import { getExplorerAddressUrl, getCurrentNetwork, isTestnet } from "@/lib/wallet/network";

interface WalletDropdownProps {
  address: string;
  children: React.ReactNode;
}

/**
 * Dropdown menu for connected wallet.
 */
export function WalletDropdown({ address, children }: WalletDropdownProps) {
  const { disconnect, authenticate, isAuthenticated, isAuthenticating } = useWalletStore();
  const [copied, setCopied] = useState(false);

  const copyAddress = useCallback(async () => {
    await navigator.clipboard.writeText(address);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [address]);

  const openExplorer = useCallback(() => {
    // Use network-specific explorer URL
    window.open(getExplorerAddressUrl(address), "_blank");
  }, [address]);

  const network = getCurrentNetwork();

  const isAuth = isAuthenticated();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium">Connected Wallet</p>
              {isTestnet() && (
                <span className="text-xs px-1.5 py-0.5 bg-yellow-500/20 text-yellow-500 rounded">
                  {network.name}
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground font-mono">
              {address.slice(0, 10)}...{address.slice(-8)}
            </p>
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />

        {/* Copy address */}
        <DropdownMenuItem onClick={copyAddress}>
          {copied ? (
            <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
          ) : (
            <Copy className="h-4 w-4 mr-2" />
          )}
          {copied ? "Copied!" : "Copy Address"}
        </DropdownMenuItem>

        {/* View on explorer */}
        <DropdownMenuItem onClick={openExplorer}>
          <ExternalLink className="h-4 w-4 mr-2" />
          View on Explorer
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        {/* Authentication status / action */}
        {isAuth ? (
          <DropdownMenuItem disabled className="text-green-600">
            <Shield className="h-4 w-4 mr-2" />
            Authenticated
          </DropdownMenuItem>
        ) : (
          <DropdownMenuItem onClick={authenticate} disabled={isAuthenticating}>
            {isAuthenticating ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Shield className="h-4 w-4 mr-2" />
            )}
            {isAuthenticating ? "Signing..." : "Sign to Authenticate"}
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        {/* Disconnect */}
        <DropdownMenuItem onClick={disconnect} className="text-red-600">
          <LogOut className="h-4 w-4 mr-2" />
          Disconnect
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
