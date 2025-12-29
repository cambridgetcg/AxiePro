/**
 * Market API functions.
 *
 * Provides typed functions for all market endpoints.
 */
import { apiClient } from './client';
import type {
  MarketStatsResponse,
  SalesResponse,
  ListingsResponse,
  FloorPricesByClassResponse,
  SalesParams,
  ListingsParams,
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
  getStats: (): Promise<MarketStatsResponse> =>
    apiClient('/market/stats'),

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
};
