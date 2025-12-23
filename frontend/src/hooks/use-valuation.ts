'use client';

/**
 * React Query hook for fetching single Axie valuation.
 */
import { useQuery } from '@tanstack/react-query';
import { valuationApi } from '@/lib/api/valuation';
import { config } from '@/lib/config';
import type { ValuationResponse } from '@/types/valuation';

/**
 * Query key factory for valuations.
 */
export const valuationKeys = {
  all: ['valuation'] as const,
  detail: (axieId: number) => [...valuationKeys.all, axieId] as const,
};

/**
 * Hook to fetch valuation for a single Axie.
 *
 * @param axieId - The Axie ID to fetch valuation for
 * @param options - Query options
 * @returns Query result with valuation data
 */
export function useValuation(
  axieId: number | null,
  options?: {
    enabled?: boolean;
    useCache?: boolean;
  }
) {
  return useQuery<ValuationResponse>({
    queryKey: valuationKeys.detail(axieId!),
    queryFn: () => valuationApi.getValuation(axieId!, options?.useCache ?? true),
    enabled: !!axieId && (options?.enabled ?? true),
    staleTime: config.valuationStaleTime,
  });
}
