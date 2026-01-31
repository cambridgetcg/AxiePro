/**
 * Market API functions.
 *
 * Provides typed functions for all market endpoints including analytics.
 */
import { apiClient } from './client';
import type {
  MarketStatsResponse,
  SalesResponse,
  ListingsResponse,
  FloorPricesByClassResponse,
  SalesParams,
  ListingsParams,
  MarketSummaryResponse,
  AnalyticsFloorPricesResponse,
  PriceHistoryResponse,
  ClassPriceHistoryResponse,
  RecentSalesResponse,
  SalesActivityResponse,
  ClassSalesResponse,
  HourlySalesResponse,
  RecentSalesParams,
  SalesActivityParams,
} from '@/types/market';

/**
 * Build URL search params from an object, filtering out undefined values.
 */
function buildSearchParams(params: object): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) {
      // Convert camelCase to snake_case for API
      const snakeKey = key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`);
      searchParams.set(snakeKey, String(value));
    }
  }
  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

export const marketApi = {
  /**
   * Get market statistics for 24h, 7d, and 30d periods.
   * GET /market/stats
   */
  getStats: (useCache = true): Promise<MarketStatsResponse> =>
    apiClient(`/market/stats?use_cache=${useCache}`),

  /**
   * Get historical sales with optional filters.
   * GET /market/sales
   */
  getSales: (params?: SalesParams): Promise<SalesResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/market/sales${query}`);
  },

  /**
   * Get active marketplace listings with optional filters.
   * GET /market/listings
   */
  getListings: (params?: ListingsParams): Promise<ListingsResponse> => {
    const query = params ? buildSearchParams(params) : '';
    return apiClient(`/market/listings${query}`);
  },

  /**
   * Get current floor prices by Axie class.
   * GET /market/floor-prices
   */
  getFloorPricesByClass: (): Promise<FloorPricesByClassResponse> =>
    apiClient('/market/floor-prices'),

  // =========================================================================
  // Analytics Endpoints
  // =========================================================================

  /**
   * Get complete market summary for the analytics dashboard.
   * GET /market/analytics/summary
   */
  getSummary: (useCache = true): Promise<MarketSummaryResponse> =>
    apiClient(`/market/analytics/summary?use_cache=${useCache}`),

  /**
   * Get floor prices by class with 24h change.
   * GET /market/analytics/floor-prices
   */
  getAnalyticsFloorPrices: (useCache = true): Promise<AnalyticsFloorPricesResponse> =>
    apiClient(`/market/analytics/floor-prices?use_cache=${useCache}`),

  /**
   * Get price history time-series for a trait.
   * GET /market/analytics/price-history
   */
  getPriceHistory: (params: {
    traitKey: string;
    interval?: string;
    limit?: number;
    useCache?: boolean;
  }): Promise<PriceHistoryResponse> => {
    const searchParams = new URLSearchParams();
    searchParams.set('trait_key', params.traitKey);
    if (params.interval) searchParams.set('interval', params.interval);
    if (params.limit) searchParams.set('limit', String(params.limit));
    if (params.useCache !== undefined) searchParams.set('use_cache', String(params.useCache));
    return apiClient(`/market/analytics/price-history?${searchParams.toString()}`);
  },

  /**
   * Get price history for a specific Axie class.
   * GET /market/analytics/class-history/{class}
   */
  getClassPriceHistory: (
    axieClass: string,
    interval = '1h',
    limit = 100,
  ): Promise<ClassPriceHistoryResponse> =>
    apiClient(`/market/analytics/class-history/${axieClass}?interval=${interval}&limit=${limit}`),

  // =========================================================================
  // Sales Activity Endpoints
  // =========================================================================

  /**
   * Get recent sales with optional class filter.
   * GET /market/sales/recent
   */
  getRecentSales: (params?: RecentSalesParams): Promise<RecentSalesResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.hours) searchParams.set('hours', String(params.hours));
    if (params?.class) searchParams.set('class', params.class);
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.useCache !== undefined) searchParams.set('use_cache', String(params.useCache));
    const query = searchParams.toString();
    return apiClient(`/market/sales/recent${query ? `?${query}` : ''}`);
  },

  /**
   * Get aggregated sales activity statistics.
   * GET /market/sales/activity
   */
  getSalesActivity: (params?: SalesActivityParams): Promise<SalesActivityResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.hours) searchParams.set('hours', String(params.hours));
    if (params?.class) searchParams.set('class', params.class);
    if (params?.useCache !== undefined) searchParams.set('use_cache', String(params.useCache));
    const query = searchParams.toString();
    return apiClient(`/market/sales/activity${query ? `?${query}` : ''}`);
  },

  /**
   * Get detailed sales data for a specific class.
   * GET /market/sales/class/{class}
   */
  getClassSales: (
    axieClass: string,
    hours = 24,
    limit = 20,
    useCache = true,
  ): Promise<ClassSalesResponse> =>
    apiClient(`/market/sales/class/${axieClass}?hours=${hours}&limit=${limit}&use_cache=${useCache}`),

  /**
   * Get hourly sales distribution for time-series visualization.
   * GET /market/sales/hourly
   */
  getHourlySales: (hours = 24, useCache = true): Promise<HourlySalesResponse> =>
    apiClient(`/market/sales/hourly?hours=${hours}&use_cache=${useCache}`),
};
