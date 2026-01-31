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
  RecentSalesResponse,
  SalesActivityResponse,
  ClassSalesResponse,
  HourlySalesResponse,
  RecentSalesParams,
  SalesActivityParams,
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
  recentSales: (params?: RecentSalesParams) => [...marketKeys.all, 'recent-sales', params] as const,
  salesActivity: (params?: SalesActivityParams) => [...marketKeys.all, 'sales-activity', params] as const,
  classSales: (axieClass: string, hours?: number) => [...marketKeys.all, 'class-sales', axieClass, hours] as const,
  hourlySales: (hours?: number) => [...marketKeys.all, 'hourly-sales', hours] as const,
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

// =============================================================================
// Sales Activity Hooks
// =============================================================================

/**
 * Hook to fetch recent sales with optional class filter.
 * Optimized for dashboard display with Redis caching.
 */
export function useRecentSales(
  params?: RecentSalesParams,
  options?: { enabled?: boolean }
) {
  return useQuery<RecentSalesResponse>({
    queryKey: marketKeys.recentSales(params),
    queryFn: () => marketApi.getRecentSales(params),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}

/**
 * Hook to fetch aggregated sales activity statistics.
 */
export function useSalesActivity(
  params?: SalesActivityParams,
  options?: { enabled?: boolean }
) {
  return useQuery<SalesActivityResponse>({
    queryKey: marketKeys.salesActivity(params),
    queryFn: () => marketApi.getSalesActivity(params),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}

/**
 * Hook to fetch detailed sales data for a specific class.
 */
export function useClassSales(
  axieClass: string,
  hours = 24,
  options?: { enabled?: boolean; limit?: number }
) {
  return useQuery<ClassSalesResponse>({
    queryKey: marketKeys.classSales(axieClass, hours),
    queryFn: () => marketApi.getClassSales(axieClass, hours, options?.limit ?? 20),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}

/**
 * Hook to fetch hourly sales distribution for charts.
 */
export function useHourlySales(
  hours = 24,
  options?: { enabled?: boolean }
) {
  return useQuery<HourlySalesResponse>({
    queryKey: marketKeys.hourlySales(hours),
    queryFn: () => marketApi.getHourlySales(hours),
    enabled: options?.enabled ?? true,
    staleTime: config.defaultStaleTime,
  });
}
