/**
 * TypeScript types for the market API.
 *
 * These types match the backend response schemas from
 * backend/src/api/routes/market.py
 */

import type { AxieClass } from './valuation';

/**
 * Market statistics for a time period.
 */
export interface MarketStats {
  volume_eth: number;
  volume_usd: number;
  sales_count: number;
  unique_buyers: number;
  unique_sellers: number;
  avg_price_eth: number;
  avg_price_usd: number;
  median_price_eth: number;
  floor_price_eth: number;
}

/**
 * Market stats response from GET /market/stats
 */
export interface MarketStatsResponse {
  success: boolean;
  data: {
    '24h': MarketStats;
    '7d': MarketStats;
    '30d': MarketStats;
  };
  meta: {
    timestamp: string;
  };
}

/**
 * Individual sale record.
 */
export interface Sale {
  tx_hash: string;
  axie_id: number;
  class: AxieClass;
  price_eth: number;
  price_usd: number;
  seller: string;
  buyer: string;
  timestamp: string;
  block_number: number;
}

/**
 * Sales list response from GET /market/sales
 */
export interface SalesResponse {
  success: boolean;
  data: Sale[];
  meta: {
    count: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}

/**
 * Active marketplace listing.
 */
export interface Listing {
  axie_id: number;
  class: AxieClass;
  price_eth: number;
  price_usd: number;
  seller: string;
  listed_at: string;
  purity: number;
  breed_count: number;
}

/**
 * Listings response from GET /market/listings
 */
export interface ListingsResponse {
  success: boolean;
  data: Listing[];
  meta: {
    count: number;
    page: number;
    per_page: number;
    total_pages: number;
  };
}

/**
 * Floor prices by class response from GET /market/floor-prices
 */
export interface FloorPricesByClassResponse {
  success: boolean;
  data: Record<AxieClass, number>;
  meta: {
    timestamp: string;
  };
}

/**
 * Parameters for fetching sales history.
 */
export interface SalesParams {
  class?: AxieClass;
  minPrice?: number;
  maxPrice?: number;
  fromDate?: string;
  toDate?: string;
  seller?: string;
  buyer?: string;
  page?: number;
  perPage?: number;
  sort?: 'price' | 'timestamp';
  order?: 'asc' | 'desc';
}

/**
 * Parameters for fetching listings.
 */
export interface ListingsParams {
  class?: AxieClass;
  minPrice?: number;
  maxPrice?: number;
  purity?: number;
  page?: number;
  perPage?: number;
  sort?: 'price' | 'listed_at';
  order?: 'asc' | 'desc';
}
