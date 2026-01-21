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
    // Ronin explorer URL
    window.open(`https://app.roninchain.com/address/${address}`, "_blank");
  }, [address]);

  const isAuth = isAuthenticated();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium">Connected Wallet</p>
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
