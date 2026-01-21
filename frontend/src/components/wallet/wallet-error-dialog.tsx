"use client";

import { AlertCircle, ExternalLink, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { WalletErrorCode } from "@/lib/wallet/ronin-connector";

interface WalletErrorDialogProps {
  error: {
    code: WalletErrorCode;
    message: string;
  } | null;
  onClose: () => void;
}

const errorConfig: Record<
  WalletErrorCode,
  {
    title: string;
    action?: {
      label: string;
      onClick: () => void;
    };
  }
> = {
  NOT_INSTALLED: {
    title: "Ronin Wallet Not Found",
    action: {
      label: "Install Ronin Wallet",
      onClick: () => window.open("https://wallet.roninchain.com/", "_blank"),
    },
  },
  CONNECTION_REJECTED: {
    title: "Connection Rejected",
  },
  SIGNATURE_REJECTED: {
    title: "Signature Rejected",
  },
  DISCONNECTED: {
    title: "Wallet Disconnected",
  },
  UNKNOWN: {
    title: "Connection Error",
  },
};

/**
 * Error dialog for wallet connection issues.
 */
export function WalletErrorDialog({ error, onClose }: WalletErrorDialogProps) {
  if (!error) return null;

  const config = errorConfig[error.code];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Dialog */}
      <div className="relative bg-background border rounded-lg shadow-lg w-full max-w-md mx-4 p-6">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>

        {/* Content */}
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 p-2 bg-red-100 dark:bg-red-900/20 rounded-full">
            <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold">{config.title}</h3>
            <p className="text-sm text-muted-foreground mt-1">{error.message}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 mt-6 justify-end">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {config.action && (
            <Button onClick={config.action.onClick}>
              {config.action.label}
              {error.code === "NOT_INSTALLED" && (
                <ExternalLink className="h-4 w-4 ml-2" />
              )}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
