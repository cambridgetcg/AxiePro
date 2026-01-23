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
  sales_count: number;
  unique_buyers: number;
  unique_sellers: number;
  avg_price_eth: number;
  median_price_eth: number;
  floor_price_eth: number | null;
  max_price_eth?: number | null;
  active_listings?: number;
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
  cached?: boolean;
}

/**
 * Floor price with 24h change for a class.
 */
export interface FloorPriceWithChange {
  class_: string;
  floor_eth: number;
  count: number;
  change_24h: number | null;
}

/**
 * Price point in time-series data.
 */
export interface PricePoint {
  time: string;
  floor_eth: number | null;
  avg_eth: number | null;
  volume: number;
  listings_count: number;
}

/**
 * Market summary combining stats, floors, and trends.
 */
export interface MarketSummary {
  stats: {
    '24h': MarketStats;
    '7d': MarketStats;
    '30d': MarketStats;
  };
  floor_prices: FloorPriceWithChange[];
  trends: {
    volume_trend_24h: number | null;
  };
  computed_at: string;
}

/**
 * Market summary response from GET /market/analytics/summary
 */
export interface MarketSummaryResponse {
  success: boolean;
  data: MarketSummary;
}

/**
 * Analytics floor prices response from GET /market/analytics/floor-prices
 */
export interface AnalyticsFloorPricesResponse {
  success: boolean;
  data: {
    timestamp: string;
    floors: FloorPriceWithChange[];
  };
}

/**
 * Price history response from GET /market/analytics/price-history
 */
export interface PriceHistoryResponse {
  success: boolean;
  data: {
    trait_key: string;
    interval: string;
    points: PricePoint[];
  };
}

/**
 * Class price history response from GET /market/analytics/class-history/{class}
 */
export interface ClassPriceHistoryResponse {
  success: boolean;
  data: {
    class: string;
    interval: string;
    points: PricePoint[];
  };
}

/**
 * Individual sale record from /market/sales endpoint.
 */
export interface Sale {
  id: number;
  axie_id: number;
  seller: string;
  buyer: string;
  price_eth: number;
  price_usd: number | null;
  sold_at: string;
  tx_hash: string;
  axie?: {
    class: string;
    purity: number;
  };
}

/**
 * Recent sale record from /market/sales/recent endpoint.
 */
export interface RecentSale {
  id: number;
  axie_id: number;
  class_: string;
  price_eth: number;
  price_usd: number | null;
  seller_address: string;
  buyer_address: string;
  tx_hash: string;
  sold_at: string;
  marketplace: string;
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

// =============================================================================
// Sales Activity Types
// =============================================================================

/**
 * Recent sales response from GET /market/sales/recent
 */
export interface RecentSalesResponse {
  success: boolean;
  data: RecentSale[];
  meta: {
    hours: number;
    class_filter: string | null;
    count: number;
    source: 'cache' | 'database';
    timestamp: string;
  };
}

/**
 * Class sales breakdown for activity stats.
 */
export interface ClassSalesBreakdown {
  sales_count: number;
  volume_eth: number;
  avg_price_eth: number;
}

/**
 * Sales activity statistics.
 */
export interface SalesActivity {
  period_hours: number;
  total_sales: number;
  total_volume_eth: number;
  avg_price_eth: number;
  median_price_eth: number;
  min_price_eth: number | null;
  max_price_eth: number | null;
  unique_buyers: number;
  unique_sellers: number;
  sales_per_hour: number;
  by_class: Record<string, ClassSalesBreakdown>;
}

/**
 * Sales activity response from GET /market/sales/activity
 */
export interface SalesActivityResponse {
  success: boolean;
  data: SalesActivity;
  meta: {
    hours: number;
    class_filter: string | null;
    source: 'cache' | 'database';
    timestamp: string;
  };
}

/**
 * Class-specific sales data.
 */
export interface ClassSales {
  class_: string;
  period_hours: number;
  total_sales: number;
  total_volume_eth: number;
  avg_price_eth: number;
  recent_sales: RecentSale[];
}

/**
 * Class sales response from GET /market/sales/class/{class}
 */
export interface ClassSalesResponse {
  success: boolean;
  data: ClassSales;
  meta: {
    class: string;
    hours: number;
    source: 'cache' | 'database';
    timestamp: string;
  };
}

/**
 * Hourly sales distribution point for time-series.
 */
export interface HourlySalesPoint {
  hour: string;
  sales_count: number;
  volume_eth: number;
  avg_price_eth: number;
}

/**
 * Hourly sales distribution response from GET /market/sales/hourly
 */
export interface HourlySalesResponse {
  success: boolean;
  data: {
    hours: number;
    distribution: HourlySalesPoint[];
  };
  meta: {
    source: 'cache' | 'database';
    timestamp: string;
  };
}

/**
 * Parameters for fetching recent sales.
 */
export interface RecentSalesParams {
  hours?: number;
  class?: string;
  limit?: number;
  useCache?: boolean;
}

/**
 * Parameters for fetching sales activity.
 */
export interface SalesActivityParams {
  hours?: number;
  class?: string;
  useCache?: boolean;
}
