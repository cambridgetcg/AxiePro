'use client';

/**
 * React Query hooks for fetching portfolio P&L data.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { portfolioApi } from '@/lib/api/portfolio';
import { config } from '@/lib/config';
import type {
  PortfolioSummaryResponse,
  PortfolioHoldingsResponse,
  AcquisitionType,
} from '@/types/portfolio';

/**
 * Query key factory for portfolio.
 */
export const portfolioKeys = {
  all: ['portfolio'] as const,
  summary: (address: string) => [...portfolioKeys.all, 'summary', address.toLowerCase()] as const,
  holdings: (
    address: string,
    filters?: { sortBy?: string; sortOrder?: string; page?: number }
  ) => [...portfolioKeys.all, 'holdings', address.toLowerCase(), filters] as const,
};

/**
 * Hook to fetch portfolio P&L summary.
 *
 * @param address - Wallet address
 * @param options - Query options
 * @returns Query result with portfolio summary
 */
export function usePortfolioSummary(
  address: string | null,
  options?: { enabled?: boolean }
) {
  return useQuery<PortfolioSummaryResponse>({
    queryKey: portfolioKeys.summary(address || ''),
    queryFn: () => portfolioApi.getSummary(address!),
    staleTime: config.valuationStaleTime,
    enabled: !!address && (options?.enabled ?? true),
  });
}

/**
 * Hook to fetch portfolio holdings with P&L.
 *
 * @param address - Wallet address
 * @param params - Query parameters
 * @returns Query result with holdings list
 */
export function usePortfolioHoldings(
  address: string | null,
  params?: {
    includeValuation?: boolean;
    onlyWithPnl?: boolean;
    sortBy?: 'unrealized_pnl' | 'cost_basis' | 'current_value' | 'acquired_at';
    sortOrder?: 'asc' | 'desc';
    page?: number;
    perPage?: number;
  }
) {
  return useQuery<PortfolioHoldingsResponse>({
    queryKey: portfolioKeys.holdings(address || '', {
      sortBy: params?.sortBy,
      sortOrder: params?.sortOrder,
      page: params?.page,
    }),
    queryFn: () => portfolioApi.getHoldings(address!, params),
    staleTime: config.valuationStaleTime,
    enabled: !!address,
  });
}

/**
 * Hook to refresh portfolio valuations.
 *
 * @returns Mutation for refreshing valuations
 */
export function useRefreshPortfolio() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (address: string) => portfolioApi.refreshValuations(address),
    onSuccess: (_, address) => {
      // Invalidate portfolio queries to refetch with new valuations
      queryClient.invalidateQueries({
        queryKey: portfolioKeys.summary(address),
      });
      queryClient.invalidateQueries({
        queryKey: ['portfolio', 'holdings', address.toLowerCase()],
      });
    },
  });
}

/**
 * Hook to update cost basis for a holding.
 *
 * Requires authentication - the auth token must be for the same wallet.
 *
 * @returns Mutation for updating cost basis
 */
export function useUpdateCostBasis() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      address,
      axieId,
      costBasisEth,
      acquisitionType,
      acquiredAt,
      authToken,
    }: {
      address: string;
      axieId: number;
      costBasisEth: number;
      acquisitionType?: AcquisitionType;
      acquiredAt?: string;
      authToken: string;
    }) =>
      portfolioApi.updateCostBasis(
        address,
        axieId,
        {
          costBasisEth,
          acquisitionType,
          acquiredAt,
        },
        authToken
      ),
    onSuccess: (_, variables) => {
      // Invalidate portfolio queries
      queryClient.invalidateQueries({
        queryKey: portfolioKeys.summary(variables.address),
      });
      queryClient.invalidateQueries({
        queryKey: ['portfolio', 'holdings', variables.address.toLowerCase()],
      });
    },
  });
}
