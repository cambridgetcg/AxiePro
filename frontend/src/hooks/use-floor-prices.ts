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
 * @returns Query result with floor prices map
 */
export function useFloorPrices() {
  return useQuery<FloorPricesResponse>({
    queryKey: floorPricesKeys.all,
    queryFn: () => valuationApi.getFloorPrices(),
    staleTime: 5 * 60_000, // 5 minutes
  });
}
