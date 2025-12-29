'use client';

/**
 * React Query hooks for market data.
 */
import { useQuery } from '@tanstack/react-query';
import { marketApi } from '@/lib/api/market';
import { config } from '@/lib/config';
import type {
  MarketStatsResponse,
  SalesResponse,
  ListingsResponse,
  FloorPricesByClassResponse,
  SalesParams,
  ListingsParams,
} from '@/types/market';

/**
 * Query key factory for market data.
 */
export const marketKeys = {
  all: ['market'] as const,
  stats: () => [...marketKeys.all, 'stats'] as const,
  sales: (params?: SalesParams) => [...marketKeys.all, 'sales', params] as const,
  listings: (params?: ListingsParams) => [...marketKeys.all, 'listings', params] as const,
  floorPrices: () => [...marketKeys.all, 'floor-prices'] as const,
};

/**
 * Hook to fetch market statistics (24h, 7d, 30d).
 */
export function useMarketStats(options?: { enabled?: boolean }) {
  return useQuery<MarketStatsResponse>({
    queryKey: marketKeys.stats(),
    queryFn: () => marketApi.getStats(),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime, // 1 minute
  });
}

/**
 * Hook to fetch historical sales with optional filters.
 */
export function useSales(
  params?: SalesParams,
  options?: { enabled?: boolean }
) {
  return useQuery<SalesResponse>({
    queryKey: marketKeys.sales(params),
    queryFn: () => marketApi.getSales(params),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}

/**
 * Hook to fetch active listings with optional filters.
 */
export function useListings(
  params?: ListingsParams,
  options?: { enabled?: boolean }
) {
  return useQuery<ListingsResponse>({
    queryKey: marketKeys.listings(params),
    queryFn: () => marketApi.getListings(params),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}

/**
 * Hook to fetch floor prices by class.
 */
export function useFloorPricesByClass(options?: { enabled?: boolean }) {
  return useQuery<FloorPricesByClassResponse>({
    queryKey: marketKeys.floorPrices(),
    queryFn: () => marketApi.getFloorPricesByClass(),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}
