"use client";

import { AlertCircle, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
 * Uses Radix Dialog with Portal for proper z-index and stacking context handling.
 */
export function WalletErrorDialog({ error, onClose }: WalletErrorDialogProps) {
  const isOpen = error !== null;
  const config = error ? errorConfig[error.code] : null;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 p-2 bg-red-100 dark:bg-red-900/20 rounded-full">
              <AlertCircle className="h-6 w-6 text-red-600 dark:text-red-400" />
            </div>
            <div className="flex-1 min-w-0 pt-1">
              <DialogTitle>{config?.title || "Error"}</DialogTitle>
              <DialogDescription className="mt-1.5">
                {error?.message || "An unknown error occurred."}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <DialogFooter className="mt-2">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          {config?.action && (
            <Button onClick={config.action.onClick}>
              {config.action.label}
              {error?.code === "NOT_INSTALLED" && (
                <ExternalLink className="h-4 w-4 ml-2" />
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
