'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  RefreshCw,
  Wallet,
  Search,
  AlertCircle,
  Info,
  Shield,
} from 'lucide-react';
import {
  PortfolioSummaryCard,
  HoldingsTable,
} from '@/components/portfolio';
import {
  usePortfolioSummary,
  usePortfolioHoldings,
  useRefreshPortfolio,
  useUpdateCostBasis,
} from '@/hooks/use-portfolio';
import { useWalletStore } from '@/stores/wallet-store';
import { cn } from '@/lib/utils';
import { isAddress } from 'viem';
import type { AcquisitionType } from '@/types/portfolio';

export default function PortfolioPage() {
  const [walletInput, setWalletInput] = useState('');
  const [activeWallet, setActiveWallet] = useState<string | null>(null);
  const [inputError, setInputError] = useState<string | null>(null);

  // Wallet store for auto-fill and authentication
  const {
    address: connectedAddress,
    isConnected,
    authToken,
    isAuthenticated,
    isOwnWallet,
    authenticate,
    isAuthenticating,
  } = useWalletStore();

  // Auto-fill and auto-load when wallet is connected
  useEffect(() => {
    if (connectedAddress && !activeWallet) {
      setWalletInput(connectedAddress);
      setActiveWallet(connectedAddress);
    }
  }, [connectedAddress, activeWallet]);

  // Determine edit permissions
  const canEdit = activeWallet ? isOwnWallet(activeWallet) : false;
  const needsAuth = activeWallet && isConnected && connectedAddress?.toLowerCase() === activeWallet.toLowerCase() && !isAuthenticated();
  const editDisabledReason = !isConnected
    ? 'Connect your wallet to edit'
    : activeWallet && connectedAddress?.toLowerCase() !== activeWallet.toLowerCase()
    ? 'You can only edit your own wallet'
    : !isAuthenticated()
    ? 'Sign in to edit cost basis'
    : undefined;

  // Fetch portfolio data
  const {
    data: summaryData,
    isLoading: summaryLoading,
    error: summaryError,
  } = usePortfolioSummary(activeWallet);

  const {
    data: holdingsData,
    isLoading: holdingsLoading,
    error: holdingsError,
  } = usePortfolioHoldings(activeWallet, {
    includeValuation: true,
    sortBy: 'unrealized_pnl',
    sortOrder: 'desc',
  });

  const refreshMutation = useRefreshPortfolio();
  const updateCostBasisMutation = useUpdateCostBasis();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInputError(null);

    const trimmed = walletInput.trim();
    if (!trimmed) {
      setInputError('Please enter a wallet address');
      return;
    }

    // Validate Ethereum address
    if (!isAddress(trimmed)) {
      setInputError('Invalid Ethereum address');
      return;
    }

    setActiveWallet(trimmed.toLowerCase());
  };

  const handleRefresh = () => {
    if (activeWallet) {
      refreshMutation.mutate(activeWallet);
    }
  };

  const handleUpdateCostBasis = (
    axieId: number,
    costBasisEth: number,
    acquisitionType?: AcquisitionType
  ) => {
    if (activeWallet && authToken) {
      updateCostBasisMutation.mutate({
        address: activeWallet,
        axieId,
        costBasisEth,
        acquisitionType,
        authToken,
      });
    }
  };

  const isLoading = summaryLoading || holdingsLoading;
  const hasError = summaryError || holdingsError;

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-2">
              <Wallet className="h-8 w-8 text-primary" />
              Portfolio P&L
            </h1>
            <p className="text-muted-foreground">
              Track your unrealized gains and losses across your Axie holdings
            </p>
          </div>

          {activeWallet && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={refreshMutation.isPending}
              >
                <RefreshCw
                  className={cn(
                    'h-4 w-4 mr-1',
                    refreshMutation.isPending && 'animate-spin'
                  )}
                />
                Refresh Valuations
              </Button>
            </div>
          )}
        </div>

        {/* Wallet Input */}
        <form onSubmit={handleSubmit} className="flex gap-2 max-w-xl">
          <div className="flex-1">
            <Input
              type="text"
              placeholder="Enter wallet address (0x...)"
              value={walletInput}
              onChange={(e) => {
                setWalletInput(e.target.value);
                setInputError(null);
              }}
              className={cn(inputError && 'border-red-500')}
            />
            {inputError && (
              <p className="text-sm text-red-500 mt-1">{inputError}</p>
            )}
          </div>
          <Button type="submit" disabled={isLoading}>
            <Search className="h-4 w-4 mr-1" />
            View Portfolio
          </Button>
        </form>

        {/* Info Alert */}
        {!activeWallet && (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertTitle>How it works</AlertTitle>
            <AlertDescription>
              <ul className="list-disc list-inside space-y-1 mt-2 text-sm">
                <li>Enter any wallet address to view its Axie holdings</li>
                <li>See current market value based on ML valuations</li>
                <li>Track unrealized P&L by setting acquisition costs</li>
                <li>Supports purchases, breeds, and gifts/airdrops</li>
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {/* Error State */}
        {hasError && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Error loading portfolio</AlertTitle>
            <AlertDescription>
              {(summaryError as Error)?.message ||
                (holdingsError as Error)?.message ||
                'Failed to load portfolio data. Please try again.'}
            </AlertDescription>
          </Alert>
        )}

        {/* Portfolio Content */}
        {activeWallet && (
          <>
            {/* Summary */}
            <PortfolioSummaryCard
              summary={summaryData?.data}
              isLoading={summaryLoading}
            />

            {/* Cost Basis Warning */}
            {summaryData?.data &&
              holdingsData?.data?.some((h) => !h.has_cost_basis) && (
                <Alert className="border-yellow-500/50 bg-yellow-500/5">
                  <AlertCircle className="h-4 w-4 text-yellow-600" />
                  <AlertTitle className="text-yellow-600">
                    Incomplete Cost Basis Data
                  </AlertTitle>
                  <AlertDescription>
                    Some holdings are missing acquisition costs. Click the edit
                    button on each holding to set the cost basis for accurate
                    P&L tracking.
                  </AlertDescription>
                </Alert>
              )}

            {/* Authentication Prompt */}
            {needsAuth && (
              <Alert className="border-primary/50 bg-primary/5">
                <Shield className="h-4 w-4 text-primary" />
                <AlertTitle className="text-primary">
                  Sign to Edit Cost Basis
                </AlertTitle>
                <AlertDescription className="flex items-center justify-between">
                  <span>
                    Sign a message with your wallet to authenticate and enable cost basis editing.
                  </span>
                  <Button
                    size="sm"
                    onClick={authenticate}
                    disabled={isAuthenticating}
                    className="ml-4"
                  >
                    {isAuthenticating ? 'Signing...' : 'Sign to Authenticate'}
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Holdings Table */}
            <HoldingsTable
              holdings={holdingsData?.data}
              isLoading={holdingsLoading}
              onUpdateCostBasis={handleUpdateCostBasis}
              canEdit={canEdit}
              editDisabledReason={editDisabledReason}
            />

            {/* Pagination Info */}
            {holdingsData?.meta && (
              <div className="flex items-center justify-between text-sm text-muted-foreground">
                <span>
                  Showing {holdingsData.data.length} of{' '}
                  {holdingsData.meta.total} holdings
                </span>
                <Badge variant="outline">
                  Page {holdingsData.meta.page} of{' '}
                  {holdingsData.meta.total_pages}
                </Badge>
              </div>
            )}
          </>
        )}

        {/* Methodology Info */}
        <section className="text-center py-4 border-t">
          <p className="text-xs text-muted-foreground">
            Current values are estimated using ML-based hedonic pricing models.
            <br />
            Actual sale prices may vary based on market conditions and buyer demand.
          </p>
        </section>
      </div>
    </div>
  );
}
