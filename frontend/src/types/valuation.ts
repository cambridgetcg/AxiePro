/**
 * TypeScript types for the valuation API.
 *
 * These types match the backend response schemas from
 * backend/src/api/routes/valuation.py
 */

/**
 * Axie class types.
 */
export type AxieClass =
  | 'beast'
  | 'bug'
  | 'bird'
  | 'plant'
  | 'aquatic'
  | 'reptile'
  | 'mech'
  | 'dawn'
  | 'dusk';

/**
 * All available Axie classes.
 */
export const AXIE_CLASSES: AxieClass[] = [
  'beast',
  'bug',
  'bird',
  'plant',
  'aquatic',
  'reptile',
  'mech',
  'dawn',
  'dusk',
];

/**
 * Valuation estimates with confidence intervals.
 */
export interface Valuation {
  hedonic_eth: number | null;
  ml_eth: number | null;
  ensemble_eth: number | null;
  confidence_lower_eth: number | null;
  confidence_upper_eth: number | null;
  confidence_score: number; // 0-1
}

/**
 * Market context for an Axie.
 */
export interface MarketContext {
  current_listing_eth: number | null;
  class_floor_eth: number | null;
  class_avg_eth: number | null;
}

/**
 * Deal analysis for an Axie.
 */
export interface DealAnalysis {
  discount_percent: number;
  z_score: number | null;
  deal_score: number; // 0-100
  is_deal: boolean;
  is_snipe: boolean;
}

/**
 * Valuation metadata.
 */
export interface ValuationMetadata {
  method: 'hedonic' | 'ensemble' | 'ml';
  model_version: string;
  computed_at: string; // ISO timestamp
}

/**
 * Full valuation response from GET /valuation/{axie_id}
 */
export interface ValuationResponse {
  axie_id: number;
  valuation: Valuation;
  market_context: MarketContext;
  deal_analysis: DealAnalysis;
  feature_contributions: Record<string, number>;
  metadata: ValuationMetadata;
}

/**
 * Batch valuation response from POST /valuation/batch
 */
export interface BatchValuationResponse {
  success: boolean;
  valuations: Array<ValuationResponse | { axie_id: number; error: string }>;
  meta: {
    requested: number;
    successful: number;
    cached: number;
  };
}

/**
 * Individual deal from deals list.
 */
export interface Deal {
  axie_id: number;
  class: string;
  listing_price_eth: number;
  fair_value_eth: number;
  discount_percent: number;
  z_score: number | null;
  deal_score: number;
  deal_type: 'deal' | 'snipe';
  marketplace_url: string;
  detected_at: string;
}

/**
 * Deals list response from GET /valuation/deals/live or /deals/snipes
 */
export interface DealsListResponse {
  success: boolean;
  data: Deal[];
  meta: {
    count: number;
    min_score?: number;
    class_filter?: string | null;
    timestamp: string;
  };
}

/**
 * Trait statistics response.
 */
export interface TraitStats {
  trait_key: string;
  trait_type: string;
  class: string | null;
  avg_price_eth: number | null;
  median_price_eth: number | null;
  std_dev_eth: number | null;
  sample_count: number;
  time_window_hours: number;
  computed_at: string;
}

/**
 * Trait stats response wrapper.
 */
export interface TraitStatsResponse {
  success: boolean;
  data: TraitStats;
}

/**
 * Floor prices response from GET /valuation/stats/floors
 */
export interface FloorPricesResponse {
  success: boolean;
  data: Record<string, number>; // class -> floor price in ETH
  meta: {
    source: 'cache' | 'computed';
  };
}

/**
 * Model info response from GET /valuation/model/info
 */
export interface ModelInfoResponse {
  success: boolean;
  data: {
    model_version?: string;
    r_squared?: number;
    adj_r_squared?: number;
    rmse?: number;
    sample_size?: number;
    feature_count?: number;
    train_start?: string;
    train_end?: string;
    trained_at?: string;
    status?: string;
    message?: string;
  };
}
