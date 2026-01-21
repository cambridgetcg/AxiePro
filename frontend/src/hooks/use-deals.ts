'use client';

/**
 * React Query hooks for fetching deals and snipes.
 */
import { useQuery } from '@tanstack/react-query';
import { valuationApi } from '@/lib/api/valuation';
import { config } from '@/lib/config';
import type { DealsListResponse, AxieClass } from '@/types/valuation';

/**
 * Query key factory for deals.
 */
export const dealsKeys = {
  all: ['deals'] as const,
  live: (filters?: { class?: AxieClass; minScore?: number }) =>
    [...dealsKeys.all, 'live', filters] as const,
  snipes: () => [...dealsKeys.all, 'snipes'] as const,
};

/**
 * Hook to fetch live deals with optional filters.
 *
 * Auto-refreshes every 30 seconds for real-time updates.
 *
 * @param filters - Optional filters for class and minimum score
 * @returns Query result with deals list
 */
export function useDeals(filters?: { class?: AxieClass; minScore?: number }) {
  return useQuery<DealsListResponse>({
    queryKey: dealsKeys.live(filters),
    queryFn: () =>
      valuationApi.getLiveDeals({
        class: filters?.class,
        minScore: filters?.minScore,
      }),
    refetchInterval: config.dealsPollingInterval,
    refetchIntervalInBackground: false, // Don't poll when tab is inactive
  });
}

/**
 * Hook to fetch top snipe opportunities.
 *
 * @param limit - Maximum number of snipes to fetch (default 20)
 * @returns Query result with snipes list
 */
export function useSnipes(limit = 20) {
  return useQuery<DealsListResponse>({
    queryKey: dealsKeys.snipes(),
    queryFn: () => valuationApi.getSnipes({ limit }),
    refetchInterval: config.dealsPollingInterval,
    refetchIntervalInBackground: false,
  });
}
