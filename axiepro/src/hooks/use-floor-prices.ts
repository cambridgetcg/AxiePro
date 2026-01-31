'use client';

/**
 * React Query hook for fetching floor prices by class.
 */
import { useQuery } from '@tanstack/react-query';
import { valuationApi } from '@/lib/api/valuation';
import type { FloorPricesResponse } from '@/types/valuation';

/**
 * Query key factory for floor prices.
 */
export const floorPricesKeys = {
  all: ['floorPrices'] as const,
};

/**
 * Hook to fetch current floor prices by class.
 *
 * Auto-refreshes every 60 seconds for near real-time updates.
 * Floor prices are updated by the backend every 5 minutes via
 * the price_ingestion pipeline.
 *
 * @returns Query result with floor prices map
 */
export function useFloorPrices() {
  return useQuery<FloorPricesResponse>({
    queryKey: floorPricesKeys.all,
    queryFn: () => valuationApi.getFloorPrices(),
    staleTime: 60_000, // 1 minute - consider data stale after 1 min
    refetchInterval: 60_000, // Auto-refresh every 60 seconds
    refetchIntervalInBackground: false, // Don't poll when tab is inactive
  });
}
